# Stage 3: Hybrid Retrieval

核心文件：

- [core/vector_store.py](../../core/vector_store.py)
- [core/keyword_retriever.py](../../core/keyword_retriever.py)
- [core/hybrid_retriever.py](../../core/hybrid_retriever.py)
- [core/literature_indexer.py](../../core/literature_indexer.py)

## 本阶段解决什么问题

单路向量检索适合语义相似，但对科研术语不总是稳。比如 `ReaxFF`、`HTPB`、`CL-20`、`300 K` 这类精确术语，关键词检索往往更可靠。Hybrid retrieval 的目标是把两者结合：

```text
vector retrieval: 找语义相近
keyword retrieval: 找精确术语
hybrid fusion: 去重、归一化、合并排序
```

## Chroma 封装

`ChromaVectorStore` 仍然是向量库入口。新增了两个点：

1. `where` metadata filter，可按 `paper_id`、`section` 等过滤。
2. `get_all()`，用于关键词检索读取 collection 中所有 chunk。

另外项目加入了 `LocalHashEmbeddingFunction`。这是一个离线 fallback，避免 Chroma 默认模型下载失败时项目跑不起来。它不是生产级 embedding，但适合教学和本地演示。

## 索引器怎么读

`core/literature_indexer.py` 负责把 PDF 文献库写入 Chroma。主流程是：

```text
load_paper_records(PDF-only)
-> load_paper_document()
-> split_paper_document()
-> chunks_to_vector_records()
-> ChromaVectorStore.upsert_chunks()
```

`index_literature_corpus()` 里的 `include_metadata_only` 参数现在只为兼容旧调用保留。无论外部怎么传，正式索引都会重新读取 PDF-only records：

```python
records = load_paper_records(..., include_metadata_only=False)
```

这保证 Chroma collection 中的 evidence chunk 都来自已有 PDF。

`max_papers` 仍然存在，但它不是正式检索策略。它只服务 Streamlit 的“高级设置 / 学习模式”，用于快速调试前 N 篇 PDF。正式问答应该让 `max_papers=None`，也就是索引全部 PDF。否则如果相关论文排在第 21 篇，而你只索引了 20 篇，系统就不可能检索到它。

## 关键词检索怎么读

`keyword_retriever.py` 用一个轻量 BM25 思路：

```python
idf = log(1 + (total_docs - doc_freq + 0.5) / (doc_freq + 0.5))
score += idf * ...
```

你不用死记公式。理解成两点即可：

- 一个词在当前 chunk 出现越多，分数越高。
- 一个词在所有 chunk 里越少见，区分度越高。

所以 `ReaxFF`、`HTPB` 这种专业词通常权重更强。

## Hybrid 合并怎么读

`_evidence_key()` 用 `paper_id::chunk_id` 做去重键：

```python
return f"{paper_id}::{chunk_id}"
```

同一个 chunk 如果被向量和关键词都召回，只保留一份。

`_normalize()` 把不同检索器的分数拉到 0-1：

```python
(score - min_score) / (max_score - min_score)
```

最后用权重合并：

```python
hybrid_score = vector_weight * vector_score + keyword_weight * keyword_score
```

当前默认 `vector_weight=0.6`、`keyword_weight=0.4`。这表示仍以语义检索为主，但给精确术语足够影响力。

## 验证方式

```bash
python -m pytest tests/test_keyword_retriever.py -q
```

也可以在 Streamlit 的“文献库概览”里先索引 PDF 文献，再到“文献问答”里提问：

```text
哪些论文涉及 RDX/HTPB 热分解，它们使用了哪些模拟方法？
```

如果只是验证代码路径，可以运行：

```bash
python -m pytest tests/test_literature_manifest.py tests/test_keyword_retriever.py -q
```

## 简历表达

可以写：

> 实现向量检索与 BM25 关键词检索融合，针对 ReaxFF、HTPB、CL-20 等领域术语提升检索稳定性，并保留 chunk 级 evidence 可追溯信息。
