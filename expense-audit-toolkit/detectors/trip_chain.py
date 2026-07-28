"""
单号关联一致性检测模块
逻辑:同一"关联单号"下的记录,按时间排序后应构成连贯的行程链。
每条记录的"城市"代表"该时间段人所在/到达的城市"(与其他模块的语义一致)。

规则:如果相邻两条记录城市不同,且后一条记录不是"打车"/"高铁"这类交通类型,
说明城市变化找不到对应的交通记录来解释 -> 行程链断裂,标记可疑。
"""

import pandas as pd

TRANSPORT_SOURCES = {"打车", "高铁", "飞机"}


def normalize_city(city: str) -> str:
    if not isinstance(city, str):
        return city
    for suffix in ["市", "省"]:
        if city.endswith(suffix):
            city = city[: -len(suffix)]
    return city


def detect_broken_trip_chains(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["城市"] = df["城市原始"].apply(normalize_city)
    df["开始时间"] = pd.to_datetime(df["开始时间"])
    df["结束时间"] = pd.to_datetime(df["结束时间"])

    flags = []
    for order_no, group in df.groupby("关联单号"):
        events = group.sort_values("开始时间").to_dict("records")
        for i in range(1, len(events)):
            prev_event, cur_event = events[i - 1], events[i]
            if prev_event["城市"] == cur_event["城市"]:
                continue  # 城市没变化,不需要交通记录解释
            if cur_event["来源"] in TRANSPORT_SOURCES:
                continue  # 城市变化,且当前记录本身就是交通记录,合理
            # 城市变了,但当前记录不是交通类型 -> 链条断裂
            flags.append({
                "人": cur_event["人"],
                "异常类型": "行程链断裂",
                "详情": f"[单号{order_no}] {prev_event['来源']}显示在{prev_event['城市']}"
                        f"({prev_event['结束时间']}结束) -> {cur_event['来源']}显示在{cur_event['城市']}"
                        f"({cur_event['开始时间']}开始),中间无交通记录佐证如何到达",
            })
    return pd.DataFrame(flags)


if __name__ == "__main__":
    df = pd.read_csv("data/mock_linked_trips.csv")
    result = detect_broken_trip_chains(df)
    if result.empty:
        print("未发现行程链断裂")
    else:
        for _, row in result.iterrows():
            print(f"\n[{row['人']}] {row['异常类型']}")
            print(f"  {row['详情']}")
