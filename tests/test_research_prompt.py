import json
from pydantic import ValidationError

from core.config import CHROMA_DB_PATH
from core.llm_client import LLMClient
from core.retriever import retrieve_evidence
from schemas.research_answer import ResearchCopilotAnswer

SYSTEM_PROMPT = """
你是一个严格、克制的 Research Copilot。

你的任务是：仅基于用户提供的 evidence chunks，生成结构化研究回答。

你必须遵守以下规则：
1. 只能依据给定 evidence 作答，不得使用外部常识补全，不得编造文献、方法、结论。
2. 输出必须是合法 JSON 对象，且只能包含以下五个字段：
   - summary
   - methods
   - findings
   - limitations
   - evidence
3. 字段类型必须满足：
   - summary: string
   - methods: array of strings
   - findings: array of strings
   - limitations: array of strings
   - evidence: array of strings
4. 不要输出 Markdown，不要输出代码块，不要输出额外解释，不要输出多余字段。
5. 如果 evidence 不足以支持某个判断：
   - 不要猜测
   - 不要强行补全
   - 应将不足写入 limitations
6. methods 只写“文中明确提到的方法/模型/实验或分析手段”。
7. findings 只写“evidence 能直接支持的发现或结论”。
8. evidence 字段应尽量保留与回答直接相关的证据片段，可适度压缩，但不能改变原意。
9. 若没有可提取的方法、发现或证据，对应字段返回空列表 []。
10. 输出必须能被标准 JSON 解析器直接解析。
"""


def build_user_prompt(query:str, evidence_chunks:list[dict]) -> str:
    formatted_chunks = []
    for idx, item in enumerate(evidence_chunks, start=1):
        metadata = item.get("metadata", {})
        source_path = metadata.get("source_path","unknown")
        chunk_id = metadata.get("chunk_id","unknown")
        text = item.get("text","")

        formatted_chunks.append(
            f"[evidence_{idx}] source={source_path} chunk_id={chunk_id}\n{text}"
        )
    evidence_text = "\n\n".join(formatted_chunks)

    return f"""用户问题：
{query}

证据片段：
{evidence_text}

请输出一个合法JSON对象，且只能包含以下字段：
summary, methods, findings, limitations, evidence
"""

def main():
    query = "六硝基六氮杂异伍兹烷晶体密度高吗？"
    evidence = retrieve_evidence(
        query = query,
        top_k= 3,
        db_path=str(CHROMA_DB_PATH),
        collection_name="day11_demo",
    )

    llm = LLMClient()
    user_prompt = build_user_prompt(query, evidence)

    result = llm.chat(
        system_prompt=SYSTEM_PROMPT,
        user_prompt=user_prompt,
    )

    print("=== 原始输出 ===")
    print(result)

    print("\n=== JSON 解析 ===")
    try:
        data = json.loads(result)
        obj = ResearchCopilotAnswer.model_validate(data)
        print(obj.model_dump())
    except (json.JSONDecodeError, ValidationError) as e:
        print("解析失败：", e)



if __name__ == "__main__":
    main()
