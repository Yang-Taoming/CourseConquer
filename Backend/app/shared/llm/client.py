"""对网关（OpenAI 兼容）的薄封装：chat / chat_json / vision / embed。

所有模型都通过同一个 client 访问，模型名由 app.config 路由。
"""
from __future__ import annotations

import base64
import json
import re
from functools import lru_cache
from typing import Any, Dict, List, Optional

import httpx
from openai import OpenAI

from app.config import get_settings


@lru_cache
def get_client() -> OpenAI:
    s = get_settings()
    # trust_env=False：网关是直连公网 IP，绕开环境里的 SOCKS 代理（否则 httpx 报缺 socksio）
    http_client = httpx.Client(trust_env=False, timeout=httpx.Timeout(180.0))
    return OpenAI(base_url=s.llm_base_url, api_key=s.llm_api_key, http_client=http_client)


def chat(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: float = 0.2,
    max_tokens: Optional[int] = None,
) -> str:
    s = get_settings()
    params: Dict[str, Any] = {
        "model": model or s.chat_model,
        "messages": messages,
        "temperature": temperature,
    }
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    resp = get_client().chat.completions.create(**params)
    return (resp.choices[0].message.content or "").strip()


def chat_json(system: str, user: str, model: Optional[str] = None) -> Dict[str, Any]:
    """让模型返回 JSON 并稳健解析（容忍代码围栏 / 多余文字）。"""
    text = chat(
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
        model=model,
        temperature=0.1,
    )
    return _extract_json(text)


def _extract_json(text: str) -> Dict[str, Any]:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\{.*\}", text, re.S)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                pass
    return {}


def vision(image_bytes: bytes, mime: str, prompt: str, model: str) -> str:
    """把图片(base64 data URL) + 提示词发给视觉模型（OCR 或 VL 都走这里）。"""
    b64 = base64.b64encode(image_bytes).decode()
    data_url = "data:%s;base64,%s" % (mime, b64)
    resp = get_client().chat.completions.create(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
        temperature=0.0,
    )
    return (resp.choices[0].message.content or "").strip()


def embed(texts: List[str], model: Optional[str] = None) -> List[List[float]]:
    s = get_settings()
    resp = get_client().embeddings.create(model=model or s.embed_model, input=texts)
    return [d.embedding for d in resp.data]
