# Stage 4: Simulation Extraction

核心文件：

- [schemas/simulation_extraction.py](../../schemas/simulation_extraction.py)
- [core/simulation_extractor.py](../../core/simulation_extractor.py)

## 本阶段解决什么问题

RAG 问答输出的是自然语言答案，但知识图谱需要结构化信息。比如一篇论文里出现：

```text
LAMMPS and ReaxFF were used for reactive molecular dynamics of RDX/HTPB at 300 K.
```

系统要能抽出：

- material: RDX, HTPB
- method: reactive molecular dynamics
- force field: ReaxFF
- software: LAMMPS
- condition: 300 K

这就是信息抽取。它不是回答用户问题，而是把文献变成可复用知识。

## Schema 怎么读

`schemas/simulation_extraction.py` 定义统一结构。所有实体都继承 `ExtractedEntity`：

```python
class ExtractedEntity(BaseModel):
    name: str
    evidence_chunk_id: int | str
    evidence_text: str = ""
```

最重要的是 `evidence_chunk_id` 和 `evidence_text`。抽取出来的实体必须能回到原文证据，否则图谱节点就会变成“无来源的知识”。

`SimulationExtraction` 是一次 chunk 抽取的总结果：

```python
class SimulationExtraction(BaseModel):
    paper_id: str
    chunk_id: int | str
    materials: list[MaterialSystem]
    methods: list[SimulationMethod]
```

## 规则抽取怎么读

第一版没有直接依赖 LLM，而是用领域词典和正则：

```python
MATERIAL_TERMS = ["CL-20", "HMX", "RDX", ...]
METHOD_TERMS = ["molecular dynamics", "ReaxFF", ...]
CONDITION_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s*(?:K|GPa|MPa|ps|fs|ns)\b")
```

这样做的好处是可测试、可解释、不需要 API key。缺点是召回有限，后续可以替换成 LLM 抽取，但 schema 不需要变。

`_snippet()` 会截取术语附近文本作为 evidence：

```python
start = max(0, idx - 80)
end = min(len(text), idx + len(term) + 120)
```

这让抽取结果能展示“为什么抽到了这个实体”。

## 为什么只抽部分 section

`extract_from_chunks()` 默认关注：

```python
{"methods", "results", "conclusion", "unknown"}
```

Introduction 里常有背景介绍，容易抽到和本文无关的材料或方法。第一版优先保证 precision。

## 为什么不从 metadata-only 抽取

抽取器的输入是 `PaperChunk`，而正式 `PaperChunk` 来自 PDF 全文。不要从只有标题、DOI、标签的 metadata-only 记录里抽取材料、方法或性能关系。

原因很简单：标题里出现 `RDX/HTPB` 只能说明论文可能相关，不能证明论文研究了什么方法、用了什么参数、报告了什么性能。把这类信息写入 schema 会污染后面的 Neo4j 图谱，也会让 Agentic RAG 产生“有实体但没有证据”的结果。

## 验证方式

```bash
python -m pytest tests/test_simulation_extractor.py -q
```

你还可以人工检查抽取 JSON：每个实体都应该带有 `evidence_chunk_id` 和 `evidence_text`，并且证据文本来自 PDF chunk。

## 简历表达

可以写：

> 针对计算模拟文献设计领域 schema，抽取材料体系、模拟方法、力场、软件、条件参数和性能指标，并为每个实体保留 evidence chunk 来源。
