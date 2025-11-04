"""
AI Writing Assistant Page

Provides a conversational interface for multi-turn AI interactions with context persistence.
Users can chat with the AI assistant to get help with grant proposals, reports, and other writing tasks.
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
    page_title="AI Writing Assistant - Org Archivist",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Initialize session state variables for chat functionality."""
    # Message history stored in session
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Current conversation ID
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None

    # Conversation history from backend (for context)
    if "conversation_history" not in st.session_state:
        st.session_state.conversation_history = []

    # Message count tracker
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0


def display_message(message: Dict[str, Any], sources: Optional[List[Dict[str, Any]]] = None):
    """
    Display a single chat message with optional sources.

    Args:
        message: Message dict with role and content
        sources: Optional list of source citations
    """
    role = message.get("role", "assistant")
    content = message.get("content", "")

    with st.chat_message(role):
        st.markdown(content)

        # Display sources if available
        if sources and len(sources) > 0:
            with st.expander(f"📚 {len(sources)} Source{'s' if len(sources) > 1 else ''} Referenced"):
                for idx, source in enumerate(sources, 1):
                    st.markdown(f"""
                    **{idx}. {source.get('filename', 'Unknown Document')}**
                    - Type: {source.get('doc_type', 'N/A')}
                    - Year: {source.get('year', 'N/A')}
                    - Relevance: {source.get('relevance', 0):.0%}

                    > {source.get('excerpt', 'No excerpt available')}
                    """)


def send_message(user_message: str):
    """
    Send a message to the backend chat API and handle the response.

    Args:
        user_message: The user's message text
    """
    client = get_api_client()

    try:
        # Prepare conversation history for API call
        # Convert session messages to API format
        conversation_history = [
            {
                "role": msg["role"],
                "content": msg["content"]
            }
            for msg in st.session_state.messages
        ]

        # Call backend chat API
        with st.spinner("Thinking..."):
            response = client.send_chat_message(
                message=user_message,
                conversation_id=st.session_state.conversation_id,
                context=None,  # TODO: Add context support (writing style, audience, etc.)
                stream=False
            )

        # Update conversation ID if this is a new conversation
        if not st.session_state.conversation_id:
            st.session_state.conversation_id = response.get("conversation_id")

        # Extract response data
        assistant_message = response.get("message", "")
        sources = response.get("sources", [])

        # Update message count
        st.session_state.message_count = response.get("message_count", len(st.session_state.messages) + 2)

        # Add user message to session
        st.session_state.messages.append({
            "role": "user",
            "content": user_message,
            "sources": None
        })

        # Add assistant response to session
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message,
            "sources": sources if sources else None
        })

        # Update conversation history for next request
        st.session_state.conversation_history = conversation_history + [
            {"role": "user", "content": user_message},
            {"role": "assistant", "content": assistant_message}
        ]

        logger.info(f"Chat message sent successfully. Conversation ID: {st.session_state.conversation_id}")

    except AuthenticationError as e:
        st.error("Authentication required. Please log in again.")
        logger.error(f"Authentication error in chat: {e}")
    except APIError as e:
        st.error(f"Failed to send message: {e.message}")
        logger.error(f"API error in chat: {e}")
    except Exception as e:
        st.error(f"An unexpected error occurred: {str(e)}")
        logger.error(f"Unexpected error in chat: {e}", exc_info=True)


def clear_conversation():
    """Clear the current conversation and start fresh."""
    st.session_state.messages = []
    st.session_state.conversation_id = None
    st.session_state.conversation_history = []
    st.session_state.message_count = 0
    logger.info("Conversation cleared")


def main():
    """Main application entry point."""
    init_session_state()

    # Header
    st.title("💬 AI Writing Assistant")
    st.markdown("""
    Get AI-powered help with grant proposals, reports, and other writing tasks.
    The assistant learns from your organization's past documents to write in your unique voice.
    """)

    # Sidebar
    with st.sidebar:
        st.markdown("### Conversation")

        # Display conversation stats
        if st.session_state.conversation_id:
            st.info(f"""
            **Active Conversation**
            - Messages: {st.session_state.message_count}
            - ID: `{st.session_state.conversation_id[:8]}...`
            """)
        else:
            st.info("No active conversation. Start chatting to begin!")

        # Clear conversation button
        if st.button("🔄 New Conversation", use_container_width=True):
            clear_conversation()
            st.rerun()

        st.markdown("---")

        # TODO: Add conversation context controls
        st.markdown("### Context Settings")
        st.info("💡 Context controls (writing style, audience, etc.) coming soon!")

        # Placeholder for future features
        # writing_style = st.selectbox("Writing Style", ["Default", "Formal", "Conversational"])
        # audience = st.selectbox("Audience", ["General", "Federal RFP", "Foundation Grant"])
        # section = st.selectbox("Section", ["Introduction", "Problem Statement", "Methodology"])

    # Main chat area
    st.markdown("---")

    # Display chat history
    for idx, message in enumerate(st.session_state.messages):
        display_message(message, message.get("sources"))

    # Chat input
    # Using st.chat_input for better UX (appears at bottom of screen)
    if prompt := st.chat_input("Ask me anything about your writing project..."):
        send_message(prompt)
        # Rerun to display the new messages
        st.rerun()

    # Help section
    with st.expander("💡 Tips for Getting the Best Results"):
        st.markdown("""
        **Effective Prompts:**
        - Be specific about what you need help with
        - Provide context about your audience and purpose
        - Ask follow-up questions to refine the response
        - Request specific sections or formats

        **Examples:**
        - "Help me write an introduction for a federal grant proposal focused on youth education."
        - "Can you suggest ways to strengthen this problem statement?"
        - "What should I include in the methodology section for a foundation grant?"
        - "Draft a compelling executive summary for our annual report."

        **Note:** This is currently using stub responses. Full AI capabilities will be enabled soon!
        """)


if __name__ == "__main__":
    main()
