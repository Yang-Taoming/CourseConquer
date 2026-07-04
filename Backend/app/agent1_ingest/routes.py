"""Agent 1 的 HTTP 接口：上传入库、列出/查看文档、语义检索、原文下载。"""
from __future__ import annotations

from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse

from app.agent1_ingest.ingest import ingest_file
from app.shared.llm import client as llm
from app.shared.parsing.router import parse as parse_file
from app.shared.storage.local import get_storage

router = APIRouter()


@router.post("/parse", summary="【测试】仅解析预览：上传文件 → 返回规范化内容，不摘要/不入库/不花 token")
async def parse_preview(file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    parsed = parse_file(data, file.filename or "unnamed")
    return {
        "ok": bool(parsed.markdown.strip()),
        "filename": parsed.filename,
        "doc_type": parsed.doc_type,
        "mime": parsed.mime,
        "parse_method": parsed.meta.get("parse_method"),
        "n_blocks": len(parsed.blocks),
        "char_count": len(parsed.markdown),
        "markdown_preview": parsed.markdown[:2000],
        "meta": parsed.meta,
    }


@router.post("/ingest", summary="上传文件 -> 解析 + 摘要标签 + 向量入库")
async def ingest(
    file: UploadFile = File(...),
    workspace_id: str = Form("default"),
    source: Optional[str] = Form(None),
):
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="空文件")
    result = ingest_file(
        data,
        file.filename or "unnamed",
        workspace_id=workspace_id,
        source=source,
    )
    return result.model_dump()


@router.get("/documents", summary="列出某工作区的所有文档")
def list_documents(workspace_id: str = Query("default")):
    return [r.model_dump() for r in get_storage().list_documents(workspace_id)]


@router.get("/documents/{doc_id}", summary="查看单个文档（含原文 markdown）")
def get_document(doc_id: str):
    rec = get_storage().get_document(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="文档不存在")
    return rec.model_dump()


@router.get("/search", summary="基于向量的语义检索")
def search(
    q: str = Query(..., description="查询语句"),
    workspace_id: str = Query("default"),
    k: int = Query(5, ge=1, le=50),
):
    try:
        emb = llm.embed([q])[0]
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=502, detail="向量化查询失败: %s" % e)
    hits = get_storage().search(workspace_id, emb, k)
    return {"query": q, "hits": hits}


@router.get("/files/{doc_id}", summary="下载/预览原始文件（供引用点击跳转打开）")
def get_file(doc_id: str):
    rec = get_storage().get_document(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="文档不存在")
    raw_path = (rec.meta or {}).get("raw_path") or ""
    p = Path(raw_path)
    if not raw_path or not p.exists():
        raise HTTPException(status_code=404, detail="原始文件未保存")
    # inline 让浏览器直接预览（PDF/图片），PDF viewer 支持 #page=N 跳页
    return FileResponse(str(p), filename=rec.filename, media_type=rec.mime or "application/octet-stream")

