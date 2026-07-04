"""解析总入口：按 doc_type 分派到对应解析器，输出规范化 ParsedDocument。

这是入库路径与（未来）问答路径共用的函数——「各种后缀的文件解析」都从这里进。
"""
from __future__ import annotations

from app.shared.parsing import mime as mimemod
from app.shared.parsing.office import parse_csv, parse_docx, parse_pptx, parse_xlsx
from app.shared.parsing.pdf import parse_pdf
from app.shared.parsing.image import parse_image
from app.shared.parsing.text import parse_text
from app.shared.schemas.document import ParsedDocument


def parse(data: bytes, filename: str) -> ParsedDocument:
    doc_type, mime = mimemod.classify(filename)

    if doc_type == "pdf":
        return parse_pdf(data, filename, mime)
    if doc_type == "docx":
        return parse_docx(data, filename, mime)
    if doc_type == "pptx":
        return parse_pptx(data, filename, mime)
    if doc_type == "xlsx":
        return parse_xlsx(data, filename, mime)
    if doc_type == "csv":
        return parse_csv(data, filename, mime)
    if doc_type == "image":
        return parse_image(data, filename, mime)
    # text / code / 未知后缀兜底
    return parse_text(data, filename, doc_type, mime)
