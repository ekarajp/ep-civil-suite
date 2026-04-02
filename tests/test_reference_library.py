from __future__ import annotations

import json
import sqlite3

from core import reference_library


def test_initialize_reference_library_creates_storage_and_schema(tmp_path) -> None:
    paths = reference_library.initialize_reference_library(tmp_path / "reference_library")

    assert paths.root.exists()
    assert paths.raw_dir.exists()
    assert paths.parsed_dir.exists()
    assert paths.index_dir.exists()
    assert paths.database_path.exists()

    with sqlite3.connect(paths.database_path) as connection:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            ).fetchall()
        }

    assert {"documents", "chunks", "document_tags"} <= tables


def test_list_documents_returns_empty_list_for_new_library(tmp_path) -> None:
    documents = reference_library.list_documents(tmp_path / "reference_library")

    assert documents == []


def test_build_reference_chunks_keeps_page_range_and_heading() -> None:
    chunks = reference_library.build_reference_chunks(
        document_name="ACI 318M-19",
        pages=(
            reference_library.ExtractedPage(
                1,
                "1.1 Scope\n\nThis code covers general requirements for structural concrete.",
            ),
            reference_library.ExtractedPage(
                2,
                "22.7.7.1 Combined shear and torsion section limits apply to solid members.",
            ),
        ),
        target_words=6,
        max_words=12,
    )

    assert len(chunks) == 2
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].section_label == "1.1 Scope"
    assert chunks[1].page_start == 2
    assert chunks[1].section_label == "22.7.7.1 Combined shear and torsion section limits apply to solid members."


def test_import_reference_document_saves_outputs_and_database_records(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "reference_library"

    def fake_extract_pdf_text(file_bytes: bytes) -> reference_library.ExtractedPdfDocument:
        return reference_library.ExtractedPdfDocument(
            page_count=2,
            pages=(
                reference_library.ExtractedPage(1, "1.1 Scope\n\nConcrete beam design requirements."),
                reference_library.ExtractedPage(2, "22.7.7.1 Combined shear and torsion section limits."),
            ),
        )

    monkeypatch.setattr(reference_library, "extract_pdf_text", fake_extract_pdf_text)

    result = reference_library.import_reference_document(
        file_name="ACI 318M-19.pdf",
        file_bytes=b"%PDF-1.4 fake sample",
        base_dir=base_dir,
        document_name="ACI 318M-19",
    )

    assert result.status == "imported"
    assert result.page_count == 2
    assert result.chunk_count >= 1

    documents = reference_library.list_documents(base_dir)
    assert len(documents) == 1
    assert documents[0].document_name == "ACI 318M-19"
    assert documents[0].parse_status == "imported"
    assert documents[0].page_count == 2
    assert documents[0].chunk_count == result.chunk_count

    raw_files = list((base_dir / "raw").glob("*.pdf"))
    parsed_text_files = list((base_dir / "parsed").glob("*.txt"))
    parsed_json_files = list((base_dir / "parsed").glob("*.json"))

    assert len(raw_files) == 1
    assert len(parsed_text_files) == 1
    assert len(parsed_json_files) == 1
    assert "Combined shear and torsion" in parsed_text_files[0].read_text(encoding="utf-8")

    parsed_payload = json.loads(parsed_json_files[0].read_text(encoding="utf-8"))
    assert parsed_payload["page_count"] == 2
    assert len(parsed_payload["pages"]) == 2


def test_import_reference_document_detects_duplicate_uploads(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "reference_library"

    monkeypatch.setattr(
        reference_library,
        "extract_pdf_text",
        lambda file_bytes: reference_library.ExtractedPdfDocument(
            page_count=1,
            pages=(reference_library.ExtractedPage(1, "Reference text for duplicate test."),),
        ),
    )

    first = reference_library.import_reference_document(
        file_name="ACI 318M-19.pdf",
        file_bytes=b"%PDF-1.4 duplicate sample",
        base_dir=base_dir,
    )
    second = reference_library.import_reference_document(
        file_name="ACI 318M-19.pdf",
        file_bytes=b"%PDF-1.4 duplicate sample",
        base_dir=base_dir,
    )

    assert first.status == "imported"
    assert second.status == "duplicate"
    assert len(reference_library.list_documents(base_dir)) == 1


def test_search_reference_chunks_returns_matching_snippets(tmp_path, monkeypatch) -> None:
    base_dir = tmp_path / "reference_library"

    monkeypatch.setattr(
        reference_library,
        "extract_pdf_text",
        lambda file_bytes: reference_library.ExtractedPdfDocument(
            page_count=2,
            pages=(
                reference_library.ExtractedPage(1, "Section 1\n\nGeneral beam design rules."),
                reference_library.ExtractedPage(2, "Section 2\n\nTorsion reinforcement and spacing limits."),
            ),
        ),
    )
    reference_library.import_reference_document(
        file_name="ACI 318M-19.pdf",
        file_bytes=b"%PDF-1.4 search sample",
        base_dir=base_dir,
    )

    results = reference_library.search_reference_chunks("torsion", base_dir=base_dir)

    assert len(results) == 1
    assert results[0].page_start <= results[0].page_end
    assert "Torsion" in results[0].snippet or "torsion" in results[0].snippet


def test_resolve_official_document_metadata_normalizes_known_aci_titles() -> None:
    metadata = reference_library.resolve_official_document_metadata(
        document_name="ACI_318M-25_SI",
        file_name="ACI_318M-25_SI.pdf",
        preview_text="ACI CODE-318-25 Building Code for Structural Concrete Code Requirements and Commentary International System of Units SI",
        document_type="Reference PDF",
    )

    assert metadata.document_name == (
        "ACI CODE-318M-25 Building Code for Structural Concrete: Code Requirements and Commentary (SI Units)"
    )
    assert metadata.display_file_name.endswith(".pdf")
    assert metadata.sort_year == 2025


def test_list_documents_sorts_by_edition_year(tmp_path) -> None:
    paths = reference_library.initialize_reference_library(tmp_path / "reference_library")
    with sqlite3.connect(paths.database_path) as connection:
        connection.executemany(
            """
            INSERT INTO documents (
                document_name,
                file_name,
                file_path,
                document_type,
                code_name,
                edition,
                file_hash,
                upload_date,
                parse_status,
                page_count
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                ("ACI 318M-19 Building Code Requirements for Structural Concrete and Commentary", "b.pdf", "b.pdf", "ACI 318 Standard", "ACI 318M-19", "19", "hash-b", "2026-01-01T00:00:00", "imported", 1),
                ("ACI 318-99 Building Code Requirements for Structural Concrete and Commentary", "a.pdf", "a.pdf", "ACI 318 Standard", "ACI 318-99", "99", "hash-a", "2026-01-01T00:00:00", "imported", 1),
                ("ACI CODE-318M-25 Building Code for Structural Concrete: Code Requirements and Commentary (SI Units)", "c.pdf", "c.pdf", "ACI 318 Standard", "ACI CODE-318M-25", "25", "hash-c", "2026-01-01T00:00:00", "imported", 1),
            ],
        )
        connection.commit()

    documents = reference_library.list_documents(tmp_path / "reference_library")

    assert [document.edition for document in documents] == ["99", "19", "25"]
