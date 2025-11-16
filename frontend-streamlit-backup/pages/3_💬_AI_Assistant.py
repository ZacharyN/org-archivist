"""
AI Writing Assistant Page

Provides a conversational interface for multi-turn AI interactions with context persistence.
Users can chat with the AI assistant to get help with grant proposals, reports, and other writing tasks.
"""

import streamlit as st
from typing import Dict, Any, List, Optional
import logging
from datetime import datetime

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

    # Conversation list from backend
    if "conversations_list" not in st.session_state:
        st.session_state.conversations_list = []

    # Search query for conversations
    if "conversation_search" not in st.session_state:
        st.session_state.conversation_search = ""

    # Delete confirmation state
    if "delete_confirm_id" not in st.session_state:
        st.session_state.delete_confirm_id = None

    # Conversation context settings
    if "context_writing_style" not in st.session_state:
        st.session_state.context_writing_style = None

    if "context_audience" not in st.session_state:
        st.session_state.context_audience = None

    if "context_section" not in st.session_state:
        st.session_state.context_section = None

    if "context_tone" not in st.session_state:
        st.session_state.context_tone = 0.5

    if "context_doc_types" not in st.session_state:
        st.session_state.context_doc_types = []

    if "context_years" not in st.session_state:
        st.session_state.context_years = []

    if "context_programs" not in st.session_state:
        st.session_state.context_programs = []

    # Context panel expanded state
    if "context_expanded" not in st.session_state:
        st.session_state.context_expanded = False


def display_message(message: Dict[str, Any], sources: Optional[List[Dict[str, Any]]] = None):
    """
    Display a single chat message with optional sources and metadata.

    Args:
        message: Message dict with role, content, timestamp, and optional metadata
        sources: Optional list of source citations
    """
    role = message.get("role", "assistant")
    content = message.get("content", "")
    timestamp = message.get("timestamp")
    metadata = message.get("metadata", {})

    with st.chat_message(role):
        # Display message content
        st.markdown(content)

        # Display metadata for assistant messages
        if role == "assistant" and metadata:
            cols = st.columns([2, 2, 2, 2])

            # Generation time
            if "generation_time" in metadata:
                gen_time = metadata["generation_time"]
                with cols[0]:
                    st.caption(f"⏱️ {gen_time:.1f}s")

            # Confidence score
            if "confidence" in metadata:
                confidence = metadata["confidence"]
                # Color code confidence: green >0.8, yellow 0.6-0.8, red <0.6
                if confidence >= 0.8:
                    color = "🟢"
                elif confidence >= 0.6:
                    color = "🟡"
                else:
                    color = "🔴"
                with cols[1]:
                    st.caption(f"{color} {confidence:.0%}")

            # Token count
            if "token_count" in metadata:
                with cols[2]:
                    st.caption(f"📝 {metadata['token_count']} tokens")

            # Model used
            if "model" in metadata:
                model_name = metadata["model"].split("-")[-1] if "-" in metadata["model"] else metadata["model"]
                with cols[3]:
                    st.caption(f"🤖 {model_name}")

        # Display timestamp
        if timestamp:
            # Parse timestamp if it's a string
            if isinstance(timestamp, str):
                try:
                    timestamp_dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    time_str = timestamp_dt.strftime("%I:%M %p")
                except Exception:
                    time_str = timestamp
            elif isinstance(timestamp, datetime):
                time_str = timestamp.strftime("%I:%M %p")
            else:
                time_str = str(timestamp)

            st.caption(f"🕒 {time_str}")

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

        # Build context from session state
        context = {}
        if st.session_state.context_writing_style:
            context["writing_style"] = st.session_state.context_writing_style
        if st.session_state.context_audience:
            context["audience"] = st.session_state.context_audience
        if st.session_state.context_section:
            context["section"] = st.session_state.context_section
        if st.session_state.context_tone is not None:
            context["tone"] = st.session_state.context_tone

        # Add document filters if any are set
        filters = {}
        if st.session_state.context_doc_types:
            filters["doc_types"] = st.session_state.context_doc_types
        if st.session_state.context_years:
            filters["years"] = st.session_state.context_years
        if st.session_state.context_programs:
            filters["programs"] = st.session_state.context_programs

        if filters:
            context["filters"] = filters

        # Call backend chat API
        with st.spinner("Thinking..."):
            response = client.send_chat_message(
                message=user_message,
                conversation_id=st.session_state.conversation_id,
                context=context if context else None,
                stream=False
            )

        # Update conversation ID if this is a new conversation
        if not st.session_state.conversation_id:
            st.session_state.conversation_id = response.get("conversation_id")

        # Extract response data
        assistant_message = response.get("message", "")
        sources = response.get("sources", [])
        metadata = response.get("metadata", {})

        # Update message count
        st.session_state.message_count = response.get("message_count", len(st.session_state.messages) + 2)

        # Add user message to session with timestamp
        st.session_state.messages.append({
            "role": "user",
            "content": user_message,
            "sources": None,
            "timestamp": datetime.now().isoformat()
        })

        # Add assistant response to session with timestamp and metadata
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_message,
            "sources": sources if sources else None,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata
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


def load_conversations():
    """Load conversation history from backend."""
    try:
        client = get_api_client()
        conversations = client.get_conversations(skip=0, limit=50)
        st.session_state.conversations_list = conversations if conversations else []
        logger.info(f"Loaded {len(st.session_state.conversations_list)} conversations")
    except AuthenticationError:
        st.error("Please log in to access conversations.")
        logger.error("Authentication error loading conversations")
    except APIError as e:
        st.error(f"Failed to load conversations: {e.message}")
        logger.error(f"API error loading conversations: {e}")
    except Exception as e:
        st.error(f"Unexpected error loading conversations: {str(e)}")
        logger.error(f"Unexpected error loading conversations: {e}", exc_info=True)


def load_conversation(conversation_id: str):
    """
    Load a specific conversation and set it as active.

    Args:
        conversation_id: UUID of conversation to load
    """
    try:
        client = get_api_client()
        with st.spinner("Loading conversation..."):
            conversation = client.get_conversation(conversation_id)

        # Update session state with loaded conversation
        st.session_state.conversation_id = conversation_id
        st.session_state.messages = conversation.get("messages", [])
        st.session_state.message_count = len(st.session_state.messages)

        # Load context if available
        context = conversation.get("context", {})
        st.session_state.context_writing_style = context.get("writing_style")
        st.session_state.context_audience = context.get("audience")
        st.session_state.context_section = context.get("section")
        st.session_state.context_tone = context.get("tone", 0.5)

        filters = context.get("filters", {})
        st.session_state.context_doc_types = filters.get("doc_types", [])
        st.session_state.context_years = filters.get("years", [])
        st.session_state.context_programs = filters.get("programs", [])

        logger.info(f"Loaded conversation: {conversation_id}")
        st.success(f"Loaded conversation with {st.session_state.message_count} messages")

    except AuthenticationError:
        st.error("Please log in to access conversations.")
        logger.error("Authentication error loading conversation")
    except APIError as e:
        st.error(f"Failed to load conversation: {e.message}")
        logger.error(f"API error loading conversation {conversation_id}: {e}")
    except Exception as e:
        st.error(f"Unexpected error loading conversation: {str(e)}")
        logger.error(f"Unexpected error loading conversation {conversation_id}: {e}", exc_info=True)


def delete_conversation_confirm(conversation_id: str):
    """
    Delete a conversation after confirmation.

    Args:
        conversation_id: UUID of conversation to delete
    """
    try:
        client = get_api_client()
        with st.spinner("Deleting conversation..."):
            client.delete_conversation(conversation_id)

        # Clear active conversation if it was deleted
        if st.session_state.conversation_id == conversation_id:
            clear_conversation()

        # Reload conversation list
        load_conversations()

        # Clear delete confirmation state
        st.session_state.delete_confirm_id = None

        st.success("Conversation deleted successfully")
        logger.info(f"Deleted conversation: {conversation_id}")

    except AuthenticationError:
        st.error("Please log in to delete conversations.")
        logger.error("Authentication error deleting conversation")
    except APIError as e:
        st.error(f"Failed to delete conversation: {e.message}")
        logger.error(f"API error deleting conversation {conversation_id}: {e}")
    except Exception as e:
        st.error(f"Unexpected error deleting conversation: {str(e)}")
        logger.error(f"Unexpected error deleting conversation {conversation_id}: {e}", exc_info=True)


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

        # Conversation History Panel
        st.markdown("### Conversation History")

        # Load conversations button
        col_load, col_refresh = st.columns([3, 1])
        with col_load:
            if st.button("📚 Load History", use_container_width=True):
                load_conversations()
                st.rerun()
        with col_refresh:
            if st.button("🔄", use_container_width=True, help="Refresh conversation list"):
                load_conversations()
                st.rerun()

        # Search/filter conversations
        search_query = st.text_input(
            "Search conversations",
            value=st.session_state.conversation_search,
            placeholder="Search by message content...",
            label_visibility="collapsed"
        )
        st.session_state.conversation_search = search_query

        # Display conversation list
        if st.session_state.conversations_list:
            # Filter conversations by search query
            filtered_conversations = st.session_state.conversations_list
            if search_query:
                filtered_conversations = [
                    conv for conv in st.session_state.conversations_list
                    if search_query.lower() in str(conv.get('messages', [])).lower()
                    or search_query.lower() in str(conv.get('conversation_id', '')).lower()
                ]

            if filtered_conversations:
                st.markdown(f"**{len(filtered_conversations)} conversation(s)**")

                # Display each conversation
                for conv in filtered_conversations:
                    conversation_id = conv.get('conversation_id')
                    messages = conv.get('messages', [])
                    message_count = len(messages)
                    created_at = conv.get('created_at', '')

                    # Get first user message as preview
                    preview = "No messages"
                    for msg in messages:
                        if msg.get('role') == 'user':
                            preview = msg.get('content', '')[:50]
                            if len(msg.get('content', '')) > 50:
                                preview += "..."
                            break

                    # Create expandable container for each conversation
                    with st.container():
                        col_info, col_actions = st.columns([4, 1])

                        with col_info:
                            # Load conversation button
                            is_active = st.session_state.conversation_id == conversation_id
                            button_label = f"{'🟢' if is_active else '💬'} {message_count} msgs"
                            if st.button(
                                button_label,
                                key=f"load_{conversation_id}",
                                use_container_width=True,
                                type="primary" if is_active else "secondary"
                            ):
                                load_conversation(conversation_id)
                                st.rerun()

                            # Preview text
                            st.caption(f"{preview}")

                        with col_actions:
                            # Delete button with confirmation
                            if st.session_state.delete_confirm_id == conversation_id:
                                if st.button("✅", key=f"confirm_{conversation_id}", use_container_width=True, help="Confirm delete"):
                                    delete_conversation_confirm(conversation_id)
                                    st.rerun()
                                if st.button("❌", key=f"cancel_{conversation_id}", use_container_width=True, help="Cancel"):
                                    st.session_state.delete_confirm_id = None
                                    st.rerun()
                            else:
                                if st.button("🗑️", key=f"delete_{conversation_id}", use_container_width=True, help="Delete conversation"):
                                    st.session_state.delete_confirm_id = conversation_id
                                    st.rerun()

                        st.markdown("---")
            else:
                st.info("No conversations match your search.")
        else:
            st.info("No conversation history. Click 'Load History' to fetch your conversations.")

        st.markdown("---")

        # Context Settings Panel
        st.markdown("### Context Settings")

        # Collapsible context panel
        with st.expander("⚙️ Configure Context", expanded=st.session_state.context_expanded):
            st.markdown("**Writing Parameters**")

            # Writing Style selector
            style_options = ["None", "Professional", "Academic", "Conversational", "Persuasive", "Technical"]
            current_style_index = 0
            if st.session_state.context_writing_style:
                try:
                    current_style_index = style_options.index(st.session_state.context_writing_style)
                except ValueError:
                    current_style_index = 0

            writing_style = st.selectbox(
                "Writing Style",
                options=style_options,
                index=current_style_index,
                help="Select the writing style for AI responses"
            )
            st.session_state.context_writing_style = None if writing_style == "None" else writing_style

            # Audience dropdown
            audience_options = [
                "None",
                "Federal Grant Reviewers",
                "Foundation Grant Reviewers",
                "Board Members",
                "General Public",
                "Donors",
                "Stakeholders"
            ]
            current_audience_index = 0
            if st.session_state.context_audience:
                try:
                    current_audience_index = audience_options.index(st.session_state.context_audience)
                except ValueError:
                    current_audience_index = 0

            audience = st.selectbox(
                "Target Audience",
                options=audience_options,
                index=current_audience_index,
                help="Who will be reading this content?"
            )
            st.session_state.context_audience = None if audience == "None" else audience

            # Section dropdown
            section_options = [
                "None",
                "Executive Summary",
                "Problem Statement",
                "Project Description",
                "Methodology",
                "Budget Narrative",
                "Evaluation Plan",
                "Sustainability"
            ]
            current_section_index = 0
            if st.session_state.context_section:
                try:
                    current_section_index = section_options.index(st.session_state.context_section)
                except ValueError:
                    current_section_index = 0

            section = st.selectbox(
                "Document Section",
                options=section_options,
                index=current_section_index,
                help="What part of the document are you working on?"
            )
            st.session_state.context_section = None if section == "None" else section

            # Tone slider
            tone = st.slider(
                "Tone Level",
                min_value=0.0,
                max_value=1.0,
                value=st.session_state.context_tone,
                step=0.1,
                help="0 = Formal/Professional, 1 = Casual/Conversational"
            )
            st.session_state.context_tone = tone

            st.markdown("---")
            st.markdown("**Document Filters**")

            # Document type filters
            doc_type_options = ["Grant Proposal", "Report", "Letter", "Email", "Presentation", "Other"]
            doc_types = st.multiselect(
                "Document Types",
                options=doc_type_options,
                default=st.session_state.context_doc_types,
                help="Filter by document types to reference"
            )
            st.session_state.context_doc_types = doc_types

            # Year filters
            current_year = 2024
            year_options = list(range(current_year, current_year - 10, -1))
            years = st.multiselect(
                "Years",
                options=year_options,
                default=st.session_state.context_years,
                help="Filter documents by year"
            )
            st.session_state.context_years = years

            # Program filters
            program_options = ["Education", "Health", "Environment", "Arts", "Social Services", "Other"]
            programs = st.multiselect(
                "Programs",
                options=program_options,
                default=st.session_state.context_programs,
                help="Filter by program area"
            )
            st.session_state.context_programs = programs

            st.markdown("---")

            # Save Context button
            if st.button("💾 Save Context", use_container_width=True, type="primary"):
                if st.session_state.conversation_id:
                    try:
                        client = get_api_client()

                        # Prepare context payload
                        context_data = {}
                        if st.session_state.context_writing_style:
                            context_data["writing_style"] = st.session_state.context_writing_style
                        if st.session_state.context_audience:
                            context_data["audience"] = st.session_state.context_audience
                        if st.session_state.context_section:
                            context_data["section"] = st.session_state.context_section
                        if st.session_state.context_tone is not None:
                            context_data["tone"] = st.session_state.context_tone

                        # Add filters
                        filters = {}
                        if st.session_state.context_doc_types:
                            filters["doc_types"] = st.session_state.context_doc_types
                        if st.session_state.context_years:
                            filters["years"] = st.session_state.context_years
                        if st.session_state.context_programs:
                            filters["programs"] = st.session_state.context_programs

                        if filters:
                            context_data["filters"] = filters

                        # Save to backend
                        with st.spinner("Saving context..."):
                            response = client.update_conversation_context(
                                conversation_id=st.session_state.conversation_id,
                                context=context_data
                            )

                        if response.get("success"):
                            st.success("✅ Context saved successfully!")
                            logger.info(f"Context saved for conversation {st.session_state.conversation_id}")
                        else:
                            st.error(f"Failed to save context: {response.get('message', 'Unknown error')}")

                    except AuthenticationError:
                        st.error("Authentication required. Please log in again.")
                    except APIError as e:
                        st.error(f"Failed to save context: {e.message}")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {str(e)}")
                        logger.error(f"Error saving context: {e}", exc_info=True)
                else:
                    st.warning("💡 Start a conversation first to save context!")

        # Display current context summary
        st.markdown("**Current Context:**")
        context_summary = []
        if st.session_state.context_writing_style:
            context_summary.append(f"📝 Style: {st.session_state.context_writing_style}")
        if st.session_state.context_audience:
            context_summary.append(f"👥 Audience: {st.session_state.context_audience}")
        if st.session_state.context_section:
            context_summary.append(f"📄 Section: {st.session_state.context_section}")

        if context_summary:
            for item in context_summary:
                st.markdown(f"- {item}")
            st.markdown(f"- 🎭 Tone: {st.session_state.context_tone:.1f}")
        else:
            st.info("No context configured")

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
        **Keyboard Shortcuts:**
        - **Enter** - Send message
        - **Shift + Enter** - Add new line in message (multi-line messages)

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

        **Understanding Response Metrics:**
        - ⏱️ **Generation Time** - How long the AI took to generate the response
        - 🟢🟡🔴 **Confidence** - AI's confidence in the response (Green >80%, Yellow 60-80%, Red <60%)
        - 📝 **Token Count** - Length of the response in tokens
        - 🤖 **Model** - Which AI model generated the response
        """)


if __name__ == "__main__":
    main()
