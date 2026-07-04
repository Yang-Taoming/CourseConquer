"""图片解析：OCR 优先 + VL 兜底。

策略：先用 OCR 模型逐字提取文字；若返回文本很少（说明多半是图表/照片/示意图，
而非文字页），再升级到视觉(VL)模型去理解并描述图像内容。
这个函数同时被 PDF 的扫描页复用。
"""
from __future__ import annotations

import re
from collections import Counter
from typing import Tuple

from app.config import get_settings
from app.shared.llm import client as llm
from app.shared.schemas.document import Block, BlockType, ParsedDocument

OCR_PROMPT = (
    "请逐字转写图片中的所有文字，按阅读顺序输出**纯文本**，保留每行的换行；"
    "不要用表格或 HTML，不要解释，只输出内容本身。"
)

VL_PROMPT = (
    "请理解这张图片并输出其内容：\n"
    "1) 逐字转写图中所有可见文字；\n"
    "2) 若包含图表 / 流程图 / 示意图 / 公式，用文字描述其结构、数据与含义。\n"
    "用 Markdown 输出，只输出内容本身。"
)


def _looks_garbage(text: str) -> bool:
    """OCR 崩坏检测：又长又空/满是重复字符或空表格单元也算失败。"""
    t = (text or "").strip()
    if not t:
        return True
    most = Counter(t).most_common(1)[0][1]
    if most / len(t) > 0.3:              # 某个字符占比过高（如崩成一堆引号）
        return True
    if t.count("<td></td>") >= 5:        # 一堆空表格单元
        return True
    real = re.sub(r"\s+", "", re.sub(r"<[^>]+>", "", t))  # 去标签与空白后的实义字符
    return len(real) < 12


def extract_image_content(image_bytes: bytes, mime: str) -> Tuple[str, str]:
    """返回 (text, method)。统一用一个视觉模型：先按 OCR 提示词转写，稀疏/崩坏再按理解提示词重试。"""
    s = get_settings()
    text = ""
    try:
        text = llm.vision(image_bytes, mime, OCR_PROMPT, model=s.vision_model)
    except Exception:
        text = ""

    method = "ocr"
    if len((text or "").strip()) < s.ocr_min_chars or _looks_garbage(text):
        # OCR 稀疏或崩坏 -> 用「理解」提示词重试（同一视觉模型，换提示词）
        try:
            vl_text = llm.vision(image_bytes, mime, VL_PROMPT, model=s.vision_model)
            if vl_text.strip() and not _looks_garbage(vl_text):
                text, method = vl_text, "vl"
        except Exception:
            pass

    text = (text or "").strip()
    if not text or _looks_garbage(text):
        method = "none" if not text else method
    return text, method


def parse_image(data: bytes, filename: str, mime: str) -> ParsedDocument:
    text, method = extract_image_content(data, mime)
    warnings = [] if text else ["图片未提取到任何内容（OCR 与 VL 均为空）"]
    blocks = [Block(type=BlockType.image, text=text, meta={"source_method": method})]
    return ParsedDocument(
        filename=filename, mime=mime, doc_type="image",
        markdown=text, blocks=blocks,
        meta={"parse_method": "image:%s" % method, "warnings": warnings},
    )
