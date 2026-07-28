"""
OCR流水线:输入一张票据图片,直接输出识别到的关键字段(金额/日期/商户名)
是 ocr_engine.py (图片->文字) 和 field_extractor.py (文字->结构化字段) 的串联
"""

import sys
from ocr_engine import ReceiptOCR
from field_extractor import extract_fields


def process_receipt(image_path: str):
    print(f"正在识别: {image_path}")
    ocr = ReceiptOCR()
    lines = ocr.extract_text(image_path)

    fields = extract_fields(lines)

    print("\n" + "=" * 40)
    print("核心信息")
    print("=" * 40)
    print(f"金额: {fields.best_amount}")
    print(f"日期: {fields.best_date}")
    print(f"商户: {fields.merchant_candidates[0] if fields.merchant_candidates else '未识别到'}")

    return fields


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python pipeline.py <图片路径>")
        sys.exit(1)

    process_receipt(sys.argv[1])
