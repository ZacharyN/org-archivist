"""
Prompt Template Management Page

Manage prompt templates for different categories: Brand Voice, Audience, Section, and Custom.
Provides create, edit, delete operations with template variable support.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
import logging

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, AuthenticationError
from config.settings import settings

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Prompt Templates - Org Archivist",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables for prompt templates."""
    # List of prompts from backend
    if "prompts" not in st.session_state:
        st.session_state.prompts = []

    # Selected category filter
    if "selected_category" not in st.session_state:
        st.session_state.selected_category = "All"

    # Active status filter
    if "active_filter" not in st.session_state:
        st.session_state.active_filter = "Active Only"

    # Editing state
    if "editing_prompt_id" not in st.session_state:
        st.session_state.editing_prompt_id = None

    # Create new prompt modal state
    if "show_create_modal" not in st.session_state:
        st.session_state.show_create_modal = False

    # Prompts loaded flag
    if "prompts_loaded" not in st.session_state:
        st.session_state.prompts_loaded = False


def load_prompts(
    category: Optional[str] = None,
    active: Optional[bool] = None,
    search: Optional[str] = None
):
    """
    Load prompts from backend with optional filters.

    Args:
        category: Filter by category
        active: Filter by active status
        search: Search term
    """
    client = get_api_client()

    try:
        with st.spinner("Loading prompt templates..."):
            response = client.list_prompts(
                category=category,
                active=active,
                search=search
            )

        if response and "prompts" in response:
            st.session_state.prompts = response["prompts"]
            st.session_state.prompts_loaded = True
            logger.info(f"Loaded {len(st.session_state.prompts)} prompt templates")
        else:
            st.error("Failed to load prompts")
            st.session_state.prompts = []

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error loading prompts: {e}")
        st.session_state.prompts = []
    except APIError as e:
        st.error(f"Failed to load prompts: {e.message}")
        logger.error(f"API error loading prompts: {e}")
        st.session_state.prompts = []
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error loading prompts: {e}", exc_info=True)
        st.session_state.prompts = []


def create_prompt(name: str, category: str, content: str, variables: List[str]) -> bool:
    """
    Create a new prompt template.

    Args:
        name: Template name
        category: Category
        content: Prompt content
        variables: List of variables

    Returns:
        True if successful, False otherwise
    """
    client = get_api_client()

    try:
        with st.spinner("Creating prompt template..."):
            response = client.create_prompt(
                name=name,
                category=category,
                content=content,
                variables=variables
            )

        if response.get("success"):
            st.success(f"✅ Prompt template '{name}' created successfully!")
            logger.info(f"Created prompt template: {name}")
            # Reload prompts
            load_prompts()
            return True
        else:
            st.error(f"Failed to create prompt: {response.get('message', 'Unknown error')}")
            return False

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error creating prompt: {e}")
        return False
    except APIError as e:
        st.error(f"Failed to create prompt: {e.message}")
        logger.error(f"API error creating prompt: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error creating prompt: {e}", exc_info=True)
        return False


def update_prompt(
    prompt_id: str,
    name: Optional[str] = None,
    content: Optional[str] = None,
    variables: Optional[List[str]] = None,
    active: Optional[bool] = None
) -> bool:
    """
    Update an existing prompt template.

    Args:
        prompt_id: Prompt ID
        name: Updated name
        content: Updated content
        variables: Updated variables
        active: Updated active status

    Returns:
        True if successful, False otherwise
    """
    client = get_api_client()

    try:
        with st.spinner("Updating prompt template..."):
            response = client.update_prompt(
                prompt_id=prompt_id,
                name=name,
                content=content,
                variables=variables,
                active=active
            )

        if response.get("success"):
            st.success("✅ Prompt template updated successfully!")
            logger.info(f"Updated prompt template: {prompt_id}")
            # Reload prompts
            load_prompts()
            return True
        else:
            st.error(f"Failed to update prompt: {response.get('message', 'Unknown error')}")
            return False

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error updating prompt: {e}")
        return False
    except APIError as e:
        st.error(f"Failed to update prompt: {e.message}")
        logger.error(f"API error updating prompt: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error updating prompt: {e}", exc_info=True)
        return False


def delete_prompt(prompt_id: str, prompt_name: str) -> bool:
    """
    Delete a prompt template.

    Args:
        prompt_id: Prompt ID
        prompt_name: Prompt name (for confirmation)

    Returns:
        True if successful, False otherwise
    """
    client = get_api_client()

    try:
        with st.spinner(f"Deleting prompt template '{prompt_name}'..."):
            response = client.delete_prompt(prompt_id)

        if response.get("success"):
            st.success(f"✅ Prompt template '{prompt_name}' deleted successfully!")
            logger.info(f"Deleted prompt template: {prompt_id}")
            # Reload prompts
            load_prompts()
            return True
        else:
            st.error(f"Failed to delete prompt: {response.get('message', 'Unknown error')}")
            return False

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error deleting prompt: {e}")
        return False
    except APIError as e:
        st.error(f"Failed to delete prompt: {e.message}")
        logger.error(f"API error deleting prompt: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error deleting prompt: {e}", exc_info=True)
        return False


def display_prompt_card(prompt: Dict[str, Any]):
    """
    Display a prompt template card.

    Args:
        prompt: Prompt template data
    """
    with st.container():
        col1, col2, col3 = st.columns([4, 1, 1])

        with col1:
            # Display status badge
            status_badge = "🟢 Active" if prompt.get("active") else "🔴 Inactive"
            st.markdown(f"### {prompt.get('name')} {status_badge}")

            st.markdown(f"**Category:** {prompt.get('category', 'N/A').replace('_', ' ').title()}")

            # Show content preview (first 150 characters)
            content_preview = prompt.get("content", "")[:150]
            if len(prompt.get("content", "")) > 150:
                content_preview += "..."
            st.markdown(f"**Preview:** {content_preview}")

            # Show variables if any
            variables = prompt.get("variables", [])
            if variables:
                st.markdown(f"**Variables:** {', '.join([f'`{{{v}}}`' for v in variables])}")

            # Show version and metadata
            st.caption(f"Version: {prompt.get('version', 1)} | Updated: {prompt.get('updated_at', 'N/A')}")

        with col2:
            # Edit button
            if st.button("✏️ Edit", key=f"edit_{prompt.get('id')}", use_container_width=True):
                st.session_state.editing_prompt_id = prompt.get("id")
                st.rerun()

        with col3:
            # Toggle active status
            new_status = not prompt.get("active")
            status_label = "🔴 Deactivate" if prompt.get("active") else "🟢 Activate"

            if st.button(status_label, key=f"toggle_{prompt.get('id')}", use_container_width=True):
                update_prompt(
                    prompt_id=prompt.get("id"),
                    active=new_status
                )
                st.rerun()

        # Delete button (separate row for confirmation)
        col_spacer, col_delete = st.columns([5, 1])
        with col_delete:
            if st.button("🗑️ Delete", key=f"delete_{prompt.get('id')}", use_container_width=True, type="secondary"):
                # Confirmation via session state
                if st.checkbox(f"Confirm delete '{prompt.get('name')}'?", key=f"confirm_delete_{prompt.get('id')}"):
                    delete_prompt(prompt.get("id"), prompt.get("name"))
                    st.rerun()

        st.markdown("---")


def show_edit_modal(prompt: Dict[str, Any]):
    """
    Show edit modal for a prompt template.

    Args:
        prompt: Prompt template data
    """
    st.markdown(f"## ✏️ Edit Prompt Template: {prompt.get('name')}")

    with st.form(f"edit_form_{prompt.get('id')}"):
        name = st.text_input("Template Name", value=prompt.get("name"), max_chars=100)

        content = st.text_area(
            "Prompt Content",
            value=prompt.get("content"),
            height=300,
            help="Use {variable_name} syntax for template variables"
        )

        variables_str = st.text_input(
            "Variables (comma-separated)",
            value=", ".join(prompt.get("variables", [])),
            help="List variable names that can be substituted in the content"
        )

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            submit = st.form_submit_button("💾 Save Changes", use_container_width=True, type="primary")

        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            # Parse variables
            variables = [v.strip() for v in variables_str.split(",") if v.strip()]

            # Update prompt
            if update_prompt(
                prompt_id=prompt.get("id"),
                name=name,
                content=content,
                variables=variables
            ):
                st.session_state.editing_prompt_id = None
                st.rerun()

        if cancel:
            st.session_state.editing_prompt_id = None
            st.rerun()


def show_create_modal():
    """Show create new prompt template modal."""
    st.markdown("## ➕ Create New Prompt Template")

    with st.form("create_prompt_form"):
        name = st.text_input("Template Name", max_chars=100)

        category = st.selectbox(
            "Category",
            options=["audience", "section", "brand_voice", "custom"],
            format_func=lambda x: x.replace("_", " ").title()
        )

        content = st.text_area(
            "Prompt Content",
            height=300,
            help="Use {variable_name} syntax for template variables"
        )

        variables_str = st.text_input(
            "Variables (comma-separated)",
            help="List variable names that can be substituted in the content (e.g., organization_name, audience)"
        )

        col1, col2, col3 = st.columns([1, 1, 2])

        with col1:
            submit = st.form_submit_button("➕ Create Template", use_container_width=True, type="primary")

        with col2:
            cancel = st.form_submit_button("❌ Cancel", use_container_width=True)

        if submit:
            # Validate inputs
            if not name or not content:
                st.error("Template name and content are required")
            else:
                # Parse variables
                variables = [v.strip() for v in variables_str.split(",") if v.strip()]

                # Create prompt
                if create_prompt(
                    name=name,
                    category=category,
                    content=content,
                    variables=variables
                ):
                    st.session_state.show_create_modal = False
                    st.rerun()

        if cancel:
            st.session_state.show_create_modal = False
            st.rerun()


def main():
    """Main application entry point."""
    init_session_state()

    # Header
    st.title("📝 Prompt Template Management")
    st.markdown("""
    Manage prompt templates for AI-powered content generation. Templates can include variables
    for dynamic content and are organized by category.
    """)

    # Sidebar filters
    with st.sidebar:
        st.markdown("### Filters")

        # Category filter
        category_options = ["All", "Audience", "Section", "Brand Voice", "Custom"]
        selected_category = st.selectbox(
            "Category",
            options=category_options,
            index=category_options.index(st.session_state.selected_category)
        )
        st.session_state.selected_category = selected_category

        # Active status filter
        active_options = ["All", "Active Only", "Inactive Only"]
        active_filter = st.selectbox(
            "Status",
            options=active_options,
            index=active_options.index(st.session_state.active_filter)
        )
        st.session_state.active_filter = active_filter

        # Search
        search_term = st.text_input("Search", placeholder="Search name or content...")

        st.markdown("---")

        # Stats
        if st.session_state.prompts_loaded:
            st.markdown(f"""
            **Template Statistics:**
            - Total: {len(st.session_state.prompts)}
            - Active: {sum(1 for p in st.session_state.prompts if p.get('active'))}
            - Inactive: {sum(1 for p in st.session_state.prompts if not p.get('active'))}
            """)

    # Main content area
    col1, col2, col3 = st.columns([2, 1, 1])

    with col1:
        st.markdown("---")

    with col2:
        if st.button("🔄 Refresh", use_container_width=True):
            st.session_state.prompts_loaded = False
            st.rerun()

    with col3:
        if st.button("➕ New Template", use_container_width=True, type="primary"):
            st.session_state.show_create_modal = True
            st.rerun()

    # Load prompts if not loaded
    if not st.session_state.prompts_loaded:
        # Apply filters
        category_filter = None if selected_category == "All" else selected_category.lower().replace(" ", "_")
        active_status = None
        if active_filter == "Active Only":
            active_status = True
        elif active_filter == "Inactive Only":
            active_status = False

        load_prompts(
            category=category_filter,
            active=active_status,
            search=search_term if search_term else None
        )

    # Show create modal if requested
    if st.session_state.show_create_modal:
        show_create_modal()
        return

    # Show edit modal if editing
    if st.session_state.editing_prompt_id:
        # Find the prompt being edited
        editing_prompt = next(
            (p for p in st.session_state.prompts if p.get("id") == st.session_state.editing_prompt_id),
            None
        )
        if editing_prompt:
            show_edit_modal(editing_prompt)
            return
        else:
            st.error("Prompt not found")
            st.session_state.editing_prompt_id = None

    # Display prompts
    st.markdown("---")

    if not st.session_state.prompts:
        st.info("No prompt templates found. Click 'New Template' to create one.")
    else:
        # Group by category
        categories = {}
        for prompt in st.session_state.prompts:
            cat = prompt.get("category", "custom")
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(prompt)

        # Display by category
        for category, prompts in categories.items():
            with st.expander(f"**{category.replace('_', ' ').title()}** ({len(prompts)} templates)", expanded=True):
                for prompt in prompts:
                    display_prompt_card(prompt)

    # Help section
    with st.expander("💡 Help: Using Prompt Templates"):
        st.markdown("""
        **Template Categories:**
        - **Audience**: Prompts tailored for specific audiences (Federal RFP, Foundation Grants, etc.)
        - **Section**: Prompts for specific document sections (Executive Summary, Methodology, etc.)
        - **Brand Voice**: Prompts that define organizational voice and style
        - **Custom**: User-defined prompts for specific use cases

        **Using Variables:**
        - Variables allow dynamic content substitution
        - Use `{variable_name}` syntax in your prompt content
        - Common variables: `{organization_name}`, `{audience}`, `{query}`, `{context}`

        **Example Template with Variables:**
        ```
        Write an introduction for {organization_name} targeting {audience}.
        The tone should be {tone} and focus on {focus_area}.
        ```

        **Best Practices:**
        - Keep templates focused on a single purpose
        - Use clear, descriptive names
        - Document expected variables
        - Test templates with sample data
        - Deactivate templates instead of deleting to preserve history
        """)


if __name__ == "__main__":
    main()
