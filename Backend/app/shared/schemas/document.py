"""规范化 Document 表示。

这是解析层的产物，也是入库(Agent1)与知识图谱(Agent2)的**共用中间表示**：
昂贵的解析（OCR/VL/office 抽取）只做一次，两条下游都消费同一个对象，
Agent2 建图时读的是这里已解析好的文本/分块，不会重新解析原始文件。
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BlockType(str, Enum):
    heading = "heading"
    paragraph = "paragraph"
    code = "code"
    table = "table"
    image = "image"   # 图片经 OCR/VL 得到的内容
    list = "list"


class Block(BaseModel):
    """带类型与来源信息的内容块，方便后续实体抽取按结构定位。"""
    type: BlockType
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)  # page/slide/lang/source_method...


class Chunk(BaseModel):
    """检索单元：一段文本 + 它在原文中的位置(页码/幻灯片/行号/段落)。"""
    ordinal: int
    text: str
    meta: Dict[str, Any] = Field(default_factory=dict)  # loc/pages/slides/lines/blocks...


class ParsedDocument(BaseModel):
    """解析器输出的规范化文档。"""
    filename: str
    mime: str
    doc_type: str                       # text/code/pdf/docx/pptx/xlsx/csv/image
    markdown: str                       # 归一化后的完整 Markdown 文本
    blocks: List[Block] = Field(default_factory=list)
    meta: Dict[str, Any] = Field(default_factory=dict)  # parse_method / pages / warnings


class Enrichment(BaseModel):
    """入库时自动生成的摘要、标签、分类。"""
    summary: str = ""
    tags: List[str] = Field(default_factory=list)
    category: str = ""


class DocumentRecord(BaseModel):
    """入库并对外返回的一条知识记录。"""
    id: str
    workspace_id: str
    filename: str
    source: Optional[str] = None
    mime: str
    doc_type: str
    created_at: str
    summary: str = ""
    tags: List[str] = Field(default_factory=list)
    category: str = ""
    n_chunks: int = 0
    markdown: str = ""
    meta: Dict[str, Any] = Field(default_factory=dict)


class IngestResult(BaseModel):
    document: DocumentRecord
    parse_methods: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
