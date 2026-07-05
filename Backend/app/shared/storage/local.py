"""本地存储：SQLite 存元数据 + 分块 + 向量(float32 blob)，用 numpy 做余弦检索。

对黑客松规模足够，且零重型依赖。向量存 blob，检索时载入内存算 cosine。
接口与 base.Storage 一致，日后可整体替换为 Chroma / pgvector。
"""
from __future__ import annotations

import json
import sqlite3
from functools import lru_cache
from typing import Any, Dict, List, Optional

import numpy as np

from app.config import get_settings
from app.shared.schemas.document import Chunk, DocumentRecord

_SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    filename     TEXT,
    source       TEXT,
    mime         TEXT,
    doc_type     TEXT,
    created_at   TEXT,
    summary      TEXT,
    tags         TEXT,   -- json array
    category     TEXT,
    n_chunks     INTEGER,
    markdown     TEXT,
    meta         TEXT    -- json object
);
CREATE TABLE IF NOT EXISTS chunks (
    id           TEXT PRIMARY KEY,
    document_id  TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    ordinal      INTEGER,
    text         TEXT,
    meta         TEXT,   -- json: loc/pages/slides/lines/blocks (来源位置)
    embedding    BLOB
);
CREATE INDEX IF NOT EXISTS idx_documents_ws ON documents(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_ws ON chunks(workspace_id);
CREATE INDEX IF NOT EXISTS idx_chunks_doc ON chunks(document_id);

-- 知识库（workspace）元信息
CREATE TABLE IF NOT EXISTS workspaces (
    id           TEXT PRIMARY KEY,
    name         TEXT,
    created_at   TEXT,
    last_used_at TEXT
);

-- 对话与消息（记忆持久化）
CREATE TABLE IF NOT EXISTS conversations (
    id            TEXT PRIMARY KEY,
    workspace_id  TEXT NOT NULL,
    title         TEXT,
    created_at    TEXT,
    updated_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_conv_ws ON conversations(workspace_id);
CREATE TABLE IF NOT EXISTS messages (
    id              TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    role            TEXT,        -- user / assistant
    content         TEXT,
    meta            TEXT,        -- json: trace / citations / provenance / route
    tokens_in       INTEGER DEFAULT 0,
    tokens_out      INTEGER DEFAULT 0,
    importance      REAL DEFAULT 0,     -- Generative Agents 重要性分（0-10）
    embedding       BLOB,               -- user 问句的 bge-m3 向量（情景记忆检索）
    created_at      TEXT
);
CREATE INDEX IF NOT EXISTS idx_msg_conv ON messages(conversation_id);

-- token 用量
CREATE TABLE IF NOT EXISTS token_usage (
    id           TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    operation    TEXT,        -- chat / kg_build / ingest
    tokens_in    INTEGER DEFAULT 0,
    tokens_out   INTEGER DEFAULT 0,
    created_at   TEXT
);
CREATE INDEX IF NOT EXISTS idx_tok_ws ON token_usage(workspace_id);
"""


def _to_blob(vec: List[float]) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def _from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


class LocalStorage:
    def __init__(self, db_path: str) -> None:
        self.db_path = str(db_path)
        with self._conn() as c:
            c.executescript(_SCHEMA)
            # 轻量迁移：给旧 messages 表补 importance / embedding 列
            cols = {r[1] for r in c.execute("PRAGMA table_info(messages)").fetchall()}
            if "importance" not in cols:
                c.execute("ALTER TABLE messages ADD COLUMN importance REAL DEFAULT 0")
            if "embedding" not in cols:
                c.execute("ALTER TABLE messages ADD COLUMN embedding BLOB")

    def _conn(self) -> sqlite3.Connection:
        c = sqlite3.connect(self.db_path)
        c.row_factory = sqlite3.Row
        return c

    # --- 写入 ---
    def add_document(
        self,
        record: DocumentRecord,
        chunks: List[Chunk],
        embeddings: List[List[float]],
    ) -> None:
        with self._conn() as c:
            c.execute(
                """INSERT OR REPLACE INTO documents
                   (id, workspace_id, filename, source, mime, doc_type, created_at,
                    summary, tags, category, n_chunks, markdown, meta)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    record.id, record.workspace_id, record.filename, record.source,
                    record.mime, record.doc_type, record.created_at, record.summary,
                    json.dumps(record.tags, ensure_ascii=False), record.category,
                    record.n_chunks, record.markdown,
                    json.dumps(record.meta, ensure_ascii=False),
                ),
            )
            # 覆盖式：先删旧分块再写新分块
            c.execute("DELETE FROM chunks WHERE document_id=?", (record.id,))
            for ch, emb in zip(chunks, embeddings):
                c.execute(
                    """INSERT INTO chunks (id, document_id, workspace_id, ordinal, text, meta, embedding)
                       VALUES (?,?,?,?,?,?,?)""",
                    ("%s:%d" % (record.id, ch.ordinal), record.id, record.workspace_id,
                     ch.ordinal, ch.text, json.dumps(ch.meta, ensure_ascii=False),
                     _to_blob(emb)),
                )

    # --- 读取 ---
    def get_document(self, doc_id: str) -> Optional[DocumentRecord]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM documents WHERE id=?", (doc_id,)).fetchone()
        return _row_to_record(row) if row else None

    def list_documents(self, workspace_id: str) -> List[DocumentRecord]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT * FROM documents WHERE workspace_id=? ORDER BY created_at DESC",
                (workspace_id,),
            ).fetchall()
        return [_row_to_record(r) for r in rows]

    # --- 检索 ---
    def search(
        self,
        workspace_id: str,
        query_embedding: List[float],
        k: int,
        doc_ids: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        q = np.asarray(query_embedding, dtype=np.float32)
        qn = q / (np.linalg.norm(q) + 1e-8)
        sql = ("""SELECT c.id, c.document_id, c.ordinal, c.text, c.meta, c.embedding,
                          d.filename
                   FROM chunks c JOIN documents d ON c.document_id = d.id
                   WHERE c.workspace_id = ?""")
        params: List[Any] = [workspace_id]
        if doc_ids:
            sql += " AND c.document_id IN (%s)" % ",".join("?" * len(doc_ids))
            params.extend(doc_ids)
        with self._conn() as c:
            rows = c.execute(sql, params).fetchall()

        scored = []
        for r in rows:
            v = _from_blob(r["embedding"])
            if v.shape != qn.shape:
                continue
            score = float(np.dot(v, qn) / (np.linalg.norm(v) + 1e-8))
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)

        out: List[Dict[str, Any]] = []
        for score, r in scored[:k]:
            meta = json.loads(r["meta"]) if r["meta"] else {}
            out.append({
                "chunk_id": r["id"],
                "document_id": r["document_id"],
                "filename": r["filename"],
                "ordinal": r["ordinal"],
                "location": meta.get("loc", ""),   # 人可读的位置，如「第7页」「第120-135行」
                "position": meta,                   # 结构化位置：pages/slides/lines/blocks
                "score": round(score, 4),
                "text": r["text"],
            })
        return out

    # --- 删除 ---
    def delete_document(self, doc_id: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM chunks WHERE document_id=?", (doc_id,))
            c.execute("DELETE FROM documents WHERE id=?", (doc_id,))

    def update_document_summary(self, doc_id: str, summary: str, tags: list, category: str) -> None:
        with self._conn() as c:
            c.execute(
                "UPDATE documents SET summary=?, tags=?, category=? WHERE id=?",
                (summary, json.dumps(tags, ensure_ascii=False), category, doc_id),
            )

    # --- 知识库（workspace）---
    def list_workspaces(self) -> List[Dict[str, Any]]:
        with self._conn() as c:
            # 已登记的 workspace ∪ 有文档但未登记的 workspace（旧数据兼容）
            rows = c.execute(
                """SELECT * FROM (
                    SELECT w.id AS id, COALESCE(w.name, w.id) AS name, w.created_at AS created_at,
                           w.last_used_at AS last_used_at,
                           (SELECT COUNT(*) FROM documents d WHERE d.workspace_id=w.id) AS n_docs,
                           (SELECT COUNT(*) FROM conversations cv WHERE cv.workspace_id=w.id) AS n_conv
                    FROM workspaces w
                    UNION ALL
                    SELECT d.workspace_id AS id, d.workspace_id AS name, NULL AS created_at, NULL AS last_used_at,
                           COUNT(*) AS n_docs, 0 AS n_conv
                    FROM documents d
                    WHERE d.workspace_id NOT IN (SELECT id FROM workspaces)
                    GROUP BY d.workspace_id
                ) ORDER BY COALESCE(last_used_at, created_at) DESC"""
            ).fetchall()
        return [dict(r) for r in rows]

    def ensure_workspace(self, workspace_id: str, name: str = "") -> None:
        with self._conn() as c:
            row = c.execute("SELECT id FROM workspaces WHERE id=?", (workspace_id,)).fetchone()
            if row is None:
                c.execute(
                    "INSERT INTO workspaces (id, name, created_at, last_used_at) VALUES (?,?,?,?)",
                    (workspace_id, name or workspace_id, _now(), _now()),
                )
            else:
                c.execute("UPDATE workspaces SET last_used_at=? WHERE id=?", (_now(), workspace_id))

    def create_workspace(self, name: str) -> str:
        import hashlib, time
        wid = "ws_" + hashlib.sha1(("%s-%f" % (name, time.time())).encode("utf-8")).hexdigest()[:12]
        with self._conn() as c:
            c.execute(
                "INSERT INTO workspaces (id, name, created_at, last_used_at) VALUES (?,?,?,?)",
                (wid, name, _now(), _now()),
            )
        return wid

    def rename_workspace(self, workspace_id: str, name: str) -> None:
        self.ensure_workspace(workspace_id)
        with self._conn() as c:
            c.execute("UPDATE workspaces SET name=? WHERE id=?", (name, workspace_id))

    def delete_workspace(self, workspace_id: str) -> None:
        with self._conn() as c:
            for tbl in ("chunks", "documents", "messages", "conversations", "token_usage"):
                if tbl in ("messages",):
                    c.execute(
                        "DELETE FROM messages WHERE conversation_id IN "
                        "(SELECT id FROM conversations WHERE workspace_id=?)", (workspace_id,))
                else:
                    c.execute("DELETE FROM %s WHERE workspace_id=?" % tbl, (workspace_id,))
            c.execute("DELETE FROM conversations WHERE workspace_id=?", (workspace_id,))
            c.execute("DELETE FROM workspaces WHERE id=?", (workspace_id,))

    # --- 对话与消息（记忆持久化）---
    def list_conversations(self, workspace_id: str) -> List[Dict[str, Any]]:
        with self._conn() as c:
            rows = c.execute(
                """SELECT cv.*, (SELECT COUNT(*) FROM messages m WHERE m.conversation_id=cv.id) AS n_msgs
                   FROM conversations cv WHERE cv.workspace_id=? ORDER BY cv.updated_at DESC""",
                (workspace_id,),
            ).fetchall()
        return [dict(r) for r in rows]

    def create_conversation(self, workspace_id: str, title: str = "") -> str:
        import hashlib, time
        cid = "cv_" + hashlib.sha1(("%s-%f" % (workspace_id, time.time())).encode("utf-8")).hexdigest()[:12]
        with self._conn() as c:
            c.execute(
                "INSERT INTO conversations (id, workspace_id, title, created_at, updated_at) VALUES (?,?,?,?,?)",
                (cid, workspace_id, title, _now(), _now()),
            )
        return cid

    def get_conversation(self, conv_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            row = c.execute("SELECT * FROM conversations WHERE id=?", (conv_id,)).fetchone()
            if not row:
                return None
            msgs = c.execute(
                "SELECT id, role, content, meta, tokens_in, tokens_out, created_at FROM messages "
                "WHERE conversation_id=? ORDER BY created_at ASC", (conv_id,),
            ).fetchall()
        out = dict(row)
        out["messages"] = [dict(m) for m in msgs]
        return out

    def delete_conversation(self, conv_id: str) -> None:
        with self._conn() as c:
            c.execute("DELETE FROM messages WHERE conversation_id=?", (conv_id,))
            c.execute("DELETE FROM conversations WHERE id=?", (conv_id,))

    def add_message(self, conv_id: str, role: str, content: str,
                    meta: Optional[Dict[str, Any]] = None,
                    tokens_in: int = 0, tokens_out: int = 0,
                    importance: float = 0.0,
                    embedding: Optional[List[float]] = None) -> None:
        import hashlib, time
        mid = "m_" + hashlib.sha1(("%s-%f" % (conv_id, time.time())).encode("utf-8")).hexdigest()[:12]
        emb_blob = _to_blob(embedding) if embedding else None
        with self._conn() as c:
            c.execute(
                """INSERT INTO messages (id, conversation_id, role, content, meta,
                                          tokens_in, tokens_out, importance, embedding, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (mid, conv_id, role, content,
                 json.dumps(meta, ensure_ascii=False) if meta else None,
                 tokens_in, tokens_out, importance, emb_blob, _now()),
            )
            c.execute("UPDATE conversations SET updated_at=? WHERE id=?", (_now(), conv_id))

    def retrieve_memory(self, conv_id: str, query_embedding: List[float],
                        k: int = 4) -> List[Dict[str, Any]]:
        """Generative Agents 情景记忆检索：score = importance × recency × relevance。

        从当前对话的过去轮次里，按 重要性·新近度·相关性 取 top-K，用于多轮记忆。
        """
        q = np.asarray(query_embedding, dtype=np.float32)
        qn = q / (np.linalg.norm(q) + 1e-8)
        with self._conn() as c:
            rows = c.execute(
                "SELECT id, role, content, importance, embedding, created_at FROM messages "
                "WHERE conversation_id=? AND embedding IS NOT NULL ORDER BY created_at ASC",
                (conv_id,),
            ).fetchall()
        if not rows:
            return []
        scored = []
        n = len(rows)
        for i, r in enumerate(rows):
            v = _from_blob(r["embedding"])
            if v.shape != qn.shape:
                continue
            rel = float(np.dot(v, qn) / (np.linalg.norm(v) + 1e-8))
            recency = 0.99 ** (n - 1 - i)            # 越新越接近 1
            importance = (r["importance"] or 1.0) / 10.0  # 归一到 0-1
            score = importance * 0.4 + recency * 0.3 + max(0, rel) * 0.3
            scored.append((score, r))
        scored.sort(key=lambda x: x[0], reverse=True)
        out = []
        for score, r in scored[:k]:
            out.append({"role": r["role"], "content": r["content"], "score": round(score, 3)})
        return out

    # --- token 用量 ---
    def add_token_usage(self, workspace_id: str, operation: str,
                        tokens_in: int = 0, tokens_out: int = 0) -> None:
        import hashlib, time
        tid = "t_" + hashlib.sha1(("%s-%s-%f" % (workspace_id, operation, time.time())).encode("utf-8")).hexdigest()[:12]
        with self._conn() as c:
            c.execute(
                "INSERT INTO token_usage (id, workspace_id, operation, tokens_in, tokens_out, created_at) VALUES (?,?,?,?,?,?)",
                (tid, workspace_id, operation, tokens_in, tokens_out, _now()),
            )

    def get_usage(self, workspace_id: str) -> Dict[str, Any]:
        with self._conn() as c:
            rows = c.execute(
                "SELECT operation, SUM(tokens_in) AS tin, SUM(tokens_out) AS tout, COUNT(*) AS n FROM token_usage "
                "WHERE workspace_id=? GROUP BY operation", (workspace_id,),
            ).fetchall()
        by_op = {r["operation"]: {"tokens_in": r["tin"] or 0, "tokens_out": r["tout"] or 0,
                                  "calls": r["n"] or 0, "total": (r["tin"] or 0) + (r["tout"] or 0)}
                 for r in rows}
        total_in = sum(v["tokens_in"] for v in by_op.values())
        total_out = sum(v["tokens_out"] for v in by_op.values())
        chat = by_op.get("chat", {"calls": 0, "total": 0})
        kg = by_op.get("kg_build", {"calls": 0, "total": 0})
        return {
            "by_operation": by_op,
            "total_tokens": total_in + total_out,
            "tokens_in": total_in, "tokens_out": total_out,
            "avg_per_answer": (chat["total"] / chat["calls"]) if chat["calls"] else 0,
            "avg_per_kg_build": (kg["total"] / kg["calls"]) if kg["calls"] else 0,
        }


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _row_to_record(row: sqlite3.Row) -> DocumentRecord:
    return DocumentRecord(
        id=row["id"],
        workspace_id=row["workspace_id"],
        filename=row["filename"],
        source=row["source"],
        mime=row["mime"],
        doc_type=row["doc_type"],
        created_at=row["created_at"],
        summary=row["summary"] or "",
        tags=json.loads(row["tags"]) if row["tags"] else [],
        category=row["category"] or "",
        n_chunks=row["n_chunks"] or 0,
        markdown=row["markdown"] or "",
        meta=json.loads(row["meta"]) if row["meta"] else {},
    )


@lru_cache
def get_storage() -> LocalStorage:
    s = get_settings()
    return LocalStorage(str(s.db_path))
