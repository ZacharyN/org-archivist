"""
Shared UI components for Streamlit frontend.

This module provides reusable UI components including loading spinners,
error displays, success messages, confirmation dialogs, and other common
UI elements used throughout the application.
"""

import streamlit as st
from typing import Optional, Callable, Any, Dict, List
import time
from datetime import datetime


# ===========================
# Loading Indicators
# ===========================

def show_loading_spinner(message: str = "Loading..."):
    """
    Display a loading spinner with a message.

    Args:
        message: Loading message to display

    Returns:
        Context manager for use with 'with' statement

    Example:
        with show_loading_spinner("Fetching data..."):
            data = api.fetch_data()
    """
    return st.spinner(message)


def show_progress_bar(
    progress: float,
    text: Optional[str] = None,
    key: Optional[str] = None
) -> None:
    """
    Display a progress bar.

    Args:
        progress: Progress value between 0.0 and 1.0
        text: Optional text to display above the progress bar
        key: Optional key for the progress bar

    Example:
        show_progress_bar(0.75, "Processing documents (3/4)...")
    """
    if text:
        st.text(text)
    st.progress(progress, key=key)


def show_skeleton_loader(num_lines: int = 3) -> None:
    """
    Display a skeleton loader (placeholder for content loading).

    Args:
        num_lines: Number of skeleton lines to show

    Example:
        show_skeleton_loader(num_lines=5)
    """
    for i in range(num_lines):
        st.empty()
        st.markdown(
            f'<div style="height: 20px; background: linear-gradient(90deg, #f0f0f0 25%, #e0e0e0 50%, #f0f0f0 75%); '
            f'background-size: 200% 100%; animation: loading 1.5s ease-in-out infinite; '
            f'border-radius: 4px; margin: 8px 0;"></div>',
            unsafe_allow_html=True
        )


# ===========================
# Message Displays
# ===========================

def show_success_message(
    message: str,
    icon: str = "✅",
    duration: Optional[int] = None
) -> None:
    """
    Display a success message.

    Args:
        message: Success message text
        icon: Icon to display (default: ✅)
        duration: Optional duration in seconds before auto-dismiss

    Example:
        show_success_message("Document uploaded successfully!")
    """
    st.success(f"{icon} {message}", icon="✅")

    if duration:
        time.sleep(duration)
        st.empty()


def show_error_message(
    message: str,
    icon: str = "❌",
    details: Optional[str] = None,
    expandable: bool = False
) -> None:
    """
    Display an error message with optional details.

    Args:
        message: Error message text
        icon: Icon to display (default: ❌)
        details: Optional detailed error information
        expandable: If True and details provided, show in expandable section

    Example:
        show_error_message(
            "Failed to upload document",
            details="Connection timeout after 30 seconds",
            expandable=True
        )
    """
    st.error(f"{icon} {message}", icon="🚨")

    if details:
        if expandable:
            with st.expander("Show details"):
                st.code(details, language="text")
        else:
            st.caption(details)


def show_warning_message(
    message: str,
    icon: str = "⚠️",
    details: Optional[str] = None
) -> None:
    """
    Display a warning message.

    Args:
        message: Warning message text
        icon: Icon to display (default: ⚠️)
        details: Optional additional details

    Example:
        show_warning_message("This action cannot be undone")
    """
    st.warning(f"{icon} {message}", icon="⚠️")

    if details:
        st.caption(details)


def show_info_message(
    message: str,
    icon: str = "ℹ️",
    details: Optional[str] = None
) -> None:
    """
    Display an informational message.

    Args:
        message: Info message text
        icon: Icon to display (default: ℹ️)
        details: Optional additional details

    Example:
        show_info_message("Your session will expire in 5 minutes")
    """
    st.info(f"{icon} {message}", icon="ℹ️")

    if details:
        st.caption(details)


# ===========================
# Confirmation Dialogs
# ===========================

@st.dialog("Confirm Action")
def show_confirmation_dialog(
    title: str,
    message: str,
    confirm_label: str = "Confirm",
    cancel_label: str = "Cancel",
    confirm_type: str = "primary",
    icon: str = "⚠️"
) -> bool:
    """
    Display a confirmation dialog (modal).

    Args:
        title: Dialog title
        message: Confirmation message
        confirm_label: Label for confirm button
        cancel_label: Label for cancel button
        confirm_type: Button type ("primary", "secondary")
        icon: Icon to display

    Returns:
        True if confirmed, False if cancelled

    Example:
        if show_confirmation_dialog(
            title="Delete Document",
            message="Are you sure you want to delete this document?",
            confirm_label="Delete",
            confirm_type="primary"
        ):
            delete_document()
    """
    st.markdown(f"### {icon} {title}")
    st.markdown(message)

    col1, col2 = st.columns(2)

    with col1:
        if st.button(cancel_label, key="cancel", use_container_width=True):
            st.rerun()
            return False

    with col2:
        if st.button(confirm_label, key="confirm", type=confirm_type, use_container_width=True):
            st.rerun()
            return True

    return False


def show_destructive_confirmation(
    action: str,
    item_name: str,
    consequences: Optional[List[str]] = None
) -> bool:
    """
    Display a confirmation dialog for destructive actions (delete, etc.).

    Args:
        action: Action being performed (e.g., "delete", "remove")
        item_name: Name of item being acted upon
        consequences: Optional list of consequences to display

    Returns:
        True if confirmed, False if cancelled

    Example:
        if show_destructive_confirmation(
            action="delete",
            item_name="Annual Report 2023",
            consequences=[
                "The document will be permanently removed",
                "All associated metadata will be deleted",
                "This action cannot be undone"
            ]
        ):
            delete_document()
    """
    st.warning(f"⚠️ **Are you sure you want to {action} '{item_name}'?**")

    if consequences:
        st.markdown("**This will:**")
        for consequence in consequences:
            st.markdown(f"- {consequence}")

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Cancel", key="cancel_destructive", use_container_width=True, type="secondary"):
            return False

    with col2:
        if st.button(
            f"{action.title()} Permanently",
            key="confirm_destructive",
            use_container_width=True,
            type="primary"
        ):
            return True

    return False


# ===========================
# Data Display Components
# ===========================

def show_metric_card(
    label: str,
    value: Any,
    delta: Optional[str] = None,
    delta_color: str = "normal",
    icon: Optional[str] = None,
    help_text: Optional[str] = None
) -> None:
    """
    Display a metric card with optional delta and icon.

    Args:
        label: Metric label
        value: Metric value
        delta: Optional change indicator
        delta_color: Color for delta ("normal", "inverse", "off")
        icon: Optional icon to display
        help_text: Optional help text tooltip

    Example:
        show_metric_card(
            label="Total Documents",
            value=142,
            delta="+12 this month",
            icon="📄"
        )
    """
    if icon:
        label = f"{icon} {label}"

    st.metric(
        label=label,
        value=value,
        delta=delta,
        delta_color=delta_color,
        help=help_text
    )


def show_status_badge(
    status: str,
    color_map: Optional[Dict[str, str]] = None
) -> None:
    """
    Display a colored status badge.

    Args:
        status: Status text
        color_map: Optional mapping of status to color

    Example:
        show_status_badge("awarded", color_map={
            "awarded": "green",
            "pending": "orange",
            "rejected": "red"
        })
    """
    default_colors = {
        "success": "green",
        "warning": "orange",
        "error": "red",
        "info": "blue",
        "draft": "gray",
        "pending": "orange",
        "awarded": "green",
        "rejected": "red",
        "active": "green",
        "inactive": "gray"
    }

    colors = color_map or default_colors
    color = colors.get(status.lower(), "blue")

    st.markdown(
        f'<span style="background-color: {color}; color: white; '
        f'padding: 4px 12px; border-radius: 12px; font-size: 14px; '
        f'font-weight: 500;">{status}</span>',
        unsafe_allow_html=True
    )


def show_empty_state(
    icon: str,
    title: str,
    description: str,
    action_label: Optional[str] = None,
    action_callback: Optional[Callable] = None
) -> None:
    """
    Display an empty state placeholder.

    Args:
        icon: Icon to display
        title: Empty state title
        description: Empty state description
        action_label: Optional action button label
        action_callback: Optional callback for action button

    Example:
        show_empty_state(
            icon="📄",
            title="No documents found",
            description="Upload your first document to get started",
            action_label="Upload Document",
            action_callback=lambda: st.switch_page("pages/upload.py")
        )
    """
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown(
            f"""
            <div style="text-align: center; padding: 60px 20px;">
                <div style="font-size: 64px; margin-bottom: 20px;">{icon}</div>
                <h3>{title}</h3>
                <p style="color: gray; margin-bottom: 30px;">{description}</p>
            </div>
            """,
            unsafe_allow_html=True
        )

        if action_label and action_callback:
            if st.button(action_label, use_container_width=True, type="primary"):
                action_callback()


# ===========================
# Form Components
# ===========================

def show_form_field(
    label: str,
    field_type: str = "text",
    key: str = None,
    default_value: Any = None,
    placeholder: str = "",
    help_text: Optional[str] = None,
    required: bool = False,
    options: Optional[List] = None,
    **kwargs
) -> Any:
    """
    Display a form field with consistent styling.

    Args:
        label: Field label
        field_type: Type of field ("text", "number", "select", "multiselect", "textarea", "date")
        key: Unique key for the field
        default_value: Default value
        placeholder: Placeholder text
        help_text: Optional help text
        required: Whether field is required
        options: Options for select/multiselect fields
        **kwargs: Additional arguments passed to Streamlit input function

    Returns:
        Field value

    Example:
        email = show_form_field(
            label="Email Address",
            field_type="text",
            key="email",
            placeholder="your.email@org.com",
            required=True
        )
    """
    full_label = f"{label} *" if required else label

    if field_type == "text":
        return st.text_input(full_label, value=default_value or "", placeholder=placeholder, help=help_text, key=key, **kwargs)
    elif field_type == "number":
        return st.number_input(full_label, value=default_value, help=help_text, key=key, **kwargs)
    elif field_type == "select":
        return st.selectbox(full_label, options=options or [], index=0, help=help_text, key=key, **kwargs)
    elif field_type == "multiselect":
        return st.multiselect(full_label, options=options or [], default=default_value, help=help_text, key=key, **kwargs)
    elif field_type == "textarea":
        return st.text_area(full_label, value=default_value or "", placeholder=placeholder, help=help_text, key=key, **kwargs)
    elif field_type == "date":
        return st.date_input(full_label, value=default_value, help=help_text, key=key, **kwargs)
    elif field_type == "checkbox":
        return st.checkbox(full_label, value=default_value or False, help=help_text, key=key, **kwargs)
    else:
        return st.text_input(full_label, value=default_value or "", placeholder=placeholder, help=help_text, key=key, **kwargs)


# ===========================
# Toast Notifications
# ===========================

def show_toast(
    message: str,
    icon: Optional[str] = None,
    duration: int = 3
) -> None:
    """
    Display a toast notification (temporary message).

    Args:
        message: Toast message
        icon: Optional icon
        duration: Duration in seconds (Streamlit default is 3)

    Example:
        show_toast("Document saved successfully!", icon="✅")
    """
    if icon:
        message = f"{icon} {message}"

    st.toast(message)


# ===========================
# Helper Functions
# ===========================

def create_download_button(
    data: Any,
    filename: str,
    label: str = "Download",
    mime_type: str = "text/plain",
    icon: str = "⬇️",
    **kwargs
) -> bool:
    """
    Create a styled download button.

    Args:
        data: Data to download
        filename: Filename for download
        label: Button label
        mime_type: MIME type of data
        icon: Icon to display
        **kwargs: Additional arguments for download_button

    Returns:
        True if button was clicked

    Example:
        create_download_button(
            data=csv_data,
            filename="export.csv",
            label="Export to CSV",
            mime_type="text/csv"
        )
    """
    return st.download_button(
        label=f"{icon} {label}",
        data=data,
        file_name=filename,
        mime=mime_type,
        **kwargs
    )


def show_divider(label: Optional[str] = None) -> None:
    """
    Display a horizontal divider with optional label.

    Args:
        label: Optional label for the divider

    Example:
        show_divider("Settings")
    """
    if label:
        st.divider()
        st.markdown(f"**{label}**")
    else:
        st.divider()


def show_help_tooltip(text: str, icon: str = "❓") -> None:
    """
    Display an inline help tooltip.

    Args:
        text: Help text
        icon: Icon to display

    Example:
        st.write("Field name")
        show_help_tooltip("Enter a unique identifier for this field")
    """
    st.caption(f"{icon} {text}")


def show_code_block(code: str, language: str = "python", line_numbers: bool = False) -> None:
    """
    Display a formatted code block.

    Args:
        code: Code to display
        language: Programming language for syntax highlighting
        line_numbers: Whether to show line numbers

    Example:
        show_code_block(
            code="def hello():\\n    print('Hello!')",
            language="python",
            line_numbers=True
        )
    """
    st.code(code, language=language, line_numbers=line_numbers)


# ===========================
# Document Metadata Form
# ===========================

def show_document_metadata_form(
    form_key: str = "document_metadata_form",
    apply_to_all: bool = True,
    default_values: Optional[Dict[str, Any]] = None
) -> Optional[Dict[str, Any]]:
    """
    Display a document metadata collection form with validation.

    This form collects all required metadata for document uploads including:
    - Document type (dropdown)
    - Year (number input)
    - Programs (multi-select)
    - Outcome (dropdown)
    - Tags (text area)
    - Notes (text area)
    - Sensitivity confirmation (checkbox)

    Args:
        form_key: Unique key for the form (required for multiple forms on same page)
        apply_to_all: Show caption indicating metadata applies to all files
        default_values: Optional dict with default values for form fields

    Returns:
        Dictionary with form data if submitted and valid, None otherwise
        Form data structure:
        {
            "type": str,
            "year": int,
            "programs": List[str],
            "outcome": str or None,
            "tags": List[str],
            "notes": str,
            "sensitivity_confirmed": bool
        }

    Example:
        >>> metadata = show_document_metadata_form(
        ...     form_key="upload_form",
        ...     apply_to_all=True
        ... )
        >>> if metadata:
        ...     # Process the metadata
        ...     upload_document(file, metadata)
    """
    # Default values
    defaults = default_values or {}

    st.markdown("#### Document Metadata")
    if apply_to_all:
        st.caption("This metadata will be applied to all uploaded files")

    with st.form(form_key):
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
                index=defaults.get("type_index", 0),
                help="Select the type of document you're uploading"
            )

            year = st.number_input(
                "Year *",
                min_value=1990,
                max_value=datetime.now().year + 5,
                value=defaults.get("year", datetime.now().year),
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
                default=defaults.get("programs", None),
                help="Select all programs that apply to this document"
            )

            outcome = st.selectbox(
                "Outcome (for grants/proposals)",
                options=["N/A", "Funded", "Not Funded", "Pending"],
                index=defaults.get("outcome_index", 0),
                help="If this is a grant or proposal, indicate the outcome"
            )

        # Tags
        tags_input = st.text_area(
            "Tags (optional)",
            value=defaults.get("tags_input", ""),
            placeholder="Enter tags separated by commas (e.g., literacy, STEM, youth)",
            help="Add descriptive tags to help organize and find this document",
            height=80
        )

        # Notes
        notes = st.text_area(
            "Notes (optional)",
            value=defaults.get("notes", ""),
            placeholder="Add any additional notes about this document...",
            help="Optional notes or context about this document",
            height=100
        )

        # Sensitivity confirmation checkbox
        st.markdown("---")
        sensitivity_confirmed = st.checkbox(
            "✅ I confirm that these documents are public-facing and appropriate for AI processing",
            value=defaults.get("sensitivity_confirmed", False),
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

        # Validation and return
        if submit_button:
            # Validation
            validation_errors = []

            if not sensitivity_confirmed:
                validation_errors.append("Please confirm that the documents are appropriate for upload.")

            if not programs:
                validation_errors.append("Please select at least one program.")

            # Show validation errors
            if validation_errors:
                for error in validation_errors:
                    st.error(f"❌ {error}")
                return None

            # Parse tags
            tags = [tag.strip() for tag in tags_input.split(",") if tag.strip()] if tags_input else []

            # Return validated metadata
            return {
                "type": document_type,
                "year": year,
                "programs": programs,
                "outcome": outcome if outcome != "N/A" else None,
                "tags": tags,
                "notes": notes,
                "sensitivity_confirmed": sensitivity_confirmed
            }

    return None
