from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    name: str
    evidence_chunk_id: int | str
    evidence_text: str = ""


class MaterialSystem(ExtractedEntity):
    role: str = Field(default="material")


class SimulationMethod(ExtractedEntity):
    method_type: str = Field(default="molecular_dynamics")


class ForceField(ExtractedEntity):
    pass


class Software(ExtractedEntity):
    pass


class SimulationCondition(ExtractedEntity):
    condition_type: str = Field(default="unknown")


class Property(ExtractedEntity):
    property_type: str = Field(default="unknown")


class Finding(ExtractedEntity):
    finding_type: str = Field(default="reported_finding")


class SimulationExtraction(BaseModel):
    paper_id: str
    chunk_id: int | str
    materials: list[MaterialSystem] = Field(default_factory=list)
    methods: list[SimulationMethod] = Field(default_factory=list)
    force_fields: list[ForceField] = Field(default_factory=list)
    software: list[Software] = Field(default_factory=list)
    conditions: list[SimulationCondition] = Field(default_factory=list)
    properties: list[Property] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)

