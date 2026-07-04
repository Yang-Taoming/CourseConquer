"""纯文本 / 代码：直接读取，无需外部工具。"""
from __future__ import annotations

from pathlib import Path

from app.shared.parsing.mime import LANG_BY_EXT
from app.shared.schemas.document import Block, BlockType, ParsedDocument


def parse_text(data: bytes, filename: str, doc_type: str, mime: str) -> ParsedDocument:
    text = data.decode("utf-8", errors="replace")
    ext = Path(filename).suffix.lower()

    if doc_type == "code":
        lang = LANG_BY_EXT.get(ext, "")
        markdown = "```%s\n%s\n```" % (lang, text)
        blocks = [Block(type=BlockType.code, text=text, meta={"lang": lang})]
    else:
        markdown = text
        blocks = [Block(type=BlockType.paragraph, text=text)]

    return ParsedDocument(
        filename=filename,
        mime=mime,
        doc_type=doc_type,
        markdown=markdown,
        blocks=blocks,
        meta={"parse_method": "direct-read"},
    )
