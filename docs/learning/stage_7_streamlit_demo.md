# Stage 7: Streamlit Demo 与运行命令

核心文件：

- [demo/streamlit_app.py](../../demo/streamlit_app.py)
- [app/main.py](../../app/main.py)
- [core/literature_indexer.py](../../core/literature_indexer.py)
- [core/graph_store.py](../../core/graph_store.py)

## 本阶段解决什么问题

前面阶段解决的是后端能力：文献读取、chunking、检索、抽取、图谱和 Agentic RAG。Stage 7 解决的是展示问题：面试官或学习者打开页面后，能不能看懂系统在做什么。

当前 Streamlit Demo 分成三个页签：

```text
文献库概览
文献问答
知识图谱
```

项目正式能力集中在 PDF 文献库、Agentic RAG 和 Neo4j 图谱。

## 文献库概览怎么读

“文献库概览”展示四个指标：

- 候选文献总数：manifest 中记录的全部论文，包括无 PDF 候选。
- 可入库 PDF 论文：当前能进入正式知识库的论文。
- 已索引 chunk：当前 Chroma collection 中已有的证据片段数量。
- 高优先级 PDF：优先用于演示和抽取的 PDF 文献数量。

正式文献库只使用已有 PDF。metadata-only 记录只用于提醒“还有哪些候选论文未来可以补 PDF”，不会进入问答、检索或图谱。

## “构建/更新 PDF 文献库索引”是什么意思

点击这个按钮时，系统会执行：

```text
读取本地 PDF 文献
-> 抽取 PDF 文本
-> 按 section 切分 evidence chunk
-> 写入 Chroma collection
-> 供文献问答检索
```

这不是“下载论文”，也不是“调用大模型总结论文”。它是把本地已有 PDF 转成后续 RAG 可以检索的索引。

## 文献问答页怎么读

“文献问答”页调用 `run_literature_agent_workflow()`。它不是简单的 `query -> retrieve -> answer`，而是展示：

- 检索计划：问题被如何拆解。
- 多论文对比表：把多个 evidence 来源放在同一张表中。
- 机制总结：围绕材料、方法、性能或分解机制的归纳。
- 知识图谱命中：展示 Neo4j 返回的 Paper -> Entity 关系路径。
- 证据片段：每条回答依据来自哪个 chunk。
- 引用与证据校验：检查回答引用是否存在对应 evidence。
- Agent 执行轨迹：展示每个节点的中间结果。

这部分是求职展示重点。它说明项目不是“套一个聊天框”，而是把科研问答过程拆成了可观察、可验证的工程流程。

## 知识图谱页怎么读

“知识图谱”页会尝试连接 Neo4j。如果 Neo4j 没启动，页面会提示图谱暂不可用，并展示 Docker 启动命令。

Neo4j 可用时，可以：

- 查看 Paper、Material、Method、ForceField、Software、Property、Finding 的实体数量。
- 点击“构建/更新知识图谱”，从 PDF chunk 抽取实体关系并写入 Neo4j。
- 输入 `RDX`、`ReaxFF`、`HTPB` 等关键词，搜索关系路径。

普通 RAG 和知识图谱的分工：

```text
Chroma: 查原文 evidence chunk
Neo4j: 查 Paper -> Entity 的结构化关系
```

Neo4j 是增强层，不是系统单点依赖。没有图谱时，系统仍能基于 Chroma 和 keyword retrieval 回答；有图谱时，Agent 可以额外融合实体关系证据。

## 运行命令

在项目根目录运行：

```bash
cd D:\codex\slzh\ai-app-engineer-roadmap
.\.venv\Scripts\python.exe -m streamlit run demo\streamlit_app.py --server.port 8501 --server.address localhost
```

如果 8501 被占用，换一个端口：

```bash
.\.venv\Scripts\python.exe -m streamlit run demo\streamlit_app.py --server.port 8502 --server.address localhost
```

FastAPI 后端可单独启动：

```bash
cd D:\codex\slzh\ai-app-engineer-roadmap
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload --port 8000
```

Neo4j 可选启动：

```bash
docker run --name em-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
```

## 验证方式

先跑测试：

```bash
.\.venv\Scripts\python.exe -m pytest -q
```

再打开 Streamlit，按这个顺序验证：

1. 进入“文献库概览”，点击“构建/更新 PDF 文献库索引”。
2. 检查结果里有实际处理 PDF 数、生成 chunk 数、跳过无 PDF 记录数和 collection 名称。
3. 进入“知识图谱”，点击“构建/更新知识图谱”。
4. 搜索 `RDX` 或 `ReaxFF`，确认能看到 Paper -> Entity 关系路径。
5. 进入“文献问答”，提问：

```text
哪些论文涉及 RDX/HTPB 热分解，它们使用了哪些模拟方法？
```

6. 检查回答是否展示“检索计划”“知识图谱命中”“证据片段”“引用与证据校验”和“Agent 执行轨迹”。

## 简历表达

可以写：

> 构建中文 Streamlit 科研问答 Demo，将 PDF 文献库索引、Agentic RAG 问答、Neo4j 图谱构建和实体关系搜索集成到可展示界面，并通过 evidence、KG 命中、trace 和 citation check 展示系统推理链路。
