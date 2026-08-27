# Stage 1: Corpus Manifest

核心文件：[core/literature_manifest.py](../../core/literature_manifest.py)

## 本阶段解决什么问题

原项目的入口是“上传一个文件再提问”。这对 Demo 足够，但不像真实实验室知识库。文献库系统需要先知道“有哪些候选论文、哪些已有 PDF、哪些优先入库”。所以第一步不是 RAG，而是建立 corpus 管理层。

`PaperRecord` 是这个阶段的核心类型。它把不同 CSV 来源统一成同一种论文记录：

```python
@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    year: str = ""
    journal: str = ""
    doi: str = ""
    file_path: str = ""
    topic_tags: str = ""
```

这里最重要的是 `paper_id`。文件名会变，PDF 路径会变，标题可能有大小写和符号差异，但 `paper_id` 是系统内部稳定主键。后续 chunk、evidence、Neo4j 节点都会依赖它。

## 核心代码怎么读

`resolved_file_path` 负责把 manifest 里的相对路径映射到项目路径：

```python
if path.is_absolute():
    return path
return LITERATURE_CORPUS_DIR / path
```

这让 CSV 可以写 `papers/EMMD-016.pdf`，不用写死每台电脑的绝对路径。

`has_pdf` 做了三个判断：

```python
path.exists()
path.suffix.lower() == ".pdf"
path.stat().st_size > 0
```

这区分了可入库 PDF 和无全文记录。当前项目的正式知识库是 PDF-only：无 PDF 的 metadata-only 记录只作为候选清单保留，不进入 Chroma 索引、Agentic RAG 问答或 Neo4j 图谱。

`_record_from_manifest`、`_record_from_core_inventory`、`_record_from_local_reaxff` 是三个适配器。它们把不同 CSV 的字段名统一成 `PaperRecord`。这体现了一个工程原则：不要让业务代码到处判断 CSV 来自哪里，把差异收敛在读取层。

## 去重逻辑

`_dedupe` 用 `paper_id` 和 DOI 去重：

```python
if record.paper_id in seen_ids:
    continue
if doi_key and doi_key in seen_dois:
    continue
```

注意当前加载顺序优先 local ReaxFF，再 core inventory，再 curated manifest。这样本地高优先级 PDF 不会被宽泛清单覆盖。

## PDF-only 活动语料

当前代码里 `load_paper_records()` 的默认行为已经改成 PDF-only：

```python
records = load_paper_records(LITERATURE_CORPUS_DIR)
assert all(record.has_pdf for record in records)
```

这批 records 才是正式进入 Chroma、Neo4j 和 Agentic RAG 的活动语料。

如果要看完整候选清单，需要显式打开：

```python
candidate_records = load_paper_records(
    LITERATURE_CORPUS_DIR,
    include_metadata_only=True,
)
```

这一步只用于统计“还有多少论文缺 PDF”。它不代表这些 metadata-only 记录会参与问答。

这个设计解决了一个关键问题：文献知识库不是论文目录。论文目录可以只有标题和 DOI，但科研问答必须能展示原文证据。没有 PDF 的记录无法提供 Methods、Results 或 Conclusion 中的 evidence chunk，所以不能进入正式索引。

## 验证方式

```bash
python -m pytest tests/test_literature_manifest.py -q
```

你应该重点看两个结果：

- 默认读到的 active records 全部 `has_pdf=True`。
- 显式 `include_metadata_only=True` 时，可以统计还有多少候选论文缺 PDF。
- metadata-only 记录即使被传入 chunk 构建，也不会生成正式 chunk。

## 简历表达

可以写：

> 设计文献 corpus manifest 管理层，统一整合本地 ReaxFF/MD PDF 文献与候选 DOI 清单，将正式 RAG 语料限定为可追溯全文 PDF，保证回答证据链可靠。
