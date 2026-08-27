# Demo 使用指南

本文档说明如何通过 FastAPI Swagger 和 Streamlit 复现当前文献库 Agentic RAG + Neo4j 知识图谱 Demo。

## 前置准备

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
copy .env.example .env
```

如需知识图谱功能，启动 Neo4j：

```bash
docker run --name em-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
```

Neo4j 未启动时，文本 RAG 仍可运行。

## FastAPI Demo

启动 API 服务：

```bash
uvicorn app.main:app --reload
```

打开 Swagger：

```text
http://127.0.0.1:8000/docs
```

### 1. 健康检查

调用 `GET /health`。

预期响应：

```json
{
  "status": "ok"
}
```

### 2. 查看文献库清单

调用 `GET /literature/papers`。

预期行为：

- 返回候选文献统计。
- 返回可入库 PDF 文献列表。
- metadata-only 记录不会进入正式 RAG 和图谱。

### 3. 构建 PDF 文献库索引

调用 `POST /literature/index`：

```json
{
  "max_papers": null,
  "build_graph": false,
  "collection_name": "energetic_materials_literature"
}
```

预期行为：

- 读取本地 PDF 文献。
- 抽取 PDF 文本。
- 按 section 切分 evidence chunk。
- 写入 Chroma collection。

### 4. 构建知识图谱

调用 `POST /literature/graph/build`：

```json
{
  "max_papers": null
}
```

预期行为：

- 从已有 PDF chunk 中抽取材料、方法、力场、软件、性质和发现。
- 写入 Neo4j。
- 返回抽取数量和实体统计。

### 5. 搜索图谱关系

调用：

```text
GET /literature/graph/relations?term=ReaxFF&limit=25
```

预期返回 Paper -> Entity 关系路径，例如：

```text
(Paper: P1) -[:USES_FORCE_FIELD]-> (ForceField: ReaxFF)
```

### 6. 文献库问答

调用 `POST /literature/ask`：

```json
{
  "query": "哪些论文涉及 RDX/HTPB 热分解，它们使用了哪些模拟方法？",
  "collection_name": "energetic_materials_literature"
}
```

预期行为：

- 返回问题类型、检索计划、结构化回答、evidence、KG context 和 Agent trace。
- Neo4j 可用且命中时，`kg_context.items` 中展示图谱关系。
- Neo4j 不可用时，回答会说明图谱未参与，本次仅基于文本混合检索。

## Streamlit Demo

启动 Streamlit：

```bash
streamlit run demo/streamlit_app.py
```

打开页面：

```text
http://localhost:8501
```

推荐手动流程：

1. 进入“文献库概览”，点击“构建/更新 PDF 文献库索引”。
2. 进入“知识图谱”，确认 Neo4j 状态；点击“构建/更新知识图谱”。
3. 在“实体关系搜索”中输入 `RDX` 或 `ReaxFF`，查看路径、论文 ID、实体和 evidence。
4. 进入“文献问答”，提问文献库问题。
5. 查看回答摘要、多论文对比表、知识图谱命中、证据片段、引用校验和 Agent trace。

## Demo 讲解要点

- Chroma 负责找原文 evidence。
- Neo4j 负责找 Paper -> Entity 的结构化关系。
- Agent trace 展示问题分析、检索计划、混合检索、KG 检索和证据融合过程。
- Citation alignment 用于检查回答中的 `[E#]` 是否真实存在。
- Neo4j 是增强层，不是单点依赖；图谱不可用时文本 RAG 仍可运行。
