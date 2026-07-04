"""按扩展名把文件路由到解析器族，并给出 doc_type 与 mime。"""
from __future__ import annotations

import mimetypes
from pathlib import Path
from typing import Tuple

CODE_EXTS = {
    ".py", ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".java", ".js", ".ts",
    ".tsx", ".jsx", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".scala",
    ".sh", ".bash", ".zsh", ".sql", ".json", ".yaml", ".yml", ".toml", ".ini",
    ".cfg", ".xml", ".html", ".htm", ".css", ".m", ".mm", ".r", ".jl", ".lua",
    ".pl", ".dart", ".vue", ".ipynb",
}

LANG_BY_EXT = {
    ".py": "python", ".c": "c", ".h": "c", ".cpp": "cpp", ".cc": "cpp",
    ".cxx": "cpp", ".hpp": "cpp", ".java": "java", ".js": "javascript",
    ".ts": "typescript", ".tsx": "tsx", ".jsx": "jsx", ".go": "go",
    ".rs": "rust", ".rb": "ruby", ".php": "php", ".swift": "swift",
    ".kt": "kotlin", ".scala": "scala", ".sh": "bash", ".bash": "bash",
    ".zsh": "bash", ".sql": "sql", ".json": "json", ".yaml": "yaml",
    ".yml": "yaml", ".toml": "toml", ".xml": "xml", ".html": "html",
    ".htm": "html", ".css": "css", ".r": "r", ".jl": "julia", ".lua": "lua",
    ".pl": "perl", ".dart": "dart", ".vue": "vue",
}

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif", ".tif", ".tiff", ".heic"}

TEXT_EXTS = {".txt", ".md", ".markdown", ".rst", ".log", ".text", ""}


def classify(filename: str) -> Tuple[str, str]:
    """返回 (doc_type, mime)。doc_type ∈ pdf/docx/pptx/xlsx/csv/image/code/text。"""
    ext = Path(filename).suffix.lower()
    guessed = mimetypes.guess_type(filename)[0] or "application/octet-stream"

    if ext == ".pdf":
        return "pdf", "application/pdf"
    if ext == ".docx":
        return "docx", (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
    if ext == ".pptx":
        return "pptx", (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    if ext in {".xlsx", ".xlsm"}:
        return "xlsx", (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    if ext == ".csv":
        return "csv", "text/csv"
    if ext in IMAGE_EXTS:
        mime = guessed if guessed.startswith("image/") else "image/%s" % ext.lstrip(".")
        return "image", mime
    if ext in CODE_EXTS:
        return "code", "text/plain"
    if ext in TEXT_EXTS:
        return "text", "text/plain"
    # 未知后缀：先当作纯文本尝试（parse_text 用 errors="replace" 兜底）
    return "text", guessed
