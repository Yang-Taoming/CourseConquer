"""Agent 1 —— 入库编排：parse -> enrich(摘要/标签) -> embed -> store。

解析只做一次，产出的 ParsedDocument 同时喂给「向量化入库」与（未来的）
知识图谱抽取，所以拆分 KG 并不需要重新解析原始文件。
每一步都独立 try/except，单步失败不影响整条记录落库，失败原因写进 warnings。
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import List, Optional

from app.config import get_settings
from app.agent1_ingest.enrich import enrich as enrich_doc
from app.shared.llm import client as llm
from app.shared.parsing.chunk import chunk_blocks
from app.shared.parsing.router import parse as parse_file
from app.shared.schemas.document import Chunk, DocumentRecord, IngestResult
from app.shared.storage.local import get_storage


def _doc_id(workspace_id: str, filename: str, data: bytes) -> str:
    h = hashlib.sha1()
    h.update(workspace_id.encode("utf-8"))
    h.update(filename.encode("utf-8"))
    h.update(data[:65536])
    h.update(str(len(data)).encode("utf-8"))
    return h.hexdigest()[:16]


def ingest_file(
    data: bytes,
    filename: str,
    workspace_id: str = "default",
    source: Optional[str] = None,
) -> IngestResult:
    s = get_settings()
    warnings: List[str] = []

    # 1) 解析（一次）
    parsed = parse_file(data, filename)
    warnings.extend(parsed.meta.get("warnings", []) or [])
    if not parsed.markdown.strip():
        warnings.append("解析结果为空（可能是不支持的内容或空文件）")

    doc_id = _doc_id(workspace_id, filename, data)

    # 2) 保存原文件（知识库要求保留原文）
    raw_path = s.files_dir / ("%s_%s" % (doc_id, filename))
    try:
        raw_path.write_bytes(data)
    except Exception as e:  # noqa: BLE001
        warnings.append("原文件保存失败: %s" % e)

    # 3) 切块（携带页码/行号等来源位置）+ 向量化
    line_based = parsed.doc_type in ("text", "code")
    chunks: List[Chunk] = chunk_blocks(parsed.blocks, s.chunk_size, s.chunk_overlap, line_based)
    embeddings: List[List[float]] = []
    if chunks:
        try:
            embeddings = llm.embed([c.text for c in chunks])
            if len(embeddings) != len(chunks):
                warnings.append("向量数量与分块不一致，已跳过向量入库")
                embeddings = []
        except Exception as e:  # noqa: BLE001
            warnings.append("向量化失败: %s" % e)
            embeddings = []

    # 4) 摘要 / 标签 / 分类
    summary, tags, category = "", [], ""
    if parsed.markdown.strip():
        try:
            en = enrich_doc(parsed.markdown, filename)
            summary, tags, category = en.summary, en.tags, en.category
        except Exception as e:  # noqa: BLE001
            warnings.append("摘要/标签生成失败: %s" % e)

    # 5) 落库
    record = DocumentRecord(
        id=doc_id,
        workspace_id=workspace_id,
        filename=filename,
        source=source,
        mime=parsed.mime,
        doc_type=parsed.doc_type,
        created_at=datetime.now(timezone.utc).isoformat(),
        summary=summary,
        tags=tags,
        category=category,
        n_chunks=len(chunks) if embeddings else 0,
        markdown=parsed.markdown,
        meta={
            "parse_method": parsed.meta.get("parse_method", ""),
            "pages": parsed.meta.get("pages"),
            "slides": parsed.meta.get("slides"),
            "raw_path": str(raw_path),
        },
    )
    store = get_storage()
    if embeddings:
        store.add_document(record, chunks, embeddings)
    else:
        store.add_document(record, [], [])  # 即使向量化失败也保留元数据+原文

    return IngestResult(
        document=record,
        parse_methods=[parsed.meta.get("parse_method", "")],
        warnings=warnings,
    )
