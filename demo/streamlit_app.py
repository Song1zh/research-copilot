import time
import sys
from pathlib import Path

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import (
    CHROMA_DB_PATH,
    LITERATURE_CHROMA_COLLECTION,
    LITERATURE_CORPUS_DIR,
    NEO4J_PASSWORD,
    NEO4J_URI,
    NEO4J_USERNAME,
)
from core.graph_store import Neo4jGraphStore
from core.literature_graph_builder import build_literature_graph
from core.literature_indexer import index_literature_corpus
from core.literature_manifest import load_paper_records, summarize_records
from core.vector_store import ChromaVectorStore
from workflows.literature_agent_workflow import run_literature_agent_workflow

st.set_page_config(
    page_title = "含能材料模拟文献助手",
    page_icon = "📄",
    layout="wide",
)

st.title("含能材料模拟文献助手")
st.caption("Energetic Materials Simulation Copilot | 实验室文献问答与可追溯评测系统")

embedding_provider = st.sidebar.selectbox(
    "Embedding Provider",
    options=["local_hash", "dashscope"],
    index=0,
    help="两种 provider 使用不同 Chroma collection；云模式失败时不会静默降级。",
)

reranker_provider = st.sidebar.selectbox(
    "Reranker Provider",
    options=["dashscope", "none"],
    index=0,
    help="混合检索后调用 qwen3-rerank；云端失败时不静默降级。",
)

kg_provider = st.sidebar.selectbox(
    "Knowledge Graph Provider",
    options=["neo4j", "none"],
    index=0,
    help="显式启用或关闭Neo4j；关闭时不会连接图数据库。",
)

def render_list_block(title:str, items:list[str]):
    st.subheader(title)
    if not items:
        st.info("无")
        return
    for idx, item in enumerate(items, start=1):
        st.markdown(f"{idx}. {item}")

def render_evidence_block(evidence_items:list[str]):
    st.subheader("证据片段")
    if not evidence_items:
        st.info("暂无证据片段")
        return

    for item in evidence_items:
        evidence_id = item.get("evidence_id","UNKNOWN")
        chunk_id = item.get("chunk_id","UNKNOWN")
        source_path = item.get("source_path","UNKNOWN")
        snippet = item.get("snippet","")
        rerank_score = item.get("rerank_score")

        with st.expander(f"{evidence_id} | chunk_id={chunk_id}"):
            st.markdown(f"**来源路径**: `{source_path}`")
            st.markdown("**片段内容**:")
            st.write(snippet)
            if rerank_score is not None:
                st.caption(
                    f"qwen3-rerank={rerank_score:.4f} | "
                    f"hybrid={item.get('pre_rerank_score')} | "
                    f"pre-rank={item.get('pre_rerank_rank')}"
                )

def render_kg_relations_block(kg_context: dict):
    st.subheader("知识图谱命中")
    if not kg_context:
        st.info("暂无知识图谱上下文。")
        return

    if not kg_context.get("available"):
        st.warning("Neo4j 图谱未参与本次回答，当前结果仅基于文本混合检索。")
        error = kg_context.get("error")
        if error:
            st.code(str(error))
        return

    items = kg_context.get("items", [])
    if not items:
        st.info("Neo4j 已连接，但未命中与当前问题实体相关的关系。")
        return

    st.success(f"命中 {len(items)} 条图谱关系。")
    st.dataframe(
        [
            {
                "路径": item.get("path_text", ""),
                "论文ID": item.get("paper_id", ""),
                "关系": item.get("relation", ""),
                "实体类型": item.get("entity_label", ""),
                "实体": item.get("entity_name", ""),
                "chunk": item.get("evidence_chunk_id", ""),
                "证据": item.get("evidence_text", ""),
            }
            for item in items
        ],
        use_container_width=True,
    )


def render_generation_status(final_output: dict):
    mode = final_output.get("generation_mode", "unknown")
    if mode == "llm":
        st.success("回答生成模式：LLM 已基于文本 evidence 和知识图谱上下文生成。")
    elif mode == "template_fallback":
        st.warning("回答生成模式：LLM 不可用或输出未通过校验，已降级为规则模板。")
        if final_output.get("llm_error"):
            st.code(str(final_output["llm_error"]))
    elif mode == "no_evidence":
        st.info("回答生成模式：未检索到 evidence，未调用 LLM。")
    else:
        st.info(f"回答生成模式：{mode}")


tab_overview, tab_literature_qa, tab_graph = st.tabs(
    ["文献库概览", "文献问答", "知识图谱"]
)

with tab_overview:
    st.subheader("文献库概览")
    candidate_records = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=True)
    records = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=False)
    candidate_summary = summarize_records(candidate_records)
    summary = summarize_records(records)
    skipped_metadata_only = candidate_summary["metadata_only"]

    try:
        indexed_chunk_count = ChromaVectorStore(
            db_path=str(CHROMA_DB_PATH),
            collection_name=LITERATURE_CHROMA_COLLECTION,
            embedding_provider=embedding_provider,
        ).count()
    except Exception:
        indexed_chunk_count = 0

    col_a, col_b, col_c, col_d = st.columns(4)
    col_a.metric("候选文献总数", candidate_summary["total"])
    col_b.metric("可入库 PDF 论文", summary["full_text_pdf"])
    col_c.metric("已索引 chunk", indexed_chunk_count)
    col_d.metric("高优先级 PDF", summary["high_priority"])

    st.info(
        "正式文献库只使用已有 PDF。无 PDF 的 metadata-only 记录仅作为候选清单保留，"
        f"本次会跳过 {skipped_metadata_only} 条。"
    )

    st.markdown("**构建/更新 PDF 文献库索引是什么意思？**")
    st.markdown(
        "- 读取本地 PDF 文献\n"
        "- 抽取 PDF 文本\n"
        "- 按 Abstract、Methods、Results 等 section 切分证据 chunk\n"
        "- 写入 Chroma 向量库\n"
        "- 后续文献问答会基于这些 chunk 检索证据"
    )

    max_papers = None
    with st.expander("高级设置 / 学习模式", expanded=False):
        st.warning(
            "学习模式只用于快速调试或课堂演示。正式问答请索引全部 PDF，"
            "否则相关论文可能没有进入知识库，答案会漏证据。"
        )
        use_limit = st.checkbox("仅索引前 N 篇 PDF", value=False)
        if use_limit:
            max_papers = st.number_input(
                "N",
                min_value=1,
                max_value=max(summary["full_text_pdf"], 1),
                value=min(20, max(summary["full_text_pdf"], 1)),
                help="只限制本次写入索引的 PDF 数量，不代表文献库总量。",
            )

    if st.button("构建/更新 PDF 文献库索引", type="primary"):
        with st.spinner("正在解析文献并写入 Chroma..."):
            result = index_literature_corpus(
                corpus_root=LITERATURE_CORPUS_DIR,
                db_path=CHROMA_DB_PATH,
                collection_name=LITERATURE_CHROMA_COLLECTION,
                max_papers=int(max_papers) if max_papers else None,
                include_metadata_only=False,
                embedding_provider=embedding_provider,
            )
        st.success("索引完成")
        col_result_a, col_result_b, col_result_c, col_result_d = st.columns(4)
        col_result_a.metric("实际处理 PDF", result.paper_count)
        col_result_b.metric("生成 chunk", result.chunk_count)
        col_result_c.metric("跳过无 PDF 记录", result.skipped_metadata_only_count)
        col_result_d.metric("Collection", result.collection_name)
        st.caption(f"Embedding provider: {result.embedding_provider}")
        st.json(result.__dict__)

    st.dataframe(
        [
            {
                "论文ID": record.paper_id,
                "标题": record.title,
                "来源": record.source_group,
                "优先级": record.ingestion_priority,
                "已有PDF": record.has_pdf,
                "标签": record.topic_tags,
            }
            for record in records
        ],
        use_container_width=True,
    )

with tab_literature_qa:
    st.subheader("文献库 Agentic RAG 问答")
    st.caption("请先在“文献库概览”中构建 PDF 文献库索引。回答会展示检索计划、证据片段和校验结果。")
    lit_query = st.text_area(
        "输入文献库问题",
        value="哪些论文涉及 RDX/HTPB 热分解，它们使用了哪些模拟方法？",
        height=120,
    )
    if st.button("运行文献问答 Agent", type="primary"):
        if not lit_query.strip():
            st.error("问题不能为空")
            st.stop()
        with st.spinner("正在进行问题分析、混合检索、KG 检索和证据融合..."):
            start = time.perf_counter()
            result = run_literature_agent_workflow(
                query=lit_query,
                collection_name=LITERATURE_CHROMA_COLLECTION,
                db_path=str(CHROMA_DB_PATH),
                embedding_provider=embedding_provider,
                reranker_provider=reranker_provider,
                kg_provider=kg_provider,
            )
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        final_output = result.get("final_output", {})
        st.metric("耗时 ms", elapsed_ms)
        render_generation_status(final_output)
        st.subheader("回答摘要")
        st.write(final_output.get("summary", ""))

        st.subheader("检索计划")
        st.json(result.get("query_plan", []))

        st.subheader("多论文对比表")
        st.dataframe(final_output.get("comparison_table", []), use_container_width=True)

        render_list_block("机制总结", final_output.get("mechanisms", []))
        render_list_block("局限性", final_output.get("limitations", []))
        render_kg_relations_block(final_output.get("kg_context", {}))
        render_evidence_block(final_output.get("evidence", []))

        st.subheader("引用与证据校验")
        st.json(result.get("alignment_check", {}))

        st.subheader("Agent 执行轨迹")
        st.json(result.get("trace", []))

with tab_graph:
    st.subheader("Neo4j 图谱状态")
    st.caption("知识图谱只从已有 PDF 文献抽取实体和关系；无 PDF 的候选记录不会进入图谱。")
    st.markdown(
        "**普通 RAG vs 知识图谱：** 普通 RAG 从 Chroma 找原文片段；知识图谱把论文中的材料、方法、力场、软件、性质和发现抽成节点与关系，"
        "用于回答“谁研究了什么、用了什么方法、报告了什么性质”这类结构化问题。"
    )
    graph = None
    try:
        graph = Neo4jGraphStore()
        graph.verify()
        st.success("Neo4j 已连接")
        summary = graph.entity_summary().__dict__
        col_g1, col_g2, col_g3, col_g4 = st.columns(4)
        col_g1.metric("论文", summary.get("papers", 0))
        col_g2.metric("材料", summary.get("materials", 0))
        col_g3.metric("方法", summary.get("methods", 0))
        col_g4.metric("发现", summary.get("findings", 0))
        col_g5, col_g6, col_g7 = st.columns(3)
        col_g5.metric("力场", summary.get("force_fields", 0))
        col_g6.metric("软件", summary.get("software", 0))
        col_g7.metric("性质", summary.get("properties", 0))
    except Exception as e:
        st.warning("Neo4j 暂不可用。文本 RAG 仍可运行。")
        st.code(str(e))
        st.markdown("**当前 Neo4j 配置**")
        st.json(
            {
                "NEO4J_URI": NEO4J_URI,
                "NEO4J_USERNAME": NEO4J_USERNAME,
                "NEO4J_PASSWORD": NEO4J_PASSWORD,
            }
        )
        st.markdown("**Docker 启动示例**")
        st.code(
            "docker run --name em-neo4j -p 7474:7474 -p 7687:7687 -e NEO4J_AUTH=neo4j/password neo4j:5",
            language="bash",
        )
    finally:
        if graph is not None:
            graph.close()

    graph_records = load_paper_records(LITERATURE_CORPUS_DIR, include_metadata_only=False)
    graph_summary = summarize_records(graph_records)
    graph_max_papers = None
    with st.expander("图谱构建设置 / 学习模式", expanded=False):
        st.info("图谱构建只处理已有 PDF 的文献，并从 Methods、Results、Conclusion 等 chunk 抽取结构化实体。")
        graph_use_limit = st.checkbox("仅为前 N 篇 PDF 构建图谱", value=False, key="graph_use_limit")
        if graph_use_limit:
            graph_max_papers = st.number_input(
                "图谱 PDF 数量 N",
                min_value=1,
                max_value=max(graph_summary["full_text_pdf"], 1),
                value=min(20, max(graph_summary["full_text_pdf"], 1)),
                key="graph_max_papers",
            )

    if st.button("构建/更新知识图谱", type="primary"):
        with st.spinner("正在抽取实体关系并写入 Neo4j..."):
            graph_result = build_literature_graph(
                graph_records,
                max_papers=int(graph_max_papers) if graph_max_papers else None,
            )
        if graph_result.ok:
            st.success("知识图谱构建完成")
        else:
            st.error("知识图谱构建失败")
        st.json(graph_result.__dict__)

    st.subheader("实体关系搜索")
    relation_term = st.text_input("输入材料、方法、力场、软件、性质或论文关键词", value="RDX")
    relation_limit = st.number_input("最多返回关系数", min_value=1, max_value=100, value=25)
    if st.button("搜索图谱关系"):
        graph = None
        try:
            graph = Neo4jGraphStore()
            graph.verify()
            relation_items = graph.query_relations(term=relation_term, limit=int(relation_limit))
            if not relation_items:
                st.info("没有找到匹配的图谱关系。")
            else:
                st.dataframe(
                    [
                        {
                            "路径": item.get("path_text", ""),
                            "论文ID": item.get("paper_id", ""),
                            "标题": item.get("title", ""),
                            "关系": item.get("relation", ""),
                            "实体类型": item.get("entity_label", ""),
                            "实体": item.get("entity_name", ""),
                            "chunk": item.get("evidence_chunk_id", ""),
                            "证据": item.get("evidence_text", ""),
                        }
                        for item in relation_items
                    ],
                    use_container_width=True,
                )
        except Exception as e:
            st.warning("Neo4j 暂不可用，无法搜索图谱关系。")
            st.code(str(e))
        finally:
            if graph is not None:
                graph.close()
