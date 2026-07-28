"""
统计异常检测模块
与之前的"时间-地点冲突检测"是互补关系:
  - 冲突检测抓的是"逻辑上讲不通"的记录(硬证据)
  - 本模块抓的是"数字上不寻常"的记录(统计信号,需要人工复核判断,不是实锤)
"""

import pandas as pd
import numpy as np


def detect_group_outliers(df: pd.DataFrame, group_col: str, value_col: str, k: float = 1.5) -> pd.DataFrame:
    """
    规则A: 组内离群点检测(IQR方法,比标准差更抗极端值干扰)
    对每个分组(比如岗位),计算金额的四分位距,超出 Q3 + k*IQR 的记录标记为异常
    """
    results = []
    for group, sub in df.groupby(group_col):
        q1, q3 = sub[value_col].quantile([0.25, 0.75])
        iqr = q3 - q1
        upper_bound = q3 + k * iqr
        outliers = sub[sub[value_col] > upper_bound].copy()
        outliers["异常类型"] = "组内金额离群点"
        outliers["组内上界"] = round(upper_bound, 2)
        results.append(outliers)
    return pd.concat(results) if results else pd.DataFrame()


def detect_threshold_clustering(df: pd.DataFrame, person_col: str, value_col: str,
                                  threshold: float, window: float = 100, min_count: int = 4) -> pd.DataFrame:
    """
    规则B: 阈值卡点检测
    检查某人是否有异常多的记录,金额精确落在审批阈值下方一小段区间内
    (正常消费金额分布是连续的,不会不自然地密集卡在某条线附近)
    """
    near_threshold = df[(df[value_col] < threshold) & (df[value_col] >= threshold - window)]
    counts = near_threshold.groupby(person_col).size()
    flagged_people = counts[counts >= min_count].index.tolist()

    result = near_threshold[near_threshold[person_col].isin(flagged_people)].copy()
    result["异常类型"] = f"疑似卡阈值({threshold}以下{window}区间内异常密集)"
    return result


def detect_frequency_anomaly(df: pd.DataFrame, person_col: str, date_col: str, z_thresh: float = 2.0) -> pd.DataFrame:
    """
    规则C: 报销频率异常检测
    按月统计每人报销次数,与其他人的月度频率分布比较,找出明显偏高的月份
    """
    df = df.copy()
    df["月份"] = pd.to_datetime(df[date_col]).dt.to_period("M")
    monthly_counts = df.groupby([person_col, "月份"]).size().reset_index(name="当月记录数")

    mean = monthly_counts["当月记录数"].mean()
    std = monthly_counts["当月记录数"].std()
    monthly_counts["z分数"] = (monthly_counts["当月记录数"] - mean) / std

    flagged = monthly_counts[monthly_counts["z分数"] > z_thresh].copy()
    flagged["异常类型"] = "月度报销频率异常偏高"
    return flagged


def main():
    df = pd.read_csv("data/mock_expenses.csv")

    print("=" * 60)
    print("规则A: 组内金额离群点检测(按岗位分组,IQR方法)")
    print("=" * 60)
    outliers = detect_group_outliers(df, group_col="岗位", value_col="金额")
    if outliers.empty:
        print("未发现离群点")
    else:
        print(outliers[["人", "岗位", "金额", "日期", "组内上界"]].to_string(index=False))

    print("\n" + "=" * 60)
    print("规则B: 阈值卡点检测(假设审批阈值=2000)")
    print("=" * 60)
    clustered = detect_threshold_clustering(df, person_col="人", value_col="金额", threshold=2000)
    if clustered.empty:
        print("未发现阈值卡点模式")
    else:
        print(clustered[["人", "金额", "日期"]].to_string(index=False))
        print(f"\n涉及人员: {clustered['人'].unique().tolist()}")

    print("\n" + "=" * 60)
    print("规则C: 月度报销频率异常检测")
    print("=" * 60)
    freq_anomaly = detect_frequency_anomaly(df, person_col="人", date_col="日期")
    if freq_anomaly.empty:
        print("未发现频率异常")
    else:
        print(freq_anomaly[["人", "月份", "当月记录数", "z分数"]].to_string(index=False))


if __name__ == "__main__":
    main()
