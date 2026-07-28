"""
批量OCR处理脚本
遍历一个文件夹里的所有票据图片,自动识别+抽取字段,汇总成一份CSV表格。

约定:图片文件名就是对应的单号(比如 R001.jpg、R002.jpg),
这样处理完之后能直接按单号跟报销记录关联起来。如果你的图片命名方式不同,
改一下下面 order_no = image_path.stem 这一行的逻辑即可。

用法:
    python batch_process.py <图片文件夹路径> <输出csv路径>
"""

import sys
from pathlib import Path
import pandas as pd

from ocr_engine import ReceiptOCR
from field_extractor import extract_fields

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp"}


def batch_process(folder_path: str, output_csv: str):
    folder = Path(folder_path)
    if not folder.is_dir():
        print(f"错误: {folder_path} 不是一个有效的文件夹")
        sys.exit(1)

    image_paths = [p for p in folder.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS]
    if not image_paths:
        print(f"文件夹 {folder_path} 里没有找到图片文件")
        sys.exit(1)

    print(f"找到 {len(image_paths)} 张图片,开始批量识别...")
    ocr = ReceiptOCR()  # 只初始化一次,避免每张图片都重新加载模型(会很慢)

    results = []
    for i, image_path in enumerate(image_paths, 1):
        order_no = image_path.stem  # 文件名(不含后缀)作为单号
        print(f"[{i}/{len(image_paths)}] 处理: {image_path.name}")

        try:
            lines = ocr.extract_text(str(image_path))
            fields = extract_fields(lines)
            results.append({
                "单号": order_no,
                "文件名": image_path.name,
                "金额": fields.best_amount,
                "日期": fields.best_date,
                "商户": fields.merchant_candidates[0] if fields.merchant_candidates else None,
                "识别状态": "成功" if fields.best_amount is not None else "金额识别失败,需人工核实",
            })
        except Exception as e:
            results.append({
                "单号": order_no,
                "文件名": image_path.name,
                "金额": None,
                "日期": None,
                "商户": None,
                "识别状态": f"处理出错: {e}",
            })

    df = pd.DataFrame(results)
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"\n处理完成,结果已保存到 {output_csv}")
    success_count = (df["识别状态"] == "成功").sum()
    print(f"成功识别: {success_count}/{len(df)}")
    if success_count < len(df):
        print("以下记录需要人工核实:")
        print(df[df["识别状态"] != "成功"][["单号", "文件名", "识别状态"]].to_string(index=False))


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python batch_process.py <图片文件夹路径> <输出csv路径>")
        print("示例: python batch_process.py C:\\发票图片 receipts_result.csv")
        sys.exit(1)

    batch_process(sys.argv[1], sys.argv[2])
