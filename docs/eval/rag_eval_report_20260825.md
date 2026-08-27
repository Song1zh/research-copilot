# Research Copilot RAG 评测报告（2026-08-25）

## 结论

百炼 `qwen3-rerank` 对当前“64维本地 hash 向量 + BM25”首阶段召回有明显
排序收益。在 44 条可回答问题上，Hit@5、Recall@5、MRR@5 和 nDCG@5
均提升，44 次重排无调用失败；平均检索延迟增加约 1.03 秒。

解除账户计费限制并更新运行环境后，已使用 `qwen3.7-max-2026-06-08`
同时作为答案生成模型和 Groundedness Judge，完成 50 条端到端评测。
Claim Support Rate 为 0.7140，加权支持率为 0.7997，Citation Coverage 为
0.9745，Citation Precision 为 1.0000，Answer Correctness 为 0.6280，
6 条领域外问题的拒答准确率为 1.0000；50 次 Judge 调用无失败。

## 数据集

- 文件：`docs/eval/rag_eval_v1.jsonl`
- 总计：50 条，30 dev / 20 test
- 可回答：44 条；领域外拒答：6 条
- 类别：8 exact lookup、10 method、10 mechanism/finding、10 comparison、
  6 graph relation、6 refusal
- 每条可回答问题绑定真实 `paper_id` 和 `chunk_id`；gold chunk 先按全文
  关键词筛选，再由 `qwen3-rerank` 在相关论文内部重排定位。

## 9 条阶段基线

| 指标 | 无 Reranker | qwen3-rerank | 变化 |
|---|---:|---:|---:|
| Hit@5 | 0.7778 | 0.8889 | +0.1111 |
| Recall@5 | 0.4537 | 0.6204 | +0.1667 |
| MRR@5 | 0.5778 | 0.8333 | +0.2555 |
| 平均延迟 | 342.36 ms | 1373.09 ms | +1030.73 ms |

原始结果：`app_data/eval/embedding_comparison_20260825_014545.json`

## 50 条正式检索评测

检索指标只统计 44 条可回答问题；6 条拒答进入生成/拒答评测，不参与召回率。

| 指标 | 无 Reranker | qwen3-rerank | 变化 |
|---|---:|---:|---:|
| Hit@5 | 0.5455 | 0.8409 | +0.2954 |
| Recall@5 | 0.4356 | 0.7689 | +0.3333 |
| MRR@5 | 0.2777 | 0.8182 | +0.5405 |
| nDCG@5 | 0.2856 | 0.7675 | +0.4819 |
| Recall@20 | 0.5436 | 0.7689 | +0.2253 |
| 平均延迟 | 289.42 ms | 1322.79 ms | +1033.37 ms |
| P50 延迟 | 296.24 ms | 1329.56 ms | +1033.32 ms |
| P95 延迟 | 332.28 ms | 1380.40 ms | +1048.12 ms |
| 调用失败 | 0 | 0 | 0 |

原始结果：`app_data/eval/rag_benchmark_20260825_020741.json`

### 分类别 qwen3-rerank 结果

| 类别 | Hit@5 | Recall@5 | MRR@5 | nDCG@5 |
|---|---:|---:|---:|---:|
| exact lookup | 0.8750 | 0.8750 | 0.8750 | 0.8750 |
| method | 0.8000 | 0.8000 | 0.7500 | 0.7631 |
| mechanism/finding | 0.7000 | 0.7000 | 0.7000 | 0.7000 |
| comparison | 0.9000 | 0.6667 | 0.8500 | 0.6762 |
| graph relation | 1.0000 | 0.8611 | 1.0000 | 0.8964 |

## 失败分析

Reranker 后仍有 7 条 Hit@5 失败：E03、M06、M09、F03、F05、F09、C02。
这些问题的共同点不是“相关候选排序错误”，而是首阶段 hash/BM25 候选中
缺少目标论文，或多论文比较需要的目标没有完整进入候选集。Reranker 只能
重排已有候选，不能补回未召回论文。因此下一项高价值升级应是完成
`text-embedding-v4` 语义索引并与当前 Reranker 联合评测，而不是继续调整
Reranker prompt。

## Groundedness 口径

代码已经实现：

- 将 summary、methods、findings、mechanisms 和 comparison finding 拆为 claim；
- 逐 claim 标记 `supported / partial / unsupported`；
- 计算 Claim Support Rate、加权支持率、Citation Coverage、Citation Precision、
  Answer Correctness 和拒答准确率；
- Judge 失败时记录 `judge_error`，不输出伪造的零分或成功分。

本次正式运行命令：

```bash
python scripts/run_rag_benchmark.py \
  --reranker-providers dashscope \
  --run-generation \
  --generation-model qwen3.7-max-2026-06-08 \
  --judge-model qwen3.7-max-2026-06-08
```

原始结果：`app_data/eval/rag_benchmark_20260825_035647.json`

### 50 条生成与 Groundedness 结果

| 指标 | 结果 |
|---|---:|
| Claim Support Rate | 0.7140 |
| 加权 Claim Support Rate | 0.7997 |
| Citation Coverage | 0.9745 |
| Citation Precision | 1.0000 |
| Answer Correctness | 0.6280 |
| 拒答准确率 | 1.0000（6/6） |
| Judge 失败 | 0 |
| 平均端到端延迟 | 85.88 s |
| P50 / P95 端到端延迟 | 89.55 s / 117.37 s |

非拒答问题共拆出 461 个原子 claim：340 个 supported、74 个 partial、
47 个 unsupported。这里的总体指标按问题汇总，不能直接用上述 claim 数量
重新计算后替代报告值。

### 分类别生成结果

| 类别 | 数量 | Claim Support | 加权支持率 | Answer Correctness |
|---|---:|---:|---:|---:|
| exact lookup | 8 | 0.63 | 0.75 | 0.75 |
| method | 10 | 0.58 | 0.67 | 0.63 |
| mechanism/finding | 10 | 0.74 | 0.83 | 0.33 |
| comparison | 10 | 0.78 | 0.83 | 0.50 |
| graph relation | 6 | 0.68 | 0.81 | 0.80 |
| refusal | 6 | - | - | 拒答 1.00 |

Groundedness 最弱的是 method 和 exact lookup。典型失败 E01 中，Reranker
把论文末尾的参考文献片段排到首位；生成模型根据论文标题给出了看似正确的
回答，但所引 E1-E3 并未包含对应事实，因此 Judge 将相关 claim 判为
unsupported。这说明当前主要瓶颈是切分/章节过滤和首阶段召回，不宜只靠
更强生成模型掩盖。

本次运行时本地 Neo4j 未启动，graph relation 问题走文本证据降级路径；因此
0.80 的 Answer Correctness 不能表述为“图谱增强效果”。

## 简历使用边界

可以写入真实的 50 条检索指标，以及“在 50 条自建评测集上完成 claim 级
Groundedness 评测，Claim Support Rate 71.4%、引用覆盖率 97.45%、拒答
准确率 100%”。必须同时说明数据集规模与自建口径，不应写成通用模型准确率；
Citation Precision 100% 只代表引用 ID 均能映射到实际检索证据，不代表
所有引用在语义上都完整支撑回答。Answer Correctness 62.8% 暂不建议作为
简历亮点，更适合作为下一轮优化基线。
