# Stage 5: Neo4j Graph

核心文件：

- [core/graph_store.py](../../core/graph_store.py)
- [core/kg_retriever.py](../../core/kg_retriever.py)
- [core/literature_graph_builder.py](../../core/literature_graph_builder.py)

## 本阶段解决什么问题

向量库擅长找文本片段，但不擅长回答关系问题：

```text
哪些 Paper 使用 ReaxFF？
哪些 Material 和 thermal decomposition 相关？
某个 Finding 有哪些 evidence chunk 支撑？
```

图数据库适合表达这类关系。这里 Neo4j 是增强层，不替代 Chroma。项目的设计是：

```text
Chroma: 文本 evidence 检索
Neo4j: 实体关系查询
Agent: 融合两类上下文
```

## 图谱模型

当前节点包括：

```text
Paper
Material
Method
ForceField
Software
Property
Finding
EvidenceChunk
```

核心关系包括：

```text
Paper -[:STUDIES]-> Material
Paper -[:USES_METHOD]-> Method
Paper -[:USES_FORCE_FIELD]-> ForceField
Paper -[:USES_SOFTWARE]-> Software
Paper -[:REPORTS]-> Property
Finding -[:SUPPORTED_BY]-> EvidenceChunk
```

图谱构建只消费 PDF chunk 的抽取结果。Manifest 中的 metadata-only 候选论文不会生成 `Paper`、`Material` 或 `Finding` 节点。这样做可以避免图谱里出现“有论文节点但没有 evidence chunk 支撑”的关系。

## `graph_store.py` 怎么读

`Neo4jGraphStore.__init__()` 里有一个重要判断：

```python
if GraphDatabase is None:
    raise GraphUnavailableError(...)
```

这让 Neo4j 成为可选能力。没有安装 driver 或没有启动 Docker 时，文本 RAG 仍可运行。

`init_constraints()` 创建唯一约束：

```cypher
CREATE CONSTRAINT paper_id_unique IF NOT EXISTS
FOR (n:Paper) REQUIRE n.paper_id IS UNIQUE
```

唯一约束的作用是防止重复入库时创建重复节点。

`upsert_extraction()` 是写图谱的核心。它先写 `Paper` 和 `EvidenceChunk`，再根据抽取结果写 `Material`、`Method`、`ForceField` 等节点和关系。这里大量使用 `MERGE`，不是 `CREATE`：

```cypher
MERGE (m:Material {name: $name})
MERGE (p)-[:STUDIES]->(m)
```

`MERGE` 的含义是“有就复用，没有就创建”，适合反复构建图谱。

## `kg_retriever.py` 怎么读

`retrieve_kg_evidence(query_terms)` 接收 Agent 识别出的实体词，例如 `RDX`、`ReaxFF`。它用 Cypher 查询相关 Paper 和实体：

```cypher
MATCH (p:Paper)-[r]->(n)
WHERE toLower(n.name) CONTAINS toLower($term)
RETURN p.paper_id, p.title, type(r), labels(n), n.name
```

返回结果会进入 Agent 的 `kg_context`。

## 启动 Neo4j

```bash
docker run --name em-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5
```

`.env` 中默认配置：

```env
NEO4J_URI=bolt://localhost:7687
NEO4J_USERNAME=neo4j
NEO4J_PASSWORD=password
```

## 简历表达

可以写：

> 使用 Neo4j 构建材料-方法-力场-性能-结论知识图谱，通过 Cypher 查询补充文本检索结果，实现图文联合 evidence fusion。
