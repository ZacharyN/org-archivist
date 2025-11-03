"""
Chat API endpoint

This module provides a conversational interface for multi-turn interactions:
- POST /api/chat - Send a message and receive a response with context
- GET /api/chat/{conversation_id} - Get conversation history
- GET /api/chat - List all conversations
- DELETE /api/chat/{conversation_id} - Delete a conversation
"""

import json
from typing import List, Optional
from fastapi import APIRouter, HTTPException, status, Depends
from uuid import uuid4, UUID
from datetime import datetime

from ..models.query import ChatMessage, ChatRequest, ChatResponse, Source
from ..models.conversation import ConversationContext, SessionMetadata
from ..models.common import ErrorResponse
from ..services.database import DatabaseService
from ..dependencies import get_database

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post(
    "",
    response_model=ChatResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid request"},
        500: {"model": ErrorResponse, "description": "Chat failed"},
    },
    summary="Send a chat message",
    description="""
    Send a message in a conversational context and receive a response.

    This endpoint supports multi-turn conversations by maintaining context:
    - Accepts conversation history from previous turns
    - Determines if RAG retrieval is needed based on query intent
    - Maintains conversation state for coherent multi-turn dialogue
    - Returns response with optional source citations

    Features:
    - Context-aware responses that reference previous messages
    - Automatic RAG integration when factual information is needed
    - Conversation history management
    - Source citation tracking across turns

    The conversation context is provided by the client and includes:
    - Previous user messages
    - Previous assistant responses
    - Any retrieved sources from previous turns

    This allows for natural follow-up questions like:
    - "Tell me more about that"
    - "Can you elaborate on the second point?"
    - "What's another example?"
    """,
)
async def chat(
    request: ChatRequest,
    db: DatabaseService = Depends(get_database)
) -> ChatResponse:
    """
    Send a chat message and receive a context-aware response.

    Args:
        request: Chat request with message and conversation history
        db: Database service for conversation persistence

    Returns:
        ChatResponse with assistant message, sources, and conversation metadata

    Raises:
        HTTPException: If message is invalid or chat fails
    """
    try:
        # Validate request
        if not request.message or not request.message.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Message is required"
            )

        # Get or create conversation
        conversation_id = request.conversation_id or str(uuid4())
        conversation_uuid = UUID(conversation_id)

        # Check if conversation exists
        existing_conversation = await db.get_conversation(conversation_uuid)

        current_time = datetime.utcnow()

        if existing_conversation is None:
            # Create new conversation with initialized context
            # Initialize session metadata for new conversations
            initial_context = {
                "session_metadata": {
                    "started_at": current_time.isoformat(),
                    "last_active": current_time.isoformat()
                },
                "artifacts": []
            }

            # Merge with any context from request
            if request.context:
                context_dict = request.context.model_dump(exclude_none=True)
                initial_context.update(context_dict)
                # Ensure session_metadata is preserved
                if "session_metadata" not in context_dict:
                    initial_context["session_metadata"] = {
                        "started_at": current_time.isoformat(),
                        "last_active": current_time.isoformat()
                    }

            await db.create_conversation(
                conversation_id=conversation_uuid,
                name=None,
                user_id=None,
                metadata={},
                context=initial_context
            )

        # Add user message to database
        user_message_id = uuid4()
        await db.add_message(
            message_id=user_message_id,
            conversation_id=conversation_uuid,
            role="user",
            content=request.message,
            sources=None,
            metadata={}
        )

        # Update context if provided in request
        # Get current conversation to access existing context
        conversation = await db.get_conversation(conversation_uuid)
        current_context = conversation.get("context", {}) if conversation else {}

        # Handle case where context might be stored as a string (JSON)
        if isinstance(current_context, str):
            try:
                current_context = json.loads(current_context)
            except json.JSONDecodeError:
                current_context = {}

        # Build updated context
        updated_context = current_context.copy() if isinstance(current_context, dict) else {}

        # Update with request context if provided
        if request.context:
            context_dict = request.context.model_dump(exclude_none=True)
            updated_context.update(context_dict)

        # Update last_query and last_active
        updated_context["last_query"] = request.message
        if "session_metadata" not in updated_context:
            updated_context["session_metadata"] = {
                "started_at": current_time.isoformat(),
                "last_active": current_time.isoformat()
            }
        else:
            # Preserve started_at, update last_active
            session_meta = updated_context.get("session_metadata", {})
            updated_context["session_metadata"] = {
                "started_at": session_meta.get("started_at", current_time.isoformat()),
                "last_active": current_time.isoformat()
            }

        # Save updated context atomically (convert to JSON for database)
        await db.update_conversation(
            conversation_id=conversation_uuid,
            context=json.dumps(updated_context)
        )

        # TODO: Implement actual chat logic
        # 1. Analyze message intent
        # needs_rag = analyze_intent(request.message, conversation["messages"])

        # 2. If RAG needed, retrieve context
        # if needs_rag:
        #     retrieval_engine = get_retrieval_engine()
        #     context = await retrieval_engine.retrieve(
        #         query=request.message,
        #         conversation_history=conversation["messages"],
        #         top_k=3
        #     )
        # else:
        #     context = []

        # 3. Build chat prompt with conversation history
        # prompt_manager = get_prompt_manager()
        # system_prompt = prompt_manager.build_chat_system_prompt()
        # messages = build_chat_messages(
        #     conversation["messages"],
        #     context
        # )

        # 4. Generate response
        # generation_service = get_generation_service()
        # response = await generation_service.generate_chat(
        #     messages=messages,
        #     system_prompt=system_prompt
        # )

        # Get conversation with messages for context
        conversation = await db.get_conversation(conversation_uuid)
        message_count = len(conversation["messages"]) if conversation else 0

        # Stub response
        response_text = f"""Thank you for your message. This is a stub chat response.

Your message: "{request.message}"

This endpoint will provide context-aware responses based on:
- Your conversation history ({len(request.conversation_history)} previous messages in request)
- Current conversation has {message_count} total messages in database
- Retrieved document context when needed
- Multi-turn dialogue capabilities

Once fully implemented, I'll be able to:
- Answer follow-up questions
- Reference previous parts of our conversation
- Provide citations to organizational documents
- Help you draft grant proposals collaboratively
"""

        # Stub sources (if RAG was used)
        sources = []
        if len(request.message) > 20:  # Simple heuristic - longer messages might need RAG
            sources = [
                Source(
                    id=1,
                    filename="conversation_context.md",
                    doc_type="Internal",
                    year=2024,
                    excerpt="Relevant context from previous conversation...",
                    relevance=0.92
                )
            ]

        # Add assistant message to database
        assistant_message_id = uuid4()
        await db.add_message(
            message_id=assistant_message_id,
            conversation_id=conversation_uuid,
            role="assistant",
            content=response_text,
            sources=[s.dict() for s in sources] if sources else None,
            metadata={}
        )

        # Get updated conversation
        updated_conversation = await db.get_conversation(conversation_uuid)

        # Parse context for response
        conversation_context = None
        try:
            context_data = updated_conversation.get("context", {})
            if context_data:
                conversation_context = ConversationContext(**context_data)
        except Exception:
            # Handle corrupted/invalid context gracefully
            conversation_context = None

        return ChatResponse(
            message=response_text,
            sources=sources,
            conversation_id=conversation_id,
            message_count=len(updated_conversation["messages"]),
            requires_rag=len(sources) > 0,
            metadata={
                "model": "claude-sonnet-4.5",
                "tokens_used": 0,
                "context_messages": len(request.conversation_history),
                "timestamp": datetime.utcnow().isoformat()
            },
            context=conversation_context
        )

    except HTTPException:
        raise
    except ValueError as e:
        # Handle UUID parsing errors
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid conversation ID format: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Chat failed: {str(e)}"
        )


@router.get(
    "/{conversation_id}",
    summary="Get conversation history",
    description="Retrieve the full message history for a conversation",
)
async def get_conversation(
    conversation_id: str,
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    Get conversation history by ID.

    Args:
        conversation_id: UUID of the conversation
        db: Database service

    Returns:
        Conversation object with all messages

    Raises:
        HTTPException: If conversation not found
    """
    try:
        conversation_uuid = UUID(conversation_id)
        conversation = await db.get_conversation(conversation_uuid)

        if conversation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )

        return conversation

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get conversation: {str(e)}"
        )


@router.delete(
    "/{conversation_id}",
    summary="Delete conversation",
    description="Delete a conversation and all its messages",
)
async def delete_conversation(
    conversation_id: str,
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    Delete a conversation.

    Args:
        conversation_id: UUID of the conversation
        db: Database service

    Returns:
        Success message

    Raises:
        HTTPException: If conversation not found
    """
    try:
        conversation_uuid = UUID(conversation_id)
        deleted = await db.delete_conversation(conversation_uuid)

        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Conversation {conversation_id} not found"
            )

        return {
            "success": True,
            "message": f"Conversation {conversation_id} deleted",
            "conversation_id": conversation_id
        }

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid conversation ID format"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete conversation: {str(e)}"
        )


@router.get(
    "",
    summary="List all conversations",
    description="Get a list of all conversation IDs and metadata",
)
async def list_conversations(
    user_id: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: DatabaseService = Depends(get_database)
) -> dict:
    """
    List all conversations.

    Args:
        user_id: Optional filter by user ID
        skip: Number of conversations to skip (for pagination)
        limit: Maximum number of conversations to return
        db: Database service

    Returns:
        List of conversation metadata (without full message history)
    """
    try:
        conversations = await db.list_conversations(
            user_id=user_id,
            skip=skip,
            limit=limit
        )

        # Add preview from first message if messages exist
        for conv in conversations:
            # Fetch just the first message for preview
            try:
                conv_uuid = UUID(conv["conversation_id"])
                full_conv = await db.get_conversation(conv_uuid)
                if full_conv and full_conv.get("messages"):
                    first_msg = full_conv["messages"][0]
                    conv["preview"] = first_msg["content"][:100] if first_msg["content"] else ""
                else:
                    conv["preview"] = ""
            except Exception:
                conv["preview"] = ""

        return {
            "conversations": conversations,
            "total_count": len(conversations),
            "skip": skip,
            "limit": limit
        }

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list conversations: {str(e)}"
        )
