from __future__ import annotations

from pathlib import Path

import streamlit as st

from core.navigation import go_home
from core.reference_library import (
    get_document,
    import_reference_document,
    initialize_reference_library,
    list_document_chunks,
    list_documents,
    load_document_text,
    retry_import,
    search_reference_chunks,
)
from core.theme import apply_theme


NOTICE_KEY = "_reference_library_notice"


def main() -> None:
    apply_theme()

    if st.sidebar.button("Home", use_container_width=True):
        go_home()
        st.rerun()

    paths = initialize_reference_library()
    documents = list_documents()

    st.markdown(
        """
        <div class="suite-hero">
          <div class="suite-eyebrow">Offline Document Store</div>
          <h1>Reference Library</h1>
          <p>
            Uploaded PDF references are stored locally, parsed locally, and indexed into a small SQLite database
            for later code lookup, warnings, and search workflows.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _inject_reference_library_css()

    _render_notice()

    documents = list_documents()
    metric_columns = st.columns(3)
    metric_columns[0].metric("Documents", len(documents))
    metric_columns[1].metric("Database", paths.database_path.name)
    metric_columns[2].metric("Storage", str(paths.root.relative_to(paths.root.parent)))

    if not documents:
        _render_import_tab(documents)
        st.caption("No reference documents have been imported yet.")
        return

    import_tab, search_tab, document_tab = st.tabs(["Import", "Search", "Documents"])
    with import_tab:
        _render_import_tab(documents)
    with search_tab:
        _render_search_tab(documents)
    with document_tab:
        _render_document_view_tab(documents)


def _inject_reference_library_css() -> None:
    st.markdown(
        """
        <style>
        .suite-hero {
            padding: 0.5rem 0 1.15rem 0;
            max-width: 920px;
        }
        .suite-eyebrow {
            display: inline-block;
            margin-bottom: 0.85rem;
            padding: 0.35rem 0.7rem;
            border-radius: 999px;
            border: 1px solid rgba(31, 111, 178, 0.18);
            background: linear-gradient(135deg, rgba(31, 111, 178, 0.1), rgba(220, 236, 248, 0.8));
            color: #1f3552;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.06em;
            text-transform: uppercase;
        }
        .suite-hero h1 {
            margin: 0;
            font-size: clamp(2rem, 4vw, 3.1rem);
            line-height: 0.98;
            letter-spacing: -0.03em;
        }
        .suite-hero p {
            margin: 0.95rem 0 0 0;
            max-width: 760px;
            font-size: 1rem;
            line-height: 1.65;
            color: #526172;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_import_tab(documents) -> None:
    _render_import_controls()
    _render_retry_controls(documents)
    st.markdown("### Imported Documents")
    st.dataframe(
        [
            {
                "Year": _document_year(document),
                "Document Name": document.document_name,
                "Edition": document.edition or "",
                "Type": document.document_type or "",
                "Upload Date": document.upload_date,
                "Status": document.parse_status,
                "Pages": document.page_count,
                "Chunks": document.chunk_count,
                "File": document.file_name,
                "Error": document.last_error or "",
            }
            for document in documents
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_import_controls() -> None:
    with st.form("reference_library_import_form", clear_on_submit=True):
        upload = st.file_uploader("Upload PDF", type=["pdf"])
        columns = st.columns((2.4, 1.2))
        document_name = columns[0].text_input("Document Name", placeholder="ACI 318M-25 SI")
        document_type = columns[1].text_input("Document Type", value="Reference PDF")
        submitted = st.form_submit_button("Process / Import", use_container_width=True)

    if not submitted:
        return
    if upload is None:
        _set_notice("warning", "Select a PDF file before starting the import.")
        st.rerun()
    result = import_reference_document(
        file_name=upload.name,
        file_bytes=upload.getvalue(),
        document_name=document_name or None,
        document_type=document_type or "Reference PDF",
    )
    notice_type = "success" if result.status == "imported" else "warning"
    if result.status in {"failed", "invalid", "missing"}:
        notice_type = "error"
    _set_notice(notice_type, result.message)
    st.rerun()


def _render_retry_controls(documents) -> None:
    retryable_documents = [document for document in documents if document.parse_status in {"failed", "empty"}]
    if not retryable_documents:
        return

    with st.expander("Retry failed or empty imports", expanded=False):
        labels = {
            f"{document.document_name} ({document.parse_status})": document.id
            for document in retryable_documents
        }
        selected_label = st.selectbox("Stored PDF", options=list(labels.keys()))
        if st.button("Retry Import", use_container_width=True):
            result = retry_import(labels[selected_label])
            notice_type = "success" if result.status == "imported" else "warning"
            if result.status in {"failed", "invalid", "missing"}:
                notice_type = "error"
            _set_notice(notice_type, result.message)
            st.rerun()


def _render_search_tab(documents) -> None:
    st.markdown("### Search Library")
    search_columns = st.columns((2.6, 1.4, 0.8))
    query = search_columns[0].text_input(
        "Keyword or section search",
        placeholder="beam torsion 22.7.7.1",
    )
    document_options = {"All documents": None}
    document_options.update({_document_option_label(document): document.id for document in documents})
    selected_document_label = search_columns[1].selectbox("Document", options=list(document_options.keys()))
    result_limit = int(search_columns[2].selectbox("Limit", options=[5, 10, 20, 50], index=1))

    if not query.strip():
        st.caption("Search by keyword, section number, or document title.")
        return

    results = search_reference_chunks(
        query,
        document_id=document_options[selected_document_label],
        limit=result_limit,
    )
    if not results:
        st.caption("No matching reference chunks were found.")
        return

    for result in results:
        heading = result.section_label or result.title or result.document_name
        with st.expander(
            f"{result.document_name} | pp. {result.page_start}-{result.page_end} | {heading}",
            expanded=False,
        ):
            st.caption(f"File: {result.file_name} | Chunk {result.chunk_index}")
            st.write(result.snippet)


def _render_document_view_tab(documents) -> None:
    st.markdown("### Document Viewer")
    document_options = {_document_option_label(document): document.id for document in documents}
    selected_label = st.selectbox("Stored document", options=list(document_options.keys()))
    document = get_document(document_options[selected_label])
    if document is None:
        st.caption("The selected document is no longer available.")
        return

    metrics = st.columns(4)
    metrics[0].metric("Status", document.parse_status)
    metrics[1].metric("Pages", document.page_count)
    metrics[2].metric("Chunks", document.chunk_count)
    metrics[3].metric("Edition", document.edition or "-")

    meta_columns = st.columns(2)
    meta_columns[0].caption(f"File: {document.file_name}")
    meta_columns[0].caption("Storage: Local managed copy inside the program library")
    meta_columns[0].caption(f"Upload Date: {document.upload_date}")
    meta_columns[1].caption(f"Code Name: {document.code_name or '-'}")
    meta_columns[1].caption(f"Type: {document.document_type or '-'}")
    meta_columns[1].caption(f"Stored Path: {document.file_path}")

    stored_pdf_path = Path(document.file_path)
    if stored_pdf_path.exists():
        with stored_pdf_path.open("rb") as source:
            st.download_button(
                "Download Stored PDF",
                data=source.read(),
                file_name=document.file_name,
                mime="application/pdf",
                use_container_width=False,
            )

    if document.last_error:
        st.warning(document.last_error)

    if document.parse_status != "imported":
        st.caption("Parsed content is only available after a successful import.")
        return

    chunks = list_document_chunks(document.id)
    if chunks:
        chunk_options = {
            f"Chunk {chunk.chunk_index} | pp. {chunk.page_start}-{chunk.page_end} | "
            f"{chunk.section_label or chunk.title or document.document_name}": chunk
            for chunk in chunks
        }
        selected_chunk_label = st.selectbox("Chunk", options=list(chunk_options.keys()))
        selected_chunk = chunk_options[selected_chunk_label]
        if selected_chunk.keywords:
            st.caption(f"Keywords: {', '.join(selected_chunk.keywords)}")
        st.text_area(
            "Chunk Text",
            value=selected_chunk.text_content,
            height=260,
            disabled=True,
        )

    parsed_text = load_document_text(document.id)
    if parsed_text:
        with st.expander("Parsed Text Preview", expanded=False):
            st.text_area(
                "Parsed Text",
                value=parsed_text[:12000],
                height=320,
                disabled=True,
            )
            if len(parsed_text) > 12000:
                st.caption("Preview truncated to the first 12,000 characters.")


def _render_notice() -> None:
    notice = st.session_state.pop(NOTICE_KEY, None)
    if not notice:
        return
    level = notice.get("level")
    message = notice.get("message", "")
    if level == "success":
        st.success(message)
    elif level == "error":
        st.error(message)
    else:
        st.warning(message)


def _set_notice(level: str, message: str) -> None:
    st.session_state[NOTICE_KEY] = {
        "level": level,
        "message": message,
    }


def _document_option_label(document) -> str:
    year = _document_year(document) or "Unknown year"
    return f"{year} | {document.document_name} [{document.parse_status}]"


def _document_year(document) -> int | str:
    if not document.edition:
        return ""
    normalized = str(document.edition).strip()
    if normalized.isdigit():
        numeric = int(normalized)
        if len(normalized) == 4:
            return numeric
        if numeric >= 90:
            return 1900 + numeric
        return 2000 + numeric
    return normalized
