# Expense Audit Toolkit

一个基于规则+统计方法+OCR的报销行为一致性检测工具包。用于识别报销记录中的逻辑矛盾、统计异常、以及票据与申报不符的情况,辅助审计人员优先排查高风险记录。

⚠️ **本项目所有数据均为虚构模拟数据,不包含任何真实公司或个人信息,仅用于演示检测逻辑。**

## 设计理念

报销审计中的问题分几类信号,确定性从高到低:
- **票据实物证据不符**:OCR识别出的票据实际金额/日期,与申报不一致
- **硬证据**:逻辑上直接矛盾(比如同一人同一时间出现在两个城市)
- **较强信号**:行程链条断裂 / 结伴报销模式异常
- **统计信号**:数字上不寻常但不代表一定有问题(离群点/阈值卡点/频率异常/金额精确度异常)
- **弱信号**:缺少佐证但可能有其他合理解释

本工具把这几类信号统一到一个评分体系里,而不是简单罗列多份互相独立的名单。

## 为什么不整体依赖LLM

核心检测逻辑用规则+统计方法实现,而不是丢给大模型判断,原因是:**可解释性**(必须能说清楚"为什么这条被标记")、**确定性**(同样数据每次结果一致)、**数据安全**(本地运行,不依赖外部API)。LLM只考虑作为非标准票据兜底抽取 / 报销备注语义检查的可选补充,尚未实现。

## 目录结构

```
expense-audit-toolkit/
├── data/                              # 模拟数据生成脚本 + 数据文件
├── detectors/
│   ├── conflict.py                    # 规则: 时间-地点冲突检测
│   ├── trip_chain.py                  # 规则: 单号关联行程链断裂检测
│   ├── statistical.py                 # 规则: 统计异常(离群点/阈值卡点/频率异常)
│   ├── receipt_cross_check.py         # 规则: OCR票据与申报记录交叉验证(含缺失票据检测)
│   ├── advanced_patterns.py           # 规则: 结伴报销模式 / 金额精确度异常
│   ├── feedback.py                    # 权重调优反馈闭环:记录复核结果,统计规则准确率
│   ├── rule_weights.json              # 各规则权重配置(可直接编辑调整,不用改代码)
│   └── scoring.py                     # 评分聚合层(整合全部规则,输出排序清单)
├── ocr/
│   ├── ocr_engine.py                  # 基于PaddleOCR的票据文字识别(本地部署)
│   ├── field_extractor.py             # 从OCR文字中抽取金额/日期/商户名
│   ├── pipeline.py                    # 单张图片:识别+抽取一步到位
│   └── batch_process.py               # 批量处理:遍历文件夹,一次性处理整批票据图片
└── README.md
```

## 已实现的检测规则(9条)

| 规则 | 类型 | 默认权重 |
|---|---|---|
| 发票金额与申报金额不符 | 票据实证 | 6 |
| 时间-地点硬冲突 | 硬证据 | 5 |
| 发票日期与申报日期不符 | 票据实证 | 4 |
| 行程链断裂 | 较强信号 | 4 |
| 疑似卡阈值 | 统计信号 | 3 |
| 结伴报销模式异常 | 较强信号 | 3 |
| 组内金额离群点 | 统计信号 | 2 |
| 月度报销频率异常 | 统计信号 | 2 |
| 金额精确度异常(疑似编造) | 统计信号 | 2 |
| 缺失票据 | 弱信号 | 2 |
| 异地住宿缺少交通佐证 | 弱信号 | 1 |
| 票据金额/日期识别失败 | 弱信号 | 1 |

权重存放在 `detectors/rule_weights.json`,可直接编辑调整,不需要改代码。

## 使用方法

```bash
pip install pandas numpy

# 生成全部模拟数据
python data/generate_mock_data.py
python data/generate_mock_travel.py
python data/generate_mock_linked_trips.py
python data/generate_mock_advanced.py

# 运行综合评分(默认用模拟数据演示全部9条规则)
python detectors/scoring.py
```

### OCR模块

```bash
pip install paddlepaddle paddleocr

# 单张图片识别
cd ocr
python pipeline.py path/to/receipt.jpg

# 批量处理一个文件夹的票据图片(文件名即单号,如 R001.jpg)
python batch_process.py C:\发票图片文件夹 result.csv
```

若在Windows上遇到 PaddlePaddle 的 oneDNN 兼容性报错(`ConvertPirAttribute2RuntimeAttribute`),在 `ocr_engine.py` 初始化 `PaddleOCR(...)` 时加上 `enable_mkldnn=False` 即可规避。

### 权重调优(需要日常持续使用积累数据)

每次人工复核完一条被标记的记录,记一笔反馈:

```python
from detectors.feedback import log_feedback
log_feedback(人="张三", 异常类型="疑似卡阈值(...)", 单号="R001", 确认结果="确认问题")
```

积累一段时间(建议每条规则至少5条样本)后,运行:

```bash
python detectors/feedback.py
```

会输出每条规则的历史准确率和权重调整建议。反馈日志文件(`feedback_log.csv`)包含真实复核记录,已加入 `.gitignore`,不会被提交。

## 接入真实数据的方法

1. 将 `data/` 下的 csv 替换为真实数据(保持列名一致)
2. 把真实票据图片放进一个文件夹,跑 `ocr/batch_process.py` 批量处理
3. 在 `scoring.py` 里,把 `mock_ocr_results` 替换成第2步生成的真实结果

**务必在本地环境处理,不要把任何真实数据上传到云端或第三方服务(包括AI助手)。**

## 后续可扩展方向

- [ ] 语义层:接入本地部署的LLM,做非标准票据的兜底抽取 / 报销备注语义合理性检查
- [ ] 可视化:Streamlit 简易看板,把排序清单和详情做成可点击的网页界面

## License

MIT
