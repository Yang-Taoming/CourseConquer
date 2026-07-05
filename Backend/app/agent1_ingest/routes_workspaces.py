"""知识库（workspace）管理 + 对话 + 用量 的 HTTP 接口。"""
from __future__ import annotations

from fastapi import APIRouter, Form, HTTPException, Query

from app.agent2_kg.graph_store import get_graph_store
from app.config import get_settings
from app.shared.llm import client as llm
from app.shared.storage.local import get_storage

router = APIRouter()


@router.post("/workspaces/{ws_id}/summarize_all", summary="生成整个知识库的总摘要（基于各文件摘要）")
def summarize_all(ws_id: str):
    store = get_storage()
    docs = store.list_documents(ws_id)
    if not docs:
        raise HTTPException(status_code=400, detail="知识库为空")
    ctx = "\n\n".join("【%s】%s" % (d.filename, (d.summary or (d.markdown or "")[:300]))
                      for d in docs[:40])
    s = get_settings()
    summary = llm.chat(
        [{"role": "system", "content": "你是知识库摘要助手。基于给定的各文件摘要，生成一份整个知识库的总摘要：涵盖主要主题、核心知识点、适用场景。用中文，Markdown。"},
         {"role": "user", "content": "知识库各文件：\n" + ctx}],
        model=s.llm_model, max_tokens=4000,
    )
    return {"summary": summary}


# ---------- 知识库（workspace）----------
@router.get("/workspaces", summary="列出所有知识库")
def list_workspaces():
    return get_storage().list_workspaces()


@router.post("/workspaces", summary="新建知识库")
def create_workspace(name: str = Form(...)):
    wid = get_storage().create_workspace(name)
    return {"id": wid, "name": name}


@router.patch("/workspaces/{workspace_id}", summary="重命名知识库")
def rename_workspace(workspace_id: str, name: str = Form(...)):
    get_storage().rename_workspace(workspace_id, name)
    return {"id": workspace_id, "name": name}


@router.delete("/workspaces/{workspace_id}", summary="删除知识库（级联清空文档/分块/图谱/对话/用量）")
def delete_workspace(workspace_id: str):
    store = get_storage()
    store.delete_workspace(workspace_id)
    get_graph_store().delete_workspace(workspace_id)
    return {"ok": True, "id": workspace_id}


# ---------- 对话（记忆持久化）----------
@router.get("/conversations", summary="列出某知识库的对话")
def list_conversations(workspace_id: str = Query(...)):
    return get_storage().list_conversations(workspace_id)


@router.post("/conversations", summary="新建对话")
def create_conversation(workspace_id: str = Form(...), title: str = Form("")):
    cid = get_storage().create_conversation(workspace_id, title)
    return {"id": cid, "workspace_id": workspace_id, "title": title}


@router.get("/conversations/{conv_id}", summary="查看对话历史（含消息）")
def get_conversation(conv_id: str):
    conv = get_storage().get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    return conv


@router.delete("/conversations/{conv_id}", summary="删除对话")
def delete_conversation(conv_id: str):
    get_storage().delete_conversation(conv_id)
    return {"ok": True, "id": conv_id}


@router.post("/conversations/{conv_id}/save_to_kb", summary="一键把对话存入知识库（转为文档入库）")
def save_conv_to_kb(conv_id: str):
    from app.agent1_ingest.ingest import ingest_file
    store = get_storage()
    conv = store.get_conversation(conv_id)
    if not conv:
        raise HTTPException(status_code=404, detail="对话不存在")
    lines = ["# 对话记录：%s\n" % (conv.get("title") or conv_id)]
    for m in conv["messages"]:
        who = "用户" if m["role"] == "user" else "CourseMind"
        lines.append("**%s**：%s\n" % (who, m["content"]))
    md = "\n".join(lines).encode("utf-8")
    fname = "对话_%s.md" % conv_id[-8:]
    res = ingest_file(md, fname, workspace_id=conv["workspace_id"], source="conversation")
    return res.document.model_dump()


# ---------- 用量统计 ----------
@router.get("/usage", summary="token 用量统计（按操作分类 + 平均）")
def get_usage(workspace_id: str = Query(...)):
    return get_storage().get_usage(workspace_id)


# ---------- 文件删除 ----------
@router.delete("/documents/{doc_id}", summary="删除某文档（含分块）")
def delete_document(doc_id: str):
    get_storage().delete_document(doc_id)
    return {"ok": True, "id": doc_id}


# ---------- 文件摘要重新生成 ----------
@router.post("/documents/{doc_id}/summarize", summary="调大模型重新生成摘要/标签，写回并返回")
def regenerate_summary(doc_id: str):
    from app.agent1_ingest.enrich import enrich as enrich_doc
    store = get_storage()
    rec = store.get_document(doc_id)
    if not rec:
        raise HTTPException(status_code=404, detail="文档不存在")
    en = enrich_doc(rec.markdown, rec.filename)
    rec.summary = en.summary
    rec.tags = en.tags
    rec.category = en.category
    store.update_document_summary(doc_id, en.summary, en.tags, en.category)
    return {"doc_id": doc_id, "summary": en.summary, "tags": en.tags, "category": en.category}
