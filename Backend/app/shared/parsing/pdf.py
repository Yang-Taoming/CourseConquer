"""PDF 混合解析：优先抽取文字层；某页几乎没有文字（扫描件）时，
把该页渲染成图片走 OCR/VL 管线。这样纯文字 PDF 零成本，扫描件也能读。
"""
from __future__ import annotations

from typing import List

import fitz  # PyMuPDF

from app.config import get_settings
from app.shared.parsing.image import extract_image_content
from app.shared.schemas.document import Block, BlockType, ParsedDocument


def parse_pdf(data: bytes, filename: str, mime: str) -> ParsedDocument:
    s = get_settings()
    doc = fitz.open(stream=data, filetype="pdf")

    lines: List[str] = []
    blocks: List[Block] = []
    methods = set()
    warnings: List[str] = []
    n_pages = 0

    for page in doc:
        n_pages += 1
        page_no = n_pages
        text = page.get_text("text").strip()

        if len(text) >= s.pdf_page_min_chars:
            methods.add("text-layer")
            lines.append(text)
            blocks.append(Block(type=BlockType.paragraph, text=text, meta={"page": page_no}))
            continue

        # 扫描/图片页：渲染成 PNG 后走图像管线
        try:
            pix = page.get_pixmap(dpi=170)
            img = pix.tobytes("png")
            ptext, method = extract_image_content(img, "image/png")
            methods.add("page-" + method)
            if ptext:
                lines.append(ptext)
                blocks.append(
                    Block(type=BlockType.image, text=ptext,
                          meta={"page": page_no, "source_method": method})
                )
            else:
                warnings.append("第 %d 页未提取到文字" % page_no)
        except Exception as e:  # noqa: BLE001
            warnings.append("第 %d 页处理失败: %s" % (page_no, e))

    doc.close()

    return ParsedDocument(
        filename=filename, mime=mime, doc_type="pdf",
        markdown="\n\n".join(lines), blocks=blocks,
        meta={
            "parse_method": "pdf:" + ",".join(sorted(methods)) if methods else "pdf:empty",
            "pages": n_pages,
            "warnings": warnings,
        },
    )
