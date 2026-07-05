"""Agent 3（问答）的对外数据结构。"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    role: str      # "user" | "assistant"
    content: str


class ChatRequest(BaseModel):
    question: str
    workspace_id: str = "default"
    conversation_id: Optional[str] = None   # 持久化对话：传入则自动读写历史（记忆）
    history: List[ChatMessage] = Field(default_factory=list)  # 显式历史（无 conversation_id 时用）
    allow_web: bool = False        # 是否允许联网搜索（默认关，避免误联网）
    top_k: Optional[int] = None
    max_rounds: Optional[int] = None


class Citation(BaseModel):
    ref: int                       # 与答案里的 [n] 对应
    doc_id: str
    filename: str
    location: str = ""             # 「第7页」「第120-135行」（人可读）
    position: Dict[str, Any] = Field(default_factory=dict)  # pages/slides/lines（结构化，供前端跳转）
    score: float = 0.0


class TraceStep(BaseModel):
    step: str                      # plan / retrieve / judge / multi_doc / web / kg / synthesize
    text: str                      # 人可读的一句话
    detail: Dict[str, Any] = Field(default_factory=dict)


class WebLink(BaseModel):
    url: str
    title: str = ""


class ChatResponse(BaseModel):
    answer: str
    route: str                     # retrieve | multi_doc | kg | web | direct | empty
    intent: str = ""
    rounds: int = 0                # 实际检索轮数
    citations: List[Citation] = Field(default_factory=list)
    trace: List[TraceStep] = Field(default_factory=list)        # 思维链（前端动态展示）
    provenance: str = "model_only"  # kb_full | kb_partial | web | model_only
    web_links: List[WebLink] = Field(default_factory=list)
    plan: Dict[str, Any] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    usage: Dict[str, Any] = Field(default_factory=dict)   # tokens_in / tokens_out / total（本次问答）
