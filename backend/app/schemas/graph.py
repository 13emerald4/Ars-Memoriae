"""Schemas for Associative Networks & Spreading Activation."""

from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field


class ConceptEdgeCreate(BaseModel):
    source_card_id: str
    target_card_id: str
    relationship_type: str = "associative"
    weight: float = Field(default=1.0, ge=0.1, le=5.0)


class ConceptEdgeOut(BaseModel):
    id: str
    source_card_id: str
    target_card_id: str
    relationship_type: str
    weight: float
    created_at: datetime


class GraphNodeOut(BaseModel):
    id: str
    card_id: str
    title: str
    deck_id: str
    deck_name: str
    state: str
    is_schema_checkpoint: bool = False
    spatial_x: float | None = None
    spatial_y: float | None = None
    spatial_locus: str | None = None
    activation: float = 0.0


class GraphEdgeOut(BaseModel):
    id: str
    source: str  # source_card_id
    target: str  # target_card_id
    relationship_type: str
    weight: float


class ConceptGraphOut(BaseModel):
    nodes: list[GraphNodeOut]
    edges: list[GraphEdgeOut]
    total_nodes: int
    total_edges: int


class SpreadingActivationNode(BaseModel):
    card_id: str
    title: str
    deck_name: str
    activation: float
    path_depth: int
    relationship_to_source: str | None = None


class SpreadingActivationResponse(BaseModel):
    source_card_id: str
    source_title: str
    activated_nodes: list[SpreadingActivationNode]


class AutoLinkResult(BaseModel):
    created_count: int
    edges: list[ConceptEdgeOut]
