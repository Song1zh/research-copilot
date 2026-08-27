# Research Copilot 面试问题库

本文档按当前版本整理：项目对外能力集中在 PDF 文献库 Agentic RAG 和 Neo4j 知识图谱。

## 1. 项目整体

### Q1：这个项目做什么？

它是一个面向 PDF 文献库的科研问答系统。系统读取本地文献库 manifest，只索引已有 PDF，把论文按 section 切成 evidence chunks，写入 Chroma，再通过 Agentic RAG 完成问题分析、混合检索、知识图谱检索、证据融合和结构化回答。

### Q2：你最核心的工程设计是什么？

核心设计是把“文本 evidence”和“图谱关系”分工明确。Chroma 负责找原文片段，Neo4j 负责查 Paper -> Material/Method/ForceField/Software/Property/Finding 的结构化关系。回答仍然保留 evidence citation，避免图谱关系脱离原文证据。

### Q3：为什么不做通用聊天机器人？

科研问答最重要的是可追溯和证据边界。通用聊天容易补常识、编结论。本项目要求回答基于文献库检索到的 evidence，并展示 trace、citation alignment 和 KG 命中。

## 2. 文献库和索引

### Q4：manifest 的作用是什么？

manifest 是文献库入口，记录 `paper_id`、标题、DOI、标签、优先级和 PDF 路径。`paper_id` 是稳定主键，后续 chunk、evidence 和 Neo4j 节点都依赖它。

### Q5：为什么正式知识库只索引已有 PDF？

只有标题和 DOI 的 metadata-only 记录无法提供 Methods、Results 或 Conclusion 原文证据。如果把它们放进 RAG，系统可能回答“看起来相关”的论文，但无法展示真实 evidence。

### Q6：section-aware chunking 解决什么问题？

普通 chunk 容易把 Methods、Results 和 References 混在一起。section-aware chunking 会识别 Abstract、Methods、Results、Conclusion 等章节，并跳过 References，让“用了什么方法”“有什么发现”这类问题更容易定位。

## 3. 检索和 Agentic RAG

### Q7：为什么要混合检索？

向量检索适合语义相近的问题，但对 `RDX`、`HTPB`、`CL-20`、`ReaxFF` 这类专业术语不一定稳定。关键词检索更适合精确术语。混合检索把两者合并，提高召回稳定性。

### Q8：Agentic RAG 的节点有哪些？

当前 workflow 包括：

```text
question_analyzer
-> query_planner
-> hybrid_retriever
-> kg_retriever
-> evidence_fusion
-> answer_generator
-> citation_verifier
-> self_reflection
```

### Q9：trace 有什么价值？

trace 记录每个节点的中间输出。它让面试官能看到系统不是一个黑盒聊天框，而是有明确的问题分析、检索计划、检索结果、图谱上下文和校验步骤。

## 4. 知识图谱

### Q10：知识图谱和普通 RAG 的区别是什么？

普通 RAG 从 Chroma 查相似文本片段，擅长回答“原文怎么说”。知识图谱把论文、材料、方法、力场、软件、性质和发现抽成节点与关系，擅长回答“哪些论文研究了什么、用了什么方法、报告了什么性质”。

### Q11：图谱里有哪些节点和关系？

节点包括：

- `Paper`
- `EvidenceChunk`
- `Material`
- `Method`
- `ForceField`
- `Software`
- `Property`
- `Finding`

关系包括：

- `Paper -[:HAS_EVIDENCE]-> EvidenceChunk`
- `Paper -[:STUDIES]-> Material`
- `Paper -[:USES_METHOD]-> Method`
- `Paper -[:USES_FORCE_FIELD]-> ForceField`
- `Paper -[:USES_SOFTWARE]-> Software`
- `Paper -[:REPORTS]-> Property`
- `Paper -[:REPORTS_FINDING]-> Finding`
- `Finding -[:SUPPORTED_BY]-> EvidenceChunk`

### Q12：Neo4j 不可用怎么办？

Neo4j 是增强层，不是单点依赖。不可用时，`kg_context.available=false`，文献问答仍然基于 Chroma 和关键词检索返回结果，并在 limitations 中说明图谱未参与。

### Q13：图谱关系如何展示？

关系查询返回 `path_text`，例如：

```text
(Paper: P1) -[:USES_FORCE_FIELD]-> (ForceField: ReaxFF)
```

Streamlit 的“知识图谱”页会用表格展示路径、论文 ID、关系、实体类型、实体、chunk 和 evidence text。

## 5. API 和 Demo

### Q14：当前主要 API 有哪些？

- `GET /health`
- `GET /literature/papers`
- `POST /literature/index`
- `POST /literature/ask`
- `POST /literature/graph/build`
- `GET /literature/graph/entities`
- `GET /literature/graph/relations`

### Q15：Streamlit Demo 怎么展示？

三个页签：

- 文献库概览：查看论文统计并构建 Chroma 索引。
- 文献问答：运行 Agentic RAG，展示回答、对比表、KG 命中、evidence 和 trace。
- 知识图谱：连接 Neo4j、构建图谱、查看实体统计、搜索关系路径。

## 6. 局限和优化

### Q16：当前项目最大的局限是什么？

当前 embedding 是本地 hash embedding，适合离线演示但语义检索能力有限。文献库回答生成仍偏规则式。图谱抽取是规则词表和正则，不是完整语义抽取。

### Q17：下一步怎么优化？

- 替换真实 embedding 模型。
- 增加 reranker。
- 为文献库回答接入专用 LLM prompt + schema。
- 用 LLM 或信息抽取模型增强图谱抽取。
- 做 claim-level citation verification。

## 7. 简历表述

可写：

> 实现 PDF 文献库 Agentic RAG 问答系统，基于 FastAPI、Chroma、Pydantic、Streamlit、LangGraph 和 Neo4j，打通 manifest 管理、PDF 解析、section-aware chunking、混合检索、evidence 引用校验、Agent trace、知识图谱构建和关系查询；Neo4j 不可用时系统自动退回文本 RAG，保证演示稳定性。
