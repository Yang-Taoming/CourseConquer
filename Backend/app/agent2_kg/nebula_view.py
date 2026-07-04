"""借鉴 NebulaGraph 的有向属性图视图（不依赖真实 NebulaGraph 服务）。

从 Agent 2 已存储的节点/边（见 graph_store.py）生成前端可交互的展示图：
  - 稳定 VID（FIXED_STRING 风格，由 tag+规范名 hash 生成）
  - 关系类型归一化（hascomplexity→HAS_COMPLEXITY 等别名映射）
  - 属性折叠：HAS_COMPLEXITY / REQUIRES / DETECTS 等literal 关系折叠进节点的
    property_values，只保留结构性的实体-实体边用于可视化，避免复杂度等叶子节点污染画布
  - GET SUBGRAPH 风格的多跳邻域子图
  - nGQL Schema 导出（展示与真实 NebulaGraph 的对应，不要求本地安装）
"""
from __future__ import annotations

import hashlib
import re
from collections import deque
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple

# NebulaGraph 风格的稳定 VID
def _vid(tag: str, name: str) -> str:
    key = re.sub(r"[^a-z0-9一-鿿]", "", name.lower())
    raw = "%s:%s" % (tag, key)
    return "v_" + hashlib.sha1(raw.encode("utf-8")).hexdigest()[:20]


# 关系别名归一化
RELATION_ALIASES = {
    "hascomplexity": "HAS_COMPLEXITY", "hastimecomplexity": "HAS_COMPLEXITY",
    "时间复杂度": "HAS_COMPLEXITY", "complexity": "HAS_COMPLEXITY",
    "condition": "REQUIRES", "适用条件": "REQUIRES", "依赖于": "REQUIRES",
    "solves": "SOLVES", "application": "SOLVES", "用途": "SOLVES",
    "implements": "IMPLEMENTS", "调用": "CALLS", "calls": "CALLS",
    "isa": "IS_A", "具有": "HAS_PROPERTY", "导致": "CAUSES",
    "features": "HAS_FEATURE", "功能": "HAS_FEATURE", "supports": "SUPPORTS",
    # 兼容我们 LLM schema 已有的类型
    "part_of": "PART_OF", "prerequisite_of": "PREREQUISITE_OF",
    "depends_on": "DEPENDS_ON", "defines": "DEFINES",
    "example_of": "EXAMPLE_OF", "uses": "USES",
    "has_complexity": "HAS_COMPLEXITY", "contrasts_with": "CONTRASTS_WITH",
    "proposed_by": "PROPOSED_BY", "related_to": "RELATED_TO",
}

# 折叠进节点属性的关系（literal/约束类，不作为可视边）
PROPERTY_RELATIONS = {
    "HAS_COMPLEXITY": "complexities",
    "REQUIRES": "constraints",
    "DETECTS": "detects",
    "HAS_FEATURE": "features",
    "HAS_PROPERTY": "properties",
    "SUPPORTS": "supports",
    "CAUSES": "effects",
}


def _normalize_relation(value: str) -> str:
    key = re.sub(r"[^a-z0-9一-鿿]", "", str(value).lower())
    if key in RELATION_ALIASES:
        return RELATION_ALIASES[key]
    return re.sub(r"[^A-Z0-9_]", "_", str(value).upper()).strip("_") or "RELATED_TO"


def _refine_tag(name: str, current_type: str) -> str:
    """对 LLM 抽取的类型做轻量修正：识别算法/复杂度/问题/约束等特殊类。"""
    c = (name or "").strip()
    if re.search(r"^(Θ|O\(|o\()", c):
        return "Complexity"
    if current_type in ("Algorithm", "Method"):
        return current_type
    algos = {"bfs", "dfs", "dijkstra", "bellman-ford", "floyd-warshall",
             "edmonds-karp", "dinic", "kmp", "kruskal", "quicksort", "mergesort"}
    if re.sub(r"[^a-z0-9]", "", c.lower()) in algos:
        return "Algorithm"
    if re.search(r"最短路|最大流|图遍历|字符串匹配|动态规划|排序|背包|mst", c, re.I):
        return "Problem"
    if re.search(r"非负|负权|流网络|无负环|适用条件", c, re.I):
        return "Constraint"
    return current_type or "Concept"


def build_nebula_view(nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]) -> Dict[str, Any]:
    """把存储层的节点/边转成 NebulaGraph 风格的展示图。"""
    # 1) 给节点分配稳定 VID + 修正 tag
    name_to_vid: Dict[str, str] = {}
    vnodes: Dict[str, Dict[str, Any]] = {}
    for n in nodes:
        name = (n.get("name") or "").strip()
        tag = _refine_tag(name, n.get("type", "Concept"))
        vid = _vid(tag, name)
        name_to_vid[name.lower()] = vid
        vnodes[vid] = {
            "id": vid, "vid": vid,
            "name": name,
            "type": tag,
            "tags": [tag],
            "description": n.get("description", "") or name,
            "doc_ids": list(n.get("doc_ids", [])),
            "mentions": n.get("mentions", 0) or 0,
            "property_values": {},
            "raw_id": n.get("id", ""),
        }

    # 2) 处理边：归一化关系类型；literal 类折叠进节点属性，结构类保留为可视边
    visible_edges: Dict[str, Dict[str, Any]] = {}
    collapsed: List[Dict[str, Any]] = []
    for e in edges:
        src_name = (e.get("source") or e.get("source_name") or "").strip()
        dst_name = (e.get("target") or e.get("target_name") or "").strip()
        if not src_name or not dst_name:
            continue
        src_vid = name_to_vid.get(src_name.lower()) or _vid("Concept", src_name)
        dst_vid = name_to_vid.get(dst_name.lower()) or _vid("Concept", dst_name)
        # 端点若不在节点表里，补一个
        for vid, nm in ((src_vid, src_name), (dst_vid, dst_name)):
            if vid not in vnodes:
                vnodes[vid] = {"id": vid, "vid": vid, "name": nm, "type": "Concept",
                               "tags": ["Concept"], "description": nm, "doc_ids": [],
                               "mentions": 0, "property_values": {}}
                name_to_vid.setdefault(nm.lower(), vid)

        rel = _normalize_relation(e.get("relation", "RELATED_TO"))
        src_node = vnodes[src_vid]
        docs = list(e.get("doc_ids", []))
        support = e.get("weight", e.get("support_count", 1)) or 1

        if rel in PROPERTY_RELATIONS:
            bucket = PROPERTY_RELATIONS[rel]
            val = dst_name
            if val not in src_node["property_values"].setdefault(bucket, []):
                src_node["property_values"][bucket].append(val)
            collapsed.append({"source": src_vid, "edge_type": rel, "value": val,
                              "support_count": support, "source_documents": docs})
        else:
            eid = "e_" + hashlib.sha1(("%s:%s:%s" % (src_vid, rel, dst_vid)).encode("utf-8")).hexdigest()[:20]
            edge = visible_edges.get(eid)
            if edge is None:
                visible_edges[eid] = {
                    "id": eid, "source": src_vid, "target": dst_vid,
                    "relation": rel, "edge_type": rel,
                    "support_count": int(support), "source_documents": docs,
                }
            else:
                edge["support_count"] += int(support)
                for d in docs:
                    if d not in edge["source_documents"]:
                        edge["source_documents"].append(d)

    # 3) 把折叠后的属性写进 description，便于前端详情面板展示
    for node in vnodes.values():
        pv = node.get("property_values") or {}
        if pv:
            lines = ["%s: %s" % (k, "、".join(v)) for k, v in pv.items() if v]
            if lines:
                node["description"] = (node["description"] + "\n" + "\n".join(lines)).strip()

    # 4) 只保留参与可视边的节点（或带属性的算法/方法节点），删孤立叶子
    connected = {endpoint for edge in visible_edges.values()
                 for endpoint in (edge["source"], edge["target"])}
    keep_nodes = {vid: n for vid, n in vnodes.items()
                  if vid in connected or n["type"] in ("Algorithm", "Method") or n.get("property_values")}
    visible_edges = {eid: e for eid, e in visible_edges.items()
                     if e["source"] in keep_nodes and e["target"] in keep_nodes}

    return {
        "nodes": list(keep_nodes.values()),
        "edges": list(visible_edges.values()),
        "view": "nebula_property_graph",
        "schema": {
            "vertex_tags": sorted({n["type"] for n in keep_nodes.values()}),
            "edge_types": sorted({e["edge_type"] for e in visible_edges.values()}),
            "vid_type": "FIXED_STRING(22)",
        },
        "stats": {
            "vertices": len(keep_nodes), "edges": len(visible_edges),
            "collapsed_property_facts": len(collapsed),
        },
        "collapsed_facts": collapsed,
    }


def get_subgraph_view(view: Dict[str, Any], start_name: str, hops: int = 2,
                      node_limit: int = 40, edge_limit: int = 80) -> Dict[str, Any]:
    """GET SUBGRAPH 风格：从某实体出发的有界多跳子图。"""
    nodes = {n["id"]: n for n in view.get("nodes", [])}
    # 找起始 VID（按名匹配）
    start_vid = None
    target_key = re.sub(r"[^a-z0-9一-鿿]", "", start_name.lower())
    for n in view.get("nodes", []):
        if re.sub(r"[^a-z0-9一-鿿]", "", n["name"].lower()) == target_key:
            start_vid = n["id"]
            break
    if not start_vid:
        return {"nodes": [], "edges": [], "view": "nebula_subgraph", "start": start_name}

    adj: Dict[str, List[Dict[str, Any]]] = {}
    for e in view.get("edges", []):
        adj.setdefault(e["source"], []).append(e)
        adj.setdefault(e["target"], []).append(e)

    visited = {start_vid}
    selected: Dict[str, Dict[str, Any]] = {}
    queue = deque([(start_vid, 0)])
    while queue and len(visited) < node_limit and len(selected) < edge_limit:
        cur, depth = queue.popleft()
        if depth >= hops:
            continue
        for e in adj.get(cur, []):
            if len(selected) >= edge_limit:
                break
            selected[e["id"]] = e
            nb = e["target"] if e["source"] == cur else e["source"]
            if nb not in visited and nb in nodes and len(visited) < node_limit:
                visited.add(nb)
                queue.append((nb, depth + 1))
    return {
        "nodes": [nodes[vid] for vid in visited if vid in nodes],
        "edges": list(selected.values()),
        "view": "nebula_subgraph", "start_vid": start_vid, "start": start_name, "hops": hops,
    }


def generate_ngql_schema() -> str:
    """生成可选的 NebulaGraph nGQL Schema（不要求本地安装 NebulaGraph）。"""
    return """CREATE SPACE IF NOT EXISTS course_kb(vid_type=FIXED_STRING(22));
USE course_kb;
CREATE TAG IF NOT EXISTS Course(name string, doc_ids string);
CREATE TAG IF NOT EXISTS Chapter(name string, doc_ids string);
CREATE TAG IF NOT EXISTS Concept(name string, doc_ids string, property_values string);
CREATE TAG IF NOT EXISTS Algorithm(name string, doc_ids string, property_values string);
CREATE TAG IF NOT EXISTS Method(name string, doc_ids string);
CREATE TAG IF NOT EXISTS Theorem(name string, doc_ids string);
CREATE TAG IF NOT EXISTS Formula(name string, doc_ids string);
CREATE TAG IF NOT EXISTS Complexity(name string);
CREATE TAG IF NOT EXISTS Problem(name string);
CREATE TAG IF NOT EXISTS Constraint(name string);
CREATE TAG IF NOT EXISTS Term(name string);
CREATE TAG IF NOT EXISTS Example(name string);
CREATE TAG IF NOT EXISTS Tool(name string);
CREATE TAG IF NOT EXISTS Person(name string);
CREATE EDGE IF NOT EXISTS PART_OF(support_count int, sources string);
CREATE EDGE IF NOT EXISTS PREREQUISITE_OF(support_count int, sources string);
CREATE EDGE IF NOT EXISTS DEPENDS_ON(support_count int, sources string);
CREATE EDGE IF NOT EXISTS DEFINES(support_count int, sources string);
CREATE EDGE IF NOT EXISTS EXAMPLE_OF(support_count int, sources string);
CREATE EDGE IF NOT EXISTS USES(support_count int, sources string);
CREATE EDGE IF NOT EXISTS CONTRASTS_WITH(support_count int, sources string);
CREATE EDGE IF NOT EXISTS PROPOSED_BY(support_count int, sources string);
CREATE EDGE IF NOT EXISTS IMPLEMENTS(support_count int, sources string);
CREATE EDGE IF NOT EXISTS CALLS(support_count int, sources string);
CREATE EDGE IF NOT EXISTS IS_A(support_count int, sources string);
CREATE EDGE IF NOT EXISTS SOLVES(support_count int, sources string);
CREATE EDGE IF NOT EXISTS RELATED_TO(support_count int, sources string);
-- HAS_COMPLEXITY / REQUIRES / DETECTS 等折叠为顶点属性，不入图。"""
