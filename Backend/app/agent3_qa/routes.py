"""Agent 3 的 HTTP 接口：对话式问答 + 多模态生成。"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Form
from fastapi.responses import FileResponse

from app.agent3_qa.generate import generate
from app.agent3_qa.qa import chat as run_chat
from app.shared.schemas.qa import ChatRequest

router = APIRouter()


@router.post("/chat", summary="Agent 3：规划→多轮检索→带引用作答（可路由到知识图谱/联网）")
def chat(req: ChatRequest):
    return run_chat(req).model_dump()


@router.post("/generate", summary="多模态生成 skill：notes/report/ppt/doc/code/image → 下载文件")
def generate_file(
    kind: str = Form(...),
    topic: str = Form(...),
    workspace_id: Optional[str] = Form(None),
    lang: str = Form("python"),
):
    p, filename, mime = generate(kind, topic, workspace_id, lang)
    return FileResponse(str(p), filename=filename, media_type=mime, content_disposition_type="attachment")
