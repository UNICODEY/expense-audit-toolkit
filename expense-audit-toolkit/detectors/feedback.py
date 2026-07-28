"""
权重调优反馈闭环
思路:审计员每次复核完一条被标记的记录,就记一笔"这条标记后来证实是真问题,还是误报"。
积累一段时间后,可以按规则统计"准确率"(有多少次标记后来被确认是真问题),
用这个数字反过来调整 rule_weights.json 里的权重 —— 准确率高的规则可以调高权重,
经常误报的规则调低权重甚至考虑砍掉。
"""

import pandas as pd
import os
import json

FEEDBACK_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "feedback_log.csv")


def log_feedback(人: str, 异常类型: str, 单号: str, 确认结果: str, 备注: str = ""):
    """
    记录一次复核反馈。
    确认结果 应该填: "确认问题" / "误报" / "无法判断"
    每次复核完一条记录,调用一次这个函数,追加写入本地日志文件。
    """
    entry = pd.DataFrame([{
        "人": 人, "异常类型": 异常类型, "单号": 单号,
        "确认结果": 确认结果, "备注": 备注,
        "记录时间": pd.Timestamp.now().strftime("%Y-%m-%d %H:%M:%S"),
    }])

    if os.path.exists(FEEDBACK_LOG_PATH):
        entry.to_csv(FEEDBACK_LOG_PATH, mode="a", header=False, index=False, encoding="utf-8-sig")
    else:
        entry.to_csv(FEEDBACK_LOG_PATH, index=False, encoding="utf-8-sig")

    print(f"已记录: [{异常类型}] {人} - {确认结果}")


def analyze_rule_accuracy() -> pd.DataFrame:
    """
    统计每条规则的历史准确率,给出权重调整建议。
    """
    if not os.path.exists(FEEDBACK_LOG_PATH):
        print("还没有任何反馈记录,先用 log_feedback() 积累数据")
        return pd.DataFrame()

    df = pd.read_csv(FEEDBACK_LOG_PATH)
    df = df[df["确认结果"].isin(["确认问题", "误报"])]  # "无法判断"的不纳入统计

    stats = df.groupby("异常类型")["确认结果"].apply(
        lambda x: (x == "确认问题").sum() / len(x)
    ).reset_index(name="准确率")
    stats["样本数"] = df.groupby("异常类型").size().values

    def suggest(row):
        if row["样本数"] < 5:
            return "样本太少,暂不建议调整"
        if row["准确率"] >= 0.7:
            return "准确率高,可考虑调高权重"
        if row["准确率"] <= 0.3:
            return "误报率高,可考虑调低权重或检查规则逻辑"
        return "维持现状"

    stats["建议"] = stats.apply(suggest, axis=1)
    return stats.sort_values("准确率", ascending=False)


if __name__ == "__main__":
    # 演示用法:模拟几条复核反馈记录
    log_feedback("研发_员工3", "疑似卡阈值(2000以下100区间内异常密集)", "TC001", "确认问题", "核实后确系拆分报销")
    log_feedback("行政_员工2", "月度报销频率异常偏高", "TA020", "误报", "该月确实出差频繁,属实")
    log_feedback("行政_员工2", "月度报销频率异常偏高", "TA021", "误报", "同上,出差密集期正常现象")

    print("\n当前反馈统计:")
    result = analyze_rule_accuracy()
    print(result.to_string(index=False) if not result.empty else "数据不足")
