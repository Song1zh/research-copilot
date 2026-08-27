# Stage 6: Agentic RAG Workflow

核心文件：[workflows/literature_agent_workflow.py](../../workflows/literature_agent_workflow.py)

## 本阶段解决什么问题

普通 RAG 常见流程是：

```text
query -> retrieve -> generate
```

Agentic RAG 的重点不是“让模型自由调用工具”，而是把复杂问答拆成可观察节点：

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

每个节点都把中间结果写入 trace，方便调试和面试展示。

## State 怎么读

`LiteratureAgentState` 是整个 workflow 的共享状态：

```python
class LiteratureAgentState(TypedDict):
    query: str
    question_type: str
    query_terms: list[str]
    text_evidence: list[dict[str, Any]]
    kg_context: dict[str, Any]
    final_output: dict[str, Any]
    trace: list[dict[str, Any]]
```

可以把它理解为节点之间传递的“工作台”。每个节点只读自己需要的字段，再写入新字段。

## 节点逐段解析

`question_analyzer()` 判断问题类型：

```python
if "对比" in query:
    question_type = "comparison"
elif "decomposition" in query:
    question_type = "mechanism"
```

它还会从问题里抓实体词，比如 `RDX`、`ReaxFF`、`HTPB`。这些词会交给 KG 检索。

`query_planner()` 目前是规则计划器：

```python
Use hybrid retrieval
Use KG retrieval
Fuse evidence
```

第一版没有必要让 LLM 生成计划，因为固定流程更稳定、更容易学习。

`hybrid_retriever_node()` 调用混合检索：

```python
retrieve_hybrid_evidence(query=state["query"], top_k=6)
```

这一步返回文本 evidence。

`kg_retriever_node()` 调用图谱检索：

```python
retrieve_kg_evidence(state.get("query_terms", []))
```

如果 Neo4j 不可用，它会把错误写入 `kg_context`，但不中断流程。

`evidence_fusion()` 用 `paper_id::chunk_id` 去重。这样同一个 chunk 即使被 vector 和 keyword 同时召回，也只出现一次。

`answer_generator()` 生成可展示结果。当前主链路会构造 evidence + KG context prompt 调用 LLM，并要求模型输出结构化 JSON；如果 LLM 不可用、JSON 不合法或 citation alignment 不通过，则降级为规则模板：

- `summary`
- `comparison_table`
- `mechanisms`
- `methods`
- `findings`
- `limitations`
- `evidence`
- `query_plan`
- `kg_context`
- `generation_mode`
- `llm_error`

它会调用 `build_evidence_items()` 生成 `[E1]`、`[E2]` 这类引用。真实 evidence、query_plan 和 kg_context 由后端固定注入，避免 LLM 自造证据来源。

`citation_verifier()` 调用旧项目已有的引用校验：

```python
check_answer_evidence_alignment(final_output)
```

这一步检查回答中的 `[E#]` 是否真实存在。

`self_reflection()` 做轻量自检：

- evidence 太少，加入 limitation。
- citation alignment 不通过，提示人工复核。

## 为什么这就是 Agentic RAG

它不是因为“用了 LangGraph”才叫 Agentic RAG，而是因为它把回答过程拆成了可观察、可替换、可验证的步骤。后续可以逐步把规则节点替换成 LLM 节点，但状态结构和 trace 机制不用推倒重来。

## 验证方式

先在 Streamlit 的“文献库概览”里构建 PDF 索引，再到“文献问答”里提问：

```text
哪些论文涉及 RDX/HTPB 热分解，它们使用了哪些模拟方法？
```

观察三个区域：

- “检索计划”
- “证据片段”
- “Agent 执行轨迹”

如果“文献库概览”里打开了“高级设置 / 学习模式”，只索引前 N 篇 PDF，那么 Agent 只能检索这 N 篇里的 evidence。正式演示和自测时应关闭这个限制，保证所有已有 PDF 都进入索引。

也可以跑：

```bash
python -m pytest tests/test_literature_agent_workflow_contract.py -q
```

## 简历表达

可以写：

> 基于 LangGraph 实现 Agentic RAG 工作流，将科研问题拆解为问题分析、查询规划、混合检索、图谱检索、证据融合、引用校验和自反式检查，并通过 trace 展示完整推理过程。
