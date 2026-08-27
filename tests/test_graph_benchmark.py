from scripts.run_graph_benchmark import _legacy_terms, set_metrics, summarize


def test_set_metrics_handles_partial_and_exact_results():
    assert set_metrics(["P1", "P2"], ["P1", "P3"]) == {
        "precision": 0.5,
        "recall": 0.5,
        "f1": 0.5,
        "exact_match": 0.0,
    }
    assert set_metrics(["P1"], ["P1"])["exact_match"] == 1.0


def test_summarize_uses_macro_average():
    rows = [
        {"precision": 1.0, "recall": 1.0, "f1": 1.0, "exact_match": 1.0, "latency_ms": 2.0},
        {"precision": 0.0, "recall": 0.0, "f1": 0.0, "exact_match": 0.0, "latency_ms": 4.0},
    ]
    result = summarize(rows)
    assert result["f1"] == 0.5
    assert result["mean_latency_ms"] == 3.0


def test_legacy_terms_reproduces_partial_english_rule_matching():
    assert _legacy_terms("哪些论文同时关联HMX与热导率？") == ["HMX"]
    assert _legacy_terms("哪篇文献报告了扩散系数？") == []
