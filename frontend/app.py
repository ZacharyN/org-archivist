"""
Org Archivist - Main Application Entry Point

This is the main entry point for the Streamlit multi-page application.
It handles authentication, session management, and navigation to other pages.
"""

import streamlit as st
from typing import Optional
import sys
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from utils.api_client import get_api_client, APIError, AuthenticationError
from config.settings import settings
from components.auth import show_user_profile, logout as auth_logout

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Org Archivist - AI Writing Assistant",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://github.com/your-org/org-archivist',
        'Report a bug': "https://github.com/your-org/org-archivist/issues",
        'About': "# Org Archivist\nAI-powered writing assistant for nonprofits"
    }
)

# Custom CSS for better styling
st.markdown("""
<style>
    /* Main container styling */
    .main > div {
        padding-top: 2rem;
    }

    /* Sidebar styling */
    .css-1d391kg {
        padding-top: 3rem;
    }

    /* Button styling */
    .stButton>button {
        width: 100%;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>

<script>
    // Rename 'app' section to 'Navigation'
    function renameAppSection() {
        const sidebar = window.parent.document.querySelector('[data-testid="stSidebarNav"]');
        if (sidebar) {
            const elements = sidebar.querySelectorAll('*');
            elements.forEach(el => {
                if (el.textContent === 'app' && el.childNodes.length === 1 && el.childNodes[0].nodeType === 3) {
                    el.textContent = 'Navigation';
                }
            });
        }
    }

    // Run immediately and on DOM changes
    renameAppSection();

    // Use MutationObserver to catch dynamically added content
    const observer = new MutationObserver(renameAppSection);
    if (window.parent.document.body) {
        observer.observe(window.parent.document.body, { childList: true, subtree: true });
    }
</script>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if 'user' not in st.session_state:
        st.session_state.user = None

    if 'user_role' not in st.session_state:
        st.session_state.user_role = None


def show_login_page():
    """Display the login page."""
    st.title("📝 Org Archivist")
    st.markdown("### AI-Powered Writing Assistant for Nonprofits")

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("#### Sign In")

        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your.email@organization.org")
            password = st.text_input("Password", type="password")

            submitted = st.form_submit_button("Sign In", use_container_width=True)

            if submitted:
                if email and password:
                    try:
                        client = get_api_client()
                        with st.spinner("Authenticating..."):
                            response = client.login(email, password)

                        # Successful login
                        if response and response.get("user"):
                            user = response.get("user")
                            st.session_state.authenticated = True
                            st.session_state.user = user
                            st.session_state.user_role = user.get('role', 'user')

                            # Set flag for post-login redirect
                            st.session_state.just_logged_in = True

                            logger.info(f"User {email} logged in successfully")
                            st.success(f"Welcome back, {user.get('name', user.get('email'))}!")
                            st.rerun()
                        else:
                            st.error("Invalid credentials. Please try again.")

                    except AuthenticationError as e:
                        st.error("❌ Invalid email or password. Please check your credentials and try again.")
                        logger.error(f"Authentication error for {email}: {e}")
                    except APIError as e:
                        st.error("❌ Unable to connect to the server. Please try again later.")
                        logger.error(f"API error during login for {email}: {e}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {str(e)}")
                        logger.error(f"Unexpected error during login for {email}: {e}", exc_info=True)
                else:
                    st.error("Please enter both email and password.")

        st.markdown("---")

        # Link to registration page
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("Create New Account", use_container_width=True):
                st.switch_page("pages/2_📝_Register.py")
        with col_b:
            st.markdown("""
            <div style='text-align: center; color: #666; font-size: 0.85em; padding-top: 8px;'>
                <p>Need help? Contact admin</p>
            </div>
            """, unsafe_allow_html=True)


def show_main_app():
    """Display the main application after authentication."""
    # Check if user just logged in and redirect to Documents page
    if st.session_state.get('just_logged_in', False):
        st.session_state.just_logged_in = False
        st.switch_page("pages/1_📂_Documents.py")

    # Sidebar
    st.sidebar.title("📝 Org Archivist")

    if st.session_state.user:
        user_name = st.session_state.user.get('name') or st.session_state.user.get('email', 'User')
        st.sidebar.markdown(f"**{user_name}**")
        st.sidebar.markdown(f"*{st.session_state.user_role.title()}*")

    st.sidebar.markdown("---")

    # Navigation - updated to match actual pages
    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/1_📂_Documents.py", label="Documents", icon="📂")
    st.sidebar.page_link("pages/3_💬_AI_Assistant.py", label="AI Assistant", icon="💬")
    st.sidebar.page_link("pages/4_⚙️_User_Preferences.py", label="User Preferences", icon="⚙️")
    st.sidebar.page_link("pages/5_📝_Prompt_Templates.py", label="Prompt Templates", icon="📝")
    st.sidebar.page_link("pages/6_⚙️_System_Settings.py", label="System Settings", icon="⚙️")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Quick Actions")

    if st.sidebar.button("💬 Start Chat", use_container_width=True, type="primary"):
        st.switch_page("pages/3_💬_AI_Assistant.py")

    if st.sidebar.button("📝 Manage Templates", use_container_width=True):
        st.switch_page("pages/5_📝_Prompt_Templates.py")

    st.sidebar.markdown("---")

    # Logout button
    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        auth_logout()
        st.rerun()

    # Main content
    st.title("Welcome to Org Archivist")

    st.markdown("""
    ### AI-Powered Writing Assistant for Nonprofits

    Org Archivist helps you create compelling grant proposals, reports, and other documents
    by learning from your organization's past writing and using AI to generate new content
    in your unique voice.
    """)

    st.markdown("---")

    # Quick stats dashboard (placeholder - will be populated from backend later)
    st.markdown("### Dashboard")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="📚 Documents",
            value="0",
            help="Total documents in your library"
        )

    with col2:
        st.metric(
            label="✍️ Writing Styles",
            value="0",
            help="AI-generated writing styles"
        )

    with col3:
        st.metric(
            label="📝 Outputs Generated",
            value="0",
            help="Total outputs created"
        )

    with col4:
        st.metric(
            label="📋 Templates",
            value="0",
            help="Prompt templates available"
        )

    st.markdown("---")

    # Quick Start Guide
    st.markdown("### Getting Started")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("""
        **1. Start a Conversation**
        - Go to AI Assistant to chat with the AI
        - Get help drafting content
        - Ask questions about your documents
        """)

        st.markdown("""
        **2. Customize Your Experience**
        - Set your preferences in User Preferences
        - Choose default audience and tone
        - Configure auto-save settings
        """)

    with col2:
        st.markdown("""
        **3. Manage Prompt Templates**
        - Create reusable prompt templates
        - Organize by category
        - Use variables for flexibility
        """)

        st.markdown("""
        **4. Configure System Settings** (Admin)
        - Adjust LLM parameters
        - Configure RAG pipeline
        - Optimize for your use case
        """)

    st.markdown("---")

    # Recent activity
    st.markdown("### Recent Activity")
    st.info("No recent activity. Start by opening the AI Assistant or creating a prompt template!")

    # Feature highlights
    with st.expander("✨ Key Features"):
        st.markdown("""
        - **AI-Powered Writing**: Generate content with Claude's advanced AI
        - **Personalized Preferences**: Save your default settings
        - **Prompt Templates**: Reusable templates for common tasks
        - **Multi-turn Conversations**: Maintain context across chat sessions
        - **Flexible Configuration**: Customize the AI behavior to match your needs
        """)


def main():
    """Main application entry point."""
    init_session_state()

    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()


if __name__ == "__main__":
    main()
