# Stage 2: Section-aware Chunking

核心文件：

- [core/paper_loader.py](../../core/paper_loader.py)
- [core/section_splitter.py](../../core/section_splitter.py)

## 本阶段解决什么问题

普通 RAG 通常按固定长度切文本。问题是科研论文的结构很强：Methods 讲方法，Results 讲结果，Conclusion 讲结论。如果把这些混在一起，问“用了什么模拟方法”时，系统可能检索到 Results 里的结论段，而不是 Methods 里的参数段。

所以本阶段把 chunk 从普通文本块升级成 `PaperChunk`：

```python
@dataclass
class PaperChunk:
    chunk_id: int
    paper_id: str
    title: str
    section: str
    text: str
    metadata: dict[str, Any]
```

关键变化是：每个 chunk 都知道自己来自哪篇论文、哪个 section。

## `paper_loader.py` 怎么读

`load_paper_document(record)` 的正式路径是读取 PDF：

1. `PaperRecord.has_pdf=True`：调用旧的 `load_document()` 抽取全文。
2. `PaperRecord.has_pdf=False`：只保留在候选清单中，不进入正式 chunk 构建。

这个取舍是为了保证回答里的 evidence chunk 都能追溯到真实全文。metadata-only 记录没有 Methods、Results 和 Conclusion 原文，不适合支撑科研问答。

换句话说，section-aware chunking 的前提是“有正文”。如果只有标题和 DOI，系统无法判断某段文本属于 Methods 还是 Results，也无法回答“模拟参数是什么”“性能指标来自哪一段结果”。所以 PDF-only 不是为了简化实现，而是为了保证证据质量。

## `section_splitter.py` 怎么读

`SECTION_PATTERNS` 是规则识别器：

```python
("methods", r"^\s*(\d+\.?\s*)?(methods?|methodology|...)\s*$")
```

它支持英文和部分中文标题，比如 `Abstract`、`Methods`、`Results and Discussion`、`结论`。

`_detect_section(line)` 先限制标题长度：

```python
if len(compact) > 80:
    return None
```

这是为了避免把正文长句误判为 section 标题。

`split_into_sections(text)` 按行扫描全文，遇到 section 标题就切换当前 section。最后 `split_paper_document()` 再调用旧的 `split_text()`，把每个 section 内部切成 chunks。

## 为什么跳过 References

```python
if section == "references":
    continue
```

References 通常包含大量文献名、期刊名和作者名，会污染检索结果。第一版问答重点是正文 evidence，所以先跳过参考文献。

## 验证方式

```bash
python -m pytest tests/test_section_splitter.py -q
```

你应该确认：

- section 能识别出 `methods/results/conclusion`。
- chunk metadata 里有 `paper_id`、`title`、`section`。
- 正式 chunk 都来自已有 PDF 文献，而不是候选元数据。

## 简历表达

可以写：

> 实现 section-aware chunking，为每个 evidence chunk 绑定 paper_id、section、DOI 和 topic tags，提高方法参数类问题的检索可追溯性。
