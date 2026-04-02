from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from io import BytesIO
import hashlib
import json
from pathlib import Path
import re
import sqlite3
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_LIBRARY_ROOT = PROJECT_ROOT / "reference_library"


@dataclass(frozen=True, slots=True)
class ReferenceLibraryPaths:
    root: Path
    raw_dir: Path
    parsed_dir: Path
    index_dir: Path
    database_path: Path


@dataclass(frozen=True, slots=True)
class ReferenceDocumentRecord:
    id: int
    document_name: str
    file_name: str
    file_path: str
    document_type: str | None
    code_name: str | None
    edition: str | None
    upload_date: str
    parse_status: str
    page_count: int
    chunk_count: int
    last_error: str | None
    parsed_text_path: str | None
    parsed_json_path: str | None


@dataclass(frozen=True, slots=True)
class ExtractedPage:
    page_number: int
    text: str


@dataclass(frozen=True, slots=True)
class ExtractedPdfDocument:
    page_count: int
    pages: tuple[ExtractedPage, ...]


@dataclass(frozen=True, slots=True)
class ReferenceChunkRecord:
    chunk_index: int
    page_start: int
    page_end: int
    section_label: str | None
    title: str | None
    text_content: str
    text_length: int
    keywords_json: str


@dataclass(frozen=True, slots=True)
class ReferenceChunkView:
    id: int
    chunk_index: int
    page_start: int
    page_end: int
    section_label: str | None
    title: str | None
    text_content: str
    text_length: int
    keywords: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReferenceSearchResult:
    document_id: int
    document_name: str
    file_name: str
    parse_status: str
    chunk_index: int
    page_start: int
    page_end: int
    section_label: str | None
    title: str | None
    snippet: str


@dataclass(frozen=True, slots=True)
class ReferenceImportResult:
    status: str
    message: str
    document_id: int | None
    document_name: str
    file_name: str
    page_count: int
    chunk_count: int


@dataclass(frozen=True, slots=True)
class OfficialDocumentMetadata:
    document_name: str
    display_file_name: str
    document_type: str | None
    code_name: str | None
    edition: str | None
    sort_year: int | None


def get_reference_library_paths(base_dir: Path | None = None) -> ReferenceLibraryPaths:
    root = (base_dir or DEFAULT_LIBRARY_ROOT).resolve()
    return ReferenceLibraryPaths(
        root=root,
        raw_dir=root / "raw",
        parsed_dir=root / "parsed",
        index_dir=root / "index",
        database_path=root / "index" / "reference_library.sqlite",
    )


def initialize_reference_library(base_dir: Path | None = None) -> ReferenceLibraryPaths:
    paths = get_reference_library_paths(base_dir)
    paths.raw_dir.mkdir(parents=True, exist_ok=True)
    paths.parsed_dir.mkdir(parents=True, exist_ok=True)
    paths.index_dir.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(paths.database_path) as connection:
        connection.execute("PRAGMA foreign_keys = ON")
        connection.executescript(_schema_sql())
        connection.commit()
    return paths


def list_documents(base_dir: Path | None = None) -> list[ReferenceDocumentRecord]:
    paths = initialize_reference_library(base_dir)
    with sqlite3.connect(paths.database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(
            """
            SELECT
                id,
                document_name,
                file_name,
                file_path,
                document_type,
                code_name,
                edition,
                upload_date,
                parse_status,
                page_count,
                last_error,
                parsed_text_path,
                parsed_json_path,
                (
                    SELECT COUNT(*)
                    FROM chunks
                    WHERE chunks.document_id = documents.id
                ) AS chunk_count
            FROM documents
            ORDER BY upload_date DESC, id DESC
            """
        ).fetchall()

    documents = [
        ReferenceDocumentRecord(
            id=int(row["id"]),
            document_name=str(row["document_name"]),
            file_name=str(row["file_name"]),
            file_path=str(row["file_path"]),
            document_type=row["document_type"],
            code_name=row["code_name"],
            edition=row["edition"],
            upload_date=str(row["upload_date"]),
            parse_status=str(row["parse_status"]),
            page_count=int(row["page_count"] or 0),
            chunk_count=int(row["chunk_count"] or 0),
            last_error=row["last_error"],
            parsed_text_path=row["parsed_text_path"],
            parsed_json_path=row["parsed_json_path"],
        )
        for row in rows
    ]
    return sorted(documents, key=_document_sort_key)


def get_document(document_id: int, base_dir: Path | None = None) -> ReferenceDocumentRecord | None:
    return next((document for document in list_documents(base_dir) if document.id == document_id), None)


def list_document_chunks(
    document_id: int,
    *,
    base_dir: Path | None = None,
    limit: int | None = None,
) -> list[ReferenceChunkView]:
    paths = initialize_reference_library(base_dir)
    sql = """
        SELECT
            id,
            chunk_index,
            page_start,
            page_end,
            section_label,
            title,
            text_content,
            text_length,
            keywords_json
        FROM chunks
        WHERE document_id = ?
        ORDER BY chunk_index ASC
    """
    parameters: list[Any] = [document_id]
    if limit is not None:
        sql += " LIMIT ?"
        parameters.append(limit)

    with sqlite3.connect(paths.database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(sql, tuple(parameters)).fetchall()

    chunk_views: list[ReferenceChunkView] = []
    for row in rows:
        try:
            keywords = tuple(json.loads(row["keywords_json"] or "[]"))
        except json.JSONDecodeError:
            keywords = ()
        chunk_views.append(
            ReferenceChunkView(
                id=int(row["id"]),
                chunk_index=int(row["chunk_index"]),
                page_start=int(row["page_start"] or 0),
                page_end=int(row["page_end"] or 0),
                section_label=row["section_label"],
                title=row["title"],
                text_content=str(row["text_content"]),
                text_length=int(row["text_length"] or 0),
                keywords=keywords,
            )
        )
    return chunk_views


def load_document_text(document_id: int, base_dir: Path | None = None) -> str:
    document = get_document(document_id, base_dir)
    if document is None or not document.parsed_text_path:
        return ""
    parsed_text_path = Path(document.parsed_text_path)
    if not parsed_text_path.exists():
        return ""
    try:
        return parsed_text_path.read_text(encoding="utf-8")
    except OSError:
        return ""


def normalize_reference_library_catalog(base_dir: Path | None = None) -> int:
    paths = initialize_reference_library(base_dir)
    updates = 0
    for document in list_documents(base_dir):
        preview_text = load_document_text(document.id, base_dir)[:2000]
        official = resolve_official_document_metadata(
            document_name=document.document_name,
            file_name=document.file_name,
            preview_text=preview_text,
            document_type=document.document_type,
        )
        synchronized = _synchronize_document_storage_paths(
            database_path=paths.database_path,
            document=document,
            display_file_name=official.display_file_name,
        )
        if (
            official.document_name == document.document_name
            and official.display_file_name == document.file_name
            and official.code_name == document.code_name
            and official.edition == document.edition
            and official.document_type == document.document_type
        ):
            if synchronized:
                updates += 1
            continue
        _update_document_identity(
            database_path=paths.database_path,
            document_id=document.id,
            document_name=official.document_name,
            file_name=official.display_file_name,
            document_type=official.document_type,
            code_name=official.code_name,
            edition=official.edition,
        )
        updates += 1
    return updates


def import_reference_document(
    *,
    file_name: str,
    file_bytes: bytes,
    base_dir: Path | None = None,
    document_name: str | None = None,
    document_type: str | None = "Reference PDF",
) -> ReferenceImportResult:
    paths = initialize_reference_library(base_dir)
    if not file_bytes:
        return ReferenceImportResult(
            status="invalid",
            message="The uploaded file is empty.",
            document_id=None,
            document_name=document_name or Path(file_name).stem or "Untitled reference",
            file_name=file_name,
            page_count=0,
            chunk_count=0,
        )

    file_hash = hashlib.sha256(file_bytes).hexdigest()
    existing_document = _find_document_by_hash(paths.database_path, file_hash)
    if existing_document is not None:
        return ReferenceImportResult(
            status="duplicate",
            message="This PDF is already stored in the local reference library.",
            document_id=existing_document["id"],
            document_name=str(existing_document["document_name"]),
            file_name=str(existing_document["file_name"]),
            page_count=int(existing_document["page_count"] or 0),
            chunk_count=int(existing_document["chunk_count"] or 0),
        )

    display_name = (document_name or Path(file_name).stem or "Untitled reference").strip()
    inferred = infer_document_metadata(file_name=file_name, document_name=display_name)
    storage_stem = _build_storage_stem(display_name)
    try:
        raw_path, parsed_text_path, parsed_json_path = _build_storage_paths(
            paths=paths,
            storage_stem=storage_stem,
            original_file_name=file_name,
            file_hash=file_hash,
        )
        raw_path.write_bytes(file_bytes)

        uploaded_at = _timestamp_now()
        document_id = _insert_document_record(
            database_path=paths.database_path,
            document_name=display_name,
            file_name=raw_path.name,
            file_path=str(raw_path),
            document_type=document_type,
            code_name=inferred["code_name"],
            edition=inferred["edition"],
            file_hash=file_hash,
            upload_date=uploaded_at,
        )
    except Exception as error:
        return ReferenceImportResult(
            status="failed",
            message=f"The PDF could not be stored in the local reference library: {error}",
            document_id=None,
            document_name=display_name,
            file_name=file_name,
            page_count=0,
            chunk_count=0,
        )

    try:
        extracted_document = extract_pdf_text(file_bytes)
        pages_payload = [
            {
                "page_number": page.page_number,
                "text": page.text,
            }
            for page in extracted_document.pages
        ]
        joined_text = "\n\n".join(page["text"] for page in pages_payload if page["text"].strip()).strip()
        official = resolve_official_document_metadata(
            document_name=display_name,
            file_name=file_name,
            preview_text=pages_payload[0]["text"] if pages_payload else "",
            document_type=document_type,
        )
        _update_document_identity(
            database_path=paths.database_path,
            document_id=document_id,
            document_name=official.document_name,
            file_name=official.display_file_name,
            document_type=official.document_type,
            code_name=official.code_name,
            edition=official.edition,
        )
        if not joined_text:
            raw_path, parsed_text_path, parsed_json_path = _synchronize_paths_for_display_name(
                raw_path=raw_path,
                parsed_text_path=parsed_text_path,
                parsed_json_path=parsed_json_path,
                display_file_name=official.display_file_name,
            )
            parsed_text_path.write_text("", encoding="utf-8")
            parsed_json_path.write_text(
                json.dumps(
                    {
                        "document_name": official.document_name,
                        "file_name": official.display_file_name,
                        "page_count": extracted_document.page_count,
                        "pages": pages_payload,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            _update_document_status(
                database_path=paths.database_path,
                document_id=document_id,
                parse_status="empty",
                page_count=extracted_document.page_count,
                parsed_text_path=str(parsed_text_path),
                parsed_json_path=str(parsed_json_path),
                last_error="No extractable text was found in this PDF.",
            )
            _update_document_file_paths(
                database_path=paths.database_path,
                document_id=document_id,
                file_path=str(raw_path),
                parsed_text_path=str(parsed_text_path),
                parsed_json_path=str(parsed_json_path),
            )
            return ReferenceImportResult(
                status="empty",
                message="The PDF was saved locally, but no extractable text was found.",
                document_id=document_id,
                document_name=official.document_name,
                file_name=official.display_file_name,
                page_count=extracted_document.page_count,
                chunk_count=0,
            )

        raw_path, parsed_text_path, parsed_json_path = _synchronize_paths_for_display_name(
            raw_path=raw_path,
            parsed_text_path=parsed_text_path,
            parsed_json_path=parsed_json_path,
            display_file_name=official.display_file_name,
        )
        parsed_text_path.write_text(joined_text, encoding="utf-8")
        parsed_json_path.write_text(
            json.dumps(
                {
                    "document_name": official.document_name,
                    "file_name": official.display_file_name,
                    "page_count": extracted_document.page_count,
                    "pages": pages_payload,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        chunks = build_reference_chunks(
            document_name=official.document_name,
            pages=extracted_document.pages,
        )
        _replace_document_chunks(
            database_path=paths.database_path,
            document_id=document_id,
            chunks=chunks,
        )
        _update_document_file_paths(
            database_path=paths.database_path,
            document_id=document_id,
            file_path=str(raw_path),
            parsed_text_path=str(parsed_text_path),
            parsed_json_path=str(parsed_json_path),
        )
        _update_document_status(
            database_path=paths.database_path,
            document_id=document_id,
            parse_status="imported",
            page_count=extracted_document.page_count,
            parsed_text_path=str(parsed_text_path),
            parsed_json_path=str(parsed_json_path),
            last_error=None,
        )
        return ReferenceImportResult(
            status="imported",
            message=f"Imported {len(chunks)} searchable chunks from the uploaded PDF.",
            document_id=document_id,
            document_name=official.document_name,
            file_name=official.display_file_name,
            page_count=extracted_document.page_count,
            chunk_count=len(chunks),
        )
    except Exception as error:
        _update_document_status(
            database_path=paths.database_path,
            document_id=document_id,
            parse_status="failed",
            page_count=0,
            parsed_text_path=None,
            parsed_json_path=None,
            last_error=str(error),
        )
        return ReferenceImportResult(
            status="failed",
            message=f"The PDF was saved locally, but parsing failed: {error}",
            document_id=document_id,
            document_name=display_name,
            file_name=raw_path.name,
            page_count=0,
            chunk_count=0,
        )


def retry_import(document_id: int, base_dir: Path | None = None) -> ReferenceImportResult:
    paths = initialize_reference_library(base_dir)
    with sqlite3.connect(paths.database_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(
            """
            SELECT id, document_name, file_name, file_path, document_type
            FROM documents
            WHERE id = ?
            """,
            (document_id,),
        ).fetchone()

    if row is None:
        return ReferenceImportResult(
            status="missing",
            message="The selected document was not found.",
            document_id=None,
            document_name="Unknown document",
            file_name="",
            page_count=0,
            chunk_count=0,
        )

    raw_path = Path(str(row["file_path"]))
    if not raw_path.exists():
        return ReferenceImportResult(
            status="missing",
            message="The raw PDF file is missing, so the import cannot be retried.",
            document_id=int(row["id"]),
            document_name=str(row["document_name"]),
            file_name=str(row["file_name"]),
            page_count=0,
            chunk_count=0,
        )

    _delete_document_record(paths.database_path, int(row["id"]))
    return import_reference_document(
        file_name=raw_path.name,
        file_bytes=raw_path.read_bytes(),
        base_dir=paths.root,
        document_name=str(row["document_name"]),
        document_type=row["document_type"],
    )


def search_reference_chunks(
    query: str,
    *,
    base_dir: Path | None = None,
    document_id: int | None = None,
    limit: int = 10,
) -> list[ReferenceSearchResult]:
    normalized_query = " ".join(query.strip().split())
    if not normalized_query:
        return []

    paths = initialize_reference_library(base_dir)
    like_query = f"%{normalized_query.lower()}%"
    sql = """
            SELECT
                documents.id AS document_id,
                documents.document_name,
                documents.file_name,
                documents.parse_status,
                chunks.chunk_index,
                chunks.page_start,
                chunks.page_end,
                chunks.section_label,
                chunks.title,
                chunks.text_content
            FROM chunks
            INNER JOIN documents ON documents.id = chunks.document_id
            WHERE
                (
                    LOWER(chunks.text_content) LIKE ?
                    OR LOWER(COALESCE(chunks.section_label, '')) LIKE ?
                    OR LOWER(COALESCE(chunks.title, '')) LIKE ?
                    OR LOWER(documents.document_name) LIKE ?
                    OR LOWER(COALESCE(documents.code_name, '')) LIKE ?
                )
    """
    parameters: list[Any] = [like_query, like_query, like_query, like_query, like_query]
    if document_id is not None:
        sql += " AND documents.id = ?"
        parameters.append(document_id)
    sql += """
            ORDER BY documents.upload_date DESC, chunks.chunk_index ASC
            LIMIT ?
    """
    parameters.append(limit)

    with sqlite3.connect(paths.database_path) as connection:
        connection.row_factory = sqlite3.Row
        rows = connection.execute(sql, tuple(parameters)).fetchall()

    return [
        ReferenceSearchResult(
            document_id=int(row["document_id"]),
            document_name=str(row["document_name"]),
            file_name=str(row["file_name"]),
            parse_status=str(row["parse_status"]),
            chunk_index=int(row["chunk_index"]),
            page_start=int(row["page_start"] or 0),
            page_end=int(row["page_end"] or 0),
            section_label=row["section_label"],
            title=row["title"],
            snippet=_build_snippet(str(row["text_content"]), normalized_query),
        )
        for row in rows
    ]


def extract_pdf_text(file_bytes: bytes) -> ExtractedPdfDocument:
    reader = _open_pdf_reader(file_bytes)
    pages = tuple(
        ExtractedPage(
            page_number=index,
            text=_normalize_page_text(page.extract_text() or ""),
        )
        for index, page in enumerate(reader.pages, start=1)
    )
    return ExtractedPdfDocument(
        page_count=len(pages),
        pages=pages,
    )


def build_reference_chunks(
    *,
    document_name: str,
    pages: tuple[ExtractedPage, ...],
    target_words: int = 900,
    max_words: int = 1200,
) -> list[ReferenceChunkRecord]:
    blocks: list[dict[str, Any]] = []
    for page in pages:
        page_blocks = _split_page_blocks(page.text)
        if not page_blocks and page.text.strip():
            page_blocks = [page.text.strip()]
        for block in page_blocks:
            normalized_block = " ".join(block.split()).strip()
            if not normalized_block:
                continue
            blocks.append(
                {
                    "page_number": page.page_number,
                    "text": normalized_block,
                    "heading": _detect_heading(normalized_block),
                }
            )

    chunks: list[ReferenceChunkRecord] = []
    current_text_parts: list[str] = []
    current_pages: list[int] = []
    current_heading: str | None = None

    for block in blocks:
        block_word_count = len(block["text"].split())
        current_word_count = len(" ".join(current_text_parts).split()) if current_text_parts else 0
        should_flush = (
            current_text_parts
            and (
                current_word_count >= target_words
                or current_word_count + block_word_count > max_words
            )
        )
        if should_flush:
            chunks.append(
                _build_chunk_record(
                    document_name=document_name,
                    chunk_index=len(chunks),
                    text_parts=current_text_parts,
                    pages=current_pages,
                    heading=current_heading,
                )
            )
            current_text_parts = []
            current_pages = []

        if block["heading"]:
            current_heading = block["heading"]
        current_text_parts.append(block["text"])
        current_pages.append(int(block["page_number"]))

    if current_text_parts:
        chunks.append(
            _build_chunk_record(
                document_name=document_name,
                chunk_index=len(chunks),
                text_parts=current_text_parts,
                pages=current_pages,
                heading=current_heading,
            )
        )

    return chunks


def infer_document_metadata(*, file_name: str, document_name: str) -> dict[str, str | None]:
    source_text = f"{document_name} {Path(file_name).stem}".replace("_", " ")
    normalized = " ".join(source_text.split())
    match = re.search(r"\b([A-Z]{2,}\s*\d{2,4}[A-Z]?)\s*[- ]\s*(\d{2,4})\b", normalized)
    code_name = None
    edition = None
    if match:
        code_name = match.group(1).replace("  ", " ").strip()
        edition = match.group(2).strip()
    return {
        "code_name": code_name,
        "edition": edition,
    }


def resolve_official_document_metadata(
    *,
    document_name: str,
    file_name: str,
    preview_text: str,
    document_type: str | None,
) -> OfficialDocumentMetadata:
    source_text = " ".join(
        part for part in [document_name, Path(file_name).stem.replace("_", " "), preview_text] if part
    )
    normalized = " ".join(source_text.split())

    patterns = (
        (
            r"\bACI\s*318M[- ]08\b",
            OfficialDocumentMetadata(
                document_name="ACI 318M-08 Building Code Requirements for Structural Concrete and Commentary",
                display_file_name="ACI_318M-08_Building_Code_Requirements_for_Structural_Concrete_and_Commentary.pdf",
                document_type="ACI 318 Standard",
                code_name="ACI 318M-08",
                edition="08",
                sort_year=2008,
            ),
        ),
        (
            r"\bACI\s*318M[- ]11\b",
            OfficialDocumentMetadata(
                document_name="ACI 318M-11 Building Code Requirements for Structural Concrete and Commentary",
                display_file_name="ACI_318M-11_Building_Code_Requirements_for_Structural_Concrete_and_Commentary.pdf",
                document_type="ACI 318 Standard",
                code_name="ACI 318M-11",
                edition="11",
                sort_year=2011,
            ),
        ),
        (
            r"\bACI\s*318M[- ]14\b",
            OfficialDocumentMetadata(
                document_name="ACI 318M-14 Building Code Requirements for Structural Concrete and Commentary",
                display_file_name="ACI_318M-14_Building_Code_Requirements_for_Structural_Concrete_and_Commentary.pdf",
                document_type="ACI 318 Standard",
                code_name="ACI 318M-14",
                edition="14",
                sort_year=2014,
            ),
        ),
        (
            r"\bACI\s*318[- ]19\b",
            OfficialDocumentMetadata(
                document_name="ACI 318M-19 Building Code Requirements for Structural Concrete and Commentary",
                display_file_name="ACI_318M-19_Building_Code_Requirements_for_Structural_Concrete_and_Commentary.pdf",
                document_type="ACI 318 Standard",
                code_name="ACI 318M-19",
                edition="19",
                sort_year=2019,
            ),
        ),
        (
            r"\bACI\s*(?:CODE[- ]?)?318[- ]25\b",
            OfficialDocumentMetadata(
                document_name="ACI CODE-318M-25 Building Code for Structural Concrete: Code Requirements and Commentary (SI Units)",
                display_file_name="ACI_CODE-318M-25_Building_Code_for_Structural_Concrete_Code_Requirements_and_Commentary_SI.pdf",
                document_type="ACI 318 Standard",
                code_name="ACI CODE-318M-25",
                edition="25",
                sort_year=2025,
            ),
        ),
        (
            r"\bACI\s*318[- ]99\b",
            OfficialDocumentMetadata(
                document_name="ACI 318-99 Building Code Requirements for Structural Concrete and Commentary",
                display_file_name="ACI_318-99_Building_Code_Requirements_for_Structural_Concrete_and_Commentary.pdf",
                document_type="ACI 318 Standard",
                code_name="ACI 318-99",
                edition="99",
                sort_year=1999,
            ),
        ),
    )
    for pattern, metadata in patterns:
        if re.search(pattern, normalized, flags=re.IGNORECASE):
            return metadata

    inferred = infer_document_metadata(file_name=file_name, document_name=document_name)
    return OfficialDocumentMetadata(
        document_name=document_name.strip(),
        display_file_name=Path(file_name).name,
        document_type=document_type,
        code_name=inferred["code_name"],
        edition=inferred["edition"],
        sort_year=_edition_to_year(inferred["edition"]),
    )


def _open_pdf_reader(file_bytes: bytes):
    from pypdf import PdfReader
    from pypdf.errors import DependencyError

    try:
        reader = PdfReader(BytesIO(file_bytes))
    except DependencyError as error:
        raise RuntimeError(
            "Encrypted PDF support is unavailable. Install pycryptodome or repair the cryptography runtime."
        ) from error
    if reader.is_encrypted:
        try:
            reader.decrypt("")
        except DependencyError as error:
            raise RuntimeError(
                "Encrypted PDF support is unavailable. Install pycryptodome or repair the cryptography runtime."
            ) from error
    return reader


def _schema_sql() -> str:
    return """
    CREATE TABLE IF NOT EXISTS documents (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_name TEXT NOT NULL,
        file_name TEXT NOT NULL,
        file_path TEXT NOT NULL,
        document_type TEXT,
        code_name TEXT,
        edition TEXT,
        file_hash TEXT NOT NULL UNIQUE,
        upload_date TEXT NOT NULL,
        parse_status TEXT NOT NULL,
        page_count INTEGER NOT NULL DEFAULT 0,
        parsed_text_path TEXT,
        parsed_json_path TEXT,
        last_error TEXT
    );

    CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        chunk_index INTEGER NOT NULL,
        page_start INTEGER,
        page_end INTEGER,
        section_label TEXT,
        title TEXT,
        text_content TEXT NOT NULL,
        text_length INTEGER NOT NULL,
        keywords_json TEXT,
        created_at TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
        UNIQUE(document_id, chunk_index)
    );

    CREATE TABLE IF NOT EXISTS document_tags (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        document_id INTEGER NOT NULL,
        tag TEXT NOT NULL,
        FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
        UNIQUE(document_id, tag)
    );

    CREATE INDEX IF NOT EXISTS idx_documents_parse_status ON documents(parse_status);
    CREATE INDEX IF NOT EXISTS idx_documents_code_name ON documents(code_name);
    CREATE INDEX IF NOT EXISTS idx_chunks_document_id ON chunks(document_id);
    CREATE INDEX IF NOT EXISTS idx_chunks_page_range ON chunks(document_id, page_start, page_end);
    """


def _find_document_by_hash(database_path: Path, file_hash: str) -> sqlite3.Row | None:
    with sqlite3.connect(database_path) as connection:
        connection.row_factory = sqlite3.Row
        return connection.execute(
            """
            SELECT
                documents.id,
                documents.document_name,
                documents.file_name,
                documents.page_count,
                (
                    SELECT COUNT(*)
                    FROM chunks
                    WHERE chunks.document_id = documents.id
                ) AS chunk_count
            FROM documents
            WHERE file_hash = ?
            """,
            (file_hash,),
        ).fetchone()


def _insert_document_record(
    *,
    database_path: Path,
    document_name: str,
    file_name: str,
    file_path: str,
    document_type: str | None,
    code_name: str | None,
    edition: str | None,
    file_hash: str,
    upload_date: str,
) -> int:
    with sqlite3.connect(database_path) as connection:
        cursor = connection.execute(
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'saved', 0)
            """,
            (
                document_name,
                file_name,
                file_path,
                document_type,
                code_name,
                edition,
                file_hash,
                upload_date,
            ),
        )
        connection.commit()
        return int(cursor.lastrowid)


def _update_document_identity(
    *,
    database_path: Path,
    document_id: int,
    document_name: str,
    file_name: str,
    document_type: str | None,
    code_name: str | None,
    edition: str | None,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE documents
            SET
                document_name = ?,
                file_name = ?,
                document_type = ?,
                code_name = ?,
                edition = ?
            WHERE id = ?
            """,
            (
                document_name,
                file_name,
                document_type,
                code_name,
                edition,
                document_id,
            ),
        )
        connection.commit()


def _update_document_file_paths(
    *,
    database_path: Path,
    document_id: int,
    file_path: str,
    parsed_text_path: str | None,
    parsed_json_path: str | None,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE documents
            SET
                file_path = ?,
                parsed_text_path = ?,
                parsed_json_path = ?
            WHERE id = ?
            """,
            (
                file_path,
                parsed_text_path,
                parsed_json_path,
                document_id,
            ),
        )
        connection.commit()


def _replace_document_chunks(
    *,
    database_path: Path,
    document_id: int,
    chunks: list[ReferenceChunkRecord],
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM chunks WHERE document_id = ?", (document_id,))
        connection.executemany(
            """
            INSERT INTO chunks (
                document_id,
                chunk_index,
                page_start,
                page_end,
                section_label,
                title,
                text_content,
                text_length,
                keywords_json,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                (
                    document_id,
                    chunk.chunk_index,
                    chunk.page_start,
                    chunk.page_end,
                    chunk.section_label,
                    chunk.title,
                    chunk.text_content,
                    chunk.text_length,
                    chunk.keywords_json,
                    _timestamp_now(),
                )
                for chunk in chunks
            ],
        )
        connection.commit()


def _update_document_status(
    *,
    database_path: Path,
    document_id: int,
    parse_status: str,
    page_count: int,
    parsed_text_path: str | None,
    parsed_json_path: str | None,
    last_error: str | None,
) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute(
            """
            UPDATE documents
            SET
                parse_status = ?,
                page_count = ?,
                parsed_text_path = ?,
                parsed_json_path = ?,
                last_error = ?
            WHERE id = ?
            """,
            (
                parse_status,
                page_count,
                parsed_text_path,
                parsed_json_path,
                last_error,
                document_id,
            ),
        )
        connection.commit()


def _delete_document_record(database_path: Path, document_id: int) -> None:
    with sqlite3.connect(database_path) as connection:
        connection.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        connection.commit()


def _build_storage_paths(
    *,
    paths: ReferenceLibraryPaths,
    storage_stem: str,
    original_file_name: str,
    file_hash: str,
) -> tuple[Path, Path, Path]:
    extension = Path(original_file_name).suffix.lower() or ".pdf"
    raw_path = paths.raw_dir / f"{storage_stem}{extension}"
    if raw_path.exists():
        raw_path = paths.raw_dir / f"{storage_stem}_{file_hash[:12]}{extension}"
    parsed_stem = raw_path.stem
    return (
        raw_path,
        paths.parsed_dir / f"{parsed_stem}.txt",
        paths.parsed_dir / f"{parsed_stem}.json",
    )


def _build_storage_stem(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value.strip()).strip("_")
    return normalized or "reference_document"


def _normalize_page_text(text: str) -> str:
    return text.replace("\x00", "").replace("\r\n", "\n").replace("\r", "\n").strip()


def _split_page_blocks(text: str) -> list[str]:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []
    blocks = [block.strip() for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    if blocks:
        return blocks
    return [line.strip() for line in normalized.splitlines() if line.strip()]


def _detect_heading(text: str) -> str | None:
    first_line = text.splitlines()[0].strip() if text else ""
    if not first_line:
        return None
    if len(first_line) > 120:
        return None
    if re.match(r"^(\d+(\.\d+)*[A-Za-z]?)\s+.+", first_line):
        return first_line
    letters = [character for character in first_line if character.isalpha()]
    if letters and sum(character.isupper() for character in letters) / len(letters) >= 0.7:
        return first_line
    return None


def _build_chunk_record(
    *,
    document_name: str,
    chunk_index: int,
    text_parts: list[str],
    pages: list[int],
    heading: str | None,
) -> ReferenceChunkRecord:
    text_content = "\n\n".join(text_parts).strip()
    page_start = min(pages)
    page_end = max(pages)
    keywords = _extract_keywords(text_content)
    return ReferenceChunkRecord(
        chunk_index=chunk_index,
        page_start=page_start,
        page_end=page_end,
        section_label=heading,
        title=heading or document_name,
        text_content=text_content,
        text_length=len(text_content),
        keywords_json=json.dumps(keywords, ensure_ascii=False),
    )


def _extract_keywords(text: str, *, limit: int = 12) -> list[str]:
    stopwords = {
        "about",
        "after",
        "all",
        "also",
        "and",
        "are",
        "been",
        "for",
        "from",
        "into",
        "more",
        "shall",
        "that",
        "than",
        "the",
        "their",
        "there",
        "these",
        "this",
        "those",
        "when",
        "with",
    }
    words = re.findall(r"[A-Za-z][A-Za-z0-9\-]{3,}", text.lower())
    ranked: list[str] = []
    for word in words:
        if word in stopwords or word in ranked:
            continue
        ranked.append(word)
        if len(ranked) >= limit:
            break
    return ranked


def _build_snippet(text: str, query: str, *, radius: int = 180) -> str:
    normalized_text = " ".join(text.split())
    lowered_text = normalized_text.lower()
    lowered_query = query.lower()
    match_index = lowered_text.find(lowered_query)
    if match_index < 0:
        return normalized_text[: radius * 2].strip()
    start = max(0, match_index - radius)
    end = min(len(normalized_text), match_index + len(query) + radius)
    snippet = normalized_text[start:end].strip()
    if start > 0:
        snippet = f"...{snippet}"
    if end < len(normalized_text):
        snippet = f"{snippet}..."
    return snippet


def _timestamp_now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def _edition_to_year(edition: str | None) -> int | None:
    if not edition:
        return None
    normalized = edition.strip()
    if not normalized.isdigit():
        return None
    numeric = int(normalized)
    if len(normalized) == 4:
        return numeric
    if numeric >= 90:
        return 1900 + numeric
    return 2000 + numeric


def _document_sort_key(document: ReferenceDocumentRecord) -> tuple[int, str]:
    year = _edition_to_year(document.edition)
    if year is None:
        return (9999, document.document_name.lower())
    return (year, document.document_name.lower())


def _synchronize_document_storage_paths(
    *,
    database_path: Path,
    document: ReferenceDocumentRecord,
    display_file_name: str,
) -> bool:
    raw_path, parsed_text_path, parsed_json_path = _synchronize_paths_for_display_name(
        raw_path=Path(document.file_path),
        parsed_text_path=Path(document.parsed_text_path) if document.parsed_text_path else None,
        parsed_json_path=Path(document.parsed_json_path) if document.parsed_json_path else None,
        display_file_name=display_file_name,
    )
    changed = (
        str(raw_path) != document.file_path
        or (str(parsed_text_path) if parsed_text_path else None) != document.parsed_text_path
        or (str(parsed_json_path) if parsed_json_path else None) != document.parsed_json_path
    )
    _update_document_file_paths(
        database_path=database_path,
        document_id=document.id,
        file_path=str(raw_path),
        parsed_text_path=str(parsed_text_path) if parsed_text_path else None,
        parsed_json_path=str(parsed_json_path) if parsed_json_path else None,
    )
    return changed


def _synchronize_paths_for_display_name(
    *,
    raw_path: Path,
    parsed_text_path: Path | None,
    parsed_json_path: Path | None,
    display_file_name: str,
) -> tuple[Path, Path | None, Path | None]:
    target_raw_path = raw_path.with_name(display_file_name)
    if raw_path.exists() and raw_path != target_raw_path and not target_raw_path.exists():
        raw_path.rename(target_raw_path)
        raw_path = target_raw_path
    elif target_raw_path.exists():
        raw_path = target_raw_path

    target_stem = raw_path.stem
    if parsed_text_path is not None:
        target_text_path = parsed_text_path.with_name(f"{target_stem}.txt")
        if parsed_text_path.exists() and parsed_text_path != target_text_path and not target_text_path.exists():
            parsed_text_path.rename(target_text_path)
            parsed_text_path = target_text_path
        elif target_text_path.exists():
            parsed_text_path = target_text_path

    if parsed_json_path is not None:
        target_json_path = parsed_json_path.with_name(f"{target_stem}.json")
        if parsed_json_path.exists() and parsed_json_path != target_json_path and not target_json_path.exists():
            parsed_json_path.rename(target_json_path)
            parsed_json_path = target_json_path
        elif target_json_path.exists():
            parsed_json_path = target_json_path

    return raw_path, parsed_text_path, parsed_json_path
