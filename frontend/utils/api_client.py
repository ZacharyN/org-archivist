"""
API client for backend communication.

This module provides a centralized API client for all backend communications.
"""

import requests
from typing import Optional, Dict, Any, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import streamlit as st

from config.settings import settings


class APIClient:
    """
    API client for Org Archivist backend.

    Handles all HTTP communication with the FastAPI backend,
    including authentication, error handling, and retries.
    """

    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        """
        Initialize the API client.

        Args:
            base_url: Base URL for the API (defaults to settings.API_BASE_URL)
            token: Authentication token (optional)
        """
        self.base_url = base_url or settings.API_BASE_URL
        self.token = token
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "PUT", "DELETE"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _get_headers(self) -> Dict[str, str]:
        """Get request headers including authentication."""
        headers = {"Content-Type": "application/json"}

        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        return headers

    def _handle_response(self, response: requests.Response) -> Any:
        """
        Handle API response and errors.

        Args:
            response: Response from requests

        Returns:
            Parsed JSON response or raises exception

        Raises:
            requests.HTTPError: For HTTP errors
        """
        try:
            response.raise_for_status()
            return response.json() if response.content else None
        except requests.HTTPError as e:
            # Try to get error message from response
            try:
                error_data = response.json()
                error_msg = error_data.get("detail", str(e))
            except:
                error_msg = str(e)

            raise requests.HTTPError(f"API Error: {error_msg}", response=response)

    # Authentication endpoints
    def login(self, email: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and get token.

        Args:
            email: User email
            password: User password

        Returns:
            Authentication response with token and user info
        """
        response = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"email": email, "password": password},
            headers=self._get_headers(),
            timeout=settings.API_TIMEOUT
        )
        return self._handle_response(response)

    def logout(self) -> None:
        """Logout current user."""
        response = self.session.post(
            f"{self.base_url}/api/auth/logout",
            headers=self._get_headers(),
            timeout=settings.API_TIMEOUT
        )
        return self._handle_response(response)

    # Document endpoints
    def get_documents(self, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get list of documents.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of documents
        """
        response = self.session.get(
            f"{self.base_url}/api/documents",
            params={"skip": skip, "limit": limit},
            headers=self._get_headers(),
            timeout=settings.API_TIMEOUT
        )
        return self._handle_response(response)

    def upload_document(self, file, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Upload a document.

        Args:
            file: File object to upload
            metadata: Document metadata

        Returns:
            Created document info
        """
        # TODO: Implement file upload
        raise NotImplementedError("Document upload not yet implemented")

    # Writing styles endpoints
    def get_writing_styles(self) -> List[Dict[str, Any]]:
        """Get list of writing styles."""
        response = self.session.get(
            f"{self.base_url}/api/writing-styles",
            headers=self._get_headers(),
            timeout=settings.API_TIMEOUT
        )
        return self._handle_response(response)

    def create_writing_style(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new writing style.

        Args:
            data: Writing style data

        Returns:
            Created writing style
        """
        response = self.session.post(
            f"{self.base_url}/api/writing-styles",
            json=data,
            headers=self._get_headers(),
            timeout=settings.API_TIMEOUT
        )
        return self._handle_response(response)

    # Chat/conversation endpoints
    def send_chat_message(self, message: str, conversation_id: Optional[str] = None,
                         context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Send a chat message and get AI response.

        Args:
            message: User message
            conversation_id: Optional conversation ID to continue
            context: Optional conversation context (style, audience, etc.)

        Returns:
            AI response with generated content
        """
        response = self.session.post(
            f"{self.base_url}/api/chat",
            json={
                "message": message,
                "conversation_id": conversation_id,
                "context": context
            },
            headers=self._get_headers(),
            timeout=120  # Longer timeout for AI generation
        )
        return self._handle_response(response)

    # Outputs endpoints
    def get_outputs(self, skip: int = 0, limit: int = 100,
                   filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Get list of past outputs.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            filters: Optional filters (type, status, etc.)

        Returns:
            List of outputs
        """
        params = {"skip": skip, "limit": limit}
        if filters:
            params.update(filters)

        response = self.session.get(
            f"{self.base_url}/api/outputs",
            params=params,
            headers=self._get_headers(),
            timeout=settings.API_TIMEOUT
        )
        return self._handle_response(response)


# Helper function to get API client from session
def get_api_client() -> APIClient:
    """
    Get API client from Streamlit session state.

    Returns:
        Configured API client instance
    """
    token = st.session_state.get('api_token')
    return APIClient(token=token)
