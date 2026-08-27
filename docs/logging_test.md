# Logging 测试记录（Day 18）

## 0. 运行命令
python -m tests.test_logging_smoke

## 1. 目标

验证 workflow 关键流程是否已经接入 logging，并满足基本可读性要求。

## 2. 当前记录的关键字段

- query
- top_k
- chunk_count
- evidence_count
- elapsed_ms
- alignment_check.is_aligned

## 3. 测试方式

- 使用 `sample.txt`
- 重复运行 10 次 workflow
- 检查终端与 `logs/app.log`

## 4. 检查项

1. 是否能看到 parse_document 日志
2. 是否能看到 retrieve_evidence 日志
3. 是否能看到 draft_answer 日志
4. 是否能看到 format_output 日志
5. 是否包含 query
6. 是否包含 top_k
7. 是否包含耗时
8. 是否包含 verifier/alignment 结果

## 5. 测试结果

- 日志文件路径：`logs/app.log`
- 运行次数：10
- 是否生成日志文件：是
- 是否包含关键字段：是
- 是否存在难以阅读的日志：是


## 6. 当前结论

Day 18 已完成 logging 初版。当前 workflow 已能够记录关键节点的 query、top-k、耗时与对齐检查结果，基本满足最小可观察性要求。