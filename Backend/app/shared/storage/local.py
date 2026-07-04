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
