"""Agent 2 的 HTTP 接口：按钮触发构建、拉取图谱、邻域子图、schema、nGQL。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Form, Query

from app.agent2_kg import schema as kg_schema
from app.agent2_kg.build import build_kg
from app.agent2_kg.graph_store import get_graph_store
from app.agent2_kg.nebula_view import build_nebula_view, generate_ngql_schema, get_subgraph_view

router = APIRouter(prefix="/kg")


def _current_view(workspace_id: str):
    """读存储层图 -> 转 NebulaGraph 风格展示图。"""
    g = get_graph_store().graph(workspace_id)
    nodes = [n.model_dump() for n in g.nodes]
    edges = []
    for e in g.edges:
        # graph_store 的边用 source_id/target_id，这里需要 name；从节点表回填
        edges.append({
            "source": _node_name(nodes, e.source_id),
            "target": _node_name(nodes, e.target_id),
            "relation": e.relation,
            "doc_ids": e.doc_ids,
            "weight": e.weight,
        })
    return build_nebula_view(nodes, edges), g


def _node_name(nodes, vid):
    for n in nodes:
        if n.get("id") == vid:
            return n.get("name", "")
    return ""


@router.post("/build", summary="【按钮】从已入库内容构建/扩展知识图谱（不重新解析）")
def build(
    workspace_id: str = Form("default"),
    doc_id: Optional[str] = Form(None),
):
    return build_kg(workspace_id=workspace_id, doc_id=doc_id).model_dump()


@router.get("", summary="拉取 NebulaGraph 风格的展示图（节点+边，供前端渲染）")
def get_graph(workspace_id: str = Query("default")):
    view, g = _current_view(workspace_id)
    return view


@router.get("/subgraph", summary="以某实体为中心的 GET SUBGRAPH 邻域（多跳）")
def get_subgraph(
    entity: str = Query(..., description="中心实体名称"),
    workspace_id: str = Query("default"),
    depth: int = Query(2, ge=1, le=3),
):
    view, _ = _current_view(workspace_id)
    return get_subgraph_view(view, entity, hops=depth)


@router.get("/schema", summary="查看当前限定的实体/关系类型")
def get_schema():
    return {"entity_types": kg_schema.ENTITY_TYPES, "relation_types": kg_schema.RELATION_TYPES}


@router.get("/ngql", summary="导出 NebulaGraph nGQL Schema（展示对应，无需本地安装）")
def get_ngql():
    return {"ngql": generate_ngql_schema()}
