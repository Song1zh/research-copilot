from typing import Any, TypedDict
from langgraph.graph import StateGraph, START, END
from core.llm_client import LLMClient
from schemas import StructuredAnswer

# 定义工作流状态，相当于工作流的全局变量
class WorkflowState(TypedDict):
    query: str
    topic: str
    intent: str
    answer: str
    structured_output: dict[str, Any]
    trace: list[dict[str, Any]]
    error: str | None

# 日志追踪，Any万能类型注解
# -> 返回类型注解
def append_trace(
        state: WorkflowState,
        node_name: str,
        input_snapshot: dict[str, Any],
        output_snapshot: dict[str, Any],
) -> list[dict[str, Any]]: # 返回更新后的日志列表
    # 拿到状态里已有的日志，
    trace = list(state.get("trace", [])) # 从state里找trace的值，没有则空
    # 添加当前节点的输入输出
    trace.append(
        {
            "node": node_name,
            "input": input_snapshot,
            "output": output_snapshot,
        }
    )
    return trace

def understand_query(state: WorkflowState) -> dict[str, Any]:
    # 记录当前输入数据
    input_snapshot = {"query": state["query"]}

    query = state["query"].strip() #处理，去空格转小写
    q_lower = query.lower()

    # 识别用户意图（关键词匹配），解释类/对比类/通用问题
    if any(word in q_lower for word in ["what","什么","解释","介绍"]):
        intent = "explanation"
    elif any(word in q_lower for word in ["compare", "区别", "对比"]):
        intent = "comparison"
    else:
        intent = "general"

    topic = query[:30] if len(query) > 30 else query # 提取主题30字

    output_snapshot = {
        "topic": topic,
        "intent": intent,
    }

    print("\n[understand_query] input:")
    print(input_snapshot)
    print("\n[understand_query] output:")
    print(output_snapshot)

    # 更新意图
    return {
        "topic": topic,
        "intent": intent,
        "trace": append_trace(state, "understand_query", input_snapshot, output_snapshot)
    }

# 调用ai生成回答，异常兜底
def generate_answer(state: WorkflowState) -> dict[str, Any]:
    # 从共享状态里拿 问题、主题、意图
    input_snapshot = {
        "query": state["query"],
        "topic": state["topic"],
        "intent": state["intent"],
    }

    system_prompt = (
        "你是一名简洁、准确的中文助教。"
        "请根据用户问题给出直接回答，避免空话"
    )

    user_prompt = f"问题：{state['query']}\n请直接回答"

    #异常处理：调用ai大模型
    try:
        llm = LLMClient()
        answer = llm.chat(system_prompt=system_prompt,user_prompt=user_prompt)
        error = None
    except Exception as e:
        answer = f"[fallback] 这是一个 toy workflow 的兜底回答：你问的是“{state['query']}”。"
        error = str(e)

    output_snapshot = {
        "answer_preview": answer[:120], # 前120个字符
        "error": error,
    }
    print("\n[generate_answer] input:")
    print(input_snapshot)
    print("[generate_answer] output:")
    print(output_snapshot)

    return {
        "answer": answer,
        "error": error,
        "trace": append_trace(state, "generate_answer", input_snapshot, output_snapshot),
    }

# 格式化最终输出
def format_output(state: WorkflowState) -> dict[str, Any]:
    input_snapshot = {
        "topic": state["topic"],
        "intent": state["intent"],
        "answer_preview": state["answer"][:120],
        "error": state["error"],
    }

    error = state.get("error")
    uncertainty = None
    if error is not None:
        uncertainty = f"LLM调用失败，已使用fallback。错误信息：{error}"

    # 构造结构化答案(Pydantic模型，规范输出格式)
    structured = StructuredAnswer(
        topic=state["topic"],
        summary=state["answer"],
        key_points=[
            f"intent={state['intent']}",
            "workflow_path=understand_query->generate_answer->format_output",
            "这是toy workflow原型。",
        ],
        citations=[],
        uncertainty=uncertainty,
    )

    output_snapshot = {
        "structured_output": structured.model_dump(),
    }
    print("\n[format_output] input:")
    print(input_snapshot)
    print("[format_output] output:")
    print(output_snapshot)

    return {
        "structured_output": structured.model_dump(),
        "trace": append_trace(state, "format_output", input_snapshot, output_snapshot),
    }


def build_graph():
    graph_builder = StateGraph(WorkflowState)

    # 添加3个执行节点
    graph_builder.add_node("understand_query", understand_query)
    graph_builder.add_node("generate_answer", generate_answer)
    graph_builder.add_node("format_output", format_output)

    # 设置执行顺序(起始节点，终点节点) 开始->理解问题->生成回答->格式化->结束
    graph_builder.add_edge(START, "understand_query")
    graph_builder.add_edge("understand_query", "generate_answer")
    graph_builder.add_edge("generate_answer", "format_output")
    graph_builder.add_edge("format_output", END)

    return graph_builder.compile()

def run_workflow(query: str) -> dict[str, Any]:
    graph = build_graph()

    initial_state: WorkflowState = {
        "query": query,
        "topic": "",
        "intent": "",
        "answer": "",
        "structured_output": {},
        "trace": [],
        "error": None,
    }

    final_state = graph.invoke(initial_state)
    return final_state

if __name__ == "__main__":
    graph = build_graph()

    test_queries = [
        "请用一句话解释什么是 FastAPI",
        "LangGraph 和普通函数串联有什么区别？",
        "列表推导式是什么？",
    ]

    for query in test_queries:
        print("\n" + "=" * 80)
        print(f"用户输入: {query}")

        # 初始化共享状态
        initial_state: WorkflowState = {
            "query": query,
            "topic": "",
            "intent": "",
            "answer": "",
            "structured_output": {},
            "trace": [],
            "error": None,
        }

        #执行工作流，得到最终状态
        final_state = graph.invoke(initial_state)

        print("\n[final structured_output]")
        print(final_state["structured_output"])

        print("\n[final trace]")
        for item in final_state["trace"]:
            print(item)