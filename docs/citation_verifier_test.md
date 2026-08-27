# Citation Verifier 测试记录（Day 16）

## 1. 目标

验证 `verify_citations()` 是否能够：

- 检查 answer 中的 claim 是否附带 evidence 引用
- 检查引用的 `evidence_id` 是否存在
- 检查 cited snippet 是否对 claim 提供基本支撑
- 识别明显的假引用样本

## 2. 文件位置

```text
core/citation_verifier.py
tests/test_citation_verifier.py