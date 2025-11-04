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
from typing import List, Dict, Any
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, AuthenticationError, ValidationError
from components.auth import require_auth
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


def show_upload_interface():
    """Display the document upload interface."""
    st.title("📂 Document Library")
    st.markdown("Upload and manage your organization's documents")

    # Create tabs for Upload and Library
    tab1, tab2 = st.tabs(["📤 Upload Documents", "📚 Document Library"])

    with tab1:
        show_upload_section()

    with tab2:
        show_document_library()


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
    """Display the document library with all uploaded documents."""
    st.markdown("### Document Library")

    client = get_api_client()

    try:
        # Fetch documents
        with st.spinner("Loading documents..."):
            documents = client.get_documents(limit=100)

        if not documents:
            st.info("📭 No documents uploaded yet. Upload your first document in the 'Upload Documents' tab!")
            return

        # Display count
        st.markdown(f"**Total Documents:** {len(documents)}")

        # Filters
        with st.expander("🔍 Filters", expanded=False):
            col1, col2, col3 = st.columns(3)
            with col1:
                filter_type = st.multiselect("Document Type", options=["All"] + list(set([doc.get("type", "") for doc in documents])))
            with col2:
                filter_year = st.multiselect("Year", options=["All"] + sorted(list(set([str(doc.get("year", "")) for doc in documents if doc.get("year")])), reverse=True))
            with col3:
                filter_program = st.multiselect("Program", options=["All"] + list(set([prog for doc in documents for prog in doc.get("programs", [])])))

        # Apply filters
        filtered_docs = documents
        if filter_type and "All" not in filter_type:
            filtered_docs = [doc for doc in filtered_docs if doc.get("type") in filter_type]
        if filter_year and "All" not in filter_year:
            filtered_docs = [doc for doc in filtered_docs if str(doc.get("year")) in filter_year]
        if filter_program and "All" not in filter_program:
            filtered_docs = [doc for doc in filtered_docs if any(prog in doc.get("programs", []) for prog in filter_program)]

        st.markdown(f"**Showing:** {len(filtered_docs)} document(s)")
        st.markdown("---")

        # Display documents
        for doc in filtered_docs:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"**📄 {doc.get('filename', 'Unknown')}**")
                    if doc.get('type'):
                        st.caption(f"Type: {doc['type']}")

                with col2:
                    if doc.get('year'):
                        st.text(f"📅 Year: {doc['year']}")
                    if doc.get('programs'):
                        st.caption(f"Programs: {', '.join(doc['programs'][:2])}{' ...' if len(doc['programs']) > 2 else ''}")

                with col3:
                    if doc.get('chunk_count'):
                        st.text(f"📊 Chunks: {doc['chunk_count']}")
                    if doc.get('outcome') and doc['outcome'] != 'N/A':
                        outcome_emoji = "✅" if doc['outcome'] == 'Funded' else "❌" if doc['outcome'] == 'Not Funded' else "⏳"
                        st.text(f"{outcome_emoji} {doc['outcome']}")

                with col4:
                    if st.button("🗑️", key=f"delete_{doc.get('doc_id', '')}"):
                        try:
                            client.delete_document(doc['doc_id'])
                            st.success("Document deleted!")
                            st.rerun()
                        except APIError as e:
                            st.error(f"Failed to delete: {e.message}")

                st.markdown("---")

    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
    except APIError as e:
        st.error(f"❌ Error loading documents: {e.message}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Error in document library: {e}", exc_info=True)


def main():
    """Main entry point for the documents page."""
    # Require authentication
    require_auth()

    # Initialize session state
    init_session_state()

    # Show upload interface
    show_upload_interface()


if __name__ == "__main__":
    main()
