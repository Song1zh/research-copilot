import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import CHROMA_DB_PATH  # noqa: E402
from workflows.project_a_workflow import run_project_a_workflow  # noqa: E402


def read_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    encodings = ["utf-8-sig", "utf-8", "gbk", "cp936"]

    last_error = None
    for enc in encodings:
        try:
            with csv_path.open("r", encoding=enc, newline="") as f:
                return list(csv.DictReader(f))
        except UnicodeDecodeError as e:
            last_error = e
            continue

    raise UnicodeDecodeError(
        "unknown",
        b"",
        0,
        1,
        f"无法用这些编码读取 CSV: {encodings}，最后一个错误: {last_error}",
    )

DEFAULT_QUESTIONS: list[dict[str, str]] = [
    {"id": "1", "category": "fact", "query": "文中研究对象是什么？"},
    {"id": "2", "category": "fact", "query": "文中主要采用了什么研究方法？"},
    {"id": "3", "category": "fact", "query": "文中分析了哪些释放物种？"},
    {"id": "4", "category": "fact", "query": "文中关注了哪些核心化学键？"},
    {"id": "5", "category": "fact", "query": "文中研究目标是什么？"},
    {"id": "6", "category": "methods_findings", "query": "MgH2/CL-20 体系中有哪些关键方法？"},
    {"id": "7", "category": "methods_findings", "query": "MgH2/CL-20 体系中有哪些主要发现？"},
    {"id": "8", "category": "methods_findings", "query": "文中如何描述 MgH2 对 CL-20 热解反应的作用？"},
    {"id": "9", "category": "methods_findings", "query": "文中提到的研究意义是什么？"},
    {"id": "10", "category": "methods_findings", "query": "文中对当前研究现状是如何概括的？"},
    {"id": "11", "category": "limitations", "query": "文中提到了哪些研究不足或空白？"},
    {"id": "12", "category": "limitations", "query": "传统实验方法有哪些局限？"},
    {"id": "13", "category": "limitations", "query": "传统 QM/DFT 方法有哪些局限？"},
    {"id": "14", "category": "limitations", "query": "文中认为当前领域存在哪些挑战？"},
    {"id": "15", "category": "limitations", "query": "哪些结论仍需要更多证据支持？"},
    {"id": "16", "category": "irrelevant", "query": "法国大革命什么时候发生？"},
    {"id": "17", "category": "irrelevant", "query": "文中是否讨论了机器学习模型训练？"},
    {"id": "18", "category": "irrelevant", "query": "文中是否给出了 CL-20 的市场价格？"},
    {"id": "19", "category": "irrelevant", "query": "文中是否研究了 Zr/H2O 体系？"},
    {"id": "20", "category": "irrelevant", "query": "文中是否给出了具体实验装置尺寸？"},
]


def safe_text(value: Any, max_len: int = 300) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    return text[:max_len]


def build_answer_summary(result: dict[str, Any], max_len: int = 300) -> str:
    final_output = result.get("final_output", {}) or {}
    summary = safe_text(final_output.get("summary", ""), max_len=max_len)
    if summary:
        return summary

    limitations = final_output.get("limitations", []) or []
    if limitations:
        return safe_text(limitations[0], max_len=max_len)

    error = result.get("error")
    if error:
        return safe_text(error, max_len=max_len)

    return "EMPTY_RESULT"


def build_evidence_ids(result: dict[str, Any]) -> str:
    final_output = result.get("final_output", {}) or {}
    evidence = final_output.get("evidence", []) or []
    ids: list[str] = []

    for item in evidence:
        if isinstance(item, dict):
            evidence_id = item.get("evidence_id")
            if evidence_id:
                ids.append(str(evidence_id))

    return ",".join(ids)


def build_first_evidence_snippet(result: dict[str, Any], max_len: int = 200) -> str:
    final_output = result.get("final_output", {}) or {}
    evidence = final_output.get("evidence", []) or []
    if not evidence:
        return ""

    first_item = evidence[0]
    if isinstance(first_item, dict):
        return safe_text(first_item.get("snippet", ""), max_len=max_len)
    return ""


def auto_json_valid(error_code: str) -> str:
    if error_code in {"DOC_EMPTY", "RETRIEVE_EMPTY", "INTERNAL_ERROR"}:
        return ""
    return "0" if error_code == "MODEL_JSON_INVALID" else "1"


def auto_schema_valid(error_code: str) -> str:
    if error_code in {"DOC_EMPTY", "RETRIEVE_EMPTY", "INTERNAL_ERROR"}:
        return ""
    return "0" if error_code == "MODEL_SCHEMA_INVALID" else "1"


def run_eval(
    file_path: Path,
    out_dir: Path,
    collection_name: str | None = None,
) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    timestamp_tag = time.strftime("%Y%m%d_%H%M%S")
    file_stem = file_path.stem
    batch_collection = collection_name or f"eval_{file_stem}_{timestamp_tag}"
    csv_path = out_dir / f"manual_eval_{file_stem}_{timestamp_tag}.csv"

    rows: list[dict[str, Any]] = []

    print(f"开始评测，文件: {file_path}")
    print(f"本轮 collection: {batch_collection}")
    print(f"结果输出到: {csv_path}")

    for q in DEFAULT_QUESTIONS:
        query = q["query"]
        qid = q["id"]
        category = q["category"]

        print(f"\n[{qid}/20] {query}")

        start = time.perf_counter()
        result = run_project_a_workflow(
            file_path=str(file_path),
            query=query,
            collection_name=batch_collection,
            db_path=str(CHROMA_DB_PATH),
        )
        elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

        error_info = result.get("error_info") or {}
        error_code = error_info.get("code", "")

        final_output = result.get("final_output", {}) or {}
        evidence_items = final_output.get("evidence", []) or []

        row = {
            "id": qid,
            "query": query,
            "category": category,
            "file_name": file_path.name,
            "collection_name": batch_collection,
            "chunk_count": result.get("chunk_count", 0),
            "evidence_count": len(evidence_items),
            "error_code": error_code,
            "json_valid": auto_json_valid(error_code),
            "schema_valid": auto_schema_valid(error_code),
            "retrieval_hit": "",          # 人工填写：1/0
            "citation_grounded": "",      # 人工填写：1/0
            "usable_answer": "",          # 人工填写：1/0
            "latency_ms": elapsed_ms,
            "answer_summary": build_answer_summary(result),
            "evidence_ids": build_evidence_ids(result),
            "first_evidence_snippet": build_first_evidence_snippet(result),
            "notes": "",
        }

        rows.append(row)

    fieldnames = [
        "id",
        "query",
        "category",
        "file_name",
        "collection_name",
        "chunk_count",
        "evidence_count",
        "error_code",
        "json_valid",
        "schema_valid",
        "retrieval_hit",
        "citation_grounded",
        "usable_answer",
        "latency_ms",
        "answer_summary",
        "evidence_ids",
        "first_evidence_snippet",
        "notes",
    ]

    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print("\n自动评测完成。")
    print("请手工补充以下 3 列：retrieval_hit、citation_grounded、usable_answer（填 1/0）。")

    auto_summary = summarize_csv(csv_path, manual_mode=False)
    summary_path = csv_path.with_name(csv_path.stem + "_auto_summary.json")
    summary_path.write_text(json.dumps(auto_summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"自动摘要已保存到: {summary_path}")
    return csv_path


def parse_binary(value: str) -> int | None:
    value = str(value).strip()
    if value == "":
        return None
    if value not in {"0", "1"}:
        return None
    return int(value)


def rate(numerator: int, denominator: int) -> float | None:
    if denominator == 0:
        return None
    return round(numerator / denominator, 4)


def summarize_csv(csv_path: Path, manual_mode: bool = True) -> dict[str, Any]:
    rows = read_csv_rows(csv_path)

    total = len(rows)

    json_valid_values = [parse_binary(r["json_valid"]) for r in rows]
    schema_valid_values = [parse_binary(r["schema_valid"]) for r in rows]
    retrieval_hit_values = [parse_binary(r["retrieval_hit"]) for r in rows]
    citation_grounded_values = [parse_binary(r["citation_grounded"]) for r in rows]
    usable_answer_values = [parse_binary(r["usable_answer"]) for r in rows]

    json_valid_known = [x for x in json_valid_values if x is not None]
    schema_valid_known = [x for x in schema_valid_values if x is not None]
    retrieval_hit_known = [x for x in retrieval_hit_values if x is not None]
    citation_grounded_known = [x for x in citation_grounded_values if x is not None]
    usable_answer_known = [x for x in usable_answer_values if x is not None]

    summary: dict[str, Any] = {
        "csv_path": str(csv_path),
        "total_questions": total,
        "json_valid_rate": rate(sum(json_valid_known), len(json_valid_known)),
        "schema_valid_rate": rate(sum(schema_valid_known), len(schema_valid_known)),
        "json_valid_known_count": len(json_valid_known),
        "schema_valid_known_count": len(schema_valid_known),
    }

    if manual_mode:
        summary.update(
            {
                "retrieval_hit_rate": rate(sum(retrieval_hit_known), len(retrieval_hit_known)),
                "citation_grounded_rate": rate(sum(citation_grounded_known), len(citation_grounded_known)),
                "usable_answer_rate": rate(sum(usable_answer_known), len(usable_answer_known)),
                "retrieval_hit_known_count": len(retrieval_hit_known),
                "citation_grounded_known_count": len(citation_grounded_known),
                "usable_answer_known_count": len(usable_answer_known),
            }
        )

    # 按 category 简单汇总
    category_stats: dict[str, dict[str, Any]] = {}
    for r in rows:
        category = r["category"]
        category_stats.setdefault(category, {"total": 0, "retrieval_hit": [], "usable_answer": []})
        category_stats[category]["total"] += 1

        rh = parse_binary(r["retrieval_hit"])
        ua = parse_binary(r["usable_answer"])
        if rh is not None:
            category_stats[category]["retrieval_hit"].append(rh)
        if ua is not None:
            category_stats[category]["usable_answer"].append(ua)

    category_summary: dict[str, Any] = {}
    for category, stat in category_stats.items():
        category_summary[category] = {
            "total": stat["total"],
            "retrieval_hit_rate": rate(sum(stat["retrieval_hit"]), len(stat["retrieval_hit"]))
            if stat["retrieval_hit"]
            else None,
            "usable_answer_rate": rate(sum(stat["usable_answer"]), len(stat["usable_answer"]))
            if stat["usable_answer"]
            else None,
        }

    summary["category_summary"] = category_summary
    return summary


def main():
    parser = argparse.ArgumentParser(description="Project A 半自动人工评测脚本")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="跑 20 条问题并生成待人工标注的 CSV")
    run_parser.add_argument(
        "--file",
        type=str,
        required=True,
        help="待评测文档路径，例如 data/uploads/sample.txt",
    )
    run_parser.add_argument(
        "--out-dir",
        type=str,
        default="app_data/eval",
        help="评测结果输出目录",
    )
    run_parser.add_argument(
        "--collection",
        type=str,
        default="",
        help="可选：手动指定本轮 collection 名称",
    )

    summarize_parser = subparsers.add_parser("summarize", help="读取已人工标注的 CSV 并汇总指标")
    summarize_parser.add_argument(
        "--csv",
        type=str,
        required=True,
        help="已经补完 retrieval_hit / citation_grounded / usable_answer 的 CSV 路径",
    )

    args = parser.parse_args()

    if args.command == "run":
        file_path = Path(args.file).resolve()
        if not file_path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")

        out_dir = Path(args.out_dir).resolve()
        collection_name = args.collection.strip() or None
        csv_path = run_eval(file_path=file_path, out_dir=out_dir, collection_name=collection_name)

        print("\n下一步：")
        print(f"1) 打开 CSV：{csv_path}")
        print("2) 手工填写 retrieval_hit / citation_grounded / usable_answer 三列（1/0）")
        print(f"3) 然后运行：python -m scripts.run_manual_eval summarize --csv \"{csv_path}\"")

    elif args.command == "summarize":
        csv_path = Path(args.csv).resolve()
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV 不存在: {csv_path}")

        summary = summarize_csv(csv_path, manual_mode=True)
        print(json.dumps(summary, ensure_ascii=False, indent=2))

        summary_path = csv_path.with_name(csv_path.stem + "_manual_summary.json")
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n人工评测摘要已保存到: {summary_path}")


if __name__ == "__main__":
    main()