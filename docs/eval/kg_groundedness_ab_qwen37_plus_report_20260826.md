# Neo4j on/off Groundedness A/B 报告（2026-08-26）

## 口径

- 数据集：`docs/eval/rag_eval_v1.jsonl`，共50题；
- 文本证据：每题先运行一次DashScope `text-embedding-v4`检索并冻结Top 6 evidence；
- A/B变量：仅切换`kg_provider=none/neo4j`；
- Reranker：关闭，`reranker_provider=none`；
- 生成与Judge模型：`qwen3.7-plus-2026-05-26`；
- 检查点：`app_data/eval/kg_ab_qwen37_plus_full50_checkpoint.json`；
- 原始结果：`app_data/eval/kg_groundedness_ab_20260826_204944.json`。

## 结果

| 组别 | Queries | Claim Support | Weighted Support | Citation Coverage | Citation Precision | Answer Correctness | Refusal Accuracy | Judge Failures |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| KG关闭 | 50 | 0.8346 | 0.9032 | 0.9644 | 1.0000 | 0.8306 | 1.0000 | 0 |
| Neo4j开启 | 50 | 0.7857 | 0.8451 | 0.9683 | 1.0000 | 0.7726 | 0.6667 | 0 |

Neo4j开启相对KG关闭的变化：

| 指标 | Delta |
|---|---:|
| Claim Support | -0.0489 |
| Weighted Support | -0.0581 |
| Citation Coverage | +0.0039 |
| Citation Precision | 0.0000 |
| Answer Correctness | -0.0580 |
| Refusal Accuracy | -0.3333 |

## 结论

1. 当前Neo4j上下文注入没有提升端到端Groundedness，反而降低Claim Support、
   Weighted Support和Answer Correctness。
2. Citation Precision维持1.0000，说明引用ID层面的对齐稳定；但这不等价于
   完整语义蕴含验证。
3. Neo4j更适合作为可控关系查询模块；直接把KG context塞进生成提示词，可能
   带来噪声或误导模型。
4. 下一步应优化KG注入策略，例如只注入与冻结文本证据同paper_id的关系、按
   问题类型选择是否启用KG、或让Agent先判断KG是否相关。

## 简历使用边界

可以写“完成Neo4j on/off A/B评测，发现当前KG注入未带来稳定端到端收益，
据此定位下一步优化方向”。不能写“Neo4j提升问答准确率”或“图谱增强效果显著”。

