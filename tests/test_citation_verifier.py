from core.citation_verifier import verify_citations


def build_good_sample() -> dict:
    return {
        "summary": "研究通过分析 H2、H2O、N2 等物质释放规律及 Mg-H、Mg-O、O-H 等核心化学键演化轨迹，从原子层面研究 MgH2 对 CL-20 热解反应的过程 [E1]",
        "methods": [
            "分析 H2、H2O、N2 等物质释放规律 [E1]",
            "剖析 Mg-H、Mg-O 及 O-H 等核心化学键演化轨迹 [E1]"
        ],
        "findings": [
            "CL-20 具备较高晶体密度和优异爆轰性能 [E2]"
        ],
        "limitations": [
            "MgH2 与 CL-20 复合体系研究仍较匮乏 [E3]"
        ],
        "evidence": [
            {
                "evidence_id": "E1",
                "chunk_id": 5,
                "source_path": "data/sample.txt",
                "snippet": "分析 H2、H2O、N2 等物质释放规律，并剖析 Mg-H、Mg-O 及 O-H 等核心化学键演化轨迹。"
            },
            {
                "evidence_id": "E2",
                "chunk_id": 0,
                "source_path": "data/sample.txt",
                "snippet": "CL-20 具备极高的晶体密度、生成焓以及优异的爆轰速度。"
            },
            {
                "evidence_id": "E3",
                "chunk_id": 3,
                "source_path": "data/sample.txt",
                "snippet": "当前针对 MgH2 与 CL-20 复合体系的研究较少。"
            },
        ],
    }


def build_fake_sample() -> dict:
    return {
        "summary": "MgH2 明显降低 CL-20 的机械感度 [E1]",
        "methods": [
            "使用 ReaxFF MD 研究体系 [E9]"
        ],
        "findings": [
            "CL-20 的爆轰速度明显降低 [E2]"
        ],
        "limitations": [
            "研究样本较少"
        ],
        "evidence": [
            {
                "evidence_id": "E1",
                "chunk_id": 5,
                "source_path": "data/sample.txt",
                "snippet": "分析 H2、H2O、N2 等物质释放规律，并剖析化学键演化轨迹。"
            },
            {
                "evidence_id": "E2",
                "chunk_id": 3,
                "source_path": "data/sample.txt",
                "snippet": "当前针对 MgH2 与 CL-20 复合体系的研究较少。"
            },
        ],
    }


def test_verify_citations_good_sample_passes():
    report = verify_citations(build_good_sample())

    assert report["is_verified"] is True
    assert report["unsupported_fields"] == []
    assert report["uncited_fields"] == []


def test_verify_citations_fake_sample_detects_errors():
    report = verify_citations(build_fake_sample())

    assert report["is_verified"] is False
    assert "summary" in report["unsupported_fields"]
    assert "methods[1]" in report["unsupported_fields"]
    assert "limitations[1]" in report["uncited_fields"]