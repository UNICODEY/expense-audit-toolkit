"""
OCR识别模块 —— 基于 PaddleOCR(本地部署,不联网)

安装(体积较大,首次安装需要一些时间):
    pip install paddlepaddle paddleocr

首次运行时,PaddleOCR会自动下载识别模型到本地缓存目录(之后就不需要联网了)。
"""

from paddleocr import PaddleOCR


class ReceiptOCR:
    def __init__(self, lang: str = "ch"):
        # PaddleOCR 3.x 新版API:不再需要 show_log / use_angle_cls 这些参数
        # use_doc_orientation_classify / use_doc_unwarping 关掉可以加快速度(票据图片通常不需要这些预处理)
        self.ocr_engine = PaddleOCR(
            lang=lang,
            use_doc_orientation_classify=False,
            use_doc_unwarping=False,
            use_textline_orientation=True,
            enable_mkldnn=False,  # 关闭oneDNN加速,规避Windows上PaddlePaddle 3.x的已知兼容性bug
        )

    def extract_text(self, image_path: str) -> list[str]:
        """
        识别图片里的所有文字,返回文字列表
        """
        result = self.ocr_engine.predict(image_path)
        lines = []
        for res in result:
            texts = res.get("rec_texts", [])
            lines.extend(texts)
        return lines


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("用法: python ocr_engine.py <图片路径>")
        sys.exit(1)

    ocr = ReceiptOCR()
    lines = ocr.extract_text(sys.argv[1])
    print("识别到的文字:")
    for line in lines:
        print(f"  - {line}")
