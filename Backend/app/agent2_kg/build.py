"""Agent 2 —— 知识图谱构建（按钮触发，可选）。

关键：**从库里已解析的 markdown 读取**，不重新解析原始文件、不重跑 OCR/VL。
对每份文档按 kg_batch_chars 分批抽取实体+关系，并入同库的图谱(去重合并)。
"""
from __future__ import annotations

from typing import List, Optional

from app.config import get_settings
from app.agent2_kg.extract import extract
from app.agent2_kg.graph_store import get_graph_store
from app.shared.schemas.kg import BuildResult
from app.shared.storage.local import get_storage


def _batches(text: str, size: int) -> List[str]:
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    paras = [p for p in text.split("\n\n") if p.strip()]
    out: List[str] = []
    cur = ""
    for p in paras:
        if len(p) > size:
            if cur:
                out.append(cur)
                cur = ""
            for i in range(0, len(p), size):
                out.append(p[i:i + size])
            continue
        if not cur:
            cur = p
        elif len(cur) + len(p) + 2 <= size:
            cur = cur + "\n\n" + p
        else:
            out.append(cur)
            cur = p
    if cur:
        out.append(cur)
    return out


def build_kg(workspace_id: str = "default", doc_id: Optional[str] = None) -> BuildResult:
    s = get_settings()
    store = get_storage()
    gstore = get_graph_store()
    warnings: List[str] = []

    # 选定要构建的文档：单篇 or 整个工作区
    if doc_id:
        rec = store.get_document(doc_id)
        docs = [rec] if rec else []
        if not rec:
            warnings.append("文档不存在: %s" % doc_id)
    else:
        docs = store.list_documents(workspace_id)

    nodes_added = 0
    edges_added = 0
    used_docs: List[str] = []

    for rec in docs:
        if not rec.markdown.strip():
            continue
        context = "课程/分类：%s；文件名：%s" % (rec.category or "未知", rec.filename)
        used_docs.append(rec.id)
        for batch in _batches(rec.markdown, s.kg_batch_chars):
            try:
                ext = extract(batch, context)
            except Exception as e:  # noqa: BLE001
                warnings.append("文档 %s 抽取失败: %s" % (rec.id, e))
                continue
            na, ea = gstore.upsert(rec.workspace_id, rec.id, ext["entities"], ext["relations"])
            nodes_added += na
            edges_added += ea

    n_total, e_total = gstore.counts(workspace_id)
    return BuildResult(
        workspace_id=workspace_id,
        doc_ids=used_docs,
        nodes_added=nodes_added,
        edges_added=edges_added,
        nodes_total=n_total,
        edges_total=e_total,
        warnings=warnings,
    )
