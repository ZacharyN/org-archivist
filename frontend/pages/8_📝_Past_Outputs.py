"""
Past Outputs Dashboard

This page displays all AI-generated outputs with filtering, search, and pagination.
Users can view past outputs, track success rates, and manage generated content.
"""

import streamlit as st
import sys
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import pandas as pd
import plotly.graph_objects as go
from dateutil import parser as date_parser

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, AuthenticationError, ValidationError
from components.auth import require_auth
from config.settings import settings

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Past Outputs - Org Archivist",
    page_icon="📝",
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

    /* Output cards */
    .output-card {
        border: 1px solid #e0e0e0;
        border-radius: 8px;
        padding: 1.5rem;
        margin: 1rem 0;
        background-color: #ffffff;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: box-shadow 0.3s ease;
    }

    .output-card:hover {
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }

    .output-title {
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 0.5rem;
        color: #1f2937;
    }

    .output-meta {
        font-size: 0.9rem;
        color: #6b7280;
        margin: 0.25rem 0;
    }

    .status-badge {
        display: inline-block;
        padding: 0.25rem 0.75rem;
        border-radius: 12px;
        font-size: 0.85rem;
        font-weight: 500;
    }

    .status-awarded {
        background-color: #d1fae5;
        color: #065f46;
    }

    .status-not-awarded {
        background-color: #fee2e2;
        color: #991b1b;
    }

    .status-pending {
        background-color: #fef3c7;
        color: #92400e;
    }

    .status-draft {
        background-color: #e5e7eb;
        color: #374151;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'outputs_page' not in st.session_state:
        st.session_state.outputs_page = 0
    if 'outputs_per_page' not in st.session_state:
        st.session_state.outputs_per_page = 25
    if 'outputs_view_mode' not in st.session_state:
        st.session_state.outputs_view_mode = 'table'  # 'table' or 'cards'
    if 'selected_output_id' not in st.session_state:
        st.session_state.selected_output_id = None


def format_currency(amount: Optional[float]) -> str:
    """Format currency value for display."""
    if amount is None or amount == 0:
        return "N/A"
    return f"${amount:,.2f}"


def format_date(date_str: Optional[str]) -> str:
    """Format date string for display."""
    if not date_str:
        return "N/A"
    try:
        dt = date_parser.parse(date_str)
        return dt.strftime('%Y-%m-%d')
    except:
        return date_str


def format_datetime(datetime_str: Optional[str]) -> str:
    """Format datetime string for display."""
    if not datetime_str:
        return "N/A"
    try:
        dt = date_parser.parse(datetime_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except:
        return datetime_str


def get_status_badge_html(status: str) -> str:
    """Generate HTML for status badge."""
    status_classes = {
        'awarded': 'status-awarded',
        'not_awarded': 'status-not-awarded',
        'pending': 'status-pending',
        'draft': 'status-draft',
        'submitted': 'status-pending'
    }

    status_labels = {
        'awarded': '✅ Awarded',
        'not_awarded': '❌ Not Awarded',
        'pending': '⏳ Pending',
        'draft': '📄 Draft',
        'submitted': '📤 Submitted'
    }

    status_lower = status.lower() if status else 'draft'
    css_class = status_classes.get(status_lower, 'status-draft')
    label = status_labels.get(status_lower, status)

    return f'<span class="status-badge {css_class}">{label}</span>'


def show_outputs_list():
    """Display the outputs list with filtering and pagination."""
    st.title("📝 Past Outputs")
    st.markdown("View and manage all AI-generated outputs")

    client = get_api_client()

    # Create tabs
    tab1, tab2 = st.tabs(["📚 Outputs Library", "📊 Statistics"])

    with tab1:
        show_outputs_library(client)

    with tab2:
        show_outputs_statistics(client)


def show_outputs_library(client):
    """Display the main outputs library with filters and search."""

    # Fetch all outputs
    try:
        with st.spinner("Loading outputs..."):
            all_outputs = client.get_outputs(limit=1000)

        if not all_outputs:
            st.info("📭 No outputs found. Start a conversation in the AI Assistant to generate content!")
            return

    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
        return
    except APIError as e:
        st.error(f"❌ Error loading outputs: {e.message}")
        return
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Error loading outputs: {e}", exc_info=True)
        return

    # Search and Filters Section
    st.markdown("#### 🔍 Search & Filters")

    col1, col2 = st.columns([2, 1])

    with col1:
        search_query = st.text_input(
            "Search outputs",
            placeholder="Search by title or content...",
            label_visibility="collapsed",
            key="output_search"
        )

    with col2:
        show_filters = st.checkbox("Show Advanced Filters", value=False)

    # Advanced Filters
    filter_type = None
    filter_status = None
    filter_funder = None
    date_range = None

    if show_filters:
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            # Get unique output types
            unique_types = sorted(list(set([
                output.get("output_type", "")
                for output in all_outputs
                if output.get("output_type")
            ])))
            filter_type = st.multiselect(
                "Output Type",
                options=unique_types,
                key="filter_output_type"
            )

        with col2:
            # Get unique statuses
            unique_statuses = sorted(list(set([
                output.get("status", "")
                for output in all_outputs
                if output.get("status")
            ])))
            filter_status = st.multiselect(
                "Status",
                options=unique_statuses,
                key="filter_status"
            )

        with col3:
            # Get unique funders
            unique_funders = sorted(list(set([
                output.get("funder_name", "")
                for output in all_outputs
                if output.get("funder_name")
            ])))
            filter_funder = st.multiselect(
                "Funder",
                options=unique_funders,
                key="filter_funder"
            )

        with col4:
            # Date range filter
            st.markdown("Date Range")
            date_from = st.date_input(
                "From",
                value=None,
                key="date_from",
                label_visibility="collapsed"
            )
            date_to = st.date_input(
                "To",
                value=None,
                key="date_to",
                label_visibility="collapsed"
            )
            if date_from or date_to:
                date_range = (date_from, date_to)

    # Apply filters
    filtered_outputs = apply_filters(
        all_outputs,
        search_query,
        filter_type,
        filter_status,
        filter_funder,
        date_range
    )

    # Display summary metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Outputs", len(all_outputs))
    with col2:
        st.metric("Filtered Results", len(filtered_outputs))
    with col3:
        awarded_count = sum(1 for o in filtered_outputs if o.get("status", "").lower() == "awarded")
        st.metric("Awarded", awarded_count)
    with col4:
        total_awarded = sum(o.get("awarded_amount", 0) or 0 for o in filtered_outputs if o.get("status", "").lower() == "awarded")
        st.metric("Total Awarded", format_currency(total_awarded))

    st.markdown("---")

    if not filtered_outputs:
        st.warning("No outputs match your search criteria. Try adjusting your filters.")
        return

    # View mode selection
    col1, col2 = st.columns([4, 1])
    with col2:
        view_mode = st.radio(
            "View",
            options=['Table', 'Cards'],
            horizontal=True,
            label_visibility="collapsed",
            key="view_mode_selector"
        )
        st.session_state.outputs_view_mode = view_mode.lower()

    # Display based on view mode
    if st.session_state.outputs_view_mode == 'table':
        show_outputs_table(filtered_outputs)
    else:
        show_outputs_cards(filtered_outputs)


def apply_filters(
    outputs: List[Dict[str, Any]],
    search_query: Optional[str],
    filter_type: Optional[List[str]],
    filter_status: Optional[List[str]],
    filter_funder: Optional[List[str]],
    date_range: Optional[tuple]
) -> List[Dict[str, Any]]:
    """Apply all filters to the outputs list."""
    filtered = outputs

    # Search filter
    if search_query:
        search_lower = search_query.lower()
        filtered = [
            output for output in filtered
            if search_lower in output.get('title', '').lower()
            or search_lower in output.get('content', '').lower()
        ]

    # Type filter
    if filter_type:
        filtered = [
            output for output in filtered
            if output.get('output_type') in filter_type
        ]

    # Status filter
    if filter_status:
        filtered = [
            output for output in filtered
            if output.get('status') in filter_status
        ]

    # Funder filter
    if filter_funder:
        filtered = [
            output for output in filtered
            if output.get('funder_name') in filter_funder
        ]

    # Date range filter
    if date_range and (date_range[0] or date_range[1]):
        date_from, date_to = date_range
        filtered_by_date = []

        for output in filtered:
            created_at = output.get('created_at')
            if not created_at:
                continue

            try:
                output_date = date_parser.parse(created_at).date()

                if date_from and date_to:
                    if date_from <= output_date <= date_to:
                        filtered_by_date.append(output)
                elif date_from:
                    if output_date >= date_from:
                        filtered_by_date.append(output)
                elif date_to:
                    if output_date <= date_to:
                        filtered_by_date.append(output)
            except:
                continue

        filtered = filtered_by_date

    return filtered


def show_outputs_table(outputs: List[Dict[str, Any]]):
    """Display outputs in a table format with pagination."""

    # Prepare data for dataframe
    table_data = []
    for output in outputs:
        # Format status
        status = output.get('status', 'draft')
        status_display = {
            'awarded': '✅ Awarded',
            'not_awarded': '❌ Not Awarded',
            'pending': '⏳ Pending',
            'draft': '📄 Draft',
            'submitted': '📤 Submitted'
        }.get(status.lower() if status else 'draft', status)

        table_data.append({
            'Title': output.get('title', 'Untitled')[:50] + ('...' if len(output.get('title', '')) > 50 else ''),
            'Type': output.get('output_type', 'N/A'),
            'Status': status_display,
            'Funder': output.get('funder_name', 'N/A'),
            'Requested': format_currency(output.get('requested_amount')),
            'Awarded': format_currency(output.get('awarded_amount')),
            'Date': format_datetime(output.get('created_at')),
            'Words': output.get('word_count', 0),
            'output_id': output.get('output_id', '')
        })

    df = pd.DataFrame(table_data)

    # Pagination controls
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

    with col1:
        per_page = st.selectbox(
            "Rows per page",
            options=[10, 25, 50, 100],
            index=[10, 25, 50, 100].index(st.session_state.outputs_per_page),
            key="outputs_per_page_select"
        )
        if per_page != st.session_state.outputs_per_page:
            st.session_state.outputs_per_page = per_page
            st.session_state.outputs_page = 0
            st.rerun()

    total_pages = (len(df) - 1) // st.session_state.outputs_per_page + 1 if len(df) > 0 else 1
    current_page = min(st.session_state.outputs_page, total_pages - 1)

    with col2:
        if st.button("⏮️ First", disabled=current_page == 0, key="first_page"):
            st.session_state.outputs_page = 0
            st.rerun()

    with col3:
        if st.button("⏭️ Last", disabled=current_page >= total_pages - 1, key="last_page"):
            st.session_state.outputs_page = total_pages - 1
            st.rerun()

    with col4:
        st.text(f"Page {current_page + 1} of {total_pages}")

    # Calculate pagination
    start_idx = current_page * st.session_state.outputs_per_page
    end_idx = min(start_idx + st.session_state.outputs_per_page, len(df))

    # Display paginated dataframe
    display_df = df.iloc[start_idx:end_idx].copy()
    display_df_for_table = display_df.drop(columns=['output_id'])

    st.markdown(f"**Showing {start_idx + 1}-{end_idx} of {len(df)} outputs**")

    st.dataframe(
        display_df_for_table,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Title": st.column_config.TextColumn("Title", width="large"),
            "Type": st.column_config.TextColumn("Type", width="small"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Funder": st.column_config.TextColumn("Funder", width="medium"),
            "Requested": st.column_config.TextColumn("Requested", width="small"),
            "Awarded": st.column_config.TextColumn("Awarded", width="small"),
            "Date": st.column_config.TextColumn("Date", width="medium"),
            "Words": st.column_config.NumberColumn("Words", width="small"),
        }
    )

    # Pagination buttons at bottom
    st.markdown("---")
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

    with col2:
        if st.button("⬅️ Previous", disabled=current_page == 0, key="prev_page_bottom"):
            st.session_state.outputs_page = max(0, current_page - 1)
            st.rerun()

    with col3:
        st.text(f"Page {current_page + 1}/{total_pages}")

    with col4:
        if st.button("Next ➡️", disabled=current_page >= total_pages - 1, key="next_page_bottom"):
            st.session_state.outputs_page = min(total_pages - 1, current_page + 1)
            st.rerun()


def show_outputs_cards(outputs: List[Dict[str, Any]]):
    """Display outputs in a card format."""

    # Pagination
    per_page = st.session_state.outputs_per_page
    current_page = st.session_state.outputs_page
    total_pages = (len(outputs) - 1) // per_page + 1 if len(outputs) > 0 else 1
    current_page = min(current_page, total_pages - 1)

    start_idx = current_page * per_page
    end_idx = min(start_idx + per_page, len(outputs))

    st.markdown(f"**Showing {start_idx + 1}-{end_idx} of {len(outputs)} outputs**")

    # Display outputs as cards
    for output in outputs[start_idx:end_idx]:
        title = output.get('title', 'Untitled Output')
        output_type = output.get('output_type', 'N/A')
        status = output.get('status', 'draft')
        funder = output.get('funder_name', 'N/A')
        requested = output.get('requested_amount')
        awarded = output.get('awarded_amount')
        created_at = format_datetime(output.get('created_at'))
        word_count = output.get('word_count', 0)

        # Create card
        with st.container():
            col1, col2 = st.columns([4, 1])

            with col1:
                st.markdown(f"<div class='output-title'>{title}</div>", unsafe_allow_html=True)
                st.markdown(f"<div class='output-meta'>📄 {output_type} • 📅 {created_at} • 📝 {word_count} words</div>", unsafe_allow_html=True)

                if funder != 'N/A':
                    st.markdown(f"<div class='output-meta'>🏛️ Funder: {funder}</div>", unsafe_allow_html=True)

                if requested:
                    st.markdown(f"<div class='output-meta'>💰 Requested: {format_currency(requested)}</div>", unsafe_allow_html=True)

                if awarded and status.lower() == 'awarded':
                    st.markdown(f"<div class='output-meta'>✅ Awarded: {format_currency(awarded)}</div>", unsafe_allow_html=True)

            with col2:
                st.markdown(get_status_badge_html(status), unsafe_allow_html=True)
                st.markdown("<br>", unsafe_allow_html=True)

                if st.button("View Details", key=f"view_{output.get('output_id')}", use_container_width=True):
                    st.session_state.selected_output_id = output.get('output_id')
                    st.rerun()

        st.markdown("---")

    # Pagination controls
    col1, col2, col3, col4, col5 = st.columns([1, 1, 1, 1, 1])

    with col2:
        if st.button("⬅️ Previous", disabled=current_page == 0, key="prev_cards"):
            st.session_state.outputs_page = max(0, current_page - 1)
            st.rerun()

    with col3:
        st.text(f"Page {current_page + 1}/{total_pages}")

    with col4:
        if st.button("Next ➡️", disabled=current_page >= total_pages - 1, key="next_cards"):
            st.session_state.outputs_page = min(total_pages - 1, current_page + 1)
            st.rerun()


def show_outputs_statistics(client):
    """Display statistics about past outputs."""
    st.markdown("### 📊 Outputs Statistics")
    st.markdown("Overview of your generated outputs")

    try:
        with st.spinner("Loading statistics..."):
            all_outputs = client.get_outputs(limit=1000)

        if not all_outputs:
            st.info("📭 No outputs available for statistics.")
            return

        # Summary metrics
        st.markdown("#### 📈 Summary Metrics")
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric("Total Outputs", len(all_outputs))

        with col2:
            awarded_count = sum(1 for o in all_outputs if o.get("status", "").lower() == "awarded")
            st.metric("Awarded", awarded_count)

        with col3:
            total_requested = sum(o.get("requested_amount", 0) or 0 for o in all_outputs)
            st.metric("Total Requested", format_currency(total_requested))

        with col4:
            total_awarded = sum(o.get("awarded_amount", 0) or 0 for o in all_outputs if o.get("status", "").lower() == "awarded")
            st.metric("Total Awarded", format_currency(total_awarded))

        st.markdown("---")

        # Charts
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 📊 Distribution by Type")
            type_counts = {}
            for output in all_outputs:
                output_type = output.get('output_type', 'Unknown')
                type_counts[output_type] = type_counts.get(output_type, 0) + 1

            if type_counts:
                fig_type = go.Figure(data=[go.Pie(
                    labels=list(type_counts.keys()),
                    values=list(type_counts.values()),
                    hole=0.3,
                    marker=dict(
                        colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
                    )
                )])

                fig_type.update_layout(
                    showlegend=True,
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20)
                )

                st.plotly_chart(fig_type, use_container_width=True)

        with col2:
            st.markdown("#### ✅ Distribution by Status")
            status_counts = {}
            for output in all_outputs:
                status = output.get('status', 'draft')
                status_counts[status] = status_counts.get(status, 0) + 1

            if status_counts:
                fig_status = go.Figure(data=[go.Bar(
                    x=list(status_counts.keys()),
                    y=list(status_counts.values()),
                    marker=dict(
                        color=list(status_counts.values()),
                        colorscale='Viridis',
                        showscale=False
                    ),
                    text=list(status_counts.values()),
                    textposition='auto',
                )])

                fig_status.update_layout(
                    xaxis_title="Status",
                    yaxis_title="Count",
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    showlegend=False
                )

                st.plotly_chart(fig_status, use_container_width=True)

        # Success rate
        st.markdown("---")
        st.markdown("#### 📈 Success Rate")

        grants_proposals = [o for o in all_outputs if o.get('output_type') in ['grant', 'proposal']]
        if grants_proposals:
            submitted = [o for o in grants_proposals if o.get('status') in ['awarded', 'not_awarded']]
            awarded = [o for o in submitted if o.get('status') == 'awarded']

            if submitted:
                success_rate = (len(awarded) / len(submitted)) * 100

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Submitted", len(submitted))
                with col2:
                    st.metric("Awarded", len(awarded))
                with col3:
                    st.metric("Success Rate", f"{success_rate:.1f}%")

    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
    except APIError as e:
        st.error(f"❌ Error loading statistics: {e.message}")
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Error in outputs statistics: {e}", exc_info=True)


def main():
    """Main entry point for the past outputs page."""
    # Require authentication
    require_auth()

    # Initialize session state
    init_session_state()

    # Show outputs list
    show_outputs_list()


if __name__ == "__main__":
    main()
