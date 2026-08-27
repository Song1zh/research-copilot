# 检索组件消融报告（2026-08-25）

## 口径

- 数据集：`docs/eval/rag_eval_v1.jsonl`中的44条可回答问题；
- 检索单位：先返回chunk，再按paper_id去重计算论文级指标；
- 策略：BM25、向量、0.6/0.4混合、混合加`qwen3-rerank`；
- Embedding：64维本地Hash与百炼`text-embedding-v4` 1024维；
- 所有组合均完成44题，成功报告无失败。

## 结果

| Embedding | 策略 | Hit@5 | Recall@5 | MRR@5 | nDCG@5 | 均值延迟 |
|---|---|---:|---:|---:|---:|---:|
| local_hash | BM25 | 0.6818 | 0.6061 | 0.4981 | 0.4931 | 252.05 ms |
| local_hash | vector | 0.2045 | 0.1515 | 0.1106 | 0.1057 | 7.95 ms |
| local_hash | hybrid | 0.5455 | 0.4356 | 0.2777 | 0.2856 | 253.93 ms |
| local_hash | hybrid + rerank | 0.8409 | 0.7689 | 0.8182 | 0.7675 | 1276.46 ms |
| text-embedding-v4 | BM25 | 0.6818 | 0.6061 | 0.4981 | 0.4931 | 934.18 ms |
| text-embedding-v4 | vector | 1.0000 | 0.9735 | 0.9659 | 0.9599 | 922.10 ms |
| text-embedding-v4 | hybrid | 1.0000 | 0.9848 | 0.9659 | 0.9616 | 1881.85 ms |
| text-embedding-v4 | hybrid + rerank | 1.0000 | 0.9697 | 0.9432 | 0.9276 | 2909.49 ms |

原始成功结果：`app_data/eval/retrieval_ablation_20260825_231149.json`。
沙箱网络失败结果另存为`retrieval_ablation_20260825_230502.json`，不得与模型
失败混淆。

## 结论

1. 本地Hash向量不是语义Embedding，单路效果明显弱于BM25；固定0.6的向量
   权重进一步拖累混合排序，因此不能把0.6/0.4描述为已验证最优权重。
2. Reranker能显著修复弱召回基线：在local_hash混合链路上，Hit@5从
   0.5455升至0.8409，MRR@5从0.2777升至0.8182，但平均延迟增加约1秒。
3. `text-embedding-v4`单路向量已经接近当前评测集上限；加入BM25仅将
   Recall@5从0.9735升至0.9848，同时延迟约翻倍。
4. 在强Embedding混合基线上继续使用Reranker并未增益，Recall@5、MRR@5和
   nDCG@5均小幅下降，说明Reranker应通过评测按场景启用，不能默认堆叠。
5. BM25在两个Collection上的质量完全相同；其延迟差异包含Collection和客户端
   初始化开销，不代表BM25进行了云模型计算。

## 使用边界

44题来自现有开发评测集，云Embedding接近满分可能反映题目规模小、Gold较易或
数据集与开发过程同源。该结果可以用于组件消融和回归，不应写成开放问答准确率。
简历如需使用，必须保留“44条自建可回答问题”口径；独立盲测完成后应优先使用
盲测结果替换本报告数字。
