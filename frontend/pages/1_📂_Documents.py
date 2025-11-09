"""
Document Upload and Management Page

This page allows users to upload and manage documents with drag-and-drop support.
Supports PDF, DOCX, and TXT files with batch upload up to 20 files.
"""

import streamlit as st
import sys
from pathlib import Path
import logging
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
import pandas as pd
import plotly.graph_objects as go
from dateutil import parser as date_parser

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, AuthenticationError, ValidationError
from components.auth import require_authentication
from config.settings import settings

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Documents - Org Archivist",
    page_icon="📂",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container styling */
    .main > div {
        padding-top: 2rem;
    }

    /* Upload section */
    .upload-section {
        border: 2px dashed #ccc;
        border-radius: 10px;
        padding: 2rem;
        text-align: center;
        background-color: #f8f9fa;
        margin: 1rem 0;
    }

    /* Progress bars */
    .stProgress > div > div > div {
        background-color: #4CAF50;
    }

    /* Warnings */
    .sensitivity-warning {
        background-color: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        margin: 1rem 0;
        border-radius: 4px;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'uploaded_files_info' not in st.session_state:
        st.session_state.uploaded_files_info = []
    if 'upload_progress' not in st.session_state:
        st.session_state.upload_progress = {}
    if 'selected_documents' not in st.session_state:
        st.session_state.selected_documents = set()
    if 'show_doc_details' not in st.session_state:
        st.session_state.show_doc_details = None
    if 'delete_doc_id' not in st.session_state:
        st.session_state.delete_doc_id = None
    if 'bulk_delete_confirm' not in st.session_state:
        st.session_state.bulk_delete_confirm = False


@st.dialog("Document Details")
def show_document_details_dialog(doc: Dict[str, Any]):
    """
    Display a modal dialog with full document metadata.

    Args:
        doc: Document dictionary with all metadata
    """
    st.markdown(f"### 📄 {doc.get('filename', 'Unknown')}")
    st.markdown("---")

    # Display metadata in organized sections
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("**Document Information**")
        st.text(f"Type: {doc.get('type', 'N/A')}")
        st.text(f"Year: {doc.get('year', 'N/A')}")
        st.text(f"Chunks: {doc.get('chunk_count', 0)}")

        # Format upload date
        upload_date = doc.get('created_at', 'N/A')
        if upload_date and upload_date != 'N/A':
            try:
                # Try to format if it's a valid datetime string
                dt = date_parser.parse(upload_date)
                upload_date = dt.strftime('%Y-%m-%d %H:%M')
            except:
                pass
        st.text(f"Uploaded: {upload_date}")

    with col2:
        st.markdown("**Programs & Outcome**")
        programs = doc.get('programs', [])
        if programs:
            for program in programs:
                st.text(f"• {program}")
        else:
            st.text("No programs assigned")

        outcome = doc.get('outcome', 'N/A')
        if outcome and outcome != 'N/A':
            st.text(f"\nOutcome: {outcome}")

    # Tags section
    st.markdown("**Tags**")
    tags = doc.get('tags', [])
    if tags:
        st.markdown(", ".join([f"`{tag}`" for tag in tags]))
    else:
        st.text("No tags")

    # Notes section
    notes = doc.get('notes', '')
    if notes:
        st.markdown("**Notes**")
        st.text_area("", value=notes, height=100, disabled=True, label_visibility="collapsed")

    # Close button
    if st.button("Close", use_container_width=True):
        st.rerun()


@st.dialog("Delete Document")
def show_delete_confirmation_dialog(doc: Dict[str, Any]):
    """
    Display a confirmation dialog for deleting a single document.

    Args:
        doc: Document to delete
    """
    st.warning("⚠️ Are you sure you want to delete this document?")

    st.markdown(f"**Filename:** {doc.get('filename', 'Unknown')}")
    st.markdown(f"**Type:** {doc.get('type', 'N/A')}")
    st.markdown(f"**Chunks:** {doc.get('chunk_count', 0)}")

    st.markdown("---")
    st.markdown("**This will:**")
    st.markdown("- Permanently remove the document from the database")
    st.markdown("- Delete all associated chunks from the vector store")
    st.markdown("- Remove all associated metadata")
    st.markdown("- **This action cannot be undone**")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.delete_doc_id = None
            st.rerun()

    with col2:
        if st.button("Delete Permanently", type="primary", use_container_width=True):
            client = get_api_client()
            try:
                with st.spinner(f"Deleting {doc.get('filename')}..."):
                    client.delete_document(doc['doc_id'])
                st.success(f"✅ Successfully deleted: {doc.get('filename')}")
                st.session_state.delete_doc_id = None
                time.sleep(1)
                st.rerun()
            except APIError as e:
                st.error(f"❌ Failed to delete: {e.message}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")


@st.dialog("Bulk Delete Documents")
def show_bulk_delete_confirmation_dialog(documents: List[Dict[str, Any]]):
    """
    Display a confirmation dialog for deleting multiple documents.

    Args:
        documents: List of documents to delete
    """
    st.warning(f"⚠️ Are you sure you want to delete {len(documents)} document(s)?")

    st.markdown("**Documents to be deleted:**")
    for doc in documents:
        st.markdown(f"- {doc.get('filename', 'Unknown')} ({doc.get('chunk_count', 0)} chunks)")

    st.markdown("---")
    st.markdown("**This will:**")
    st.markdown(f"- Permanently remove **{len(documents)} documents** from the database")
    st.markdown(f"- Delete all associated chunks from the vector store")
    st.markdown("- Remove all associated metadata")
    st.markdown("- **This action cannot be undone**")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.bulk_delete_confirm = False
            st.rerun()

    with col2:
        if st.button(f"Delete All {len(documents)}", type="primary", use_container_width=True):
            client = get_api_client()
            success_count = 0
            failed = []

            progress_bar = st.progress(0)
            status_text = st.empty()

            for idx, doc in enumerate(documents):
                try:
                    status_text.text(f"Deleting {idx + 1}/{len(documents)}: {doc.get('filename')}...")
                    client.delete_document(doc['doc_id'])
                    success_count += 1
                except Exception as e:
                    failed.append((doc.get('filename'), str(e)))

                progress_bar.progress((idx + 1) / len(documents))

            # Clear selection
            st.session_state.selected_documents = set()
            st.session_state.bulk_delete_confirm = False

            # Show results
            if success_count > 0:
                st.success(f"✅ Successfully deleted {success_count} document(s)")
            if failed:
                st.error(f"❌ Failed to delete {len(failed)} document(s)")
                with st.expander("Show errors"):
                    for filename, error in failed:
                        st.text(f"• {filename}: {error}")

            time.sleep(2)
            st.rerun()


def show_upload_interface():
    """Display the document upload interface."""
    st.title("📂 Document Library")
    st.markdown("Upload and manage your organization's documents")

    # Create tabs for Upload, Library, and Statistics
    tab1, tab2, tab3 = st.tabs(["📤 Upload Documents", "📚 Document Library", "📊 Statistics"])

    with tab1:
        show_upload_section()

    with tab2:
        show_document_library()

    with tab3:
        show_statistics_dashboard()


def show_upload_section():
    """Display the upload section with drag-and-drop interface."""
    st.markdown("### Upload Documents")

    # Sensitivity warning
    st.markdown("""
    <div class="sensitivity-warning">
        <h4 style="margin-top: 0;">⚠️ Important: Public Documents Only</h4>
        <p><strong>Only upload public-facing documents.</strong> Do not upload confidential, financial, or sensitive operational documents.</p>
        <p><strong>Appropriate documents:</strong></p>
        <ul>
            <li>Published grant proposals</li>
            <li>Annual reports (public versions)</li>
            <li>Public program descriptions</li>
            <li>Published impact reports</li>
            <li>Public-facing strategic plans</li>
            <li>Donor communications</li>
        </ul>
        <p><strong>Do NOT upload:</strong> Financial documents, client/beneficiary information, confidential donor information,
        internal personnel documents, proprietary operational documents, or board minutes.</p>
    </div>
    """, unsafe_allow_html=True)

    # File uploader with drag-and-drop
    st.markdown("#### Select Files to Upload")
    st.info("📁 Supported formats: PDF, DOCX, TXT | Maximum 20 files per batch")

    uploaded_files = st.file_uploader(
        "Drag and drop files here or click to browse",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        help="Upload up to 20 documents at once. Supported formats: PDF, DOCX, TXT",
        label_visibility="collapsed"
    )

    # Check file count
    if uploaded_files and len(uploaded_files) > 20:
        st.error(f"⚠️ Too many files selected ({len(uploaded_files)}). Maximum is 20 files per batch.")
        uploaded_files = uploaded_files[:20]
        st.warning("Only the first 20 files will be processed.")

    # Show file list if files are selected
    if uploaded_files:
        st.markdown(f"#### Selected Files ({len(uploaded_files)})")

        # Display file information
        for idx, file in enumerate(uploaded_files):
            col1, col2, col3 = st.columns([3, 1, 1])
            with col1:
                st.text(f"📄 {file.name}")
            with col2:
                file_size = len(file.getvalue()) / (1024 * 1024)  # Convert to MB
                st.text(f"{file_size:.2f} MB")
            with col3:
                st.text(file.type if file.type else "Unknown")

        st.markdown("---")

        # Metadata form
        st.markdown("#### Document Metadata")
        st.caption("This metadata will be applied to all uploaded files")

        with st.form("document_metadata_form"):
            col1, col2 = st.columns(2)

            with col1:
                document_type = st.selectbox(
                    "Document Type *",
                    options=[
                        "Grant Proposal",
                        "Annual Report",
                        "Program Description",
                        "Impact Report",
                        "Strategic Plan",
                        "Donor Communication",
                        "Other"
                    ],
                    help="Select the type of document you're uploading"
                )

                year = st.number_input(
                    "Year *",
                    min_value=1990,
                    max_value=datetime.now().year + 5,
                    value=datetime.now().year,
                    help="Year the document was created or published"
                )

            with col2:
                programs = st.multiselect(
                    "Programs *",
                    options=[
                        "Education",
                        "Health",
                        "Youth Development",
                        "Community Development",
                        "Arts & Culture",
                        "Environment",
                        "Economic Development",
                        "Other"
                    ],
                    help="Select all programs that apply to this document",
                    default=None
                )

                outcome = st.selectbox(
                    "Outcome (for grants/proposals)",
                    options=["N/A", "Funded", "Not Funded", "Pending"],
                    index=0,
                    help="If this is a grant or proposal, indicate the outcome"
                )

            # Tags
            tags_input = st.text_input(
                "Tags (optional)",
                placeholder="Enter tags separated by commas (e.g., literacy, STEM, youth)",
                help="Add descriptive tags to help organize and find this document"
            )

            # Notes
            notes = st.text_area(
                "Notes (optional)",
                placeholder="Add any additional notes about this document...",
                help="Optional notes or context about this document"
            )

            # Sensitivity confirmation checkbox
            st.markdown("---")
            sensitivity_confirmed = st.checkbox(
                "✅ I confirm that these documents are public-facing and appropriate for AI processing",
                value=False,
                help="You must confirm that the documents do not contain sensitive, confidential, or proprietary information"
            )

            # Submit button
            col1, col2, col3 = st.columns([2, 1, 2])
            with col2:
                submit_button = st.form_submit_button(
                    "Upload Files",
                    use_container_width=True,
                    type="primary",
                    disabled=not sensitivity_confirmed
                )

            if submit_button:
                if not sensitivity_confirmed:
                    st.error("❌ Please confirm that the documents are appropriate for upload.")
                elif not programs:
                    st.error("❌ Please select at least one program.")
                else:
                    # Process uploads
                    process_uploads(
                        uploaded_files,
                        document_type,
                        year,
                        programs,
                        outcome,
                        tags_input,
                        notes,
                        sensitivity_confirmed
                    )


def process_uploads(
    files: List,
    document_type: str,
    year: int,
    programs: List[str],
    outcome: str,
    tags_input: str,
    notes: str,
    sensitivity_confirmed: bool
):
    """Process the file uploads."""
    client = get_api_client()

    # Parse tags
    tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []

    # Create metadata dict
    metadata = {
        "type": document_type,
        "year": year,
        "programs": programs,
        "outcome": outcome if outcome != "N/A" else None,
        "tags": tags,
        "notes": notes
    }

    # Progress tracking
    st.markdown("### Upload Progress")
    progress_bar = st.progress(0)
    status_text = st.empty()

    total_files = len(files)
    successful_uploads = 0
    failed_uploads = []

    # Process each file
    for idx, file in enumerate(files):
        try:
            # Update progress
            progress = (idx) / total_files
            progress_bar.progress(progress)
            status_text.text(f"Uploading {idx + 1}/{total_files}: {file.name}...")

            # Reset file pointer
            file.seek(0)

            # Upload file
            response = client.upload_document(
                file=file,
                metadata=metadata,
                sensitivity_confirmed=sensitivity_confirmed
            )

            if response:
                successful_uploads += 1
                logger.info(f"Successfully uploaded: {file.name}")
            else:
                failed_uploads.append((file.name, "Unknown error"))

        except ValidationError as e:
            logger.error(f"Validation error uploading {file.name}: {e}")
            failed_uploads.append((file.name, f"Validation error: {e.message}"))
        except APIError as e:
            logger.error(f"API error uploading {file.name}: {e}")
            failed_uploads.append((file.name, f"API error: {e.message}"))
        except Exception as e:
            logger.error(f"Unexpected error uploading {file.name}: {e}", exc_info=True)
            failed_uploads.append((file.name, f"Error: {str(e)}"))

    # Complete progress
    progress_bar.progress(1.0)
    status_text.text(f"Upload complete: {successful_uploads}/{total_files} successful")

    # Show results
    st.markdown("---")
    st.markdown("### Upload Results")

    if successful_uploads > 0:
        st.success(f"✅ Successfully uploaded {successful_uploads} file(s)")

    if failed_uploads:
        st.error(f"❌ Failed to upload {len(failed_uploads)} file(s)")
        with st.expander("View error details"):
            for filename, error in failed_uploads:
                st.text(f"• {filename}: {error}")

    # Clear file uploader by refreshing
    if successful_uploads > 0:
        st.info("💡 You can now upload more files or view your document library in the 'Document Library' tab.")


def show_document_library():
    """Display the document library with all uploaded documents using an interactive table."""
    st.markdown("### Document Library")

    client = get_api_client()

    # Initialize session state for pagination
    if 'doc_page' not in st.session_state:
        st.session_state.doc_page = 0
    if 'doc_per_page' not in st.session_state:
        st.session_state.doc_per_page = 25

    try:
        # Fetch documents
        with st.spinner("Loading documents..."):
            all_documents = client.get_documents(limit=1000)

        if not all_documents:
            st.info("📭 No documents uploaded yet. Upload your first document in the 'Upload Documents' tab!")
            return

        # Search and Filters Section
        st.markdown("#### 🔍 Search & Filters")

        col1, col2 = st.columns([2, 1])

        with col1:
            search_query = st.text_input(
                "Search documents",
                placeholder="Search by filename, tags, or notes...",
                label_visibility="collapsed",
                key="doc_search"
            )

        with col2:
            show_filters = st.checkbox("Show Advanced Filters", value=False)

        # Advanced Filters
        filter_type = None
        filter_year = None
        filter_program = None

        if show_filters:
            col1, col2, col3 = st.columns(3)

            with col1:
                # Get unique document types
                unique_types = sorted(list(set([doc.get("type", "") for doc in all_documents if doc.get("type")])))
                filter_type = st.multiselect(
                    "Document Type",
                    options=unique_types,
                    key="filter_type"
                )

            with col2:
                # Get unique years
                unique_years = sorted(list(set([doc.get("year") for doc in all_documents if doc.get("year")])), reverse=True)
                filter_year = st.multiselect(
                    "Year",
                    options=unique_years,
                    key="filter_year"
                )

            with col3:
                # Get unique programs
                unique_programs = sorted(list(set([prog for doc in all_documents for prog in doc.get("programs", []) if prog])))
                filter_program = st.multiselect(
                    "Program",
                    options=unique_programs,
                    key="filter_program"
                )

        # Apply search filter
        filtered_docs = all_documents
        if search_query:
            search_lower = search_query.lower()
            filtered_docs = [
                doc for doc in filtered_docs
                if search_lower in doc.get('filename', '').lower()
                or search_lower in ' '.join(doc.get('tags', [])).lower()
                or search_lower in doc.get('notes', '').lower()
            ]

        # Apply type filter
        if filter_type:
            filtered_docs = [doc for doc in filtered_docs if doc.get("type") in filter_type]

        # Apply year filter
        if filter_year:
            filtered_docs = [doc for doc in filtered_docs if doc.get("year") in filter_year]

        # Apply program filter
        if filter_program:
            filtered_docs = [doc for doc in filtered_docs if any(prog in doc.get("programs", []) for prog in filter_program)]

        # Display stats
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Documents", len(all_documents))
        with col2:
            st.metric("Filtered Results", len(filtered_docs))
        with col3:
            total_chunks = sum(doc.get('chunk_count', 0) for doc in filtered_docs)
            st.metric("Total Chunks", total_chunks)

        st.markdown("---")

        if not filtered_docs:
            st.warning("No documents match your search criteria. Try adjusting your filters.")
            return

        # Prepare data for dataframe
        table_data = []
        for doc in filtered_docs:
            # Format programs as comma-separated string
            programs_str = ', '.join(doc.get('programs', []))

            # Format outcome with emoji
            outcome = doc.get('outcome')
            outcome_display = ""
            if outcome and outcome != 'N/A':
                if outcome == 'Funded':
                    outcome_display = "✅ Funded"
                elif outcome == 'Not Funded':
                    outcome_display = "❌ Not Funded"
                elif outcome == 'Pending':
                    outcome_display = "⏳ Pending"
                else:
                    outcome_display = outcome

            table_data.append({
                'Filename': doc.get('filename', 'Unknown'),
                'Type': doc.get('type', ''),
                'Year': doc.get('year', ''),
                'Programs': programs_str,
                'Outcome': outcome_display,
                'Chunks': doc.get('chunk_count', 0),
                'Upload Date': doc.get('created_at', ''),
                'doc_id': doc.get('doc_id', '')  # Hidden but used for deletion
            })

        df = pd.DataFrame(table_data)

        # Pagination controls
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            per_page = st.selectbox(
                "Rows per page",
                options=[10, 25, 50, 100],
                index=[10, 25, 50, 100].index(st.session_state.doc_per_page),
                key="per_page_select"
            )
            if per_page != st.session_state.doc_per_page:
                st.session_state.doc_per_page = per_page
                st.session_state.doc_page = 0
                st.rerun()

        total_pages = (len(df) - 1) // st.session_state.doc_per_page + 1 if len(df) > 0 else 1
        current_page = min(st.session_state.doc_page, total_pages - 1)

        with col2:
            if st.button("⏮️ First", disabled=current_page == 0):
                st.session_state.doc_page = 0
                st.rerun()

        with col3:
            if st.button("⏭️ Last", disabled=current_page >= total_pages - 1):
                st.session_state.doc_page = total_pages - 1
                st.rerun()

        with col4:
            st.text(f"Page {current_page + 1} of {total_pages}")

        # Calculate pagination
        start_idx = current_page * st.session_state.doc_per_page
        end_idx = min(start_idx + st.session_state.doc_per_page, len(df))

        # Display paginated dataframe
        display_df = df.iloc[start_idx:end_idx].copy()

        # Drop doc_id from display (keep it in the original df for deletion)
        display_df_for_table = display_df.drop(columns=['doc_id'])

        st.markdown(f"**Showing {start_idx + 1}-{end_idx} of {len(df)} documents**")

        # Display interactive dataframe
        st.dataframe(
            display_df_for_table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Filename": st.column_config.TextColumn("Filename", width="medium"),
                "Type": st.column_config.TextColumn("Type", width="small"),
                "Year": st.column_config.NumberColumn("Year", width="small"),
                "Programs": st.column_config.TextColumn("Programs", width="medium"),
                "Outcome": st.column_config.TextColumn("Outcome", width="small"),
                "Chunks": st.column_config.NumberColumn("Chunks", width="small"),
                "Upload Date": st.column_config.TextColumn("Upload Date", width="medium"),
            }
        )

        # Delete functionality
        st.markdown("---")
        st.markdown("#### 🗑️ Delete Document")
        st.caption("Select a document to delete from the table above, then enter its filename below to confirm deletion.")

        col1, col2 = st.columns([3, 1])
        with col1:
            delete_filename = st.text_input(
                "Enter filename to delete",
                placeholder="Type the exact filename to delete...",
                key="delete_filename_input"
            )

        with col2:
            st.markdown("<br>", unsafe_allow_html=True)  # Spacer
            delete_button = st.button("🗑️ Delete Document", type="primary", use_container_width=True)

        if delete_button:
            if not delete_filename:
                st.error("❌ Please enter a filename.")
            else:
                # Find document by filename
                matching_docs = [doc for doc in filtered_docs if doc.get('filename') == delete_filename]

                if not matching_docs:
                    st.error(f"❌ No document found with filename: {delete_filename}")
                elif len(matching_docs) > 1:
                    st.error(f"❌ Multiple documents found with that filename. Please contact support.")
                else:
                    doc_to_delete = matching_docs[0]
                    try:
                        with st.spinner(f"Deleting {delete_filename}..."):
                            client.delete_document(doc_to_delete['doc_id'])
                        st.success(f"✅ Successfully deleted: {delete_filename}")
                        time.sleep(1)
                        st.rerun()
                    except APIError as e:
                        st.error(f"❌ Failed to delete: {e.message}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")

        # Pagination buttons at bottom
        st.markdown("---")
        col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

        with col2:
            if st.button("⬅️ Previous", disabled=current_page == 0, key="prev_bottom"):
                st.session_state.doc_page = max(0, current_page - 1)
                st.rerun()

        with col3:
            st.text(f"Page {current_page + 1}/{total_pages}")

        with col4:
            if st.button("Next ➡️", disabled=current_page >= total_pages - 1, key="next_bottom"):
                st.session_state.doc_page = min(total_pages - 1, current_page + 1)
                st.rerun()

    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
    except APIError as e:
        st.error(f"❌ Error loading documents: {e.message}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Error in document library: {e}", exc_info=True)


def show_statistics_dashboard():
    """Display document library statistics dashboard."""
    st.markdown("### 📊 Library Statistics")
    st.markdown("Overview of your document collection")

    client = get_api_client()

    try:
        # Fetch statistics from API
        with st.spinner("Loading statistics..."):
            stats = client.get_document_stats()
            all_documents = client.get_documents(limit=1000)

        if not stats:
            st.warning("Unable to load statistics.")
            return

        # Top-level metrics
        st.markdown("#### 📈 Summary Metrics")
        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                label="Total Documents",
                value=stats.get("total_documents", 0),
                help="Total number of documents in the library"
            )

        with col2:
            st.metric(
                label="Total Chunks",
                value=f"{stats.get('total_chunks', 0):,}",
                help="Total number of processed chunks across all documents"
            )

        with col3:
            avg_chunks = stats.get("avg_chunks_per_doc", 0.0)
            st.metric(
                label="Avg. Chunks/Doc",
                value=f"{avg_chunks:.1f}",
                help="Average number of chunks per document"
            )

        st.markdown("---")

        # Charts section
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 Distribution by Type")
            by_type = stats.get("by_type", {})

            if by_type:
                # Create pie chart for document types
                fig_type = go.Figure(data=[go.Pie(
                    labels=list(by_type.keys()),
                    values=list(by_type.values()),
                    hole=0.3,
                    marker=dict(
                        colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8', '#F7DC6F', '#BB8FCE']
                    )
                )])

                fig_type.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20)
                )

                st.plotly_chart(fig_type, use_container_width=True)
            else:
                st.info("No document type data available")

        with col2:
            st.markdown("#### 📅 Distribution by Year")
            by_year = stats.get("by_year", {})

            if by_year:
                # Create bar chart for years
                # Sort years for better visualization
                years_sorted = sorted(by_year.items())
                years = [str(year) for year, _ in years_sorted]
                counts = [count for _, count in years_sorted]

                fig_year = go.Figure(data=[go.Bar(
                    x=years,
                    y=counts,
                    marker=dict(
                        color=counts,
                        colorscale='Viridis',
                        showscale=False
                    ),
                    text=counts,
                    textposition='auto',
                )])

                fig_year.update_layout(
                    xaxis_title="Year",
                    yaxis_title="Number of Documents",
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    showlegend=False
                )

                st.plotly_chart(fig_year, use_container_width=True)
            else:
                st.info("No year data available")

        st.markdown("---")

        # Outcome distribution (if available)
        by_outcome = stats.get("by_outcome", {})
        if by_outcome and any(by_outcome.values()):
            st.markdown("#### ✅ Distribution by Outcome")

            # Filter out N/A or null outcomes
            filtered_outcomes = {k: v for k, v in by_outcome.items() if k and k != "N/A" and v > 0}

            if filtered_outcomes:
                col1, col2, col3, col4 = st.columns(4)

                # Display outcome metrics
                outcomes_display = [
                    ("Funded", "✅", "green"),
                    ("Not Funded", "❌", "red"),
                    ("Pending", "⏳", "orange")
                ]

                cols = [col1, col2, col3, col4]
                idx = 0

                for outcome_name, emoji, color in outcomes_display:
                    if outcome_name in filtered_outcomes:
                        with cols[idx]:
                            st.metric(
                                label=f"{emoji} {outcome_name}",
                                value=filtered_outcomes[outcome_name]
                            )
                            idx += 1

                st.markdown("---")

        # Recent uploads
        st.markdown("#### 🕒 Recent Uploads")

        if all_documents:
            # Sort documents by upload date (most recent first)
            sorted_docs = sorted(
                all_documents,
                key=lambda x: x.get('created_at', ''),
                reverse=True
            )[:10]  # Get top 10 most recent

            if sorted_docs:
                # Prepare data for display
                recent_data = []
                for doc in sorted_docs:
                    # Format upload date
                    upload_date = doc.get('created_at', 'N/A')
                    if upload_date and upload_date != 'N/A':
                        try:
                            dt = date_parser.parse(upload_date)
                            upload_date = dt.strftime('%Y-%m-%d %H:%M')
                        except:
                            pass

                    recent_data.append({
                        'Filename': doc.get('filename', 'Unknown'),
                        'Type': doc.get('type', 'N/A'),
                        'Year': doc.get('year', 'N/A'),
                        'Chunks': doc.get('chunk_count', 0),
                        'Upload Date': upload_date
                    })

                df_recent = pd.DataFrame(recent_data)

                st.dataframe(
                    df_recent,
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Filename": st.column_config.TextColumn("Filename", width="large"),
                        "Type": st.column_config.TextColumn("Type", width="medium"),
                        "Year": st.column_config.TextColumn("Year", width="small"),
                        "Chunks": st.column_config.NumberColumn("Chunks", width="small"),
                        "Upload Date": st.column_config.TextColumn("Upload Date", width="medium"),
                    }
                )
            else:
                st.info("No recent uploads to display")
        else:
            st.info("No documents available")

    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
    except APIError as e:
        st.error(f"❌ Error loading statistics: {e.message}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Error in statistics dashboard: {e}", exc_info=True)


def main():
    """Main entry point for the documents page."""
    # Require authentication
    require_authentication()

    # Initialize session state
    init_session_state()

    # Show upload interface
    show_upload_interface()


if __name__ == "__main__":
    main()
