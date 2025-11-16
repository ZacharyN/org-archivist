"""
User Preferences Page

Allows users to configure personal preferences including writing defaults, citation style,
auto-save settings, and UI theme. Preferences are persisted to the backend and cached in
session state for performance.
"""

import streamlit as st
from typing import Dict, Any, Optional
import logging

# Add parent directory to path for imports
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, AuthenticationError
from components.auth import require_authentication
from config.settings import settings

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="User Preferences - Org Archivist",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables for preferences."""
    # Cached preferences from backend
    if "user_preferences" not in st.session_state:
        st.session_state.user_preferences = None

    # Preferences loaded flag
    if "preferences_loaded" not in st.session_state:
        st.session_state.preferences_loaded = False

    # Frontend-only preferences (theme)
    if "theme" not in st.session_state:
        st.session_state.theme = "light"


def load_preferences() -> Optional[Dict[str, Any]]:
    """
    Load user preferences from backend config API.

    Returns:
        Dict with user preferences or None if load fails
    """
    client = get_api_client()

    try:
        with st.spinner("Loading preferences..."):
            response = client.get_config()

        if response.get("success"):
            config = response.get("config", {})
            prefs = config.get("user_preferences", {})

            # Cache in session state
            st.session_state.user_preferences = prefs
            st.session_state.preferences_loaded = True

            logger.info("User preferences loaded successfully")
            return prefs
        else:
            st.error(f"Failed to load preferences: {response.get('message', 'Unknown error')}")
            return None

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error loading preferences: {e}")
        return None
    except APIError as e:
        st.error(f"Failed to load preferences: {e.message}")
        logger.error(f"API error loading preferences: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error loading preferences: {e}", exc_info=True)
        return None


def save_preferences(preferences: Dict[str, Any]) -> bool:
    """
    Save user preferences to backend config API.

    Args:
        preferences: Dictionary with user preference updates

    Returns:
        True if save successful, False otherwise
    """
    client = get_api_client()

    try:
        with st.spinner("Saving preferences..."):
            response = client.update_config({"user_preferences": preferences})

        if response.get("success"):
            # Update cached preferences
            st.session_state.user_preferences = preferences
            st.success("✅ Preferences saved successfully!")
            logger.info("User preferences saved successfully")
            return True
        else:
            st.error(f"Failed to save preferences: {response.get('message', 'Unknown error')}")
            return False

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error saving preferences: {e}")
        return False
    except APIError as e:
        st.error(f"Failed to save preferences: {e.message}")
        logger.error(f"API error saving preferences: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error saving preferences: {e}", exc_info=True)
        return False


def main():
    """Main application entry point."""
    # Require authentication
    require_authentication()

    init_session_state()

    # Header
    st.title("⚙️ User Preferences")
    st.markdown("""
    Customize your writing experience with personalized defaults and settings.
    These preferences will be applied across all your writing sessions.
    """)

    # Load preferences if not loaded
    if not st.session_state.preferences_loaded:
        prefs = load_preferences()
        if prefs is None:
            st.warning("Using default preferences. Save your preferences to persist them across sessions.")
            prefs = {
                "default_audience": None,
                "default_section": None,
                "default_tone": None,
                "citation_style": "numbered",
                "auto_save_interval": 60,
            }
            st.session_state.user_preferences = prefs
    else:
        prefs = st.session_state.user_preferences

    # Preferences Form
    st.markdown("---")
    st.subheader("Writing Defaults")

    col1, col2 = st.columns(2)

    with col1:
        # Audience Type
        audience_options = [
            "None (select for each document)",
            "Federal Grant Reviewers",
            "Foundation Grant Reviewers",
            "Board Members",
            "General Public",
            "Donors",
            "Stakeholders",
        ]

        current_audience = prefs.get("default_audience")
        audience_index = 0 if current_audience is None else (
            audience_options.index(current_audience) if current_audience in audience_options else 0
        )

        default_audience = st.selectbox(
            "Default Audience",
            options=audience_options,
            index=audience_index,
            help="Set a default audience type for your writing projects"
        )

        # Convert "None" selection to None
        if default_audience == "None (select for each document)":
            default_audience = None

        # Section Type
        section_options = [
            "None (select for each document)",
            "Executive Summary",
            "Problem Statement",
            "Project Description",
            "Methodology",
            "Budget Narrative",
            "Evaluation Plan",
            "Sustainability",
        ]

        current_section = prefs.get("default_section")
        section_index = 0 if current_section is None else (
            section_options.index(current_section) if current_section in section_options else 0
        )

        default_section = st.selectbox(
            "Default Section",
            options=section_options,
            index=section_index,
            help="Set a default section type for your writing projects"
        )

        # Convert "None" selection to None
        if default_section == "None (select for each document)":
            default_section = None

    with col2:
        # Tone Level
        tone_options = [
            "None (select for each document)",
            "Professional",
            "Formal",
            "Conversational",
            "Academic",
            "Persuasive",
        ]

        current_tone = prefs.get("default_tone")
        tone_index = 0 if current_tone is None else (
            tone_options.index(current_tone) if current_tone in tone_options else 0
        )

        default_tone = st.selectbox(
            "Default Tone",
            options=tone_options,
            index=tone_index,
            help="Set a default writing tone for your projects"
        )

        # Convert "None" selection to None
        if default_tone == "None (select for each document)":
            default_tone = None

        # Citation Style
        citation_options = ["numbered", "footnote", "apa"]

        current_citation = prefs.get("citation_style", "numbered")
        citation_index = citation_options.index(current_citation) if current_citation in citation_options else 0

        citation_style = st.selectbox(
            "Citation Style",
            options=citation_options,
            index=citation_index,
            help="Choose how sources should be cited in your documents",
            format_func=lambda x: x.upper() if x == "apa" else x.capitalize()
        )

    # Auto-save Settings
    st.markdown("---")
    st.subheader("Auto-save Settings")

    auto_save_interval = st.slider(
        "Auto-save Interval (seconds)",
        min_value=10,
        max_value=300,
        value=prefs.get("auto_save_interval", 60),
        step=10,
        help="How often to automatically save your work (10-300 seconds)"
    )

    # UI Theme (Frontend-only preference)
    st.markdown("---")
    st.subheader("User Interface")

    theme_options = ["light", "dark", "auto"]
    current_theme = st.session_state.theme
    theme_index = theme_options.index(current_theme) if current_theme in theme_options else 0

    theme = st.selectbox(
        "Theme",
        options=theme_options,
        index=theme_index,
        help="Choose your preferred UI theme",
        format_func=lambda x: x.capitalize()
    )

    # Update theme in session state
    st.session_state.theme = theme

    # Note about theme
    st.info("💡 **Note:** Theme preference is stored locally in your browser session. Set your theme preference in Streamlit settings for persistent theme across sessions.")

    # Save Button
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Preferences", use_container_width=True, type="primary"):
            # Prepare preferences payload
            preferences_update = {
                "default_audience": default_audience,
                "default_section": default_section,
                "default_tone": default_tone,
                "citation_style": citation_style,
                "auto_save_interval": auto_save_interval,
            }

            # Save to backend
            if save_preferences(preferences_update):
                st.rerun()

    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True):
            # Reset preferences to defaults
            default_prefs = {
                "default_audience": None,
                "default_section": None,
                "default_tone": None,
                "citation_style": "numbered",
                "auto_save_interval": 60,
            }

            if save_preferences(default_prefs):
                st.session_state.theme = "light"
                st.rerun()

    # Current Preferences Display
    with st.sidebar:
        st.markdown("### Current Preferences")

        st.markdown(f"""
        **Writing Defaults:**
        - Audience: {default_audience or "Not set"}
        - Section: {default_section or "Not set"}
        - Tone: {default_tone or "Not set"}

        **Citation:** {citation_style.upper() if citation_style == "apa" else citation_style.capitalize()}

        **Auto-save:** Every {auto_save_interval}s

        **Theme:** {theme.capitalize()}
        """)


if __name__ == "__main__":
    main()
