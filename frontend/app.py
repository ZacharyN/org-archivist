"""
Org Archivist - Main Application Entry Point

This is the main entry point for the Streamlit multi-page application.
It handles authentication, session management, and navigation to other pages.
"""

import streamlit as st
from typing import Optional
import sys
from pathlib import Path

# Add backend to path for API client access
backend_path = Path(__file__).parent.parent / "backend"
sys.path.insert(0, str(backend_path))

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
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables."""
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False

    if 'user' not in st.session_state:
        st.session_state.user = None

    if 'user_role' not in st.session_state:
        st.session_state.user_role = None

    if 'api_token' not in st.session_state:
        st.session_state.api_token = None


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
                    # TODO: Implement actual authentication via backend API
                    # For now, show a placeholder message
                    with st.spinner("Authenticating..."):
                        # Placeholder authentication logic
                        # This will be replaced with actual API call to backend
                        st.warning("⚠️ Authentication system not yet implemented. Backend integration pending.")

                        # TODO: Replace with actual API call:
                        # response = requests.post(
                        #     f"{API_BASE_URL}/api/auth/login",
                        #     json={"email": email, "password": password}
                        # )
                        # if response.status_code == 200:
                        #     data = response.json()
                        #     st.session_state.authenticated = True
                        #     st.session_state.user = data['user']
                        #     st.session_state.user_role = data['user']['role']
                        #     st.session_state.api_token = data['token']
                        #     st.rerun()
                else:
                    st.error("Please enter both email and password.")

        st.markdown("---")
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.9em;'>
            <p>Don't have an account? Contact your administrator.</p>
        </div>
        """, unsafe_allow_html=True)


def show_main_app():
    """Display the main application after authentication."""
    st.sidebar.title("📝 Org Archivist")
    st.sidebar.markdown(f"**{st.session_state.user.get('name', 'User')}**")
    st.sidebar.markdown(f"*{st.session_state.user_role.title()}*")
    st.sidebar.markdown("---")

    # Navigation
    st.sidebar.page_link("app.py", label="🏠 Home", icon="🏠")
    st.sidebar.page_link("pages/1_📚_Document_Library.py", label="Document Library", icon="📚")
    st.sidebar.page_link("pages/2_✍️_Writing_Styles.py", label="Writing Styles", icon="✍️")
    st.sidebar.page_link("pages/3_💬_AI_Assistant.py", label="AI Writing Assistant", icon="💬")
    st.sidebar.page_link("pages/4_📊_Past_Outputs.py", label="Past Outputs", icon="📊")
    st.sidebar.page_link("pages/5_⚙️_Settings.py", label="Settings", icon="⚙️")

    st.sidebar.markdown("---")

    if st.sidebar.button("🚪 Sign Out", use_container_width=True):
        # Clear session state
        for key in list(st.session_state.keys()):
            del st.session_state[key]
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

    # Quick stats dashboard
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
            label="✅ Success Rate",
            value="N/A",
            help="Grant/proposal success rate"
        )

    st.markdown("---")

    # Quick actions
    st.markdown("### Quick Actions")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.button("📤 Upload Documents", use_container_width=True, type="secondary")

    with col2:
        st.button("💬 Start Writing", use_container_width=True, type="primary")

    with col3:
        st.button("✍️ Create Writing Style", use_container_width=True, type="secondary")

    st.markdown("---")

    # Recent activity
    st.markdown("### Recent Activity")
    st.info("No recent activity. Start by uploading documents or creating a writing style!")


def main():
    """Main application entry point."""
    init_session_state()

    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_main_app()


if __name__ == "__main__":
    main()
