"""Agent 3 的 HTTP 接口：对话式问答。"""
from __future__ import annotations

from fastapi import APIRouter

from app.agent3_qa.qa import chat as run_chat
from app.shared.schemas.qa import ChatRequest

router = APIRouter()


@router.post("/chat", summary="Agent 3：规划→多轮检索→带引用作答（可路由到知识图谱/联网）")
def chat(req: ChatRequest):
    return run_chat(req).model_dump()
