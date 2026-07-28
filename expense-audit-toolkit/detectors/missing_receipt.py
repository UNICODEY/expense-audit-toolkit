"""
缺失票据检测
有报销记录、但完全找不到对应票据图片(OCR结果里没有这个单号)的情况 —— 需要人工核实是否漏传票据,或者压根没有真实票据。
"""

import pandas as pd


def detect_missing_receipts(expense_records: pd.DataFrame, receipt_ocr_results: dict) -> pd.DataFrame:
    """
    expense_records: 需包含 单号/人 列
    receipt_ocr_results: {单号: ReceiptFields} 字典,是已经跑过OCR的票据结果
    """
    flags = []
    for _, row in expense_records.iterrows():
        order_no = row["单号"]
        if order_no not in receipt_ocr_results:
            flags.append({
                "人": row["人"],
                "单号": order_no,
                "异常类型": "缺失票据",
                "详情": f"报销记录[{order_no}]找不到对应的票据图片/OCR结果,需人工核实",
            })
    return pd.DataFrame(flags)


if __name__ == "__main__":
    mock_expense = pd.DataFrame([
        {"单号": "R001", "人": "销售_员工1"},
        {"单号": "R003", "人": "行政_员工1"},  # 这条没有票据
    ])
    mock_ocr_results = {"R001": object()}  # 只有 R001 有票据

    result = detect_missing_receipts(mock_expense, mock_ocr_results)
    print(result.to_string(index=False) if not result.empty else "未发现缺失票据")
