"""集中配置：从 Backend/model-config/models.yaml 读取网关、密钥、模型路由与解析参数。

不同人用不同 key —— 把你自己的 key 放在 model-config/models.yaml（已 gitignore）。
模板见 model-config/models.example.yaml。环境变量可覆盖（LLM_API_KEY / LLM_BASE_URL 等）。
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

import yaml

BASE_DIR = Path(__file__).resolve().parent.parent  # -> Backend/
_MODEL_CONFIG = BASE_DIR / "model-config" / "models.yaml"
_MODEL_EXAMPLE = BASE_DIR / "model-config" / "models.example.yaml"


def _load_yaml() -> Dict[str, Any]:
    for p in (_MODEL_CONFIG, _MODEL_EXAMPLE):
        if p.exists():
            try:
                return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
            except Exception:
                return {}
    return {}


class Settings:
    def __init__(self) -> None:
        cfg = _load_yaml()
        gw = cfg.get("gateway", {}) or {}
        models = cfg.get("models", {}) or {}
        parsing = cfg.get("parsing", {}) or {}
        qa = cfg.get("qa", {}) or {}
        kg = cfg.get("kg", {}) or {}

        # --- 网关（环境变量可覆盖）---
        self.llm_base_url = os.environ.get("LLM_BASE_URL", gw.get("base_url", "http://localhost:8000/v1"))
        self.llm_api_key = os.environ.get("LLM_API_KEY", gw.get("api_key", ""))

        # --- 模型路由 ---
        self.llm_model = models.get("llm_model", "gpt-5.1-high")
        self.llm_model_strong = models.get("llm_model_strong", "gpt-5.1-high")
        self.vision_model = models.get("vision_model", "gpt-5.1-high")
        self.embed_model = models.get("embed_model", "BAAI/bge-m3")
        self.web_model = models.get("web_model", "moonshotai/kimi-k2:online")
        self.image_model = models.get("image_model", "gpt-image-1")  # 多模态生成：图像

        # --- 存储路径 ---
        self.data_dir = BASE_DIR / "data"
        self.db_path = self.data_dir / "knowledge.db"
        self.files_dir = self.data_dir / "files"

        # --- 解析 / 切块 ---
        self.ocr_min_chars = int(parsing.get("ocr_min_chars", 12))
        self.pdf_page_min_chars = int(parsing.get("pdf_page_min_chars", 8))
        self.chunk_size = int(parsing.get("chunk_size", 1000))
        self.chunk_overlap = int(parsing.get("chunk_overlap", 150))
        self.enrich_max_chars = int(parsing.get("enrich_max_chars", 6000))

        # --- 问答 (Agent 3) ---
        self.qa_top_k = int(qa.get("top_k", 5))
        self.qa_max_rounds = int(qa.get("max_rounds", 3))
        self.qa_context_budget = int(qa.get("context_budget", 7000))
        self.qa_history_turns = int(qa.get("history_turns", 4))

        # --- 知识图谱 (Agent 2) ---
        self.kg_batch_chars = int(kg.get("batch_chars", 3500))

        self.ensure_dirs()

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.files_dir.mkdir(parents=True, exist_ok=True)


@lru_cache
def get_settings() -> Settings:
    return Settings()
