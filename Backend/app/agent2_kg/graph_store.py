"""知识图谱存储：SQLite 的 kg_nodes / kg_edges，带实体去重(按规范名合并)。

与 Agent 1 的存储同库(knowledge.db)，图谱是 Agent 1 分块的**派生结构**。
节点按 (workspace_id, 规范化名称) 去重；跨文档同名概念自动合并、累加 mentions。
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from functools import lru_cache
from typing import Dict, List, Tuple

from app.config import get_settings
from app.agent2_kg import schema
from app.shared.schemas.kg import GraphView, KGEdge, KGNode

_SCHEMA = """
CREATE TABLE IF NOT EXISTS kg_nodes (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name         TEXT,
    type         TEXT,
    description  TEXT,
    doc_ids      TEXT,   -- json array
    mentions     INTEGER DEFAULT 0
);
CREATE TABLE IF NOT EXISTS kg_edges (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    source_id    TEXT,
    target_id    TEXT,
    relation     TEXT,
    doc_ids      TEXT,   -- json array
    weight       INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_kgnodes_ws ON kg_nodes(workspace_id);
CREATE INDEX IF NOT EXISTS idx_kgedges_ws ON kg_edges(workspace_id);
"""

# 更具体的类型可覆盖泛化类型
_GENERIC = {"Concept", "Term"}


def _node_id(workspace_id: str, name: str) -> str:
    key = "%s::%s" % (workspace_id, " ".join(name.split()).strip().lower())
    return "n" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:15]


def _edge_id(workspace_id: str, src_id: str, dst_id: str, relation: str) -> str:
    key = "%s::%s::%s::%s" % (workspace_id, src_id, dst_id, relation)
    return "e" + hashlib.sha1(key.encode("utf-8")).hexdigest()[:15]


class GraphStore:
    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    def upsert(
        self,
        workspace_id: str,
        doc_id: str,
        entities: List[Dict[str, str]],
        relations: List[Dict[str, str]],
    ) -> Tuple[int, int]:
        """把一份文档抽取到的实体/关系并入图谱，返回 (新增节点数, 新增边数)。"""
        nodes_added = 0
        edges_added = 0
        name_to_id: Dict[str, str] = {}

        with self._conn() as c:
            for e in entities:
                nid = _node_id(workspace_id, e["name"])
                name_to_id[e["name"].lower()] = nid
                row = c.execute("SELECT id, type, doc_ids, mentions FROM kg_nodes WHERE id=?",
                                (nid,)).fetchone()
                if row is None:
                    c.execute(
                        """INSERT INTO kg_nodes (id, workspace_id, name, type, description, doc_ids, mentions)
                           VALUES (?,?,?,?,?,?,?)""",
                        (nid, workspace_id, e["name"], e["type"], e.get("description", ""),
                         json.dumps([doc_id], ensure_ascii=False), 1),
                    )
                    nodes_added += 1
                else:
                    doc_ids = set(json.loads(row["doc_ids"] or "[]"))
                    doc_ids.add(doc_id)
                    new_type = row["type"]
                    if row["type"] in _GENERIC and e["type"] not in _GENERIC:
                        new_type = e["type"]  # 用更具体的类型覆盖
                    c.execute(
                        "UPDATE kg_nodes SET doc_ids=?, mentions=mentions+1, type=?, "
                        "description=CASE WHEN description='' THEN ? ELSE description END WHERE id=?",
                        (json.dumps(sorted(doc_ids), ensure_ascii=False), new_type,
                         e.get("description", ""), nid),
                    )

            for r in relations:
                sid = name_to_id.get(r["source"].lower())
                tid = name_to_id.get(r["target"].lower())
                if not sid or not tid:
                    continue
                eid = _edge_id(workspace_id, sid, tid, r["relation"])
                row = c.execute("SELECT id, doc_ids FROM kg_edges WHERE id=?", (eid,)).fetchone()
                if row is None:
                    c.execute(
                        """INSERT INTO kg_edges (id, workspace_id, source_id, target_id, relation, doc_ids, weight)
                           VALUES (?,?,?,?,?,?,?)""",
                        (eid, workspace_id, sid, tid, r["relation"],
                         json.dumps([doc_id], ensure_ascii=False), 1),
                    )
                    edges_added += 1
                else:
                    doc_ids = set(json.loads(row["doc_ids"] or "[]"))
                    doc_ids.add(doc_id)
                    c.execute("UPDATE kg_edges SET doc_ids=?, weight=weight+1 WHERE id=?",
                              (json.dumps(sorted(doc_ids), ensure_ascii=False), eid))

        return nodes_added, edges_added

    def counts(self, workspace_id: str) -> Tuple[int, int]:
        with self._conn() as c:
            n = c.execute("SELECT COUNT(*) FROM kg_nodes WHERE workspace_id=?", (workspace_id,)).fetchone()[0]
            e = c.execute("SELECT COUNT(*) FROM kg_edges WHERE workspace_id=?", (workspace_id,)).fetchone()[0]
        return n, e

    def delete_workspace(self, workspace_id: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM kg_nodes WHERE workspace_id=?", (workspace_id,))
            c.execute("DELETE FROM kg_edges WHERE workspace_id=?", (workspace_id,))

    def graph(self, workspace_id: str) -> GraphView:
        with self._conn() as c:
            nrows = c.execute("SELECT * FROM kg_nodes WHERE workspace_id=? ORDER BY mentions DESC",
                              (workspace_id,)).fetchall()
            erows = c.execute("SELECT * FROM kg_edges WHERE workspace_id=?", (workspace_id,)).fetchall()
        nodes = [KGNode(id=r["id"], name=r["name"], type=r["type"], description=r["description"] or "",
                        doc_ids=json.loads(r["doc_ids"] or "[]"), mentions=r["mentions"] or 0) for r in nrows]
        edges = [KGEdge(id=r["id"], source_id=r["source_id"], target_id=r["target_id"],
                        relation=r["relation"], doc_ids=json.loads(r["doc_ids"] or "[]"),
                        weight=r["weight"] or 0) for r in erows]
        return GraphView(workspace_id=workspace_id, nodes=nodes, edges=edges)

    def subgraph(self, workspace_id: str, entity: str, depth: int = 1) -> GraphView:
        """以某实体为中心、按边扩展 depth 跳的邻域子图。"""
        start = _node_id(workspace_id, entity)
        with self._conn() as c:
            all_nodes = {r["id"]: r for r in c.execute(
                "SELECT * FROM kg_nodes WHERE workspace_id=?", (workspace_id,)).fetchall()}
            all_edges = c.execute("SELECT * FROM kg_edges WHERE workspace_id=?", (workspace_id,)).fetchall()
        if start not in all_nodes:
            return GraphView(workspace_id=workspace_id, nodes=[], edges=[])

        keep = {start}
        for _ in range(max(0, depth)):
            frontier = set()
            for r in all_edges:
                if r["source_id"] in keep:
                    frontier.add(r["target_id"])
                if r["target_id"] in keep:
                    frontier.add(r["source_id"])
            keep |= frontier
        nodes = [KGNode(id=r["id"], name=r["name"], type=r["type"], description=r["description"] or "",
                        doc_ids=json.loads(r["doc_ids"] or "[]"), mentions=r["mentions"] or 0)
                 for nid, r in all_nodes.items() if nid in keep]
        edges = [KGEdge(id=r["id"], source_id=r["source_id"], target_id=r["target_id"],
                        relation=r["relation"], doc_ids=json.loads(r["doc_ids"] or "[]"),
                        weight=r["weight"] or 0)
                 for r in all_edges if r["source_id"] in keep and r["target_id"] in keep]
        return GraphView(workspace_id=workspace_id, nodes=nodes, edges=edges)


@lru_cache
def get_graph_store() -> GraphStore:
    s = get_settings()
    return GraphStore(str(s.db_path))
