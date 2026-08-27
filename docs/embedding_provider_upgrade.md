# Embedding Provider升级与评测记录

## 边界

本次只升级向量后端和检索评测，不引入reranker，也不把引用校验包装为语义蕴含判断。

## 实现

- `local_hash`：保留64维离线hash向量，适合测试和无网络演示。
- `dashscope`：通过OpenAI兼容接口调用 `text-embedding-v4`，默认1024维、每批10条。
- provider必须显式选择；云端失败时不自动回退。
- collection名称自动包含provider、模型和维度后缀。
- FastAPI索引/问答请求和Streamlit侧边栏都可选择provider。

## 真实基线

评测集为 `docs/eval_literature_questions.csv`。其中9条问题具有人工标注的相关论文ID，1条为超出文献库范围的拒答问题。

2026-07-31运行本地hash基线：

| 指标 | 结果 |
| --- | ---: |
| 可评分问题 | 9 |
| Hit@5 | 0.7778 |
| Recall@5 | 0.4537 |
| MRR@5 | 0.5778 |
| 平均检索耗时 | 254.18 ms |
| 失败数 | 0 |

原始结果：`app_data/eval/embedding_comparison_20260731_004107.json`。

## 云端结果状态

云端接口已完成真实调用尝试，但服务返回账户状态异常（Arrearage），因此没有产生可用的云向量对照指标。不得在简历中填写云向量“提升比例”。账户恢复后执行：

```bash
python scripts/compare_embedding_retrieval.py --providers dashscope
```

若只需要复用已建索引，可加 `--skip-index`。

## 面试表达

可以说：

> 我先保留了64维hash embedding作为离线可运行基线，再把向量后端抽象为显式provider，新增百炼OpenAI兼容的text-embedding-v4。两种向量使用独立Chroma collection，云端失败时不静默降级，避免评测结果被混淆。本地基线在9条人工标注文献问题上的Hit@5为0.7778、Recall@5为0.4537；云端评测因为账户状态异常尚未得到有效数字，所以没有写提升比例。

不能说：

- 云向量已经显著提升召回率。
- 项目已经完成生产级embedding切换。
- 当前评测足以证明系统泛化能力。
