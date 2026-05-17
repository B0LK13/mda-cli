from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mda_cli.document_io import (
    DocumentReadError,
    count_supported_files_in_dir,
    read_document_text,
    restructured_output_path,
    supported_extensions,
)


def test_supported_extensions_env_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MDA_EXTENSIONS", ".md,TXT")
    assert supported_extensions() == (".md", ".txt")


def test_count_supported_files_in_dir(tmp_path: Path) -> None:
    (tmp_path / "a.md").write_text("# A", encoding="utf-8")
    (tmp_path / "b.txt").write_text("hello", encoding="utf-8")
    (tmp_path / "c.pdf").write_bytes(b"%PDF-1.4")
    assert count_supported_files_in_dir(tmp_path) == 3


def test_read_document_text_txt(tmp_path: Path) -> None:
    p = tmp_path / "note.txt"
    p.write_text("Plain text\n", encoding="utf-8", newline="\n")
    assert read_document_text(p) == "Plain text\n"


def test_read_document_text_doc_rejected(tmp_path: Path) -> None:
    p = tmp_path / "legacy.doc"
    p.write_bytes(b"fake")
    with pytest.raises(DocumentReadError, match="Legacy .doc"):
        read_document_text(p)


def test_read_pdf_requires_extra(tmp_path: Path) -> None:
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    with patch.dict("sys.modules", {"pypdf": None}):
        with pytest.raises(DocumentReadError, match="pdf extra"):
            read_document_text(p)


def test_read_pdf_mocked(tmp_path: Path) -> None:
    p = tmp_path / "x.pdf"
    p.write_bytes(b"%PDF-1.4\n")
    page = MagicMock()
    page.extract_text.return_value = "Page one"
    reader = MagicMock()
    reader.pages = [page]
    fake_pypdf = MagicMock()
    fake_pypdf.PdfReader.return_value = reader
    with patch.dict("sys.modules", {"pypdf": fake_pypdf}):
        assert read_document_text(p) == "Page one"


def test_read_docx_mocked(tmp_path: Path) -> None:
    p = tmp_path / "x.docx"
    p.write_bytes(b"PK\x03\x04")
    para = MagicMock()
    para.text = "Hello docx"
    doc = MagicMock()
    doc.paragraphs = [para]
    fake_docx = MagicMock()
    fake_docx.Document.return_value = doc
    with patch.dict("sys.modules", {"docx": fake_docx}):
        assert read_document_text(p) == "Hello docx"


def test_restructured_output_path_mda_always_md(tmp_path: Path) -> None:
    pdf = tmp_path / "report.pdf"
    assert restructured_output_path(pdf).name == "report.restructured.md"
    assert restructured_output_path(pdf, skill_id="markdown-document-architect").name == (
        "report.restructured.md"
    )


def test_restructured_output_path_categorize_txt_sidecar(tmp_path: Path) -> None:
    txt = tmp_path / "note.txt"
    assert restructured_output_path(txt, skill_id="categorize-vault-notes").name == (
        "note.restructured.txt"
    )
    md = tmp_path / "note.md"
    assert restructured_output_path(md, skill_id="categorize-vault-notes").name == (
        "note.restructured.md"
    )
