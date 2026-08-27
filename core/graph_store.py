from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from core.config import NEO4J_PASSWORD, NEO4J_URI, NEO4J_USERNAME
from schemas.simulation_extraction import SimulationExtraction

try:
    from neo4j import GraphDatabase
except Exception:  # pragma: no cover - optional dependency fallback
    GraphDatabase = None


class GraphUnavailableError(RuntimeError):
    pass


@dataclass
class GraphEntitySummary:
    papers: int = 0
    materials: int = 0
    methods: int = 0
    force_fields: int = 0
    software: int = 0
    properties: int = 0
    findings: int = 0


def format_graph_relation_row(record: dict[str, Any]) -> dict[str, Any]:
    labels = record.get("labels") or []
    entity_label = labels[0] if labels else "Entity"
    relation = str(record.get("relation") or "")
    paper_id = str(record.get("paper_id") or "")
    entity_name = str(record.get("entity_name") or record.get("entity") or "")
    return {
        "paper_id": paper_id,
        "title": record.get("title") or "",
        "relation": relation,
        "entity_label": entity_label,
        "entity_name": entity_name,
        "evidence_chunk_id": record.get("evidence_chunk_id"),
        "evidence_text": record.get("evidence_text") or "",
        "path_text": f"(Paper: {paper_id}) -[:{relation}]-> ({entity_label}: {entity_name})",
    }


class Neo4jGraphStore:
    def __init__(
        self,
        uri: str = NEO4J_URI,
        username: str = NEO4J_USERNAME,
        password: str = NEO4J_PASSWORD,
    ):
        if GraphDatabase is None:
            raise GraphUnavailableError("neo4j driver is not installed. Install neo4j or skip graph features.")
        self.driver = GraphDatabase.driver(uri, auth=(username, password))

    def close(self) -> None:
        self.driver.close()

    def verify(self) -> bool:
        try:
            self.driver.verify_connectivity()
            return True
        except Exception as exc:
            raise GraphUnavailableError(str(exc)) from exc

    def init_constraints(self) -> None:
        queries = [
            "CREATE CONSTRAINT paper_id_unique IF NOT EXISTS FOR (n:Paper) REQUIRE n.paper_id IS UNIQUE",
            "CREATE CONSTRAINT material_name_unique IF NOT EXISTS FOR (n:Material) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT method_name_unique IF NOT EXISTS FOR (n:Method) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT force_field_name_unique IF NOT EXISTS FOR (n:ForceField) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT software_name_unique IF NOT EXISTS FOR (n:Software) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT property_name_unique IF NOT EXISTS FOR (n:Property) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT finding_id_unique IF NOT EXISTS FOR (n:Finding) REQUIRE n.finding_id IS UNIQUE",
            "CREATE CONSTRAINT chunk_id_unique IF NOT EXISTS FOR (n:EvidenceChunk) REQUIRE n.chunk_key IS UNIQUE",
        ]
        with self.driver.session() as session:
            for query in queries:
                session.run(query)

    def clear_project_graph(self) -> None:
        with self.driver.session() as session:
            session.run(
                """
                MATCH (n)
                WHERE n:Paper OR n:Material OR n:Method OR n:ForceField
                   OR n:Software OR n:Property OR n:Finding OR n:EvidenceChunk
                DETACH DELETE n
                """
            ).consume()

    def upsert_paper(self, paper: dict[str, Any]) -> None:
        with self.driver.session() as session:
            session.run(
                """
                MERGE (p:Paper {paper_id: $paper_id})
                SET p.title = $title,
                    p.doi = $doi,
                    p.year = $year,
                    p.journal = $journal
                """,
                paper,
            )

    def upsert_extraction(self, paper: dict[str, Any], extraction: SimulationExtraction) -> None:
        self.upsert_paper(paper)
        chunk_key = f"{extraction.paper_id}::{extraction.chunk_id}"

        with self.driver.session() as session:
            session.run(
                """
                MATCH (p:Paper {paper_id: $paper_id})
                MERGE (c:EvidenceChunk {chunk_key: $chunk_key})
                SET c.paper_id = $paper_id, c.chunk_id = $chunk_id
                MERGE (p)-[:HAS_EVIDENCE]->(c)
                """,
                paper_id=extraction.paper_id,
                chunk_key=chunk_key,
                chunk_id=str(extraction.chunk_id),
            )

            for entity in extraction.materials:
                session.run(
                    """
                    MATCH (p:Paper {paper_id: $paper_id})
                    MERGE (m:Material {name: $name})
                    MERGE (p)-[r:STUDIES]->(m)
                    ON CREATE SET r.evidence_chunk_id = $evidence_chunk_id,
                                  r.evidence_text = $evidence_text
                    """,
                    paper_id=extraction.paper_id,
                    name=entity.name,
                    evidence_chunk_id=str(entity.evidence_chunk_id),
                    evidence_text=entity.evidence_text,
                )
            for entity in extraction.methods:
                session.run(
                    """
                    MATCH (p:Paper {paper_id: $paper_id})
                    MERGE (m:Method {name: $name})
                    MERGE (p)-[r:USES_METHOD]->(m)
                    ON CREATE SET r.evidence_chunk_id = $evidence_chunk_id,
                                  r.evidence_text = $evidence_text
                    """,
                    paper_id=extraction.paper_id,
                    name=entity.name,
                    evidence_chunk_id=str(entity.evidence_chunk_id),
                    evidence_text=entity.evidence_text,
                )
            for entity in extraction.force_fields:
                session.run(
                    """
                    MATCH (p:Paper {paper_id: $paper_id})
                    MERGE (f:ForceField {name: $name})
                    MERGE (p)-[r:USES_FORCE_FIELD]->(f)
                    ON CREATE SET r.evidence_chunk_id = $evidence_chunk_id,
                                  r.evidence_text = $evidence_text
                    """,
                    paper_id=extraction.paper_id,
                    name=entity.name,
                    evidence_chunk_id=str(entity.evidence_chunk_id),
                    evidence_text=entity.evidence_text,
                )
            for entity in extraction.software:
                session.run(
                    """
                    MATCH (p:Paper {paper_id: $paper_id})
                    MERGE (s:Software {name: $name})
                    MERGE (p)-[r:USES_SOFTWARE]->(s)
                    ON CREATE SET r.evidence_chunk_id = $evidence_chunk_id,
                                  r.evidence_text = $evidence_text
                    """,
                    paper_id=extraction.paper_id,
                    name=entity.name,
                    evidence_chunk_id=str(entity.evidence_chunk_id),
                    evidence_text=entity.evidence_text,
                )
            for entity in extraction.properties:
                session.run(
                    """
                    MATCH (p:Paper {paper_id: $paper_id})
                    MERGE (prop:Property {name: $name})
                    MERGE (p)-[r:REPORTS]->(prop)
                    ON CREATE SET r.evidence_chunk_id = $evidence_chunk_id,
                                  r.evidence_text = $evidence_text
                    """,
                    paper_id=extraction.paper_id,
                    name=entity.name,
                    evidence_chunk_id=str(entity.evidence_chunk_id),
                    evidence_text=entity.evidence_text,
                )
            for idx, entity in enumerate(extraction.findings):
                finding_id = f"{extraction.paper_id}::{extraction.chunk_id}::finding_{idx}"
                session.run(
                    """
                    MATCH (p:Paper {paper_id: $paper_id})
                    MATCH (c:EvidenceChunk {chunk_key: $chunk_key})
                    MERGE (f:Finding {finding_id: $finding_id})
                    SET f.text = $text
                    MERGE (p)-[r:REPORTS_FINDING]->(f)
                    SET r.evidence_chunk_id = $evidence_chunk_id,
                        r.evidence_text = $evidence_text
                    MERGE (f)-[:SUPPORTED_BY]->(c)
                    """,
                    paper_id=extraction.paper_id,
                    chunk_key=chunk_key,
                    finding_id=finding_id,
                    text=entity.name,
                    evidence_chunk_id=str(entity.evidence_chunk_id),
                    evidence_text=entity.evidence_text,
                )

    def entity_summary(self) -> GraphEntitySummary:
        labels = {
            "papers": "Paper",
            "materials": "Material",
            "methods": "Method",
            "force_fields": "ForceField",
            "software": "Software",
            "properties": "Property",
            "findings": "Finding",
        }
        counts: dict[str, int] = {}
        with self.driver.session() as session:
            for key, label in labels.items():
                record = session.run(f"MATCH (n:{label}) RETURN count(n) AS count").single()
                counts[key] = int(record["count"]) if record else 0
        return GraphEntitySummary(**counts)

    def query_relations(self, term: str = "", limit: int = 25) -> list[dict[str, Any]]:
        term = term.strip()
        limit = max(int(limit), 1)
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (p:Paper)-[r]->(n)
                WHERE type(r) IN [
                    "STUDIES",
                    "USES_METHOD",
                    "USES_FORCE_FIELD",
                    "USES_SOFTWARE",
                    "REPORTS",
                    "REPORTS_FINDING"
                ]
                  AND (
                    $term = ""
                    OR toLower(coalesce(n.name, n.text, "")) CONTAINS toLower($term)
                    OR toLower(p.title) CONTAINS toLower($term)
                    OR toLower(p.paper_id) CONTAINS toLower($term)
                  )
                RETURN p.paper_id AS paper_id,
                       p.title AS title,
                       type(r) AS relation,
                       labels(n) AS labels,
                       coalesce(n.name, n.text) AS entity_name,
                       r.evidence_chunk_id AS evidence_chunk_id,
                       r.evidence_text AS evidence_text
                ORDER BY p.paper_id, relation, entity_name
                LIMIT $limit
                """,
                term=term,
                limit=limit,
            )
            return [format_graph_relation_row(dict(record)) for record in records]

    def query_relations_by_terms(
        self,
        terms: list[str],
        limit: int = 8,
    ) -> list[dict[str, Any]]:
        normalized = list(dict.fromkeys(term.strip() for term in terms if term.strip()))
        if not normalized:
            return []
        limit = max(int(limit), 1)
        relation_types = [
            "STUDIES",
            "USES_METHOD",
            "USES_FORCE_FIELD",
            "USES_SOFTWARE",
            "REPORTS",
            "REPORTS_FINDING",
        ]
        with self.driver.session() as session:
            records = session.run(
                """
                MATCH (p:Paper)-[matched_relation]->(matched_entity)
                WHERE type(matched_relation) IN $relation_types
                  AND any(
                    term IN $terms
                    WHERE toLower(coalesce(matched_entity.name, matched_entity.text, ''))
                          = toLower(term)
                  )
                WITH p,
                     collect(DISTINCT toLower(coalesce(matched_entity.name, matched_entity.text, '')))
                       AS matched_terms
                WHERE all(term IN $terms WHERE toLower(term) IN matched_terms)
                WITH p ORDER BY p.paper_id LIMIT $limit
                MATCH (p)-[r]->(n)
                WHERE type(r) IN $relation_types
                  AND any(
                    term IN $terms
                    WHERE toLower(coalesce(n.name, n.text, '')) = toLower(term)
                  )
                RETURN p.paper_id AS paper_id,
                       p.title AS title,
                       type(r) AS relation,
                       labels(n) AS labels,
                       coalesce(n.name, n.text) AS entity_name,
                       r.evidence_chunk_id AS evidence_chunk_id,
                       r.evidence_text AS evidence_text
                ORDER BY p.paper_id, relation, entity_name
                """,
                terms=normalized,
                relation_types=relation_types,
                limit=limit,
            )
            return [format_graph_relation_row(dict(record)) for record in records]
