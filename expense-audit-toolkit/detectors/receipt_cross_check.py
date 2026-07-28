"""
OCR交叉验证模块
把票据OCR识别出的字段(金额/日期/商户),跟员工申报的报销记录做比对,
找出"申报信息"和"票据实际内容"不一致的情况 —— 这是最直接的造假信号之一。
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from ocr.field_extractor import ReceiptFields


def cross_check_receipt(claimed_amount: float, claimed_date: str,
                         ocr_fields: ReceiptFields, amount_tolerance: float = 1.0) -> list[dict]:
    """
    对比"员工申报的报销记录"与"票据OCR识别出的实际内容"
    claimed_amount / claimed_date: 报销系统里员工申报的金额和日期
    ocr_fields: 从票据图片OCR识别+抽取出的字段

    返回: 发现的不一致项列表(可能为空,代表一致)
    """
    issues = []

    # 检查1: 金额是否一致(允许小额误差,应对OCR识别精度问题,不是允许作弊空间)
    if ocr_fields.best_amount is not None:
        diff = abs(ocr_fields.best_amount - claimed_amount)
        if diff > amount_tolerance:
            issues.append({
                "异常类型": "发票金额与申报金额不符",
                "详情": f"申报金额{claimed_amount},票据识别金额{ocr_fields.best_amount},相差{diff:.2f}",
            })
    else:
        issues.append({
            "异常类型": "票据金额识别失败",
            "详情": "OCR未能识别出票据上的金额,需要人工核实票据本身是否完整/清晰",
        })

    # 检查2: 日期是否一致
    if ocr_fields.best_date is not None:
        if ocr_fields.best_date != claimed_date:
            issues.append({
                "异常类型": "发票日期与申报日期不符",
                "详情": f"申报日期{claimed_date},票据识别日期{ocr_fields.best_date}",
            })
    else:
        issues.append({
            "异常类型": "票据日期识别失败",
            "详情": "OCR未能识别出票据上的日期,需要人工核实",
        })

    return issues


def batch_cross_check(expense_records: pd.DataFrame, receipt_ocr_results: dict) -> pd.DataFrame:
    """
    批量交叉验证。
    expense_records: 报销记录表,需包含 单号/人/金额/日期 列
    receipt_ocr_results: {单号: ReceiptFields} 的字典,是每张票据OCR处理后的结果

    实际使用时,你需要自己写一小段代码,把每张票据图片跑一遍 pipeline.py 里的
    process_receipt()函数,得到 ReceiptFields,再按单号存进这个字典里传进来。
    """
    all_flags = []
    for _, row in expense_records.iterrows():
        order_no = row["单号"]
        if order_no not in receipt_ocr_results:
            continue  # 这条记录没有对应的票据图片,跳过(可以另外做"缺失票据"检测)

        ocr_fields = receipt_ocr_results[order_no]
        issues = cross_check_receipt(row["金额"], row["日期"], ocr_fields)

        for issue in issues:
            all_flags.append({
                "人": row["人"],
                "单号": order_no,
                "异常类型": issue["异常类型"],
                "详情": issue["详情"],
            })

    return pd.DataFrame(all_flags)


if __name__ == "__main__":
    # 用模拟数据演示:一条金额一致,一条金额不一致
    from dataclasses import dataclass

    mock_expense_records = pd.DataFrame([
        {"单号": "R001", "人": "销售_员工1", "金额": 1580.00, "日期": "2026-02-12"},
        {"单号": "R002", "人": "研发_员工2", "金额": 1580.00, "日期": "2026-02-12"},
    ])

    # 模拟票据OCR结果: R001一致,R002金额被虚报(票据实际只有800,却申报了1580)
    mock_ocr_results = {
        "R001": ReceiptFields(amounts=[1564.36, 15.64, 1580.00], dates=["2026-02-12"],
                               merchant_candidates=["福州市台江区某餐厅"]),
        "R002": ReceiptFields(amounts=[790.0, 800.0], dates=["2026-02-12"],
                               merchant_candidates=["福州市某餐厅"]),
    }

    result = batch_cross_check(mock_expense_records, mock_ocr_results)
    print("=" * 60)
    print("OCR交叉验证结果")
    print("=" * 60)
    if result.empty:
        print("全部一致,未发现问题")
    else:
        print(result.to_string(index=False))
