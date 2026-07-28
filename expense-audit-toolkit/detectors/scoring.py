"""
评分聚合层
把各个检测器(硬冲突、统计异常等)的输出,按权重合并成一份"综合可疑度"排序清单。

设计原则:
- 硬证据(逻辑上直接矛盾)权重最高,因为可信度/确定性最强
- 统计信号权重较低,因为只是"不寻常",不是"确凿证据",需要人工判断
- 同一人被多个规则命中,分数累加 -> 自然排到复核清单前面
"""

import json
import os
import pandas as pd

# 权重从外部配置文件读取,方便调整而不需要改代码
_WEIGHTS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rule_weights.json")
with open(_WEIGHTS_PATH, "r", encoding="utf-8") as f:
    RULE_WEIGHTS = {k: v for k, v in json.load(f).items() if not k.startswith("_")}


def get_weight(anomaly_type: str) -> int:
    for key, weight in RULE_WEIGHTS.items():
        if anomaly_type.startswith(key):
            return weight
    return 1  # 未知规则类型,给最低权重,避免漏算


def aggregate_scores(*flagged_dfs: pd.DataFrame) -> pd.DataFrame:
    """
    输入: 多个检测器输出的 DataFrame,每个都必须包含 '人' 和 '异常类型' 两列
    输出: 按人汇总的评分表,按总分降序排列
    """
    all_flags = []
    for df in flagged_dfs:
        if df is None or df.empty:
            continue
        all_flags.append(df[["人", "异常类型"]])

    if not all_flags:
        return pd.DataFrame(columns=["人", "综合可疑分", "命中规则数", "命中的异常类型"])

    combined = pd.concat(all_flags, ignore_index=True)
    combined["权重"] = combined["异常类型"].apply(get_weight)

    summary = combined.groupby("人").agg(
        综合可疑分=("权重", "sum"),
        命中规则数=("异常类型", "count"),
        命中的异常类型=("异常类型", lambda x: " | ".join(sorted(set(x)))),
    ).reset_index()

    return summary.sort_values("综合可疑分", ascending=False).reset_index(drop=True)


if __name__ == "__main__":
    import sys
    sys.path.insert(0, ".")
    from detectors.conflict import detect_time_location_conflicts
    from detectors.statistical import detect_group_outliers, detect_threshold_clustering, detect_frequency_anomaly
    from detectors.trip_chain import detect_broken_trip_chains
    from detectors.advanced_patterns import detect_co_occurrence_pattern, detect_amount_precision_anomaly

    travel_df = pd.read_csv("data/mock_travel_timeline.csv")
    expense_df = pd.read_csv("data/mock_expenses.csv")
    linked_trip_df = pd.read_csv("data/mock_linked_trips.csv")
    advanced_df = pd.read_csv("data/mock_advanced_patterns.csv")

    conflicts = detect_time_location_conflicts(travel_df)
    outliers = detect_group_outliers(expense_df, group_col="岗位", value_col="金额")
    clustered = detect_threshold_clustering(expense_df, person_col="人", value_col="金额", threshold=2000)
    freq = detect_frequency_anomaly(expense_df, person_col="人", date_col="日期")
    broken_chains = detect_broken_trip_chains(linked_trip_df)
    co_occur = detect_co_occurrence_pattern(advanced_df)
    precision_anomaly = detect_amount_precision_anomaly(advanced_df)

    # OCR交叉验证 + 缺失票据检测:全自动版本,直接读两份CSV做比对
    # 实际使用时,把这两个路径换成: 真实报销记录.csv 和 ocr/batch_process.py 生成的结果csv
    from detectors.receipt_cross_check import cross_check_from_csv
    receipt_issues = cross_check_from_csv("data/mock_receipt_expense.csv", "data/mock_receipt_ocr_result.csv")

    result = aggregate_scores(
        conflicts, outliers, clustered, freq, broken_chains,
        receipt_issues, co_occur, precision_anomaly,
    )

    print("=" * 70)
    print("综合可疑度排序清单(建议审计员按此顺序优先复核)")
    print("=" * 70)
    print(result.to_string(index=False))
