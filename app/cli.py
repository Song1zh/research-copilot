import argparse
import json
from typing import Any

from core.llm_client import LLMClient
from workflows.toy_workflow import run_workflow

def run_llm_mode(query:str) -> None:
    llm = LLMClient()
    answer = llm.chat(
        system_prompt="你是一名简洁、准确的中文助教，请直接回答用户问题",
        user_prompt=query,
    )

    print("\n===CLI DEMO:LLM MODE===")
    print(f"用户问题：{query}")
    print(f"模型回答：{answer}")

def run_workflow_mode(query:str, show_trace:bool) -> None:
    results = run_workflow(query)

    print("\n===CLI DEMO:WORKFLOW MODE===")
    print(f"用户问题：{query}")

    structured_output = results.get("structured_output",{})
    print("\n结构化输出")
    print(json.dumps(structured_output, ensure_ascii=False, indent=2))

    if show_trace:
        print("\nTrace")
        print(json.dumps(results.get("trace", []), ensure_ascii=False, indent=2))

def main():
    # 定义命令行参数解析器
    parser = argparse.ArgumentParser(description="Week1 minimal Client")
    parser.add_argument(
        "--mode",
        choices=["llm", "workflow"],
        required=True,
        help="选择演示模式：llm或workflow",
    )
    parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="用户输入问题",
    )
    parser.add_argument(
        "--trace",
        action="store_true",
        help="在workflow模式下打印trace",
    )
    args = parser.parse_args()

    try:
        if args.mode == "llm":
            run_llm_mode(args.query)
        elif args.mode == "workflow":
            run_workflow_mode(args.query, args.trace)
    except Exception as e:
        print(f"\nCLI 运行失败: {e}")

if __name__ == "__main__":
    main()