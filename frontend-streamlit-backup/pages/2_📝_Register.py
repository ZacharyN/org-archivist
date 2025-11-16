"""
User Registration Page

This page allows new users to register for an account.
"""

import streamlit as st
import sys
from pathlib import Path
import logging

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, ValidationError
from config.settings import settings

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Register - Org Archivist",
    page_icon="📝",
    layout="centered",
)

# Custom CSS
st.markdown("""
<style>
    .main > div {
        padding-top: 2rem;
    }

    .stButton>button {
        width: 100%;
    }

    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def show_registration_form():
    """Display the registration form."""
    st.title("📝 Create Account")
    st.markdown("### Join Org Archivist")

    st.markdown("---")

    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        st.markdown("#### Account Information")

        with st.form("registration_form"):
            email = st.text_input(
                "Email Address",
                placeholder="your.email@organization.org",
                help="Enter your work email address"
            )

            full_name = st.text_input(
                "Full Name",
                placeholder="John Doe",
                help="Enter your full name"
            )

            password = st.text_input(
                "Password",
                type="password",
                help="Must be at least 8 characters long"
            )

            password_confirm = st.text_input(
                "Confirm Password",
                type="password",
                help="Re-enter your password"
            )

            role = st.selectbox(
                "Role",
                options=["writer", "editor", "admin"],
                index=0,
                help="Select your role - contact admin if you need editor or admin access"
            )

            # Role descriptions
            with st.expander("ℹ️ Role Descriptions"):
                st.markdown("""
                **Writer**
                - Can use AI assistant to generate content
                - Can manage their own outputs
                - Can view shared documents

                **Editor**
                - All Writer permissions
                - Can manage writing styles
                - Can manage prompt templates
                - Can edit shared documents

                **Admin**
                - All Editor permissions
                - Can manage system settings
                - Can manage users
                - Full system access
                """)

            submitted = st.form_submit_button("Create Account", use_container_width=True)

            if submitted:
                # Validation
                if not email or not password:
                    st.error("Please enter both email and password.")
                elif len(password) < 8:
                    st.error("Password must be at least 8 characters long.")
                elif password != password_confirm:
                    st.error("Passwords do not match.")
                else:
                    try:
                        client = get_api_client()

                        with st.spinner("Creating your account..."):
                            response = client.register(
                                email=email,
                                password=password,
                                full_name=full_name if full_name else None,
                                role=role
                            )

                        if response:
                            logger.info(f"User registered successfully: {email}")
                            st.success("Account created successfully!")
                            st.info("You can now log in with your credentials.")

                            # Show login button
                            if st.button("Go to Login Page"):
                                st.switch_page("app.py")
                        else:
                            st.error("Registration failed. Please try again.")

                    except ValidationError as e:
                        st.error(f"Validation error: {e.message}")
                        logger.error(f"Validation error during registration for {email}: {e}")
                    except APIError as e:
                        # Handle specific error messages
                        if "already registered" in str(e.message).lower():
                            st.error("This email address is already registered. Please try logging in instead.")
                        else:
                            st.error(f"Registration failed: {e.message}")
                        logger.error(f"API error during registration for {email}: {e}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {str(e)}")
                        logger.error(f"Unexpected error during registration for {email}: {e}", exc_info=True)

        st.markdown("---")

        # Link to login page
        st.markdown("""
        <div style='text-align: center; color: #666; font-size: 0.9em;'>
            <p>Already have an account? <a href="/" target="_self">Sign in here</a></p>
        </div>
        """, unsafe_allow_html=True)


def main():
    """Main entry point for the registration page."""
    # If user is already authenticated, redirect to main app
    if st.session_state.get('authenticated', False):
        st.info("You are already logged in.")
        if st.button("Go to Home"):
            st.switch_page("app.py")
    else:
        show_registration_form()


if __name__ == "__main__":
    main()
