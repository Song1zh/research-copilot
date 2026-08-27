import time
from typing import Literal
from pydantic import BaseModel, Field

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from schemas.api_response import ApiResponse
from core.api_response import success_response, failure_response
from core.config import CHROMA_DB_PATH
from core.config import LITERATURE_CHROMA_COLLECTION, LITERATURE_CORPUS_DIR
from core.graph_store import Neo4jGraphStore
from core.literature_graph_builder import build_literature_graph
from core.literature_indexer import index_literature_corpus
from core.literature_manifest import load_paper_records, summarize_records
from workflows.literature_agent_workflow import run_literature_agent_workflow

#1.创建FastAPI应用实例
app = FastAPI(
    title="Literature Copilot API",
    description="PDF 文献库 Agentic RAG + Neo4j 知识图谱 API",
    version="1.0",
)


class LiteratureIndexRequest(BaseModel):
    max_papers: int | None = Field(default=None, description="学习/调试用：最多索引前 N 篇 PDF；None 表示索引全部 PDF")
    build_graph: bool = Field(default=False, description="是否同时构建 Neo4j 图谱")
    collection_name: str = Field(default=LITERATURE_CHROMA_COLLECTION, description="Chroma collection 名称")
    embedding_provider: Literal["local_hash", "dashscope"] = Field(
        default="local_hash",
        description="显式选择离线 hash 或 DashScope 云向量；两者使用不同 collection",
    )


class LiteratureAskRequest(BaseModel):
    query: str = Field(..., description="面向文献库的问题")
    collection_name: str = Field(default=LITERATURE_CHROMA_COLLECTION, description="Chroma collection 名称")
    embedding_provider: Literal["local_hash", "dashscope"] = Field(
        default="local_hash",
        description="必须与建库时使用的 embedding provider 一致",
    )
    reranker_provider: Literal["none", "dashscope"] = Field(
        default="dashscope",
        description="显式选择云端重排；调用失败时不静默降级",
    )
    kg_provider: Literal["none", "neo4j"] = Field(
        default="neo4j",
        description="显式关闭或启用 Neo4j；用于功能运行和 A/B 评测",
    )


class LiteratureGraphBuildRequest(BaseModel):
    max_papers: int | None = Field(default=None, description="学习/调试用：最多处理前 N 篇 PDF；None 表示处理全部 PDF")
    replace_existing: bool = Field(default=False, description="是否先清理现有项目图谱后完整重建")

#2.接口1：健康检查接口，验证服务是否正常运行
@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    body = failure_response(
        code="HTTP_ERROR",
        message=str(exc.detail),
        stage="http",
        details=None,
    )
    return JSONResponse(status_code=exc.status_code, content=body.model_dump())
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    body = failure_response(
        code="REQUEST_VALIDATION_ERROR",
        message="请求参数校验失败",
        stage="request_validation",
        details=exc.errors(),
    )
    return JSONResponse(status_code=422, content=body.model_dump())


@app.get("/literature/papers", response_model=ApiResponse)
def list_literature_papers() -> ApiResponse:
    candidate_records = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=True)
    records = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=False)
    candidate_summary = summarize_records(candidate_records)
    summary = summarize_records(records)
    return success_response(
        message="文献库清单读取成功",
        data={
            "summary": summary,
            "candidate_summary": candidate_summary,
            "skipped_metadata_only_count": candidate_summary["metadata_only"],
            "papers": [
                {
                    "paper_id": record.paper_id,
                    "title": record.title,
                    "year": record.year,
                    "journal": record.journal,
                    "doi": record.doi,
                    "topic_tags": record.topic_tags,
                    "source_group": record.source_group,
                    "category": record.category,
                    "ingestion_priority": record.ingestion_priority,
                    "has_pdf": record.has_pdf,
                    "source_type": record.source_type,
                }
                for record in records
            ],
        },
    )


@app.post("/literature/index", response_model=ApiResponse)
def index_literature(req: LiteratureIndexRequest) -> ApiResponse:
    start = time.perf_counter()
    result = index_literature_corpus(
        corpus_root=LITERATURE_CORPUS_DIR,
        db_path=CHROMA_DB_PATH,
        collection_name=req.collection_name,
        max_papers=req.max_papers,
        include_metadata_only=False,
        embedding_provider=req.embedding_provider,
    )

    graph_result = None
    if req.build_graph:
        records = load_paper_records(
            LITERATURE_CORPUS_DIR,
            include_metadata_only=False,
        )
        graph_result = build_literature_graph(records, max_papers=req.max_papers).__dict__

    return success_response(
        message="文献库索引完成",
        data={
            "paper_count": result.paper_count,
            "full_text_count": result.full_text_count,
            "metadata_only_count": result.metadata_only_count,
            "skipped_metadata_only_count": result.skipped_metadata_only_count,
            "chunk_count": result.chunk_count,
            "collection_name": result.collection_name,
            "embedding_provider": result.embedding_provider,
            "graph_result": graph_result,
        },
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


@app.post("/literature/ask", response_model=ApiResponse)
def ask_literature(req: LiteratureAskRequest) -> ApiResponse:
    start = time.perf_counter()
    result = run_literature_agent_workflow(
        query=req.query,
        collection_name=req.collection_name,
        db_path=str(CHROMA_DB_PATH),
        embedding_provider=req.embedding_provider,
        reranker_provider=req.reranker_provider,
        kg_provider=req.kg_provider,
    )
    return success_response(
        message="文献库问答完成",
        data={
            "collection_name": req.collection_name,
            "embedding_provider": req.embedding_provider,
            "reranker_provider": req.reranker_provider,
            "kg_provider": req.kg_provider,
            "question_type": result.get("question_type"),
            "query_plan": result.get("query_plan", []),
            "final_output": result.get("final_output", {}),
            "alignment_check": result.get("alignment_check", {}),
            "trace": result.get("trace", []),
            "error": result.get("error"),
        },
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


@app.get("/literature/graph/entities", response_model=ApiResponse)
def literature_graph_entities() -> ApiResponse:
    graph = None
    try:
        graph = Neo4jGraphStore()
        graph.verify()
        summary = graph.entity_summary().__dict__
        return success_response(
            message="Neo4j 图谱实体统计读取成功",
            data={"available": True, **summary},
        )
    except Exception as exc:
        return success_response(
            message="Neo4j 图谱暂不可用",
            data={"available": False, "error": str(exc)},
        )
    finally:
        if graph is not None:
            graph.close()

@app.post("/literature/graph/build", response_model=ApiResponse)
def build_literature_graph_endpoint(req: LiteratureGraphBuildRequest) -> ApiResponse:
    start = time.perf_counter()
    records = load_paper_records(
        LITERATURE_CORPUS_DIR,
        include_metadata_only=False,
    )
    result = build_literature_graph(
        records,
        max_papers=req.max_papers,
        replace_existing=req.replace_existing,
    )

    summary = None
    if result.ok:
        graph = None
        try:
            graph = Neo4jGraphStore()
            graph.verify()
            summary = graph.entity_summary().__dict__
        except Exception as exc:
            summary = {"available": False, "error": str(exc)}
        finally:
            if graph is not None:
                graph.close()

    return success_response(
        message="Neo4j 图谱构建完成" if result.ok else "Neo4j 图谱构建失败",
        data={
            "available": result.ok,
            "ok": result.ok,
            "extraction_count": result.extraction_count,
            "error": result.error,
            "entity_summary": summary,
        },
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )


@app.get("/literature/graph/relations", response_model=ApiResponse)
def literature_graph_relations(
    term: str = Query(default="", description="实体、论文标题或 paper_id 关键词"),
    limit: int = Query(default=25, ge=1, le=100, description="最多返回关系行数"),
) -> ApiResponse:
    graph = None
    try:
        graph = Neo4jGraphStore()
        graph.verify()
        items = graph.query_relations(term=term, limit=limit)
        return success_response(
            message="Neo4j 图谱关系读取成功",
            data={
                "available": True,
                "term": term,
                "limit": limit,
                "items": items,
            },
        )
    except Exception as exc:
        return success_response(
            message="Neo4j 图谱暂不可用",
            data={
                "available": False,
                "term": term,
                "limit": limit,
                "items": [],
                "error": str(exc),
            },
        )
    finally:
        if graph is not None:
            graph.close()

