"""
Writing Styles List and Management Page

This page displays all writing styles with filtering, search, and management capabilities.
Users can view, activate/deactivate, edit, and delete writing styles.
"""

import streamlit as st
import sys
from pathlib import Path
import logging
import time
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, AuthenticationError, ValidationError
from components.auth import require_auth
from components.ui import (
    show_loading_spinner,
    show_error_message,
    show_success_message,
    show_warning_message,
    show_empty_state,
    show_status_badge
)
from config.settings import settings

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Writing Styles - Org Archivist",
    page_icon="✍️",
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

    /* Style card styling */
    .style-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1rem;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        transition: box-shadow 0.2s;
    }

    .style-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.1);
    }

    .style-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }

    .style-card-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #1f2937;
        margin: 0;
    }

    .style-card-meta {
        font-size: 0.9rem;
        color: #6b7280;
        margin: 0.25rem 0;
    }

    .style-type-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
        margin-right: 8px;
    }

    .style-type-grant {
        background-color: #dbeafe;
        color: #1e40af;
    }

    .style-type-proposal {
        background-color: #e0e7ff;
        color: #4338ca;
    }

    .style-type-report {
        background-color: #ddd6fe;
        color: #6d28d9;
    }

    .status-active {
        color: #059669;
        font-weight: 500;
    }

    .status-inactive {
        color: #9ca3af;
        font-weight: 500;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'styles_view_mode' not in st.session_state:
        st.session_state.styles_view_mode = 'cards'
    if 'delete_style_id' not in st.session_state:
        st.session_state.delete_style_id = None
    if 'toggle_style_id' not in st.session_state:
        st.session_state.toggle_style_id = None


@st.dialog("Delete Writing Style")
def show_delete_confirmation_dialog(style: Dict[str, Any]):
    """
    Display a confirmation dialog for deleting a writing style.

    Args:
        style: Writing style to delete
    """
    st.warning("⚠️ Are you sure you want to delete this writing style?")

    st.markdown(f"**Name:** {style.get('name', 'Unknown')}")
    st.markdown(f"**Type:** {style.get('type', 'N/A')}")
    st.markdown(f"**Created:** {style.get('created_at', 'N/A')}")

    st.markdown("---")
    st.markdown("**This will:**")
    st.markdown("- Permanently remove the writing style from the database")
    st.markdown("- Make this style unavailable for future content generation")
    st.markdown("- **This action cannot be undone**")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Cancel", use_container_width=True):
            st.session_state.delete_style_id = None
            st.rerun()

    with col2:
        if st.button("Delete Permanently", type="primary", use_container_width=True):
            client = get_api_client()
            try:
                with st.spinner(f"Deleting {style.get('name')}..."):
                    client.delete_writing_style(style['style_id'])
                st.success(f"✅ Successfully deleted: {style.get('name')}")
                st.session_state.delete_style_id = None
                time.sleep(1)
                st.rerun()
            except APIError as e:
                st.error(f"❌ Failed to delete: {e.message}")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")


def render_style_card(style: Dict[str, Any], col_idx: int):
    """
    Render a single writing style card.

    Args:
        style: Writing style data
        col_idx: Column index for unique keys
    """
    # Get style data
    style_id = style.get('style_id', '')
    name = style.get('name', 'Unnamed Style')
    style_type = style.get('type', 'unknown').lower()
    description = style.get('description', '')
    active = style.get('active', True)
    created_at = style.get('created_at', '')
    sample_count = style.get('sample_count', 0)

    # Format created date
    try:
        from dateutil import parser
        dt = parser.parse(created_at)
        formatted_date = dt.strftime('%b %d, %Y')
    except:
        formatted_date = created_at

    # Type badge class
    type_class_map = {
        'grant': 'style-type-grant',
        'proposal': 'style-type-proposal',
        'report': 'style-type-report'
    }
    type_class = type_class_map.get(style_type, 'style-type-grant')

    # Render card
    with st.container():
        st.markdown(f"""
        <div class="style-card">
            <div class="style-card-header">
                <h3 class="style-card-title">{name}</h3>
            </div>
            <div>
                <span class="style-type-badge {type_class}">{style_type.title()}</span>
                <span class="{'status-active' if active else 'status-inactive'}">
                    {'● Active' if active else '○ Inactive'}
                </span>
            </div>
            <p class="style-card-meta">Created: {formatted_date} | {sample_count} sample(s)</p>
        </div>
        """, unsafe_allow_html=True)

        # Show description if available
        if description:
            with st.expander("📝 Description"):
                st.write(description)

        # Action buttons
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            view_button = st.button(
                "👁️ View",
                key=f"view_{style_id}_{col_idx}",
                use_container_width=True,
                help="View full style details"
            )
            if view_button:
                # Navigate to style details (to be implemented)
                st.info("View functionality will be implemented in the next phase")

        with col2:
            edit_button = st.button(
                "✏️ Edit",
                key=f"edit_{style_id}_{col_idx}",
                use_container_width=True,
                help="Edit this writing style"
            )
            if edit_button:
                # Navigate to edit page (to be implemented)
                st.info("Edit functionality will be implemented in the next phase")

        with col3:
            toggle_label = "🔴 Deactivate" if active else "🟢 Activate"
            toggle_button = st.button(
                toggle_label,
                key=f"toggle_{style_id}_{col_idx}",
                use_container_width=True,
                help=f"{'Deactivate' if active else 'Activate'} this style"
            )
            if toggle_button:
                toggle_writing_style(style)

        with col4:
            delete_button = st.button(
                "🗑️ Delete",
                key=f"delete_{style_id}_{col_idx}",
                use_container_width=True,
                type="secondary",
                help="Permanently delete this style"
            )
            if delete_button:
                st.session_state.delete_style_id = style_id
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)


def render_cards_view(styles: List[Dict[str, Any]]):
    """
    Render writing styles in card view.

    Args:
        styles: List of writing styles
    """
    # Display in grid (2 columns)
    num_cols = 2
    cols = st.columns(num_cols)

    for idx, style in enumerate(styles):
        col_idx = idx % num_cols
        with cols[col_idx]:
            render_style_card(style, idx)


def render_table_view(styles: List[Dict[str, Any]]):
    """
    Render writing styles in table view.

    Args:
        styles: List of writing styles
    """
    import pandas as pd

    table_data = []
    for style in styles:
        # Format created date
        created_at = style.get('created_at', '')
        try:
            from dateutil import parser
            dt = parser.parse(created_at)
            formatted_date = dt.strftime('%Y-%m-%d')
        except:
            formatted_date = created_at

        # Format active status
        active = style.get('active', True)
        status_display = "✅ Active" if active else "⭕ Inactive"

        table_data.append({
            'Name': style.get('name', 'Unnamed'),
            'Type': style.get('type', '').title(),
            'Status': status_display,
            'Samples': style.get('sample_count', 0),
            'Created': formatted_date,
            'style_id': style.get('style_id', '')  # Hidden but used for actions
        })

    df = pd.DataFrame(table_data)

    # Display dataframe
    st.dataframe(
        df.drop(columns=['style_id']),
        use_container_width=True,
        hide_index=True,
        column_config={
            "Name": st.column_config.TextColumn("Name", width="medium"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Samples": st.column_config.NumberColumn("Samples", width="small"),
            "Created": st.column_config.TextColumn("Created", width="small"),
        }
    )

    # Action section below table
    st.markdown("---")
    st.markdown("#### 🔧 Manage Writing Style")
    st.caption("Select a writing style from the table above to manage it")

    col1, col2 = st.columns([3, 1])
    with col1:
        style_names = [s.get('name', 'Unnamed') for s in styles]
        selected_name = st.selectbox(
            "Select writing style",
            options=[""] + style_names,
            index=0,
            key="manage_style_select"
        )

    if selected_name and selected_name != "":
        # Find selected style
        selected_style = next((s for s in styles if s.get('name') == selected_name), None)

        if selected_style:
            col1, col2, col3, col4 = st.columns(4)

            with col1:
                if st.button("👁️ View Details", use_container_width=True):
                    st.info("View functionality will be implemented in the next phase")

            with col2:
                if st.button("✏️ Edit Style", use_container_width=True):
                    st.info("Edit functionality will be implemented in the next phase")

            with col3:
                active = selected_style.get('active', True)
                toggle_label = "🔴 Deactivate" if active else "🟢 Activate"
                if st.button(toggle_label, use_container_width=True):
                    toggle_writing_style(selected_style)

            with col4:
                if st.button("🗑️ Delete", type="secondary", use_container_width=True):
                    st.session_state.delete_style_id = selected_style.get('style_id')
                    st.rerun()


def toggle_writing_style(style: Dict[str, Any]):
    """
    Toggle active status of a writing style.

    Args:
        style: Writing style to toggle
    """
    client = get_api_client()
    style_id = style.get('style_id')
    current_active = style.get('active', True)
    new_active = not current_active

    try:
        with st.spinner(f"{'Deactivating' if current_active else 'Activating'} {style.get('name')}..."):
            client.update_writing_style(style_id, {"active": new_active})

        action = "deactivated" if current_active else "activated"
        st.success(f"✅ Successfully {action}: {style.get('name')}")
        time.sleep(1)
        st.rerun()
    except APIError as e:
        st.error(f"❌ Failed to toggle status: {e.message}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")


def show_writing_styles_page():
    """Display the writing styles management page."""
    st.title("✍️ Writing Styles")
    st.markdown("Manage your organization's writing styles for AI-generated content")

    client = get_api_client()

    # View mode toggle
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("### Your Writing Styles")

    with col2:
        view_mode = st.selectbox(
            "View",
            options=["Cards", "Table"],
            index=0 if st.session_state.styles_view_mode == 'cards' else 1,
            key="view_mode_select",
            label_visibility="collapsed"
        )
        if view_mode.lower() != st.session_state.styles_view_mode:
            st.session_state.styles_view_mode = view_mode.lower()
            st.rerun()

    with col3:
        if st.button("➕ Create New Style", use_container_width=True, type="primary"):
            st.switch_page("pages/7.1_✍️_Create_Writing_Style.py")

    st.markdown("---")

    # Filters section
    st.markdown("#### 🔍 Filters")

    col1, col2, col3 = st.columns([2, 2, 2])

    with col1:
        search_query = st.text_input(
            "Search by name or description",
            placeholder="Search writing styles...",
            key="styles_search",
            label_visibility="collapsed"
        )

    with col2:
        filter_type = st.multiselect(
            "Filter by Type",
            options=["Grant", "Proposal", "Report"],
            key="filter_type",
            placeholder="All types"
        )

    with col3:
        filter_status = st.selectbox(
            "Filter by Status",
            options=["All", "Active Only", "Inactive Only"],
            index=1,  # Default to Active Only
            key="filter_status"
        )

    st.markdown("---")

    try:
        # Fetch writing styles
        with st.spinner("Loading writing styles..."):
            # Determine active_only parameter based on filter
            if filter_status == "All":
                all_styles = client.get_writing_styles(active_only=False)
            elif filter_status == "Active Only":
                all_styles = client.get_writing_styles(active_only=True)
            else:  # Inactive Only
                all_styles_unfiltered = client.get_writing_styles(active_only=False)
                all_styles = [s for s in all_styles_unfiltered if not s.get('active', True)]

        if not all_styles:
            show_empty_state(
                icon="✍️",
                title="No writing styles found",
                description="Create your first writing style to get started with AI-powered content generation",
                action_label="Create Writing Style",
                action_callback=lambda: st.info("This will navigate to the style creator")
            )
            return

        # Apply search filter
        filtered_styles = all_styles
        if search_query:
            search_lower = search_query.lower()
            filtered_styles = [
                style for style in filtered_styles
                if search_lower in style.get('name', '').lower()
                or search_lower in style.get('description', '').lower()
            ]

        # Apply type filter
        if filter_type:
            filter_type_lower = [t.lower() for t in filter_type]
            filtered_styles = [
                style for style in filtered_styles
                if style.get('type', '').lower() in filter_type_lower
            ]

        # Display stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Styles", len(all_styles))
        with col2:
            active_count = sum(1 for s in all_styles if s.get('active', True))
            st.metric("Active", active_count)
        with col3:
            inactive_count = len(all_styles) - active_count
            st.metric("Inactive", inactive_count)
        with col4:
            st.metric("Filtered Results", len(filtered_styles))

        st.markdown("---")

        if not filtered_styles:
            st.warning("No writing styles match your search criteria. Try adjusting your filters.")
            return

        # Render styles based on view mode
        if st.session_state.styles_view_mode == 'cards':
            render_cards_view(filtered_styles)
        else:
            render_table_view(filtered_styles)

    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
    except APIError as e:
        st.error(f"❌ Error loading writing styles: {e.message}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Error in writing styles page: {e}", exc_info=True)


def main():
    """Main entry point for the writing styles page."""
    # Require authentication
    require_auth()

    # Initialize session state
    init_session_state()

    # Handle delete confirmation dialog
    if st.session_state.delete_style_id:
        # Fetch the style to delete
        client = get_api_client()
        try:
            style = client.get_writing_style(st.session_state.delete_style_id)
            show_delete_confirmation_dialog(style)
        except Exception as e:
            st.error(f"Error loading style: {str(e)}")
            st.session_state.delete_style_id = None

    # Show main page
    show_writing_styles_page()


if __name__ == "__main__":
    main()
