"""
API client for backend communication with JWT authentication.

This module provides a centralized, fully-typed API client for all backend communications
with comprehensive JWT authentication, automatic token refresh, retry logic, and error handling.
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable, Iterator
from enum import Enum

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st

from config.settings import settings


logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base exception for API errors."""

    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[requests.Response] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response = response


class AuthenticationError(APIError):
    """Raised when authentication fails."""
    pass


class AuthorizationError(APIError):
    """Raised when user lacks permission for an operation."""
    pass


class ValidationError(APIError):
    """Raised when request validation fails."""
    pass


class NotFoundError(APIError):
    """Raised when a resource is not found."""
    pass


class ServerError(APIError):
    """Raised when server encounters an error."""
    pass


class TokenManager:
    """
    Manages JWT token storage and refresh.

    Stores tokens in Streamlit session state and handles automatic refresh.
    """

    def __init__(self):
        """Initialize token manager."""
        self._ensure_session_state()

    def _ensure_session_state(self) -> None:
        """Ensure session state variables exist."""
        if 'api_token' not in st.session_state:
            st.session_state.api_token = None
        if 'refresh_token' not in st.session_state:
            st.session_state.refresh_token = None
        if 'token_expires_at' not in st.session_state:
            st.session_state.token_expires_at = None

    @property
    def access_token(self) -> Optional[str]:
        """Get current access token."""
        return st.session_state.get('api_token')

    @access_token.setter
    def access_token(self, value: Optional[str]) -> None:
        """Set access token."""
        st.session_state.api_token = value

    @property
    def refresh_token(self) -> Optional[str]:
        """Get current refresh token."""
        return st.session_state.get('refresh_token')

    @refresh_token.setter
    def refresh_token(self, value: Optional[str]) -> None:
        """Set refresh token."""
        st.session_state.refresh_token = value

    @property
    def token_expires_at(self) -> Optional[datetime]:
        """Get token expiration time."""
        return st.session_state.get('token_expires_at')

    @token_expires_at.setter
    def token_expires_at(self, value: Optional[datetime]) -> None:
        """Set token expiration time."""
        st.session_state.token_expires_at = value

    def is_token_expired(self) -> bool:
        """
        Check if current token is expired or about to expire.

        Returns:
            True if token is expired or expires within 5 minutes
        """
        if not self.token_expires_at:
            return True

        # Consider token expired if it expires within 5 minutes
        buffer = timedelta(minutes=5)
        return datetime.now() >= (self.token_expires_at - buffer)

    def clear_tokens(self) -> None:
        """Clear all authentication tokens."""
        self.access_token = None
        self.refresh_token = None
        self.token_expires_at = None
        logger.info("Cleared authentication tokens")

    def set_tokens(self, access_token: str, refresh_token: str, expires_at: datetime) -> None:
        """
        Set authentication tokens.

        Args:
            access_token: JWT access token
            refresh_token: JWT refresh token
            expires_at: Token expiration datetime
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expires_at = expires_at
        logger.info(f"Set authentication tokens (expires at {expires_at})")


class APIClient:
    """
    Comprehensive API client for Org Archivist backend.

    Features:
    - JWT authentication with automatic token refresh
    - Automatic retry with exponential backoff
    - Comprehensive error handling with typed exceptions
    - Support for all backend endpoints
    - Streaming support for AI responses
    - File upload support
    - Full type hints for IDE support
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        token_manager: Optional[TokenManager] = None,
        auto_refresh: bool = True
    ):
        """
        Initialize the API client.

        Args:
            base_url: Base URL for the API (defaults to settings.API_BASE_URL)
            token_manager: TokenManager instance (creates new if None)
            auto_refresh: Automatically refresh expired tokens
        """
        self.base_url = (base_url or settings.API_BASE_URL).rstrip('/')
        self.token_manager = token_manager or TokenManager()
        self.auto_refresh = auto_refresh
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """
        Create a requests session with retry logic.

        Returns:
            Configured session with retry strategy
        """
        session = requests.Session()

        # Configure retry strategy
        # - 3 total retries
        # - Exponential backoff (1s, 2s, 4s)
        # - Retry on specific HTTP status codes
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE", "PATCH"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """
        Get request headers including authentication.

        Args:
            include_auth: Include Authorization header if token available

        Returns:
            Headers dictionary
        """
        headers = {"Content-Type": "application/json"}

        if include_auth and self.token_manager.access_token:
            headers["Authorization"] = f"Bearer {self.token_manager.access_token}"

        return headers

    def _handle_response(self, response: requests.Response) -> Any:
        """
        Handle API response and errors.

        Args:
            response: Response from requests

        Returns:
            Parsed JSON response or None

        Raises:
            AuthenticationError: For 401 errors
            AuthorizationError: For 403 errors
            NotFoundError: For 404 errors
            ValidationError: For 422 errors
            ServerError: For 5xx errors
            APIError: For other HTTP errors
        """
        try:
            response.raise_for_status()

            # Return None for empty responses
            if not response.content:
                return None

            # Try to parse JSON
            try:
                return response.json()
            except ValueError:
                return response.text

        except requests.HTTPError as e:
            # Try to get error message from response
            error_msg = str(e)
            detail = None

            try:
                error_data = response.json()
                detail = error_data.get("detail", error_msg)
            except:
                pass

            # Raise specific exception based on status code
            if response.status_code == 401:
                raise AuthenticationError(detail or "Authentication required", response.status_code, response)
            elif response.status_code == 403:
                raise AuthorizationError(detail or "Permission denied", response.status_code, response)
            elif response.status_code == 404:
                raise NotFoundError(detail or "Resource not found", response.status_code, response)
            elif response.status_code == 422:
                raise ValidationError(detail or "Validation error", response.status_code, response)
            elif response.status_code >= 500:
                raise ServerError(detail or "Server error", response.status_code, response)
            else:
                raise APIError(detail or error_msg, response.status_code, response)

    def _request(
        self,
        method: str,
        endpoint: str,
        include_auth: bool = True,
        auto_refresh: bool = True,
        **kwargs
    ) -> Any:
        """
        Execute HTTP request with error handling and optional token refresh.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE, etc.)
            endpoint: API endpoint path (without base URL)
            include_auth: Include authentication header
            auto_refresh: Attempt to refresh token if expired
            **kwargs: Additional arguments passed to requests

        Returns:
            Parsed response data

        Raises:
            Various APIError subclasses based on response
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        # Add headers
        headers = kwargs.pop('headers', {})
        headers.update(self._get_headers(include_auth=include_auth))

        # Check if token needs refresh (but only if we're including auth)
        if (include_auth and auto_refresh and self.auto_refresh and
            self.token_manager.access_token and self.token_manager.is_token_expired()):
            try:
                logger.info("Token expired, attempting refresh...")
                self.refresh_access_token()
                # Update headers with new token
                headers.update(self._get_headers(include_auth=include_auth))
            except Exception as e:
                logger.warning(f"Token refresh failed: {e}")
                # Continue with request - might still work or will fail with 401

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=headers,
                timeout=kwargs.pop('timeout', settings.API_TIMEOUT),
                **kwargs
            )
            return self._handle_response(response)

        except AuthenticationError as e:
            # If we get 401 and we have a refresh token, try refreshing once
            if auto_refresh and self.token_manager.refresh_token and not self.token_manager.is_token_expired():
                try:
                    logger.info("Got 401, attempting token refresh...")
                    self.refresh_access_token()
                    # Retry request with new token
                    headers.update(self._get_headers(include_auth=include_auth))
                    response = self.session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        timeout=kwargs.get('timeout', settings.API_TIMEOUT),
                        **kwargs
                    )
                    return self._handle_response(response)
                except Exception as refresh_error:
                    logger.error(f"Token refresh failed: {refresh_error}")
                    raise e
            raise

    # ========== Authentication Endpoints ==========

    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and get tokens.

        Args:
            email: User email
            password: User password

        Returns:
            Authentication response with tokens and user info

        Raises:
            AuthenticationError: If credentials are invalid
        """
        try:
            response = self._request(
                method="POST",
                endpoint="/api/auth/login",
                json={"email": email, "password": password},
                include_auth=False,  # No auth needed for login
                auto_refresh=False  # Can't refresh during login
            )

            # Store tokens
            if response and 'access_token' in response:
                expires_at = datetime.fromisoformat(response['expires_at'].replace('Z', '+00:00'))
                self.token_manager.set_tokens(
                    access_token=response['access_token'],
                    refresh_token=response['refresh_token'],
                    expires_at=expires_at
                )
                logger.info(f"Successfully logged in as {email}")

            return response

        except APIError as e:
            logger.error(f"Login failed for {email}: {e}")
            raise

    def logout(self) -> Dict[str, Any]:
        """
        Logout current user and invalidate session.

        Returns:
            Logout response
        """
        try:
            response = self._request(
                method="POST",
                endpoint="/api/auth/logout",
                auto_refresh=False  # Don't refresh during logout
            )

            # Clear local tokens
            self.token_manager.clear_tokens()
            logger.info("Successfully logged out")

            return response

        except APIError as e:
            logger.error(f"Logout failed: {e}")
            # Clear tokens anyway
            self.token_manager.clear_tokens()
            raise

    def refresh_access_token(self) -> Dict[str, Any]:
        """
        Refresh access token using refresh token.

        Returns:
            New authentication response with refreshed tokens

        Raises:
            AuthenticationError: If refresh fails
        """
        if not self.token_manager.refresh_token:
            raise AuthenticationError("No refresh token available")

        try:
            # Note: Assuming backend has a refresh endpoint
            # Adjust this based on actual backend implementation
            response = self._request(
                method="POST",
                endpoint="/api/auth/refresh",
                json={"refresh_token": self.token_manager.refresh_token},
                include_auth=False,
                auto_refresh=False
            )

            # Update tokens
            if response and 'access_token' in response:
                expires_at = datetime.fromisoformat(response['expires_at'].replace('Z', '+00:00'))
                self.token_manager.set_tokens(
                    access_token=response['access_token'],
                    refresh_token=response.get('refresh_token', self.token_manager.refresh_token),
                    expires_at=expires_at
                )
                logger.info("Successfully refreshed access token")

            return response

        except APIError as e:
            logger.error(f"Token refresh failed: {e}")
            # Clear tokens on refresh failure
            self.token_manager.clear_tokens()
            raise AuthenticationError("Failed to refresh token") from e

    def validate_session(self) -> Dict[str, Any]:
        """
        Validate current session.

        Returns:
            Session validation response with user info

        Raises:
            AuthenticationError: If session is invalid
        """
        return self._request(
            method="GET",
            endpoint="/api/auth/session"
        )

    def get_current_user(self) -> Dict[str, Any]:
        """
        Get current authenticated user's profile.

        Returns:
            User profile data

        Raises:
            AuthenticationError: If not authenticated
        """
        return self._request(
            method="GET",
            endpoint="/api/auth/me"
        )

    # ========== Document Endpoints ==========

    def get_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of documents.

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            filters: Optional filters (type, year, program, etc.)

        Returns:
            List of documents
        """
        params = {"skip": skip, "limit": limit}
        if filters:
            params.update(filters)

        return self._request(
            method="GET",
            endpoint="/api/documents",
            params=params
        )

    def get_document(self, document_id: str) -> Dict[str, Any]:
        """
        Get specific document by ID.

        Args:
            document_id: Document UUID

        Returns:
            Document data

        Raises:
            NotFoundError: If document not found
        """
        return self._request(
            method="GET",
            endpoint=f"/api/documents/{document_id}"
        )

    def upload_document(
        self,
        file,
        metadata: Dict[str, Any],
        sensitivity_confirmed: bool = False
    ) -> Dict[str, Any]:
        """
        Upload a document with metadata.

        Args:
            file: File object to upload
            metadata: Document metadata (type, year, programs, etc.)
            sensitivity_confirmed: User confirmed document is public

        Returns:
            Created document info

        Raises:
            ValidationError: If validation fails
        """
        # Prepare multipart/form-data
        files = {'file': file}
        data = {
            **metadata,
            'sensitivity_confirmed': sensitivity_confirmed
        }

        # Remove Content-Type header for multipart upload
        headers = self._get_headers(include_auth=True)
        headers.pop('Content-Type', None)

        return self._request(
            method="POST",
            endpoint="/api/documents/upload",
            files=files,
            data=data,
            headers=headers
        )

    def delete_document(self, document_id: str) -> Dict[str, Any]:
        """
        Delete a document.

        Args:
            document_id: Document UUID

        Returns:
            Deletion confirmation

        Raises:
            NotFoundError: If document not found
            AuthorizationError: If user lacks permission
        """
        return self._request(
            method="DELETE",
            endpoint=f"/api/documents/{document_id}"
        )

    # ========== Writing Styles Endpoints ==========

    def get_writing_styles(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """
        Get list of writing styles.

        Args:
            active_only: Only return active styles

        Returns:
            List of writing styles
        """
        params = {"active_only": active_only} if active_only else {}
        return self._request(
            method="GET",
            endpoint="/api/writing-styles",
            params=params
        )

    def get_writing_style(self, style_id: str) -> Dict[str, Any]:
        """
        Get specific writing style.

        Args:
            style_id: Writing style UUID

        Returns:
            Writing style data
        """
        return self._request(
            method="GET",
            endpoint=f"/api/writing-styles/{style_id}"
        )

    def create_writing_style(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new writing style.

        Args:
            data: Writing style data (name, type, samples, etc.)

        Returns:
            Created writing style

        Raises:
            ValidationError: If validation fails
        """
        return self._request(
            method="POST",
            endpoint="/api/writing-styles",
            json=data
        )

    def update_writing_style(self, style_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing writing style.

        Args:
            style_id: Writing style UUID
            data: Updated writing style data

        Returns:
            Updated writing style
        """
        return self._request(
            method="PUT",
            endpoint=f"/api/writing-styles/{style_id}",
            json=data
        )

    def delete_writing_style(self, style_id: str) -> Dict[str, Any]:
        """
        Delete a writing style.

        Args:
            style_id: Writing style UUID

        Returns:
            Deletion confirmation
        """
        return self._request(
            method="DELETE",
            endpoint=f"/api/writing-styles/{style_id}"
        )

    def analyze_writing_samples(self, samples: List[str], style_type: str) -> Dict[str, Any]:
        """
        Analyze writing samples and generate style prompt.

        Args:
            samples: List of writing sample texts
            style_type: Type of writing style (grant, proposal, report)

        Returns:
            AI-generated style analysis and prompt
        """
        return self._request(
            method="POST",
            endpoint="/api/writing-styles/analyze",
            json={"samples": samples, "style_type": style_type},
            timeout=120  # Longer timeout for AI analysis
        )

    # ========== Chat/Conversation Endpoints ==========

    def send_chat_message(
        self,
        message: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Send a chat message and get AI response.

        Args:
            message: User message
            conversation_id: Optional conversation ID to continue
            context: Optional conversation context (style, audience, etc.)
            stream: Return streaming response (not yet implemented)

        Returns:
            AI response with generated content
        """
        data = {
            "message": message,
            "conversation_id": conversation_id,
            "context": context or {}
        }

        return self._request(
            method="POST",
            endpoint="/api/chat",
            json=data,
            timeout=120  # Longer timeout for AI generation
        )

    def get_conversations(
        self,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get list of conversations.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversations
        """
        return self._request(
            method="GET",
            endpoint="/api/conversations",
            params={"skip": skip, "limit": limit}
        )

    def get_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Get specific conversation with full history.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Conversation data with messages
        """
        return self._request(
            method="GET",
            endpoint=f"/api/conversations/{conversation_id}"
        )

    def delete_conversation(self, conversation_id: str) -> Dict[str, Any]:
        """
        Delete a conversation.

        Args:
            conversation_id: Conversation UUID

        Returns:
            Deletion confirmation
        """
        return self._request(
            method="DELETE",
            endpoint=f"/api/conversations/{conversation_id}"
        )

    # ========== Outputs Endpoints ==========

    def get_outputs(
        self,
        skip: int = 0,
        limit: int = 100,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get list of past outputs.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters (type, status, date_range, etc.)

        Returns:
            List of outputs
        """
        params = {"skip": skip, "limit": limit}
        if filters:
            params.update(filters)

        return self._request(
            method="GET",
            endpoint="/api/outputs",
            params=params
        )

    def get_output(self, output_id: str) -> Dict[str, Any]:
        """
        Get specific output.

        Args:
            output_id: Output UUID

        Returns:
            Output data
        """
        return self._request(
            method="GET",
            endpoint=f"/api/outputs/{output_id}"
        )

    def create_output(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create/save a new output.

        Args:
            data: Output data (content, metadata, etc.)

        Returns:
            Created output
        """
        return self._request(
            method="POST",
            endpoint="/api/outputs",
            json=data
        )

    def update_output(self, output_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing output (e.g., mark success, add notes).

        Args:
            output_id: Output UUID
            data: Updated output data

        Returns:
            Updated output
        """
        return self._request(
            method="PUT",
            endpoint=f"/api/outputs/{output_id}",
            json=data
        )

    def delete_output(self, output_id: str) -> Dict[str, Any]:
        """
        Delete an output.

        Args:
            output_id: Output UUID

        Returns:
            Deletion confirmation
        """
        return self._request(
            method="DELETE",
            endpoint=f"/api/outputs/{output_id}"
        )

    # ========== Configuration Management ==========

    def get_config(self) -> Dict[str, Any]:
        """
        Get system configuration.

        Returns:
            Dictionary with complete configuration including:
            - llm_config: LLM model parameters
            - rag_config: RAG pipeline settings
            - user_preferences: User preference settings

        Raises:
            APIError: If request fails
        """
        return self._request(
            method="GET",
            endpoint="/api/config"
        )

    def update_config(self, config_update: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update system configuration.

        Only provided sections will be updated. For example, you can update
        just user preferences without affecting LLM or RAG config.

        Args:
            config_update: Dictionary with configuration updates
                Supported keys:
                - llm_config: LLM model configuration updates
                - rag_config: RAG pipeline configuration updates
                - user_preferences: User preference updates

        Returns:
            Dictionary with updated configuration

        Raises:
            ValidationError: If configuration validation fails
            APIError: If request fails

        Example:
            >>> client.update_config({
            ...     "user_preferences": {
            ...         "default_audience": "Federal Grant Reviewers",
            ...         "citation_style": "apa",
            ...         "auto_save_interval": 120
            ...     }
            ... })
        """
        return self._request(
            method="PUT",
            endpoint="/api/config",
            json=config_update
        )

    # ========== Prompt Template Management ==========

    def list_prompts(
        self,
        category: Optional[str] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List all prompt templates with optional filtering.

        Args:
            category: Filter by category (audience, section, brand_voice, custom)
            active: Filter by active status
            search: Search in name and content

        Returns:
            Dictionary with structure:
            {
                "prompts": [list of prompt templates],
                "total": int (total count)
            }

        Raises:
            APIError: If request fails
        """
        params = {}
        if category is not None:
            params["category"] = category
        if active is not None:
            params["active"] = active
        if search is not None:
            params["search"] = search

        return self._request(
            method="GET",
            endpoint="/api/prompts",
            params=params
        )

    def get_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """
        Get a specific prompt template.

        Args:
            prompt_id: Prompt template ID

        Returns:
            Dictionary with structure:
            {
                "prompt": {...},
                "success": bool,
                "message": str
            }

        Raises:
            APIError: If request fails or prompt not found
        """
        return self._request(
            method="GET",
            endpoint=f"/api/prompts/{prompt_id}"
        )

    def create_prompt(
        self,
        name: str,
        category: str,
        content: str,
        variables: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new prompt template.

        Args:
            name: Template name
            category: Category (audience, section, brand_voice, custom)
            content: Prompt content
            variables: List of variable names used in the template

        Returns:
            Dictionary with structure:
            {
                "prompt": {...},
                "success": bool,
                "message": str
            }

        Raises:
            ValidationError: If validation fails
            APIError: If request fails
        """
        data = {
            "name": name,
            "category": category,
            "content": content,
            "variables": variables or []
        }

        return self._request(
            method="POST",
            endpoint="/api/prompts",
            json=data
        )

    def update_prompt(
        self,
        prompt_id: str,
        name: Optional[str] = None,
        content: Optional[str] = None,
        variables: Optional[List[str]] = None,
        active: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Update an existing prompt template.

        Args:
            prompt_id: Prompt template ID
            name: Updated name (optional)
            content: Updated content (optional)
            variables: Updated variables (optional)
            active: Updated active status (optional)

        Returns:
            Dictionary with structure:
            {
                "prompt": {...},
                "success": bool,
                "message": str
            }

        Raises:
            ValidationError: If validation fails
            APIError: If request fails or prompt not found
        """
        data = {}
        if name is not None:
            data["name"] = name
        if content is not None:
            data["content"] = content
        if variables is not None:
            data["variables"] = variables
        if active is not None:
            data["active"] = active

        return self._request(
            method="PUT",
            endpoint=f"/api/prompts/{prompt_id}",
            json=data
        )

    def delete_prompt(self, prompt_id: str) -> Dict[str, Any]:
        """
        Delete a prompt template.

        Args:
            prompt_id: Prompt template ID

        Returns:
            Dictionary with structure:
            {
                "success": bool,
                "message": str,
                "prompt_id": str
            }

        Raises:
            APIError: If request fails or prompt not found
        """
        return self._request(
            method="DELETE",
            endpoint=f"/api/prompts/{prompt_id}"
        )


# ========== Helper Functions ==========

def get_api_client(
    base_url: Optional[str] = None,
    auto_refresh: bool = True
) -> APIClient:
    """
    Get configured API client instance.

    Convenience function to create API client with default token manager
    from Streamlit session state.

    Args:
        base_url: Override default API base URL
        auto_refresh: Enable automatic token refresh

    Returns:
        Configured API client instance
    """
    return APIClient(base_url=base_url, auto_refresh=auto_refresh)


def require_authentication() -> APIClient:
    """
    Ensure user is authenticated and return API client.

    Use this as a guard at the top of pages that require authentication.
    Redirects to login if not authenticated.

    Returns:
        Authenticated API client

    Raises:
        AuthenticationError: If not authenticated (triggers login redirect)
    """
    client = get_api_client()

    # Check if we have a token
    if not client.token_manager.access_token:
        st.error("Please log in to access this page.")
        st.stop()

    # Validate session
    try:
        client.validate_session()
        return client
    except AuthenticationError:
        st.error("Your session has expired. Please log in again.")
        client.token_manager.clear_tokens()
        st.stop()
