"""
结构化字段抽取模块
从 OCR 识别出的原始文字列表里,用正则规则提取关键字段:金额 / 日期 / 商户名

先用规则覆盖标准发票/小票格式,复杂或非标准格式的票据,后续可以考虑接入
本地部署的LLM做兜底抽取(把这些文字喂给本地模型,让它按JSON格式提取字段)。
"""

import re
from dataclasses import dataclass, field


@dataclass
class ReceiptFields:
    amounts: list[float] = field(default_factory=list)   # 识别到的所有金额候选(可能有多个,比如小计/合计/税额)
    dates: list[str] = field(default_factory=list)        # 识别到的所有日期候选
    merchant_candidates: list[str] = field(default_factory=list)  # 商户名候选

    @property
    def best_amount(self):
        """启发式:取识别到的最大金额,通常合计金额是最大的那个数字"""
        return max(self.amounts) if self.amounts else None

    @property
    def best_date(self):
        return self.dates[0] if self.dates else None


AMOUNT_PATTERN = re.compile(r"(?<!\d)(\d{1,6}(?:\.\d{1,2})?)(?!\d)")
DATE_PATTERNS = [
    re.compile(r"(\d{4})[年\-/](\d{1,2})[月\-/](\d{1,2})日?"),
    re.compile(r"(\d{4})-(\d{2})(\d{2})(?!\d)"),  # 兼容 OCR 漏识别横杠的情况,如 "2026-0212"
]
MERCHANT_KEYWORDS = ["有限公司", "餐厅", "酒店", "商行", "商户", "个体工商户", "公司", "餐"]


def extract_fields(lines: list[str]) -> ReceiptFields:
    fields = ReceiptFields()

    for line in lines:
        # 先检查这一行是不是日期,如果是,提取日期后跳过金额提取(避免年份数字被误判成金额)
        is_date_line = False
        for pattern in DATE_PATTERNS:
            m = pattern.search(line)
            if m:
                y, mo, d = m.groups()
                fields.dates.append(f"{y}-{int(mo):02d}-{int(d):02d}")
                is_date_line = True
                break
        if is_date_line:
            continue

        # 提取金额候选
        for match in AMOUNT_PATTERN.finditer(line):
            raw = match.group(1)
            try:
                value = float(raw)
                if value > 0:
                    fields.amounts.append(value)
            except ValueError:
                continue

        # 提取商户名候选(包含关键词的行)
        for kw in MERCHANT_KEYWORDS:
            if kw in line:
                fields.merchant_candidates.append(line)
                break

    return fields


if __name__ == "__main__":
    # 用一段模拟的OCR识别结果测试(不依赖真实图片,方便直接验证抽取逻辑)
    mock_ocr_lines = [
        "电子发票(普通发票)",
        "开票日期: 2026年02月12日",
        "购买方信息",
        "名称: 某某科技有限公司",
        "销售方信息",
        "名称: 福州市台江区某某餐厅",
        "项目名称  金额  税率  税额",
        "*餐饮服务*餐费  1564.36  1%  15.64",
        "价税合计(大写) 壹仟伍佰捌拾圆整  (小写) ¥1580.00",
    ]

    fields = extract_fields(mock_ocr_lines)
    print("提取到的金额候选:", fields.amounts)
    print("最可能的合计金额:", fields.best_amount)
    print("提取到的日期候选:", fields.dates)
    print("最可能的日期:", fields.best_date)
    print("商户名候选行:", fields.merchant_candidates)
