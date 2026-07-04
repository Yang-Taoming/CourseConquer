"""按 Block 切块，并让每个 chunk 携带**来源位置**(页码/幻灯片/行号/段落)。

这样检索命中一个 chunk 时，能直接定位到「某文件 第7页 / 第120-135行」。
- PDF -> 页码 (block.meta['page'])
- PPT -> 幻灯片号 (block.meta['slide'])
- xlsx -> 工作表 (block.meta['sheet'])
- 纯文本/代码 -> 行号（line_based=True 时按换行计算）
- 其它(docx 段落等) -> 段落序号
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from app.shared.schemas.document import Block, Chunk


def _loc_group(b: Block) -> Tuple[Optional[Any], Optional[Any]]:
    m = b.meta or {}
    return (m.get("page"), m.get("slide"))


def _range_label(unit: str, values: List[Any]) -> str:
    if len(values) == 1:
        return "%s%s" % (unit, values[0])
    return "%s%s-%s" % (unit, values[0], values[-1])


def _build_meta(buf: List[Tuple[int, Block]], line_based: bool) -> Dict[str, Any]:
    idxs = [i for i, _ in buf]
    pages = sorted({b.meta.get("page") for _, b in buf if (b.meta or {}).get("page")})
    slides = sorted({b.meta.get("slide") for _, b in buf if (b.meta or {}).get("slide")})
    sheets = [s for s in {(b.meta or {}).get("sheet") for _, b in buf} if s]
    meta: Dict[str, Any] = {"blocks": [idxs[0], idxs[-1]]}

    if pages:
        meta["pages"] = pages
        meta["loc"] = _range_label("第", pages) + "页"
    elif slides:
        meta["slides"] = slides
        meta["loc"] = "幻灯片" + _range_label("", slides)
    elif sheets:
        meta["sheets"] = sheets
        meta["loc"] = "工作表 " + "、".join(str(s) for s in sheets)
    elif line_based and len(buf) == 1:
        n = buf[0][1].text.count("\n") + 1
        meta["lines"] = [1, n]
        meta["loc"] = "第1-%d行" % n
    else:
        meta["loc"] = "第%d段" % (idxs[0] + 1) if len(idxs) == 1 \
            else "第%d-%d段" % (idxs[0] + 1, idxs[-1] + 1)
    return meta


def _split_big_block(idx: int, block: Block, size: int, overlap: int,
                     line_based: bool) -> List[Tuple[str, Dict[str, Any]]]:
    text = block.text
    page = (block.meta or {}).get("page")
    slide = (block.meta or {}).get("slide")
    is_line = line_based and page is None and slide is None
    step = max(1, size - overlap)
    out: List[Tuple[str, Dict[str, Any]]] = []
    for start in range(0, len(text), step):
        sub = text[start:start + size]
        if not sub.strip():
            continue
        meta: Dict[str, Any] = {"blocks": [idx, idx]}
        if page:
            meta["pages"] = [page]
            meta["loc"] = "第%s页" % page
        elif slide:
            meta["slides"] = [slide]
            meta["loc"] = "幻灯片%s" % slide
        elif is_line:
            sl = text[:start].count("\n") + 1
            el = text[:start + len(sub)].count("\n") + 1
            meta["lines"] = [sl, el]
            meta["loc"] = "第%d-%d行" % (sl, el)
        else:
            meta["loc"] = "第%d段" % (idx + 1)
        out.append((sub, meta))
    return out


def chunk_blocks(blocks: List[Block], size: int, overlap: int,
                 line_based: bool = False) -> List[Chunk]:
    chunks: List[Chunk] = []
    buf: List[Tuple[int, Block]] = []
    buf_len = 0
    buf_group: Tuple[Optional[Any], Optional[Any]] = (None, None)

    def flush() -> None:
        nonlocal buf, buf_len
        if not buf:
            return
        text = "\n\n".join(b.text for _, b in buf).strip()
        if text:
            chunks.append(Chunk(ordinal=len(chunks), text=text,
                                meta=_build_meta(buf, line_based)))
        buf = []
        buf_len = 0

    for idx, b in enumerate(blocks):
        btext = b.text or ""
        if not btext.strip():
            continue
        if len(btext) > size:
            flush()
            for sub, meta in _split_big_block(idx, b, size, overlap, line_based):
                chunks.append(Chunk(ordinal=len(chunks), text=sub, meta=meta))
            continue
        group = _loc_group(b)
        if buf and (group != buf_group or buf_len + len(btext) > size):
            flush()
        if not buf:
            buf_group = group
        buf.append((idx, b))
        buf_len += len(btext) + 2
    flush()

    for i, c in enumerate(chunks):
        c.ordinal = i
    return chunks
