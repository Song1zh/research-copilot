# Neo4j Graph 评测报告（2026-08-25）

## 结论

已在清洗重建后的 Neo4j 图谱上完成 20 条独立 graph 问题评测。题集覆盖
8 条单跳、8 条双条件和 4 条多条件关系查询；每个 gold 论文必须对全部
标注实体存在带 `evidence_chunk_id` 和 `evidence_text` 的精确关系。

在同一图谱、同一题集上，旧版“英文规则解析 + 逐词 Top8 并集”的宏平均
F1 为 0.4093、Exact Match 为 0.1000；加入中英文最长匹配和共享 Paper 的
AND 交集查询后，F1 与 Exact Match 均达到 1.0000，20 条查询无失败。

## 清洗与重建

本轮只清理 Neo4j 中带项目标签的节点与关系，PDF、Chroma 和评测文件未被
删除。随后从 40 篇本地 PDF 完整重建图谱。

| 节点 | 清洗前 | 清洗后 |
|---|---:|---:|
| Paper | 40 | 38 |
| Material | 13 | 12 |
| Method | 7 | 5 |
| ForceField | 5 | 4 |
| Software | 3 | 2 |
| Property | 8 | 8 |
| Finding | 902 | 817 |

清洗后只有 38 个 Paper 节点，是因为 2 篇 PDF 没有留下可用的领域实体关系，
不是文献文件丢失。主要改动包括：

- ASCII 实体使用词边界，避免 `Al -> thermal/all`、`NTO -> into`；
- `ReaxFF/ReaxFF-lg`只建模为 ForceField，不再重复作为 Method；
- 跳过显式 References 和高引用密度 unknown chunk；
- 一旦进入引用尾部，停止抽取该论文后续 unknown chunk；关系证据使用首次
  命中片段，避免被文末引用覆盖；
- 问题分析增加中英文别名、最长匹配和重叠消解；
- 多实体问题改为 Neo4j 共享 Paper 的 AND 交集查询。

## 图谱与问题集

- 问题集：`docs/eval/graph_eval_v1.jsonl`
- 构建脚本：`scripts/build_graph_eval_dataset.py`
- 本地基准：`scripts/run_graph_benchmark.py`
- 标注口径：`neo4j_exact_relation_and_manual_evidence_review_v1`
- split：12 dev / 8 test

```bash
python scripts/build_graph_eval_dataset.py
python scripts/run_graph_benchmark.py
```

## 同口径优化对照

| 策略 | Precision | Recall | F1 | Exact Match | 平均延迟 |
|---|---:|---:|---:|---:|---:|
| Legacy：英文规则 + 逐词Top8并集 | 0.5000 | 0.4225 | 0.4093 | 0.1000 | 3.01 ms |
| Current：中英文最长匹配 + AND交集 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 17.10 ms |
| Oracle：标注实体 + 精确交集 | 1.0000 | 1.0000 | 1.0000 | 1.0000 | 4.55 ms |

原始结果：`app_data/eval/graph_benchmark_20260825_045453.json`

当前策略比 legacy 多做实体消歧和多实体交集，因此延迟增加约 15 ms；对本地
交互仍可忽略。Current 与 Oracle 一致，说明这 20 条受控问题的实体解析和
关系查询已经对齐。

## 文本 RAG + Reranker 基线

在相同 20 条问题上运行本地 Hash/BM25 混合检索和百炼 `qwen3-rerank`：

| Hit@5 | Recall@5 | MRR@5 | nDCG@5 | Recall@20 | 平均延迟 | 失败 |
|---:|---:|---:|---:|---:|---:|---:|
| 0.7000 | 0.5767 | 0.6250 | 0.5472 | 0.5767 | 1290.38 ms | 0 |

原始结果：`app_data/eval/rag_benchmark_20260825_045535.json`

文本检索的排序指标与图谱集合 F1 口径不同，不能直接按数值比较。结果说明
文本片段检索和结构化集合查询适合不同任务：原文事实仍依赖 Chroma evidence，
多实体论文集合更适合 Neo4j AND 查询。

## 使用边界

1. 20 条题目来自当前图谱精确关系并经过人工证据复核，因此 100% 只表示
   受控关系查询契约通过，不能外推为开放问答准确率。
2. 当前 `STUDIES` 仍表示“文献中有材料关联”，不能区分 primary target、
   comparison 和 background mention；题目统一使用“关联”，不写“主要研究”。
3. 888 个 Finding 仍由规则抽取，存在句子截断风险，本轮关系题不把 Finding
   文本作为主要 gold 判据。
4. 尚未完成相同生成模型下的 Neo4j on/off Groundedness 对照，因此不能宣称
   Neo4j 已提升最终答案正确率或 Groundedness。

## 简历使用边界

可以写：

> 构建覆盖40篇领域文献的Neo4j关系图谱，针对中英文实体识别和多条件查询实现
> 最长匹配与共享Paper的AND交集；构造20条单跳/多条件关系评测集，将结构化
> KG检索F1由40.93%提升至100%、Exact Match由10%提升至100%。

必须保留“20条自建关系评测集”和“结构化KG检索”口径；不能改写为“Agent
问答准确率100%”。下一步需要显式增加 `kg_provider=none/neo4j`，再运行相同
LLM与文本证据下的端到端Groundedness A/B。
