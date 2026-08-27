# 测试套件说明

## 测试目标

自动测试主要验证简历和 GitHub 审阅时最关键的项目契约：

- 文本切分行为。
- 检索结果格式化。
- Schema 解析与校验。
- 引用校验。
- 统一 API 响应结构。
- 文献库 manifest、section-aware chunking 和混合检索。
- 知识图谱契约和 Neo4j 不可用时的 fallback。
- Agentic RAG workflow 结构化兜底。

## 运行方式

```bash
python -m pytest -q
```

## 自动测试与手动检查

带有 `test_*` 函数的 pytest 文件属于自动测试，应尽量不依赖外部 LLM 调用。

`tests/` 目录下的自动测试应尽量不依赖外部 LLM 或正在运行的 Neo4j。Neo4j 相关测试优先验证不可用场景和结构化返回契约。

## 人工评测

配置好文献库索引后，可以运行文献库评测脚本：

```bash
python scripts/run_literature_eval.py
```

评测问题集和结果说明见 `docs/eval_literature_questions.csv` 与 `docs/evaluation_report.md`。
