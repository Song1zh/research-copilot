from __future__ import annotations

from typing import Any

from core.graph_store import Neo4jGraphStore


def normalize_kg_provider(provider: str | None) -> str:
    normalized = (provider or "neo4j").strip().lower()
    aliases = {"off": "none", "disabled": "none", "graph": "neo4j"}
    normalized = aliases.get(normalized, normalized)
    if normalized not in {"none", "neo4j"}:
        raise ValueError(
            f"unsupported kg provider: {provider!r}; supported values: none, neo4j"
        )
    return normalized


def retrieve_kg_evidence(
    query_terms: list[str],
    limit: int = 8,
    provider: str = "neo4j",
) -> dict[str, Any]:
    provider = normalize_kg_provider(provider)
    if provider == "none":
        return {
            "available": False,
            "disabled": True,
            "provider": "none",
            "items": [],
            "error": None,
        }
    if not query_terms:
        return {"available": False, "items": [], "error": "no query terms"}

    graph = None
    try:
        graph = Neo4jGraphStore()
        graph.verify()
        items = graph.query_relations_by_terms(query_terms, limit=limit)
        return {
            "available": True,
            "disabled": False,
            "provider": "neo4j",
            "items": items,
            "operator": "AND",
            "query_terms": query_terms,
            "error": None,
        }
    except Exception as exc:
        return {
            "available": False,
            "disabled": False,
            "provider": "neo4j",
            "items": [],
            "error": str(exc),
        }
    finally:
        if graph is not None:
            graph.close()
