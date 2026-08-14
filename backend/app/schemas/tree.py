"""Knowledge-tree request/response contracts."""

from __future__ import annotations

from pydantic import BaseModel, Field


class TreeNodeOut(BaseModel):
    id: str
    parent_id: str | None
    kind: str  # topic | deck | source | extract
    title: str
    position: int
    collapsed: bool
    # The resolved value — a node with no declared priority reports the nearest
    # ancestor's, with `priority_inherited` saying so.
    priority: int
    priority_inherited: bool
    # Rolled up over the whole subtree, so a collapsed branch still tells you
    # what is waiting inside it.
    card_count: int = 0
    due_count: int = 0
    new_count: int = 0
    extract_count: int = 0
    deck_id: str | None = None
    source_id: str | None = None
    extract_id: str | None = None
    # Mastery gating — see tree_service._apply_gating. mastery_pct is rolled
    # up over this node's whole subtree the same way card_count is.
    mastery_pct: int = 0
    locked: bool = False
    requires_node_id: str | None = None
    requires_title: str | None = None
    mastery_threshold: int = 90
    children: list[TreeNodeOut] = Field(default_factory=list)


# `children` refers to the class being defined, and `from __future__ import
# annotations` leaves it a string — resolve it before FastAPI builds a schema.
TreeNodeOut.model_rebuild()


class TreeOut(BaseModel):
    nodes: list[TreeNodeOut] = Field(default_factory=list)


class TopicCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    parent_id: str | None = None
    priority: int | None = Field(default=None, ge=0, le=100)


class NodeUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    priority: int | None = Field(default=None, ge=0, le=100)
    collapsed: bool | None = None
    # §9: write the priority onto every entity in the branch, not just this
    # node — the sweep that makes a whole subject matter more.
    cascade: bool = False
    # Mastery gating. requires_node_id present-but-null clears the gate — see
    # the same "key present in the payload" convention priority/parent use.
    requires_node_id: str | None = None
    mastery_threshold: int | None = Field(default=None, ge=1, le=100)


class NodeMove(BaseModel):
    parent_id: str | None = None
    position: int | None = None


class BranchSummary(BaseModel):
    node_id: str
    title: str
    deck_count: int
    extract_count: int
