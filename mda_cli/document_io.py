"""Supported extensions and text extraction from documents."""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_SUPPORTED_EXTENSIONS: tuple[str, ...] = (".md", ".pdf", ".docx", ".doc", ".txt")


class DocumentReadError(Exception):
    """Could not extract text from a source file."""


def supported_extensions() -> tuple[str, ...]:
    """Return configured extensions (lowercase, with leading dot)."""
    raw = os.environ.get("MDA_EXTENSIONS", "").strip()
    if not raw:
        return DEFAULT_SUPPORTED_EXTENSIONS
    parts: list[str] = []
    for piece in raw.split(","):
        p = piece.strip().lower()
        if not p:
            continue
        parts.append(p if p.startswith(".") else f".{p}")
    return tuple(parts) if parts else DEFAULT_SUPPORTED_EXTENSIONS


def is_supported_extension(path: Path) -> bool:
    return path.suffix.lower() in supported_extensions()


def is_restructured_output_name(name: str) -> bool:
    lower = name.lower()
    return lower.endswith(".restructured.md") or lower.endswith(".restructured.txt")


def count_supported_files_in_dir(
    directory: Path,
    *,
    include_restructured: bool = False,
    extensions: tuple[str, ...] | None = None,
) -> int:
    """Count supported files directly in ``directory`` (not recursive)."""
    if not directory.is_dir():
        return 0
    exts = extensions if extensions is not None else supported_extensions()
    n = 0
    try:
        for entry in directory.iterdir():
            if not entry.is_file():
                continue
            if entry.suffix.lower() not in exts:
                continue
            if not include_restructured and is_restructured_output_name(entry.name):
                continue
            n += 1
    except OSError:
        return 0
    return n


def read_markdown_text(path: Path) -> str:
    """Read markdown/skill text: UTF-8, UTF-8-with-BOM, or UTF-16 LE/BE (BOM)."""
    data = path.read_bytes()
    if data.startswith(b"\xff\xfe"):
        return data.decode("utf-16-le")
    if data.startswith(b"\xfe\xff"):
        return data.decode("utf-16-be")
    if data.startswith(b"\xef\xbb\xbf"):
        return data.decode("utf-8-sig")
    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", errors="replace")


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError as e:
        raise DocumentReadError(
            f"PDF support requires the pdf extra: pip install 'mda-cli[pdf]' "
            f"(or pip install pypdf). ({e})"
        ) from e
    try:
        reader = PdfReader(str(path))
        parts: list[str] = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                parts.append(text)
        return "\n\n".join(parts)
    except Exception as e:
        raise DocumentReadError(f"Failed to read PDF {path.name}: {e}") from e


def _read_docx(path: Path) -> str:
    try:
        from docx import Document
    except ImportError as e:
        raise DocumentReadError(
            f"DOCX support requires the docx extra: pip install 'mda-cli[docx]' "
            f"(or pip install python-docx). ({e})"
        ) from e
    try:
        doc = Document(str(path))
        return "\n".join(p.text for p in doc.paragraphs if p.text)
    except Exception as e:
        raise DocumentReadError(f"Failed to read DOCX {path.name}: {e}") from e


def read_document_text(path: Path) -> str:
    """Extract plain text from a supported source file."""
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        return read_markdown_text(path)
    if ext == ".pdf":
        return _read_pdf(path)
    if ext == ".docx":
        return _read_docx(path)
    if ext == ".doc":
        raise DocumentReadError(
            f"Legacy .doc is not supported ({path.name}). "
            "Convert to .docx (e.g. LibreOffice) or export as PDF, then retry."
        )
    raise DocumentReadError(f"Unsupported file type: {path.name}")


def restructured_output_path(src: Path, *, skill_id: str | None = None) -> Path:
    """Sibling output path for a restructured artifact.

    - ``markdown-document-architect`` (default): always ``*.restructured.md``.
    - ``categorize-vault-notes``: ``*.restructured.txt`` for non-Markdown sources.
    """
    sid = (skill_id or "").strip() or "markdown-document-architect"
    ext = src.suffix.lower()
    if sid == "categorize-vault-notes" and ext != ".md":
        return src.with_name(f"{src.stem}.restructured.txt")
    return src.with_name(f"{src.stem}.restructured.md")
