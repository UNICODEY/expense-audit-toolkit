import pandas as pd
import numpy as np
from datetime import datetime, timedelta

np.random.seed(42)

records = []
roles = {
    "销售": {"mean": 800, "std": 300, "n": 40},
    "研发": {"mean": 150, "std": 60, "n": 40},
    "行政": {"mean": 100, "std": 40, "n": 40},
}

person_id = 0
for role, params in roles.items():
    n_people = 5
    for p in range(n_people):
        person_id += 1
        person = f"{role}_员工{p+1}"
        n_records = params["n"] // n_people
        for i in range(n_records):
            amount = max(20, np.random.normal(params["mean"], params["std"]))
            date = datetime(2026, 1, 1) + timedelta(days=int(np.random.uniform(0, 150)))
            records.append({
                "人": person, "岗位": role, "金额": round(amount, 2),
                "日期": date.strftime("%Y-%m-%d"), "类型": "招待费"
            })

# ---- 刻意植入的异常case,用于验证检测逻辑 ----

# 异常1: "销售_员工1" 金额远超同组水平(统计离群点)
for i in range(3):
    date = datetime(2026, 3, 1) + timedelta(days=i * 10)
    records.append({
        "人": "销售_员工1", "岗位": "销售", "金额": round(np.random.uniform(4500, 5200), 2),
        "日期": date.strftime("%Y-%m-%d"), "类型": "招待费"
    })

# 异常2: "研发_员工3" 大量记录卡在审批阈值(假设阈值2000)下方
for i in range(6):
    date = datetime(2026, 2, 1) + timedelta(days=i * 7)
    records.append({
        "人": "研发_员工3", "岗位": "研发", "金额": round(np.random.uniform(1920, 1998), 2),
        "日期": date.strftime("%Y-%m-%d"), "类型": "招待费"
    })

# 异常3: "行政_员工2" 报销频率突然暴增(某月记录数远超其他月份/其他人)
for i in range(10):
    date = datetime(2026, 4, 1) + timedelta(days=i * 2)
    records.append({
        "人": "行政_员工2", "岗位": "行政", "金额": round(np.random.uniform(80, 150), 2),
        "日期": date.strftime("%Y-%m-%d"), "类型": "招待费"
    })

df = pd.DataFrame(records)
df.to_csv("/home/claude/expense-audit-toolkit/data/mock_expenses.csv", index=False, encoding="utf-8-sig")
print(f"生成了 {len(df)} 条模拟记录")
print(df.groupby("岗位")["金额"].describe())
