from __future__ import annotations

import json
import re
import sys
import argparse
from collections import defaultdict
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.config import CHROMA_DB_PATH, LITERATURE_CHROMA_COLLECTION
from core.vector_store import ChromaVectorStore
from core.rerankers import Reranker, build_reranker


OUTPUT_PATH = PROJECT_ROOT / "docs" / "eval" / "rag_eval_v1.jsonl"


# id, category, question, paper ids, expected terms, reference answer, required claims
SEEDS = [
    ("E01", "exact_lookup", "哪篇论文研究了温度和压力对β-HMX热导率张量的影响？", "ARXIV-001", "HMX;thermal conductivity;pressure;temperature", "ARXIV-001研究了β-HMX热导率张量随温度和压力的变化。", ["ARXIV-001", "β-HMX热导率", "温度和压力"]),
    ("E02", "exact_lookup", "哪篇论文把Green-Kubo和Helfand-moment用于β-HMX热导率预测？", "ARXIV-003", "Green-Kubo;Helfand;thermal conductivity;HMX", "ARXIV-003讨论了Green-Kubo和Helfand-moment热导率预测。", ["ARXIV-003", "Green-Kubo", "Helfand"]),
    ("E03", "exact_lookup", "哪篇论文使用ReaxFF分子动力学研究RDX-Al界面？", "LRX-CORE-005", "RDX;Al;ReaxFF;interface", "LRX-CORE-005使用ReaxFF分子动力学研究RDX-Al界面。", ["LRX-CORE-005", "RDX-Al", "ReaxFF"]),
    ("E04", "exact_lookup", "哪份方法文献在ReaxFF中显式表示电子？", "LRX-METHOD-001", "eReaxFF;explicit electrons;reactive force field", "LRX-METHOD-001介绍了显式电子的eReaxFF。", ["LRX-METHOD-001", "eReaxFF", "显式电子"]),
    ("E05", "exact_lookup", "哪篇论文为RDX构建了图神经网络粗粒化力场？", "ARXIV-008", "RDX;graph neural network;coarse-grain;force field", "ARXIV-008为RDX分子晶体构建了GNN粗粒化力场。", ["ARXIV-008", "RDX", "GNN粗粒化力场"]),
    ("E06", "exact_lookup", "哪篇论文研究了TATB弹性各向异性随温度和压力的变化？", "ARXIV-004", "TATB;elastic anisotropy;temperature;pressure", "ARXIV-004研究了TATB弹性各向异性的温压依赖。", ["ARXIV-004", "TATB", "弹性各向异性"]),
    ("E07", "exact_lookup", "哪篇论文用有限元模拟预测PBX有效弹性模量？", "ARXIV-010", "PBX;finite element;elastic moduli", "ARXIV-010用有限元模拟研究PBX有效弹性模量。", ["ARXIV-010", "有限元", "有效弹性模量"]),
    ("E08", "exact_lookup", "哪篇论文研究CL-20/HMX共晶及其PBX的界面作用和力学性能？", "EMMD-016", "CL-20;HMX;cocrystal;interface;mechanical properties", "EMMD-016研究了CL-20/HMX共晶及其PBX的界面作用和力学性能。", ["EMMD-016", "CL-20/HMX", "界面与力学性能"]),
    ("M01", "method", "气相RDX高温单分子解离研究采用了什么模拟方法？", "LRX-CORE-002", "RDX;ab initio molecular dynamics;dissociation", "该研究采用从头算分子动力学研究气相RDX高温解离。", ["从头算分子动力学", "气相RDX", "高温解离"]),
    ("M02", "method", "RDX碎裂路径研究结合了哪两类方法？", "LRX-CORE-003", "RDX;fragmentation;tandem mass spectrometry;density functional theory", "该研究结合串联质谱与密度泛函理论分析RDX碎裂路径。", ["串联质谱", "DFT", "RDX碎裂"]),
    ("M03", "method", "RDX-Al界面热力学模拟使用了什么反应力场方法？", "LRX-CORE-005", "RDX;Al;ReaxFF;molecular dynamics", "RDX-Al界面研究使用ReaxFF反应分子动力学。", ["RDX-Al", "ReaxFF", "分子动力学"]),
    ("M04", "method", "CL-20/HMX热分解模拟使用了什么软件、力场和系综设置？", "CORE-DL-001", "LAMMPS;ReaxFF/lg;NVT;NPT;2000 K", "研究使用LAMMPS和ReaxFF/lg，先进行NVT/NPT平衡，再在2000 K开展NVT反应模拟。", ["LAMMPS", "ReaxFF/lg", "NVT/NPT"]),
    ("M05", "method", "β-HMX热导率张量研究采用了哪类分子动力学方法？", "ARXIV-001", "equilibrium molecular dynamics;thermal conductivity;HMX", "研究采用平衡分子动力学计算β-HMX热导率张量。", ["平衡分子动力学", "β-HMX", "热导率张量"]),
    ("M06", "method", "β-HMX热流过滤研究比较了哪些热导率计算形式？", "ARXIV-003", "Green-Kubo;Helfand-moment;heat-current filtering", "研究比较了Green-Kubo与Helfand-moment形式并讨论热流过滤。", ["Green-Kubo", "Helfand-moment", "热流过滤"]),
    ("M07", "method", "TATB弹性张量的温压依赖是如何用MD建模的？", "ARXIV-004", "TATB;molecular dynamics;elastic tensor;temperature;pressure", "研究用分子动力学计算不同温度和压力下的TATB弹性张量。", ["TATB", "MD", "温压相关弹性张量"]),
    ("M08", "method", "晶间热点研究如何区分压缩功和剪切功的影响？", "ARXIV-002", "hotspot;compressive;shear work;molecular dynamics", "研究通过分子动力学改变压缩与横向剪切加载来区分两类做功贡献。", ["分子动力学", "压缩功", "剪切功"]),
    ("M09", "method", "聚合物影响RDX孔洞塌缩的研究采用了什么模拟方法？", "ARXIV-005", "RDX;polymer;pore collapse;reactive molecular dynamics", "研究采用反应分子动力学模拟含聚合物膜的RDX冲击孔洞塌缩。", ["反应分子动力学", "RDX", "聚合物孔洞塌缩"]),
    ("M10", "method", "PBX全原子微结构构建工具生成并验证了哪些类型的模型？", "ARXIV-007", "all-atom;PBX;RDX;TATB;polystyrene;microstructure", "该工具构建RDX-聚苯乙烯和TATB-聚苯乙烯等全原子PBX微结构并用力学或冲击性质验证。", ["全原子PBX", "RDX/TATB-聚苯乙烯", "性质验证"]),
    ("F01", "mechanism_finding", "RDX早期分解中aminoxyl或nitroxyl自由基扮演什么角色？", "LRX-CORE-001", "RDX;aminoxyl;nitroxyl;radicals;early decomposition", "该文聚焦aminoxyl/nitroxyl自由基与RDX早期分解路径的关系。", ["RDX早期分解", "aminoxyl/nitroxyl自由基"]),
    ("F02", "mechanism_finding", "为什么凝聚相含能材料分解不能只用单分子机制解释？", "LRX-CORE-006", "condensed phase;unimolecular;bimolecular;activation energy;ReaxFF", "凝聚相中双分子自由基反应可提供较低活化路径，需要与单分子机制共同考虑。", ["凝聚相", "单分子与双分子机制", "较低活化路径"]),
    ("F03", "mechanism_finding", "聚合物膜如何影响RDX冲击孔洞塌缩热点的临界性？", "ARXIV-005", "polymer;RDX;pore collapse;hotspot;criticality", "聚合物会改变热点温度和临界性；惰性聚合物常延迟反应，但特定几何可能加速化学反应。", ["改变热点温度与临界性", "几何依赖", "可能延迟或加速反应"]),
    ("F04", "mechanism_finding", "TATB与HMX相比为什么表现出更弱的能量局域化？", "ARXIV-006", "TATB;HMX;energy localization;insensitivity;hotspot", "研究观察到TATB比HMX能量局域化更弱，这可能有助于解释其较低冲击感度。", ["TATB能量局域化更弱", "与低感度相关"]),
    ("F05", "mechanism_finding", "高压如何通过剪切应变过度形核抑制RDX塑性？", "ARXIV-012", "RDX;high pressure;plasticity;shear strain;clusters", "高压下形成许多小而独立的剪切簇，降低塑性驱动力并抑制连续剪切带发展。", ["高压", "小型独立剪切簇", "抑制塑性"]),
    ("F06", "mechanism_finding", "CL-20/HMX反应模拟给出的分解阶段和典型产物是什么？", "CORE-DL-001", "CL-20;HMX;decomposition;HONO;NO;N2;H2O", "分解经历初级碎片形成、碎片单分子分解和气相反应，并生成N2、NO、H2O等稳定产物。", ["三阶段分解", "HONO等中间体", "N2/NO/H2O产物"]),
    ("F07", "mechanism_finding", "CL-20/TNT共晶降低感度的研究从什么尺度解释该现象？", "LRX-CORE-004", "CL-20;TNT;sensitivity;micromechanical", "该研究从微观力学角度解释CL-20/TNT晶体感度降低。", ["CL-20/TNT", "微观力学", "感度降低"]),
    ("F08", "mechanism_finding", "β-HMX在高压下哪些分子结构变化被视为潜在弱点？", "ARXIV-009", "HMX;pressure;weak spots;bond;angle", "研究通过键长和环角随压力的响应识别β-HMX分子内潜在弱点。", ["β-HMX", "压力响应", "分子弱点"]),
    ("F09", "mechanism_finding", "纳米铝/硝化纤维素复合颗粒对推进剂表面团聚有什么影响？", "LRX-CORE-008", "nano-aluminum;nitrocellulose;agglomeration;propellant", "复合介观颗粒可减少表面团聚，并可能改善相对微米铝颗粒的燃烧表现。", ["减少表面团聚", "推进剂", "纳米铝/硝化纤维素"]),
    ("F10", "mechanism_finding", "含锆HTPB/AP推进剂的燃速受哪些配方因素影响？", "LRX-CORE-009", "HTPB;AP;zirconium;burning rate;pressure exponent", "文献讨论锆或锆铝添加、AP粒度/比例和燃速催化剂对燃速与压强指数的影响。", ["HTPB/AP", "锆添加", "燃速与压强指数"]),
    ("C01", "comparison", "两篇β-HMX热导率论文的研究重点有何不同？", "ARXIV-001;ARXIV-003", "HMX;thermal conductivity;pressure;temperature;Green-Kubo;Helfand", "ARXIV-001关注温压下热导率张量，ARXIV-003关注Green-Kubo/Helfand热流处理与预测方法。", ["ARXIV-001温压张量", "ARXIV-003热流过滤"]),
    ("C02", "comparison", "现有热点论文分别从哪些尺度和机制研究热点形成？", "ARXIV-002;ARXIV-005;ARXIV-006;ARXIV-011", "hotspot;compressive;shear;polymer;pore collapse;mesoscale", "文献分别研究晶间压缩/剪切做功、聚合物孔洞塌缩、缺陷与取向，以及介观模型和原子模型的一致性。", ["压缩/剪切", "聚合物孔洞塌缩", "缺陷取向", "介观-原子一致性"]),
    ("C03", "comparison", "三篇RDX分解研究在方法与对象上有什么区别？", "LRX-CORE-001;LRX-CORE-002;LRX-CORE-003", "RDX;radicals;ab initio molecular dynamics;mass spectrometry;DFT", "三篇文献分别关注早期自由基、气相高温AIMD解离，以及串联质谱结合DFT的碎裂路径。", ["早期自由基", "AIMD气相解离", "质谱+DFT碎裂"]),
    ("C04", "comparison", "CL-20/HMX的常规MD性能研究与反应MD分解研究有何区别？", "EMMD-016;CORE-DL-001", "CL-20;HMX;mechanical properties;interface;ReaxFF;decomposition", "EMMD-016侧重界面作用和力学性能，CORE-DL-001侧重ReaxFF热分解与感度机制。", ["界面/力学性能", "ReaxFF热分解", "研究目标不同"]),
    ("C05", "comparison", "TATB的弹性各向异性研究和热点能量局域化研究分别关注什么？", "ARXIV-004;ARXIV-006", "TATB;elastic anisotropy;hotspot;energy localization", "ARXIV-004关注温压下弹性各向异性，ARXIV-006关注冲击缺陷引发的热点和能量局域化。", ["弹性各向异性", "热点能量局域化"]),
    ("C06", "comparison", "RDX的GNN粗粒化力场与RDX-Al ReaxFF研究在建模目标上有何区别？", "ARXIV-008;LRX-CORE-005", "RDX;GNN;coarse-grain;RDX-Al;ReaxFF", "ARXIV-008发展RDX粗粒化GNN力场，LRX-CORE-005用ReaxFF描述RDX-Al界面反应热力学。", ["GNN粗粒化", "ReaxFF界面反应", "建模目标差异"]),
    ("C07", "comparison", "PBX全原子构建与有限元有效模量研究如何互补？", "ARXIV-007;ARXIV-010", "PBX;all-atom;microstructure;finite element;elastic moduli", "ARXIV-007提供全原子PBX微结构，ARXIV-010从有限元尺度分析微结构对有效弹性模量预测的影响。", ["全原子微结构", "有限元有效模量", "尺度互补"]),
    ("C08", "comparison", "ReaxFF用户手册、SCM方程参考和方程文档分别适合解决什么问题？", "LRX-METHOD-002;LRX-METHOD-004;LRX-METHOD-006", "ReaxFF;manual;equations;setup;parameter", "用户手册适合配置与操作，SCM参考和方程文档适合查能量项、参数与公式定义。", ["配置操作", "方程与能量项", "参数定义"]),
    ("C09", "comparison", "Strachan 2003与van Duin 2005两篇ReaxFF含能材料文献有何方法传承关系？", "LRX-METHOD-008;LRX-METHOD-009", "ReaxFF;energetic materials;RDX;reactive molecular dynamics", "两篇文献均为ReaxFF含能材料反应模拟基础资料，后者进一步展示参数化和热分解反应模拟。", ["ReaxFF含能材料", "反应MD基础"]),
    ("C10", "comparison", "纳米铝/硝化纤维素与含锆HTPB/AP推进剂研究分别如何改进燃烧？", "LRX-CORE-008;LRX-CORE-009", "propellant;aluminum;nitrocellulose;zirconium;HTPB;AP;burning", "前者通过复合铝颗粒减少团聚，后者通过锆系添加和燃速催化剂调控HTPB/AP燃烧性能。", ["复合铝颗粒减少团聚", "锆系添加调节燃速"]),
    ("G01", "graph_relation", "哪些论文同时关联RDX与孔洞塌缩热点？", "ARXIV-005;ARXIV-011", "RDX;pore collapse;hotspot", "ARXIV-005和ARXIV-011关联RDX孔洞塌缩与热点问题。", ["ARXIV-005", "ARXIV-011", "RDX热点"]),
    ("G02", "graph_relation", "哪些文献把RDX与ReaxFF反应分子动力学联系起来？", "LRX-CORE-005;LRX-METHOD-008;LRX-METHOD-009", "RDX;ReaxFF;reactive molecular dynamics", "LRX-CORE-005、LRX-METHOD-008和LRX-METHOD-009提供RDX/ReaxFF关联证据。", ["RDX", "ReaxFF", "三篇相关文献"]),
    ("G03", "graph_relation", "哪些论文关联HMX与热导率计算？", "ARXIV-001;ARXIV-003", "HMX;thermal conductivity", "ARXIV-001和ARXIV-003均关联HMX热导率计算。", ["ARXIV-001", "ARXIV-003", "HMX热导率"]),
    ("G04", "graph_relation", "哪些论文从力学或冲击角度研究TATB？", "ARXIV-002;ARXIV-004;ARXIV-006;CORE-DL-003", "TATB;mechanical;shock;elasticity;hotspot", "ARXIV-002、ARXIV-004、ARXIV-006和CORE-DL-003从热点、弹性或温度效应研究TATB。", ["TATB", "热点/弹性/温度效应"]),
    ("G05", "graph_relation", "哪些论文同时关联CL-20、HMX与分子动力学？", "EMMD-016;CORE-DL-001", "CL-20;HMX;molecular dynamics", "EMMD-016和CORE-DL-001均关联CL-20/HMX与分子动力学。", ["EMMD-016", "CORE-DL-001", "CL-20/HMX MD"]),
    ("G06", "graph_relation", "哪些论文把PBX与力学性能或弹性模量联系起来？", "EMMD-016;ARXIV-010;CORE-DL-003", "PBX;mechanical properties;elastic moduli", "EMMD-016、ARXIV-010和CORE-DL-003包含PBX力学性能或弹性模量证据。", ["PBX", "力学性能/弹性模量", "相关论文"]),
    ("R01", "refusal", "当前文献库能否给出锂电池电解液配方优化建议？", "", "lithium battery;electrolyte", "当前含能材料MD文献库没有足够证据回答锂电池电解液设计问题，应拒答。", ["证据不足", "拒答"]),
    ("R02", "refusal", "请根据文献库解释蛋白质折叠中的伴侣蛋白机制。", "", "protein folding;chaperone", "当前文献库不包含蛋白质折叠证据，应拒答。", ["证据不足", "拒答"]),
    ("R03", "refusal", "预测下周某支股票的收盘价。", "", "stock price;prediction", "文献库不包含股票市场数据，不能预测股价，应拒答。", ["无金融证据", "拒答"]),
    ("R04", "refusal", "根据这些论文给出儿童退烧药的具体剂量。", "", "medical dosage;child", "含能材料论文不能支持医疗剂量建议，应明确拒答。", ["无医疗证据", "拒答"]),
    ("R05", "refusal", "这些论文能预测香港明天的降雨量吗？", "", "weather;rainfall;Hong Kong", "文献库不含天气数据，不能预测降雨，应拒答。", ["无天气证据", "拒答"]),
    ("R06", "refusal", "请根据文献库生成一张火星城市概念图。", "", "Mars city;image generation", "文献检索问答系统没有相关证据或图像生成能力，应拒答或说明能力边界。", ["能力边界", "拒答"]),
]


def _terms(value: str) -> list[str]:
    return [term.strip().lower() for term in value.split(";") if term.strip()]


def _rank_local_chunks(
    items: list[dict[str, Any]], terms: list[str]
) -> list[dict[str, Any]]:
    section_bonus = {"abstract": 4, "results": 3, "methods": 3, "conclusion": 2, "introduction": 1}
    scored = []
    for item in items:
        text = " ".join(str(item.get("text") or "").split())
        lowered = text.lower()
        term_score = sum(6 for term in terms if term in lowered)
        token_score = sum(
            1
            for term in terms
            for token in re.findall(r"[a-z0-9][a-z0-9+@-]*", term)
            if len(token) >= 3 and token in lowered
        )
        section = str((item.get("metadata") or {}).get("section") or "").lower()
        scored.append((term_score + token_score + section_bonus.get(section, 0), len(text), item))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    if not scored or scored[0][0] <= 0:
        raise ValueError("no evidence chunk matched expected terms")
    return [row[2] for row in scored]


def _best_chunk(
    items: list[dict[str, Any]],
    terms: list[str],
    *,
    question: str,
    reranker: Reranker | None,
) -> dict[str, Any]:
    locally_ranked = _rank_local_chunks(items, terms)
    if reranker is None:
        return locally_ranked[0]
    return reranker.rerank(question, locally_ranked[:40], top_n=1)[0]


def build_dataset(*, cloud_resolve: bool = False) -> list[dict[str, Any]]:
    store = ChromaVectorStore(
        db_path=str(CHROMA_DB_PATH),
        collection_name=LITERATURE_CHROMA_COLLECTION,
        embedding_provider="local_hash",
    )
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in store.get_all():
        paper_id = str((item.get("metadata") or {}).get("paper_id") or "")
        if paper_id:
            by_paper[paper_id].append(item)

    category_dev_limits = {
        "exact_lookup": 5,
        "method": 6,
        "mechanism_finding": 6,
        "comparison": 6,
        "graph_relation": 4,
        "refusal": 3,
    }
    category_seen: dict[str, int] = defaultdict(int)
    reranker = build_reranker("dashscope") if cloud_resolve else None
    rows = []
    for question_id, category, question, paper_value, term_value, reference, claims in SEEDS:
        category_seen[category] += 1
        paper_ids = [part for part in paper_value.split(";") if part]
        relevant_chunk_ids = []
        gold_evidence = []
        for paper_id in paper_ids:
            if paper_id not in by_paper:
                raise ValueError(f"{question_id}: unknown or unindexed paper_id {paper_id}")
            chunk = _best_chunk(
                by_paper[paper_id],
                _terms(term_value),
                question=question,
                reranker=reranker,
            )
            metadata = chunk.get("metadata") or {}
            chunk_id = metadata.get("chunk_id")
            relevant_chunk_ids.append(f"{paper_id}:{chunk_id}")
            gold_evidence.append(
                {
                    "paper_id": paper_id,
                    "chunk_id": chunk_id,
                    "section": metadata.get("section", "unknown"),
                    "snippet": " ".join(str(chunk.get("text") or "").split())[:420],
                }
            )
            if cloud_resolve:
                print(
                    f"resolved {question_id} {paper_id}:{chunk_id} "
                    f"score={chunk.get('rerank_score', 0):.4f}",
                    flush=True,
                )
        rows.append(
            {
                "question_id": question_id,
                "split": (
                    "dev"
                    if category_seen[category] <= category_dev_limits[category]
                    else "test"
                ),
                "category": category,
                "difficulty": (
                    "hard" if category in {"comparison", "graph_relation"} else "medium"
                    if category in {"method", "mechanism_finding"} else "easy"
                ),
                "question": question,
                "relevant_paper_ids": paper_ids,
                "relevant_chunk_ids": relevant_chunk_ids,
                "reference_answer": reference,
                "required_claims": claims,
                "expected_terms": _terms(term_value),
                "should_refuse": category == "refusal",
                "gold_evidence": gold_evidence,
                "annotation_basis": "manifest_and_indexed_full_text_v1",
            }
        )
    if len(rows) != 50:
        raise AssertionError(f"expected 50 questions, got {len(rows)}")
    if sum(row["split"] == "dev" for row in rows) != 30:
        raise AssertionError("expected a 30/20 dev/test split")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the evidence-anchored 50-query RAG eval set")
    parser.add_argument(
        "--cloud-resolve",
        action="store_true",
        help="Use DashScope qwen3-rerank within each labeled paper to locate gold chunks",
    )
    args = parser.parse_args()
    rows = build_dataset(cloud_resolve=args.cloud_resolve)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"output": str(OUTPUT_PATH), "questions": len(rows)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
