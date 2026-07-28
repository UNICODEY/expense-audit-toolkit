"""
进阶检测规则:
1. 结伴模式检测 —— 两人频繁在同一单号下共同出现,超出正常协作水平
2. 金额精确度异常检测 —— 金额小数位分布过于"工整"(比如总是整数),
   不符合真实消费的自然随机性,反而可能是刻意编造
"""

import pandas as pd
from itertools import combinations
from collections import Counter


def detect_co_occurrence_pattern(df: pd.DataFrame, min_co_occur: int = 4, min_ratio: float = 0.7) -> pd.DataFrame:
    """
    规则: 结伴模式检测
    统计每对人员在同一"关联单号"下共同出现的次数,
    如果共同出现次数达到阈值、且占其中一人总报销次数的比例过高,标记为可疑结伴模式。
    """
    order_people = df.groupby("关联单号")["人"].apply(set)
    person_total_orders = df.groupby("人")["关联单号"].nunique()

    pair_counts = Counter()
    for people in order_people:
        if len(people) < 2:
            continue
        for pair in combinations(sorted(people), 2):
            pair_counts[pair] += 1

    flags = []
    for (p1, p2), count in pair_counts.items():
        if count < min_co_occur:
            continue
        ratio1 = count / person_total_orders.get(p1, 1)
        ratio2 = count / person_total_orders.get(p2, 1)
        if max(ratio1, ratio2) >= min_ratio:
            for person in (p1, p2):
                flags.append({
                    "人": person,
                    "异常类型": "结伴报销模式异常",
                    "详情": f"与{p2 if person == p1 else p1}共同出现在{count}个关联单号中"
                            f"(占该人报销记录的{max(ratio1, ratio2):.0%})",
                })
    return pd.DataFrame(flags)


def detect_amount_precision_anomaly(df: pd.DataFrame, person_col: str = "人", amount_col: str = "金额",
                                     min_records: int = 5, roundness_thresh: float = 0.9) -> pd.DataFrame:
    """
    规则: 金额精确度异常检测(反向验证 —— "过于完美"的记录)
    真实消费金额通常带有随机的小数位(比如87.35、142.80)。
    如果某人的报销记录里,绝大多数金额都是整数或者"整十/整百",
    统计上不自然,可能是刻意编造的整数金额,而非真实消费凭证。
    """
    flags = []
    for person, group in df.groupby(person_col):
        if len(group) < min_records:
            continue
        amounts = group[amount_col]
        is_round = amounts.apply(lambda x: x == round(x))  # 是否为整数金额(无小数)
        round_ratio = is_round.mean()

        if round_ratio >= roundness_thresh:
            flags.append({
                "人": person,
                "异常类型": "金额精确度异常(疑似编造)",
                "详情": f"{len(group)}条记录中,{is_round.sum()}条为整数金额"
                        f"(占比{round_ratio:.0%}),真实消费金额通常不会如此规整",
            })
    return pd.DataFrame(flags)


if __name__ == "__main__":
    df = pd.read_csv("data/mock_advanced_patterns.csv")

    print("=" * 60)
    print("规则: 结伴报销模式检测")
    print("=" * 60)
    co_occur = detect_co_occurrence_pattern(df)
    print(co_occur.to_string(index=False) if not co_occur.empty else "未发现异常结伴模式")

    print("\n" + "=" * 60)
    print("规则: 金额精确度异常检测")
    print("=" * 60)
    precision = detect_amount_precision_anomaly(df)
    print(precision.to_string(index=False) if not precision.empty else "未发现精确度异常")
