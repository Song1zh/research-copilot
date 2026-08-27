# Learning Notes Index

这组文档用于配合代码学习，而不是替代代码。建议按顺序读，每读完一章就跑对应测试或 Demo。

## 推荐阅读顺序

1. [Stage 1: Corpus Manifest](stage_1_corpus_manifest.md)
2. [Stage 2: Section-aware Chunking](stage_2_section_chunking.md)
3. [Stage 3: Hybrid Retrieval](stage_3_hybrid_retrieval.md)
4. [Stage 4: Simulation Extraction](stage_4_simulation_extraction.md)
5. [Stage 5: Neo4j Graph](stage_5_neo4j_graph.md)
6. [Stage 6: Agentic RAG Workflow](stage_6_agentic_rag.md)
7. [Stage 7: Streamlit Demo 与运行命令](stage_7_streamlit_demo.md)

## 学习主线

当前项目聚焦 PDF 文献库系统，关键链路是：

```text
文献库 manifest
-> section-aware chunks
-> hybrid retrieval
-> 领域实体抽取
-> Neo4j 图谱
-> Agentic RAG workflow
-> 中文 Streamlit Demo
```

不要把这些能力当成孤立技术栈。它们解决的是同一个问题：让科研文献问答成为“可追溯、可检索、可结构化复用的实验室知识库”。

## 当前版本的关键产品决策

正式文献库是 **PDF-only**。Manifest 中仍然可以记录 metadata-only 候选论文，但这些记录只用于后续补全文献，不进入 Chroma 索引、Neo4j 图谱或 Agentic RAG 问答。

这个取舍是为了保证回答能追溯到真实全文证据。如果把只有标题、DOI 和标签的记录也放进知识库，系统可能回答“看起来相关”的论文，但无法展示 Methods、Results 或 Conclusion 原文证据，这对科研问答和求职展示都不够可信。
