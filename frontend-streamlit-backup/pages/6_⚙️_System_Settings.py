"""
System Settings Page

Provides configuration interface for system-wide settings including LLM model parameters
and RAG pipeline configuration. Admin-only write access with read-only view for other users.
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
    page_title="System Settings - Org Archivist",
    page_icon="⚙️",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables for system settings."""
    # Cached system configuration from backend
    if "system_config" not in st.session_state:
        st.session_state.system_config = None

    # Config loaded flag
    if "config_loaded" not in st.session_state:
        st.session_state.config_loaded = False

    # User role (for access control)
    # TODO: Get from actual authentication system
    if "user_role" not in st.session_state:
        st.session_state.user_role = "admin"  # Default to admin for development


def load_system_config() -> Optional[Dict[str, Any]]:
    """
    Load system configuration from backend.

    Returns:
        Dict with system configuration or None if load fails
    """
    client = get_api_client()

    try:
        with st.spinner("Loading system configuration..."):
            response = client.get_config()

        if response.get("success"):
            config = response.get("config", {})

            # Cache in session state
            st.session_state.system_config = config
            st.session_state.config_loaded = True

            logger.info("System configuration loaded successfully")
            return config
        else:
            st.error(f"Failed to load configuration: {response.get('message', 'Unknown error')}")
            return None

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error loading config: {e}")
        return None
    except APIError as e:
        st.error(f"Failed to load configuration: {e.message}")
        logger.error(f"API error loading config: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error loading config: {e}", exc_info=True)
        return None


def save_system_config(config_update: Dict[str, Any]) -> bool:
    """
    Save system configuration to backend.

    Args:
        config_update: Dictionary with configuration updates

    Returns:
        True if save successful, False otherwise
    """
    client = get_api_client()

    try:
        with st.spinner("Saving configuration..."):
            response = client.update_config(config_update)

        if response.get("success"):
            # Update cached configuration
            st.session_state.system_config = response.get("config", {})
            st.success("✅ Configuration saved successfully!")
            logger.info("System configuration saved successfully")
            return True
        else:
            st.error(f"Failed to save configuration: {response.get('message', 'Unknown error')}")
            return False

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error saving config: {e}")
        return False
    except APIError as e:
        st.error(f"Failed to save configuration: {e.message}")
        logger.error(f"API error saving config: {e}")
        return False
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error saving config: {e}", exc_info=True)
        return False


def reset_to_defaults() -> bool:
    """
    Reset configuration to default values.

    Returns:
        True if reset successful, False otherwise
    """
    client = get_api_client()

    try:
        with st.spinner("Resetting to defaults..."):
            # Call reset endpoint via API client
            # Note: This endpoint might not exist in API client yet, using update with defaults
            response = client.update_config({
                "llm_config": {
                    "model_name": "claude-sonnet-4-5-20250929",
                    "temperature": 0.3,
                    "max_tokens": 4096
                },
                "rag_config": {
                    "embedding_model": "bge-large-en-v1.5",
                    "chunk_size": 500,
                    "chunk_overlap": 50,
                    "default_retrieval_count": 5,
                    "similarity_threshold": 0.7,
                    "recency_weight": 0.7
                }
            })

        if response.get("success"):
            st.session_state.system_config = response.get("config", {})
            st.success("✅ Configuration reset to defaults!")
            logger.info("System configuration reset to defaults")
            return True
        else:
            st.error(f"Failed to reset configuration: {response.get('message', 'Unknown error')}")
            return False

    except Exception as e:
        st.error(f"Failed to reset configuration: {str(e)}")
        logger.error(f"Error resetting config: {e}", exc_info=True)
        return False


def main():
    """Main application entry point."""
    # Require authentication
    require_authentication()

    init_session_state()

    # Header
    st.title("⚙️ System Settings")
    st.markdown("""
    Configure system-wide parameters for the LLM model and RAG pipeline.
    These settings affect all users and writing sessions.
    """)

    # Check user permissions
    is_admin = st.session_state.user_role == "admin"

    if not is_admin:
        st.warning("⚠️ **Read-only mode:** You have view-only access to system settings. Contact an administrator to make changes.")

    # Load configuration if not loaded
    if not st.session_state.config_loaded:
        config = load_system_config()
        if config is None:
            st.warning("Using default configuration. Save settings to persist them across sessions.")
            config = {
                "llm_config": {
                    "model_name": "claude-sonnet-4-5-20250929",
                    "temperature": 0.3,
                    "max_tokens": 4096
                },
                "rag_config": {
                    "embedding_model": "bge-large-en-v1.5",
                    "chunk_size": 500,
                    "chunk_overlap": 50,
                    "default_retrieval_count": 5,
                    "similarity_threshold": 0.7,
                    "recency_weight": 0.7
                }
            }
            st.session_state.system_config = config
    else:
        config = st.session_state.system_config

    # LLM Configuration Section
    st.markdown("---")
    st.subheader("🤖 LLM Model Configuration")
    st.markdown("Settings for the Claude language model used for content generation.")

    llm_config = config.get("llm_config", {})

    col1, col2 = st.columns(2)

    with col1:
        model_name = st.text_input(
            "Model Name",
            value=llm_config.get("model_name", "claude-sonnet-4-5-20250929"),
            disabled=not is_admin,
            help="Claude model identifier (e.g., claude-sonnet-4-5-20250929)"
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=float(llm_config.get("temperature", 0.3)),
            step=0.05,
            disabled=not is_admin,
            help="Controls randomness in generation. Lower = more focused, Higher = more creative"
        )

    with col2:
        max_tokens = st.number_input(
            "Max Tokens",
            min_value=512,
            max_value=8192,
            value=int(llm_config.get("max_tokens", 4096)),
            step=256,
            disabled=not is_admin,
            help="Maximum number of tokens the model can generate in a single response"
        )

        st.markdown("**Current Settings:**")
        st.markdown(f"""
        - Model: `{model_name}`
        - Temp: `{temperature:.2f}`
        - Max Tokens: `{max_tokens}`
        """)

    # RAG Configuration Section
    st.markdown("---")
    st.subheader("🔍 RAG Pipeline Configuration")
    st.markdown("Settings for document retrieval and embedding generation.")

    rag_config = config.get("rag_config", {})

    col1, col2, col3 = st.columns(3)

    with col1:
        st.markdown("**Document Processing**")

        embedding_model = st.text_input(
            "Embedding Model",
            value=rag_config.get("embedding_model", "bge-large-en-v1.5"),
            disabled=not is_admin,
            help="Model used to generate document embeddings"
        )

        chunk_size = st.number_input(
            "Chunk Size (tokens)",
            min_value=100,
            max_value=1000,
            value=int(rag_config.get("chunk_size", 500)),
            step=50,
            disabled=not is_admin,
            help="Target size for document chunks"
        )

        chunk_overlap = st.number_input(
            "Chunk Overlap (tokens)",
            min_value=0,
            max_value=200,
            value=int(rag_config.get("chunk_overlap", 50)),
            step=10,
            disabled=not is_admin,
            help="Overlap between consecutive chunks"
        )

    with col2:
        st.markdown("**Retrieval Parameters**")

        retrieval_count = st.number_input(
            "Retrieval Count",
            min_value=1,
            max_value=20,
            value=int(rag_config.get("default_retrieval_count", 5)),
            step=1,
            disabled=not is_admin,
            help="Number of document chunks to retrieve"
        )

        similarity_threshold = st.slider(
            "Similarity Threshold",
            min_value=0.0,
            max_value=1.0,
            value=float(rag_config.get("similarity_threshold", 0.7)),
            step=0.05,
            disabled=not is_admin,
            help="Minimum similarity score for retrieval (0.0-1.0)"
        )

        recency_weight = st.slider(
            "Recency Weight",
            min_value=0.0,
            max_value=1.0,
            value=float(rag_config.get("recency_weight", 0.7)),
            step=0.05,
            disabled=not is_admin,
            help="Weight given to recent documents (0.0-1.0)"
        )

    with col3:
        st.markdown("**Current RAG Settings:**")
        st.markdown(f"""
        **Processing:**
        - Model: `{embedding_model}`
        - Chunk Size: `{chunk_size}` tokens
        - Overlap: `{chunk_overlap}` tokens

        **Retrieval:**
        - Count: `{retrieval_count}` chunks
        - Similarity: `{similarity_threshold:.2f}`
        - Recency: `{recency_weight:.2f}`
        """)

    # Save and Reset Buttons
    st.markdown("---")

    col1, col2, col3 = st.columns([1, 1, 2])

    with col1:
        if st.button("💾 Save Configuration", use_container_width=True, type="primary", disabled=not is_admin):
            # Prepare configuration update
            config_update = {
                "llm_config": {
                    "model_name": model_name,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                },
                "rag_config": {
                    "embedding_model": embedding_model,
                    "chunk_size": chunk_size,
                    "chunk_overlap": chunk_overlap,
                    "default_retrieval_count": retrieval_count,
                    "similarity_threshold": similarity_threshold,
                    "recency_weight": recency_weight
                }
            }

            # Validate chunk overlap < chunk size
            if chunk_overlap >= chunk_size:
                st.error("❌ Chunk overlap must be less than chunk size!")
            else:
                # Save to backend
                if save_system_config(config_update):
                    st.rerun()

    with col2:
        if st.button("🔄 Reset to Defaults", use_container_width=True, disabled=not is_admin):
            if reset_to_defaults():
                st.rerun()

    # Configuration Tips
    with st.sidebar:
        st.markdown("### Configuration Tips")

        with st.expander("💡 LLM Settings Guide"):
            st.markdown("""
            **Temperature:**
            - `0.0-0.3`: Focused, deterministic outputs
            - `0.3-0.7`: Balanced creativity
            - `0.7-1.0`: Creative, varied outputs

            **Max Tokens:**
            - `512-1024`: Short responses
            - `1024-4096`: Medium documents
            - `4096-8192`: Long-form content
            """)

        with st.expander("🔍 RAG Settings Guide"):
            st.markdown("""
            **Chunk Size:**
            - Smaller (100-300): Better precision
            - Medium (300-700): Balanced
            - Larger (700-1000): More context

            **Retrieval Count:**
            - Fewer (1-3): Fast, focused
            - Medium (3-7): Balanced
            - More (7-20): Comprehensive

            **Similarity Threshold:**
            - High (0.8-1.0): Only very relevant
            - Medium (0.6-0.8): Balanced
            - Low (0.0-0.6): Broad retrieval
            """)

        st.markdown("---")
        st.markdown("### Current Status")

        if is_admin:
            st.success("✅ **Admin Access**\nFull configuration control")
        else:
            st.info("👀 **Read-Only**\nView mode only")


if __name__ == "__main__":
    main()
