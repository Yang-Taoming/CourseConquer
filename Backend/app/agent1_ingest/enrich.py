"""入库时的自动加工：生成摘要、关键词标签、学科/主题分类。"""
from __future__ import annotations

from app.config import get_settings
from app.shared.llm import client as llm
from app.shared.schemas.document import Enrichment

SYSTEM = (
    "你是一个知识库整理助手，面向学生的课程资料。"
    "请阅读内容，产出简洁的中文摘要、关键词标签和一个学科/主题分类。"
)


def enrich(markdown: str, filename: str) -> Enrichment:
    s = get_settings()
    text = (markdown or "")[: s.enrich_max_chars]
    user = (
        "文件名：%s\n\n内容：\n%s\n\n"
        "请只输出 JSON，不要额外文字，格式如下：\n"
        '{"summary": "150字以内的中文摘要", '
        '"tags": ["3到8个关键词标签"], '
        '"category": "所属学科或主题，如：数据结构 / 线性代数 / 操作系统"}'
    ) % (filename, text)

    data = llm.chat_json(SYSTEM, user, model=s.llm_model)
    raw_tags = data.get("tags") or []
    if isinstance(raw_tags, str):
        raw_tags = [raw_tags]
    tags = [str(t).strip() for t in raw_tags if str(t).strip()][:12]

    return Enrichment(
        summary=str(data.get("summary", "")).strip(),
        tags=tags,
        category=str(data.get("category", "")).strip(),
    )
