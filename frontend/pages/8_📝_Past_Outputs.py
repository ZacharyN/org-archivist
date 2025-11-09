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
    """Display comprehensive statistics and analytics about past outputs."""
    st.markdown("### 📊 Outputs Analytics Dashboard")
    st.markdown("Comprehensive analytics and insights from your generated outputs")

    try:
        with st.spinner("Loading analytics..."):
            # Fetch comprehensive analytics
            analytics = client.get_analytics_summary()
            funder_performance = client.get_funder_performance(limit=10)

        overall = analytics.get('overall', {})
        top_styles = analytics.get('top_writing_styles', [])
        top_funders = analytics.get('top_funders', [])
        year_trends = analytics.get('year_over_year_trends', [])

        # Summary metrics row
        st.markdown("#### 📈 Overall Performance")
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            st.metric("Total Outputs", overall.get('total_outputs', 0))

        with col2:
            st.metric("Submitted", overall.get('submitted_count', 0))

        with col3:
            st.metric("Awarded", overall.get('awarded_count', 0))

        with col4:
            success_rate = overall.get('success_rate', 0)
            st.metric("Success Rate", f"{success_rate:.1f}%")

        with col5:
            total_awarded = overall.get('total_awarded', 0)
            st.metric("Total Awarded", format_currency(total_awarded))

        st.markdown("---")

        # Row 1: Success Rate by Writing Style and Funder
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 🎨 Success Rate by Writing Style")
            if top_styles:
                style_names = [f"Style {s['writing_style_id'][:8]}..." if s['writing_style_id'] else 'Unknown' for s in top_styles]
                success_rates = [s['success_rate'] for s in top_styles]
                submitted_counts = [s['submitted_count'] for s in top_styles]

                fig_styles = go.Figure()

                fig_styles.add_trace(go.Bar(
                    x=style_names,
                    y=success_rates,
                    text=[f"{rate:.1f}%" for rate in success_rates],
                    textposition='auto',
                    marker=dict(
                        color=success_rates,
                        colorscale='RdYlGn',
                        showscale=True,
                        colorbar=dict(title="Success Rate %")
                    ),
                    hovertemplate='<b>%{x}</b><br>Success Rate: %{y:.1f}%<br>Submitted: %{customdata}<extra></extra>',
                    customdata=submitted_counts
                ))

                fig_styles.update_layout(
                    xaxis_title="Writing Style",
                    yaxis_title="Success Rate (%)",
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    showlegend=False
                )

                st.plotly_chart(fig_styles, use_container_width=True)
            else:
                st.info("No writing style data available. Start using writing styles in your outputs!")

        with col2:
            st.markdown("#### 🏛️ Success Rate by Funder")
            if funder_performance:
                funder_names = [f['funder_name'] for f in funder_performance[:10]]
                funder_success_rates = [f['success_rate'] for f in funder_performance[:10]]
                funder_submissions = [f['total_submissions'] for f in funder_performance[:10]]

                fig_funders = go.Figure()

                fig_funders.add_trace(go.Bar(
                    x=funder_names,
                    y=funder_success_rates,
                    text=[f"{rate:.1f}%" for rate in funder_success_rates],
                    textposition='auto',
                    marker=dict(
                        color=funder_success_rates,
                        colorscale='Blues',
                        showscale=True,
                        colorbar=dict(title="Success Rate %")
                    ),
                    hovertemplate='<b>%{x}</b><br>Success Rate: %{y:.1f}%<br>Submissions: %{customdata}<extra></extra>',
                    customdata=funder_submissions
                ))

                fig_funders.update_layout(
                    xaxis_title="Funder",
                    yaxis_title="Success Rate (%)",
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    showlegend=False,
                    xaxis=dict(tickangle=-45)
                )

                st.plotly_chart(fig_funders, use_container_width=True)
            else:
                st.info("No funder data available. Start tracking funders in your outputs!")

        st.markdown("---")

        # Row 2: Award Amounts Over Time and Distribution by Type
        col1, col2 = st.columns(2)

        with col1:
            st.markdown("#### 💰 Award Amounts Over Time")
            if year_trends:
                years = [t['year'] for t in year_trends]
                awarded_amounts = [t['total_awarded'] for t in year_trends]
                success_rates_by_year = [t['success_rate'] for t in year_trends]

                fig_trends = go.Figure()

                # Award amounts (bars)
                fig_trends.add_trace(go.Bar(
                    name='Total Awarded',
                    x=years,
                    y=awarded_amounts,
                    text=[format_currency(amt) for amt in awarded_amounts],
                    textposition='auto',
                    marker=dict(color='#4ECDC4'),
                    yaxis='y'
                ))

                # Success rate (line)
                fig_trends.add_trace(go.Scatter(
                    name='Success Rate',
                    x=years,
                    y=success_rates_by_year,
                    mode='lines+markers',
                    line=dict(color='#FF6B6B', width=3),
                    marker=dict(size=10),
                    yaxis='y2',
                    hovertemplate='<b>%{x}</b><br>Success Rate: %{y:.1f}%<extra></extra>'
                ))

                fig_trends.update_layout(
                    xaxis_title="Year",
                    yaxis=dict(
                        title="Total Awarded ($)",
                        titlefont=dict(color="#4ECDC4"),
                        tickfont=dict(color="#4ECDC4")
                    ),
                    yaxis2=dict(
                        title="Success Rate (%)",
                        titlefont=dict(color="#FF6B6B"),
                        tickfont=dict(color="#FF6B6B"),
                        overlaying='y',
                        side='right'
                    ),
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    hovermode='x unified',
                    legend=dict(
                        orientation="h",
                        yanchor="bottom",
                        y=1.02,
                        xanchor="right",
                        x=1
                    )
                )

                st.plotly_chart(fig_trends, use_container_width=True)
            else:
                st.info("No historical data available. Start submitting outputs with dates!")

        with col2:
            st.markdown("#### 📊 Distribution by Type")
            if overall.get('by_type'):
                type_data = overall['by_type']

                fig_type = go.Figure(data=[go.Pie(
                    labels=list(type_data.keys()),
                    values=list(type_data.values()),
                    hole=0.4,
                    marker=dict(
                        colors=['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
                    ),
                    textinfo='label+percent',
                    hovertemplate='<b>%{label}</b><br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
                )])

                fig_type.update_layout(
                    height=400,
                    margin=dict(t=20, b=20, l=20, r=20),
                    showlegend=True,
                    legend=dict(
                        orientation="v",
                        yanchor="middle",
                        y=0.5,
                        xanchor="left",
                        x=1.02
                    )
                )

                st.plotly_chart(fig_type, use_container_width=True)
            else:
                st.info("No output type data available.")

        st.markdown("---")

        # Row 3: Detailed Funder Performance Table
        st.markdown("#### 📋 Detailed Funder Performance")
        if funder_performance:
            funder_df = pd.DataFrame([
                {
                    'Funder': f['funder_name'],
                    'Total Submissions': f['total_submissions'],
                    'Awarded': f['awarded_count'],
                    'Not Awarded': f['not_awarded_count'],
                    'Pending': f['pending_count'],
                    'Success Rate': f"{f['success_rate']:.1f}%",
                    'Total Requested': format_currency(f['total_requested']),
                    'Total Awarded': format_currency(f['total_awarded']),
                    'Avg Award': format_currency(f['avg_award_amount'])
                }
                for f in funder_performance
            ])

            st.dataframe(
                funder_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Funder": st.column_config.TextColumn("Funder", width="medium"),
                    "Total Submissions": st.column_config.NumberColumn("Total", width="small"),
                    "Awarded": st.column_config.NumberColumn("✅ Awarded", width="small"),
                    "Not Awarded": st.column_config.NumberColumn("❌ Rejected", width="small"),
                    "Pending": st.column_config.NumberColumn("⏳ Pending", width="small"),
                    "Success Rate": st.column_config.TextColumn("Success %", width="small"),
                    "Total Requested": st.column_config.TextColumn("Requested", width="small"),
                    "Total Awarded": st.column_config.TextColumn("Awarded", width="small"),
                    "Avg Award": st.column_config.TextColumn("Avg Award", width="small"),
                }
            )
        else:
            st.info("No funder performance data available.")

        st.markdown("---")

        # Row 4: Awards vs Requests Comparison
        st.markdown("#### 💵 Awards vs Requests Analysis")
        if overall.get('total_requested', 0) > 0:
            col1, col2, col3 = st.columns(3)

            total_requested = overall.get('total_requested', 0)
            total_awarded = overall.get('total_awarded', 0)
            award_rate = (total_awarded / total_requested * 100) if total_requested > 0 else 0

            with col1:
                st.metric(
                    "Total Requested",
                    format_currency(total_requested),
                    help="Total amount requested across all submissions"
                )

            with col2:
                st.metric(
                    "Total Awarded",
                    format_currency(total_awarded),
                    help="Total amount awarded"
                )

            with col3:
                st.metric(
                    "Award Rate",
                    f"{award_rate:.1f}%",
                    help="Percentage of requested amount that was awarded"
                )

            # Visual comparison
            fig_comparison = go.Figure()

            fig_comparison.add_trace(go.Bar(
                name='Requested',
                x=['Amount'],
                y=[total_requested],
                text=[format_currency(total_requested)],
                textposition='auto',
                marker=dict(color='#FFA07A')
            ))

            fig_comparison.add_trace(go.Bar(
                name='Awarded',
                x=['Amount'],
                y=[total_awarded],
                text=[format_currency(total_awarded)],
                textposition='auto',
                marker=dict(color='#4ECDC4')
            ))

            fig_comparison.update_layout(
                xaxis_title="",
                yaxis_title="Amount ($)",
                height=300,
                margin=dict(t=20, b=20, l=20, r=20),
                showlegend=True,
                barmode='group',
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1
                )
            )

            st.plotly_chart(fig_comparison, use_container_width=True)
        else:
            st.info("No financial data available. Start tracking requested and awarded amounts!")

    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
    except APIError as e:
        st.error(f"❌ Error loading analytics: {e.message}")
        logger.error(f"API error in analytics: {e}")
    except Exception as e:
        st.error(f"❌ Unexpected error loading analytics: {str(e)}")
        logger.error(f"Error in outputs analytics: {e}", exc_info=True)


def show_output_detail():
    """Display detailed view of a selected output."""
    output_id = st.session_state.selected_output_id

    if not output_id:
        st.error("No output selected")
        return

    client = get_api_client()

    # Back button at the top
    if st.button("⬅️ Back to Outputs List", key="back_to_list"):
        st.session_state.selected_output_id = None
        st.rerun()

    st.markdown("---")

    # Fetch full output data
    try:
        with st.spinner("Loading output details..."):
            output = client.get_output(output_id)
    except AuthenticationError:
        st.error("❌ Authentication required. Please log in.")
        return
    except APIError as e:
        st.error(f"❌ Error loading output: {e.message}")
        return
    except Exception as e:
        st.error(f"❌ Unexpected error: {str(e)}")
        logger.error(f"Error loading output {output_id}: {e}", exc_info=True)
        return

    # Create two-column layout: content on left, metadata on right
    col_content, col_meta = st.columns([2, 1])

    with col_content:
        # Title and basic info
        st.title(output.get('title', 'Untitled Output'))

        # Output type and status badges
        output_type = output.get('output_type', 'N/A')
        status = output.get('status', 'draft')

        badge_col1, badge_col2, badge_col3 = st.columns([1, 1, 2])
        with badge_col1:
            st.markdown(f"**Type:** {output_type}")
        with badge_col2:
            st.markdown(get_status_badge_html(status), unsafe_allow_html=True)

        st.markdown("---")

        # Get content for buttons
        content = output.get('content', '')

        # Action buttons
        btn_col1, btn_col2, btn_col3 = st.columns(3)

        with btn_col1:
            # Download as .txt
            st.download_button(
                label="📄 Download .txt",
                data=content,
                file_name=f"{output.get('title', 'output').replace(' ', '_')}.txt",
                mime="text/plain",
                key="download_txt",
                use_container_width=True
            )

        with btn_col2:
            # Download as .docx (placeholder - would need python-docx)
            st.button("📝 Download .docx", key="download_docx", disabled=True, use_container_width=True)

        with btn_col3:
            # Delete button (with confirmation)
            if st.button("🗑️ Delete", key="delete_output", use_container_width=True):
                st.session_state.confirm_delete = True

        if st.session_state.get('confirm_delete'):
            st.warning("⚠️ Are you sure you want to delete this output? This cannot be undone.")
            confirm_col1, confirm_col2 = st.columns(2)
            with confirm_col1:
                if st.button("Yes, Delete", key="confirm_delete_yes", type="primary"):
                    try:
                        client.delete_output(output_id)
                        st.success("✅ Output deleted successfully")
                        st.session_state.selected_output_id = None
                        st.session_state.confirm_delete = False
                        st.rerun()
                    except APIError as e:
                        st.error(f"❌ Error deleting output: {e.message}")
            with confirm_col2:
                if st.button("Cancel", key="confirm_delete_no"):
                    st.session_state.confirm_delete = False
                    st.rerun()

        st.markdown("---")

        # Display full content with formatting
        st.markdown("### 📄 Content")

        # Create tabs for different views
        content_tab1, content_tab2 = st.tabs(["📖 Formatted View", "📋 Raw Text (Copy-Friendly)"])

        with content_tab1:
            # Display content with formatting
            st.markdown(
                f"""
                <div style="
                    border: 1px solid #e0e0e0;
                    border-radius: 8px;
                    padding: 2rem;
                    background-color: #ffffff;
                    max-height: 600px;
                    overflow-y: auto;
                    line-height: 1.6;
                    white-space: pre-wrap;
                ">
                {content}
                </div>
                """,
                unsafe_allow_html=True
            )

        with content_tab2:
            # Display in text area for easy copying
            st.text_area(
                "Content",
                value=content,
                height=600,
                label_visibility="collapsed",
                key="content_text_area"
            )

    with col_meta:
        # Metadata sidebar
        st.markdown("### 📊 Metadata")

        # Success Tracking Form
        st.markdown("#### 🎯 Success Tracking")

        with st.expander("📝 Update Success Information", expanded=False):
            with st.form(key=f"success_tracking_form_{output_id}"):
                st.markdown("Update grant/proposal success tracking information:")

                # Status
                current_status = output.get('status', 'draft')
                status_options = ['draft', 'submitted', 'pending', 'awarded', 'not_awarded']
                status_index = status_options.index(current_status) if current_status in status_options else 0

                new_status = st.selectbox(
                    "Status",
                    options=status_options,
                    index=status_index,
                    format_func=lambda x: {
                        'draft': '📄 Draft',
                        'submitted': '📤 Submitted',
                        'pending': '⏳ Pending',
                        'awarded': '✅ Awarded',
                        'not_awarded': '❌ Not Awarded'
                    }.get(x, x),
                    key=f"status_{output_id}"
                )

                # Funder information
                st.markdown("**Funder Information:**")

                new_funder_name = st.text_input(
                    "Funder Name",
                    value=output.get('funder_name', ''),
                    key=f"funder_name_{output_id}"
                )

                col1, col2 = st.columns(2)
                with col1:
                    new_requested_amount = st.number_input(
                        "Requested Amount ($)",
                        min_value=0.0,
                        value=float(output.get('requested_amount') or 0.0),
                        step=1000.0,
                        format="%.2f",
                        key=f"requested_amount_{output_id}"
                    )

                with col2:
                    new_awarded_amount = st.number_input(
                        "Awarded Amount ($)",
                        min_value=0.0,
                        value=float(output.get('awarded_amount') or 0.0),
                        step=1000.0,
                        format="%.2f",
                        key=f"awarded_amount_{output_id}",
                        disabled=new_status not in ['awarded']
                    )

                # Dates
                st.markdown("**Important Dates:**")

                col1, col2 = st.columns(2)
                with col1:
                    current_submission_date = None
                    if output.get('submission_date'):
                        try:
                            current_submission_date = date_parser.parse(output.get('submission_date')).date()
                        except:
                            pass

                    new_submission_date = st.date_input(
                        "Submission Date",
                        value=current_submission_date,
                        key=f"submission_date_{output_id}"
                    )

                with col2:
                    current_decision_date = None
                    if output.get('decision_date'):
                        try:
                            current_decision_date = date_parser.parse(output.get('decision_date')).date()
                        except:
                            pass

                    new_decision_date = st.date_input(
                        "Decision Date",
                        value=current_decision_date,
                        key=f"decision_date_{output_id}",
                        disabled=new_status not in ['awarded', 'not_awarded']
                    )

                # Success notes
                new_success_notes = st.text_area(
                    "Success Notes",
                    value=output.get('success_notes', ''),
                    height=150,
                    help="Add notes about the outcome, what worked well, lessons learned, etc.",
                    key=f"success_notes_{output_id}"
                )

                # Submit button
                submitted = st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True)

                if submitted:
                    # Prepare update data
                    update_data = {
                        'status': new_status,
                        'funder_name': new_funder_name if new_funder_name else None,
                        'requested_amount': new_requested_amount if new_requested_amount > 0 else None,
                        'awarded_amount': new_awarded_amount if new_awarded_amount > 0 and new_status == 'awarded' else None,
                        'submission_date': new_submission_date.isoformat() if new_submission_date else None,
                        'decision_date': new_decision_date.isoformat() if new_decision_date and new_status in ['awarded', 'not_awarded'] else None,
                        'success_notes': new_success_notes if new_success_notes else None
                    }

                    try:
                        with st.spinner("Updating output..."):
                            client.update_output(output_id, update_data)
                        st.success("✅ Success tracking information updated!")
                        st.rerun()
                    except ValidationError as e:
                        st.error(f"❌ Validation error: {e.message}")
                    except APIError as e:
                        st.error(f"❌ Error updating output: {e.message}")
                    except Exception as e:
                        st.error(f"❌ Unexpected error: {str(e)}")
                        logger.error(f"Error updating output {output_id}: {e}", exc_info=True)

        st.markdown("---")

        # Word count
        word_count = output.get('word_count', 0)
        st.metric("Word Count", f"{word_count:,}")

        st.markdown("---")

        # Dates
        st.markdown("#### 📅 Dates")
        created_at = format_datetime(output.get('created_at'))
        updated_at = format_datetime(output.get('updated_at'))

        st.markdown(f"**Created:** {created_at}")
        st.markdown(f"**Updated:** {updated_at}")

        if output.get('submission_date'):
            submission_date = format_date(output.get('submission_date'))
            st.markdown(f"**Submitted:** {submission_date}")

        if output.get('decision_date'):
            decision_date = format_date(output.get('decision_date'))
            st.markdown(f"**Decision:** {decision_date}")

        st.markdown("---")

        # Writing style
        if output.get('writing_style_id'):
            st.markdown("#### ✍️ Writing Style")
            st.markdown(f"Style ID: `{output.get('writing_style_id')[:8]}...`")

        st.markdown("---")

        # Funder information
        if output.get('funder_name'):
            st.markdown("#### 🏛️ Funder Information")
            st.markdown(f"**Funder:** {output.get('funder_name')}")

            if output.get('requested_amount'):
                st.markdown(f"**Requested:** {format_currency(output.get('requested_amount'))}")

            if output.get('awarded_amount') and status.lower() == 'awarded':
                st.markdown(f"**Awarded:** {format_currency(output.get('awarded_amount'))}")

        st.markdown("---")

        # Status timeline
        st.markdown("#### 📈 Status Timeline")

        # Show status progression
        statuses = ['draft', 'submitted', 'pending', 'awarded' if status.lower() == 'awarded' else 'not_awarded']
        current_status = status.lower()

        for idx, timeline_status in enumerate(statuses):
            if timeline_status == current_status:
                st.markdown(f"✅ **{timeline_status.replace('_', ' ').title()}** (Current)")
                break
            elif statuses.index(current_status) > idx:
                st.markdown(f"✅ {timeline_status.replace('_', ' ').title()}")
            else:
                st.markdown(f"⭕ {timeline_status.replace('_', ' ').title()}")

        st.markdown("---")

        # Success notes
        if output.get('success_notes'):
            st.markdown("#### 📝 Notes")
            st.text_area(
                "Success Notes",
                value=output.get('success_notes'),
                height=150,
                disabled=True,
                label_visibility="collapsed"
            )

        # Metadata (sources, confidence, etc.)
        if output.get('metadata'):
            st.markdown("---")
            st.markdown("#### 🔍 Technical Metadata")
            with st.expander("View Metadata"):
                st.json(output.get('metadata'))

        # Created by
        if output.get('created_by'):
            st.markdown("---")
            st.markdown(f"**Created by:** {output.get('created_by')}")


def main():
    """Main entry point for the past outputs page."""
    # Require authentication
    require_auth()

    # Initialize session state
    init_session_state()

    # Check if viewing a specific output
    if st.session_state.selected_output_id:
        show_output_detail()
    else:
        # Show outputs list
        show_outputs_list()


if __name__ == "__main__":
    main()
