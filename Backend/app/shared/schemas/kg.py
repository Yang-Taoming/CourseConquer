"""知识图谱的对外数据结构。"""
from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class KGNode(BaseModel):
    id: str
    name: str
    type: str
    description: str = ""
    doc_ids: List[str] = Field(default_factory=list)
    mentions: int = 0


class KGEdge(BaseModel):
    id: str
    source_id: str
    target_id: str
    relation: str
    doc_ids: List[str] = Field(default_factory=list)
    weight: int = 0


class GraphView(BaseModel):
    workspace_id: str
    nodes: List[KGNode] = Field(default_factory=list)
    edges: List[KGEdge] = Field(default_factory=list)


class BuildResult(BaseModel):
    workspace_id: str
    doc_ids: List[str] = Field(default_factory=list)   # 本次参与构建的文档
    nodes_added: int = 0
    edges_added: int = 0
    nodes_total: int = 0
    edges_total: int = 0
    warnings: List[str] = Field(default_factory=list)
