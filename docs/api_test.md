# API 联调记录

## 目标

验证当前 FastAPI 服务提供 PDF 文献库 Agentic RAG 和 Neo4j 知识图谱能力。旧版上传问答入口已移除，不再作为 API 联调对象。

## 启动服务

```bash
uvicorn app.main:app --reload
```

Swagger 地址：

```text
http://127.0.0.1:8000/docs
```

## 接口列表

- `GET /health`
- `GET /literature/papers`
- `POST /literature/index`
- `POST /literature/ask`
- `GET /literature/graph/entities`
- `POST /literature/graph/build`
- `GET /literature/graph/relations`

## 1. 健康检查

请求：

```text
GET /health
```

预期：

```json
{
  "status": "ok"
}
```

## 2. 文献库清单

请求：

```text
GET /literature/papers
```

预期：

- `success=true`
- `data.summary.full_text_pdf >= 1`
- `data.papers` 只包含已有 PDF 的正式入库论文

## 3. 构建文献库索引

请求：

```text
POST /literature/index
```

请求体：

```json
{
  "max_papers": null,
  "build_graph": false,
  "collection_name": "energetic_materials_literature",
  "embedding_provider": "local_hash"
}
```

预期：

- 返回 `chunk_count`
- 返回 `collection_name`
- 返回 `embedding_provider`
- 实际 collection 会自动增加 provider 与维度后缀，防止不同向量空间混用
- `skipped_metadata_only_count` 记录无 PDF 候选数量

## 4. 文献库问答

请求：

```text
POST /literature/ask
```

请求体：

```json
{
  "query": "哪些论文涉及 RDX/HTPB 热分解，它们使用了哪些模拟方法？",
  "collection_name": "energetic_materials_literature",
  "embedding_provider": "local_hash"
}
```

预期：

- 返回 `final_output.summary`
- 返回 `final_output.evidence`
- 返回 `final_output.kg_context`
- 返回 `trace`
- Neo4j 不可用时不影响文本 RAG 返回
- 问答时的 `embedding_provider` 必须与建库时一致

## Embedding provider约定

- `local_hash`：64维确定性离线向量，用于本地演示和测试。
- `dashscope`：调用OpenAI兼容的 `text-embedding-v4`，默认1024维。

### Reranker 参数

`POST /literature/ask` 支持显式 `reranker_provider`：

- `dashscope`：混合检索融合去重后，调用 `qwen3-rerank` 对候选片段重排；
- `none`：保留混合检索排序，用于离线测试和 A/B 基线；
- 默认值为 `dashscope`，云端失败不会静默回退到 `none`。

```json
{
  "query": "RDX 热分解研究使用了哪些模拟方法？",
  "embedding_provider": "local_hash",
  "reranker_provider": "dashscope"
}
```

成功结果的 evidence 内会保留 `hybrid_score`、`pre_rerank_rank`、
`pre_rerank_score`、`rerank_score`、`reranker_model`、候选数量和重排耗时。
- 两种provider使用独立collection。
- 云模式缺少密钥、欠费或调用失败时直接报错，不会静默退回hash。

## 5. 图谱实体统计

请求：

```text
GET /literature/graph/entities
```

预期：

- Neo4j 可用时返回 `available=true` 和实体数量。
- Neo4j 不可用时返回 `available=false` 和错误信息，HTTP 仍为 200。

## 6. 构建知识图谱

请求：

```text
POST /literature/graph/build
```

请求体：

```json
{
  "max_papers": null
}
```

预期：

- Neo4j 可用时返回 `ok=true`
- 返回 `extraction_count`
- 返回 `entity_summary`

## 7. 搜索图谱关系

请求：

```text
GET /literature/graph/relations?term=ReaxFF&limit=25
```

预期：

- Neo4j 可用时返回 `items`
- 每条关系包含 `paper_id`、`title`、`relation`、`entity_label`、`entity_name`、`evidence_chunk_id`、`evidence_text`、`path_text`
- `path_text` 示例：`(Paper: P1) -[:USES_FORCE_FIELD]-> (ForceField: ReaxFF)`

## 结论

当前 API 对外能力集中在 PDF 文献库索引、文献问答和 Neo4j 知识图谱。
