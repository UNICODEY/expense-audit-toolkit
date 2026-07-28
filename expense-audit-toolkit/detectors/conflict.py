"""
时间-地点冲突检测模块(硬证据信号)
逻辑与之前 Excel 版本一致:同一人在时间重叠区间内出现在不同城市 -> 矛盾
"""

import pandas as pd


def normalize_city(city: str) -> str:
    if not isinstance(city, str):
        return city
    for suffix in ["市", "省"]:
        if city.endswith(suffix):
            city = city[: -len(suffix)]
    return city


def detect_time_location_conflicts(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["城市"] = df["城市原始"].apply(normalize_city)
    df["开始时间"] = pd.to_datetime(df["开始时间"])
    df["结束时间"] = pd.to_datetime(df["结束时间"])

    conflicts = []
    for person, group in df.groupby("人"):
        events = group.sort_values("开始时间").to_dict("records")
        for i in range(len(events)):
            for j in range(i + 1, len(events)):
                a, b = events[i], events[j]
                if a["城市"] == b["城市"]:
                    continue
                latest_start = max(a["开始时间"], b["开始时间"])
                earliest_end = min(a["结束时间"], b["结束时间"])
                if latest_start < earliest_end:
                    conflicts.append({
                        "人": person,
                        "异常类型": "时间-地点硬冲突",
                        "详情": f"{a['来源']}显示在{a['城市']}({a['开始时间']}~{a['结束时间']}) vs "
                                f"{b['来源']}显示在{b['城市']}({b['开始时间']}~{b['结束时间']})",
                    })
    return pd.DataFrame(conflicts)


if __name__ == "__main__":
    df = pd.read_csv("data/mock_travel_timeline.csv")
    result = detect_time_location_conflicts(df)
    print(result.to_string(index=False) if not result.empty else "未发现冲突")
