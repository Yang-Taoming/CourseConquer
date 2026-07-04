"""从一段文本抽取实体+关系（限定 schema），并做基本清洗。"""
from __future__ import annotations

from typing import Any, Dict, List

from app.config import get_settings
from app.agent2_kg import schema
from app.shared.llm import client as llm


def _norm(name: str) -> str:
    return " ".join(str(name).split()).strip()


def extract(text: str, context: str) -> Dict[str, List[Dict[str, Any]]]:
    """返回 {'entities': [...], 'relations': [...]}，类型已按 schema 过滤。"""
    s = get_settings()
    data = llm.chat_json(
        schema.build_system_prompt(),
        schema.user_prompt(context, text),
        model=s.llm_model,
    )

    # --- 清洗实体 ---
    entities: List[Dict[str, Any]] = []
    seen = {}
    for e in (data.get("entities") or []):
        name = _norm(e.get("name", ""))
        etype = str(e.get("type", "")).strip()
        if not name:
            continue
        if etype not in schema.ENTITY_TYPES:
            etype = schema.DEFAULT_ENTITY_TYPE
        key = name.lower()
        if key in seen:
            continue
        seen[key] = etype
        entities.append({"name": name, "type": etype,
                         "description": str(e.get("description", "")).strip()})

    # --- 清洗关系（端点若缺失则补成默认类型实体，保证图连通）---
    relations: List[Dict[str, Any]] = []
    for r in (data.get("relations") or []):
        src = _norm(r.get("source", ""))
        dst = _norm(r.get("target", ""))
        rel = str(r.get("relation", "")).strip()
        if not src or not dst or src.lower() == dst.lower():
            continue
        if rel not in schema.RELATION_TYPES:
            rel = schema.FALLBACK_RELATION
        for endpoint in (src, dst):
            if endpoint.lower() not in seen:
                seen[endpoint.lower()] = schema.DEFAULT_ENTITY_TYPE
                entities.append({"name": endpoint, "type": schema.DEFAULT_ENTITY_TYPE,
                                 "description": ""})
        relations.append({"source": src, "target": dst, "relation": rel})

    return {"entities": entities, "relations": relations}
