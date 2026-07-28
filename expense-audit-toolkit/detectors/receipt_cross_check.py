"""
OCR交叉验证模块
把票据OCR识别出的字段(金额/日期),跟员工申报的报销记录做比对,
找出"申报信息"和"票据实际内容"不一致的情况 —— 这是最直接的造假信号之一。

推荐用法(全自动,两步完成,不需要手写任何胶水代码):
    1. python ocr/batch_process.py 图片文件夹 receipts_result.csv
    2. from detectors.receipt_cross_check import cross_check_from_csv
       cross_check_from_csv("真实报销记录.csv", "receipts_result.csv")
"""

import pandas as pd


def cross_check_from_csv(expense_csv_path: str, ocr_result_csv_path: str, amount_tolerance: float = 1.0) -> pd.DataFrame:
    """
    expense_csv_path: 报销记录表,需包含 单号/人/金额/日期 列
    ocr_result_csv_path: ocr/batch_process.py 批量处理后生成的结果CSV,
                          已经自带 单号/金额/日期/商户 列,可以直接用
    """
    expense_df = pd.read_csv(expense_csv_path)
    ocr_df = pd.read_csv(ocr_result_csv_path)

    # 按单号合并两张表,只保留报销记录里有、但OCR结果里也存在的部分做金额/日期比对
    merged = expense_df.merge(
        ocr_df[["单号", "金额", "日期"]],
        on="单号", how="left", suffixes=("_申报", "_票据"),
    )

    all_flags = []
    for _, row in merged.iterrows():
        order_no = row["单号"]

        if pd.isna(row["金额_票据"]):
            all_flags.append({"人": row["人"], "单号": order_no, "异常类型": "缺失票据",
                               "详情": f"报销记录[{order_no}]在OCR结果中找不到对应票据"})
            continue

        diff = abs(row["金额_票据"] - row["金额_申报"])
        if diff > amount_tolerance:
            all_flags.append({"人": row["人"], "单号": order_no, "异常类型": "发票金额与申报金额不符",
                               "详情": f"申报{row['金额_申报']},票据识别{row['金额_票据']},相差{diff:.2f}"})

        if pd.notna(row.get("日期_票据")) and str(row["日期_票据"]) != str(row["日期_申报"]):
            all_flags.append({"人": row["人"], "单号": order_no, "异常类型": "发票日期与申报日期不符",
                               "详情": f"申报{row['日期_申报']},票据识别{row['日期_票据']}"})

    return pd.DataFrame(all_flags)


if __name__ == "__main__":
    # 用 data/ 目录下已经准备好的模拟CSV演示效果
    result = cross_check_from_csv("data/mock_receipt_expense.csv", "data/mock_receipt_ocr_result.csv")
    print("=" * 60)
    print("OCR交叉验证结果")
    print("=" * 60)
    print(result.to_string(index=False) if not result.empty else "全部一致,未发现问题")
