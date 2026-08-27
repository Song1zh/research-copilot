# 评测补强状态（2026-08-25）

## 已完成

- 44条可回答问题、2种Embedding、4种检索策略的8组消融；
- 显式`kg_provider=none/neo4j`，API、工作流和Streamlit均可切换；
- Neo4j A/B冻结同一文本证据，支持两组并发、逐题checkpoint、resume和失败成对重试；
- 独立盲测双文件、证据复核校验、至少30题限制和SHA-256冻结；
- 实验室试用匿名记录模板、同意校验和空数据防伪汇总；
- 80项自动化测试通过，2条Chroma legacy配置警告。

## 检索消融结论

成功原始结果：`app_data/eval/retrieval_ablation_20260825_231149.json`；报告：
`docs/eval/retrieval_ablation_report_20260825.md`。云Embedding单路向量Hit@5为
1.0000、Recall@5为0.9735；混合Recall@5为0.9848；继续加入Reranker后
Recall@5降至0.9697且延迟上升。因此Reranker只在local_hash弱基线上有明显
收益，不能宣称对所有Embedding都有效。

## Neo4j A/B当前状态

Checkpoint：`app_data/eval/kg_ab_full50_checkpoint.json`。当前有21题两组均为
有效结果，18题因百炼返回`AllocationQuota.FreeTierOnly`失败，剩余11题尚未
运行。失败题不纳入有效均值，也不能形成最终A/B结论。修复配额后运行：

```powershell
.\.venv\Scripts\python.exe scripts\run_kg_groundedness_ab.py `
  --embedding-provider dashscope `
  --reranker-provider none `
  --generation-model qwen3.7-max-2026-06-08 `
  --judge-model qwen3.7-max-2026-06-08 `
  --checkpoint app_data\eval\kg_ab_full50_checkpoint.json `
  --resume --retry-failures
```

## 外部验收仍需完成

独立盲测必须由未参与调参的实验室成员出题并复核Gold；真实试用必须由真实
参与者提交问题与评分。当前模板为空，不能写入简历人数、满意度、成功率或
盲测成绩。
