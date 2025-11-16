# Streamlit Frontend Development Plan

**Document Version:** 1.0
**Date:** 2025-01-04
**Target Backend API Version:** 1.0 (27/32 endpoints ready)
**Estimated Timeline:** 4 weeks (parallel with backend AI chat completion)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Project Setup](#project-setup)
3. [Architecture Overview](#architecture-overview)
4. [Development Phases](#development-phases)
5. [Component Specifications](#component-specifications)
6. [Docker Integration](#docker-integration)
7. [State Management](#state-management)
8. [API Client Implementation](#api-client-implementation)
9. [Testing Strategy](#testing-strategy)
10. [Deployment Considerations](#deployment-considerations)
11. [Best Practices & Patterns](#best-practices--patterns)

---

## Executive Summary

### Objective

Build a production-ready Streamlit frontend for the Nebraska Children and Families Foundation's "Foundation Historian" AI-powered grant writing assistant.

### Success Criteria

- ✅ Complete all 8 core user workflows (document management, writing styles, AI generation, outputs tracking, etc.)
- ✅ Seamless JWT authentication with session management
- ✅ Real-time AI streaming responses
- ✅ Role-based access control (admin, editor, writer)
- ✅ Responsive, intuitive UI that requires minimal training
- ✅ Production-ready Docker deployment

### Key Decisions

| Decision Point | Choice | Rationale |
|----------------|--------|-----------|
| **Framework** | Streamlit 1.31+ | Rapid development, pure Python, built-in components |
| **API Client** | httpx (async) | Modern, async support, better than requests |
| **State Management** | st.session_state | Native Streamlit state management |
| **Auth Strategy** | JWT with refresh tokens | Secure, stateless, matches backend |
| **Deployment** | Docker container in docker-compose | Consistent with backend infrastructure |
| **Routing** | Page-based with st.navigation | Clean separation of concerns |

---

## Project Setup

### Directory Structure

```
org-archivist/
├── frontend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── .streamlit/
│   │   └── config.toml
│   ├── app.py                          # Main entry point
│   ├── config/
│   │   └── settings.py                 # Environment configuration
│   ├── api/
│   │   ├── __init__.py
│   │   ├── client.py                   # Base API client
│   │   ├── auth.py                     # Auth endpoints
│   │   ├── documents.py                # Document endpoints
│   │   ├── writing_styles.py           # Writing style endpoints
│   │   ├── outputs.py                  # Outputs endpoints
│   │   ├── chat.py                     # Chat endpoints
│   │   └── admin.py                    # Admin endpoints
│   ├── pages/
│   │   ├── 1_📚_Document_Library.py
│   │   ├── 2_✍️_Writing_Styles.py
│   │   ├── 3_💬_AI_Assistant.py
│   │   ├── 4_📊_Past_Outputs.py
│   │   ├── 5_⚙️_Settings.py
│   │   └── 6_🔒_Admin.py              # Admin only
│   ├── components/
│   │   ├── __init__.py
│   │   ├── auth.py                     # Login/logout components
│   │   ├── document_uploader.py        # Document upload widget
│   │   ├── style_creator.py            # Writing style creator
│   │   ├── chat_interface.py           # Chat UI components
│   │   ├── output_form.py              # Output tracking form
│   │   └── utils.py                    # Shared utilities
│   ├── models/
│   │   ├── __init__.py
│   │   ├── auth.py                     # Auth models (User, Token)
│   │   ├── documents.py                # Document models
│   │   ├── writing_styles.py           # Writing style models
│   │   ├── outputs.py                  # Output models
│   │   └── chat.py                     # Chat models
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── session.py                  # Session management
│   │   ├── validators.py               # Input validation
│   │   └── formatters.py               # Display formatters
│   └── tests/
│       ├── __init__.py
│       ├── test_api_client.py
│       ├── test_auth.py
│       └── test_components.py
├── docker-compose.yml                   # Updated with frontend service
└── .env                                 # Updated with frontend vars
```

### Dependencies (requirements.txt)

```txt
# Streamlit Framework
streamlit==1.31.0
streamlit-extras==0.3.6

# HTTP Client
httpx==0.26.0

# Data Validation
pydantic==2.5.3
pydantic-settings==2.1.0

# Environment Management
python-dotenv==1.0.0

# Date/Time Utilities
python-dateutil==2.8.2

# JSON Handling
orjson==3.9.12

# Testing
pytest==7.4.4
pytest-asyncio==0.23.3
pytest-httpx==0.28.0
```

### Streamlit Configuration (.streamlit/config.toml)

```toml
[server]
port = 8501
address = "0.0.0.0"
headless = true
runOnSave = true
enableCORS = false
enableXsrfProtection = true

[browser]
gatherUsageStats = false
serverAddress = "localhost"
serverPort = 8501

[theme]
primaryColor = "#1f77b4"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#262730"
font = "sans serif"

[client]
showErrorDetails = true
toolbarMode = "minimal"
```

### Environment Configuration (config/settings.py)

```python
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    API_BASE_URL: str = "http://backend:8000"
    API_TIMEOUT: int = 30

    # App Configuration
    APP_NAME: str = "Foundation Historian"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Session Configuration
    SESSION_TIMEOUT: int = 3600  # 1 hour
    REFRESH_TOKEN_THRESHOLD: int = 300  # Refresh if < 5 min left

    # Upload Configuration
    MAX_FILE_SIZE_MB: int = 50
    ALLOWED_FILE_TYPES: list[str] = [".pdf", ".docx", ".txt"]

    # Pagination
    DEFAULT_PAGE_SIZE: int = 20
    MAX_PAGE_SIZE: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
```

---

## Architecture Overview

### Component Interaction Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                      Streamlit Frontend                      │
│                                                               │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Pages     │  │ Components  │  │    Models   │         │
│  │             │  │             │  │             │         │
│  │ • Document  │  │ • Auth UI   │  │ • User      │         │
│  │   Library   │  │ • Uploader  │  │ • Document  │         │
│  │ • Styles    │  │ • Chat      │  │ • Style     │         │
│  │ • Assistant │  │ • Forms     │  │ • Output    │         │
│  │ • Outputs   │  │ • Tables    │  │ • Chat      │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
│         │                │                │                 │
│         └────────────────┴────────────────┘                 │
│                          │                                   │
│                   ┌──────▼──────┐                           │
│                   │ API Client  │                           │
│                   │             │                           │
│                   │ • httpx     │                           │
│                   │ • Auth      │                           │
│                   │ • Retry     │                           │
│                   │ • Streaming │                           │
│                   └──────┬──────┘                           │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           │ HTTP/JSON
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                         │
│                                                               │
│  /api/auth       /api/documents    /api/chat                │
│  /api/styles     /api/outputs      /api/admin               │
└─────────────────────────────────────────────────────────────┘
```

### Authentication Flow

```
┌──────────┐                    ┌──────────┐                    ┌──────────┐
│          │  1. Login Request  │          │  2. Validate       │          │
│ Frontend ├───────────────────►│ Backend  ├───────────────────►│ Database │
│          │                    │          │                    │          │
│          │◄───────────────────┤          │◄───────────────────┤          │
│          │  3. JWT Tokens     │          │                    │          │
└────┬─────┘                    └──────────┘                    └──────────┘
     │
     │ 4. Store in session_state
     │ 5. Set auto-refresh timer
     │
     │  6. API Request (with access token)
     ├──────────────────────────►
     │
     │  7. Token expiring?
     ├──────────────────────────►
     │  8. Use refresh token
     │
     │◄──────────────────────────┤
     │  9. New access token
     │
     │  10. Continue API calls
     └──────────────────────────►
```

---

## Development Phases

### Phase 1: Foundation (Week 1)

**Goal:** Set up project infrastructure and implement authentication

#### Tasks

1. **Project Setup** (Day 1)
   - [ ] Create frontend directory structure
   - [ ] Initialize requirements.txt
   - [ ] Configure .streamlit/config.toml
   - [ ] Create Dockerfile for frontend
   - [ ] Update docker-compose.yml with frontend service

2. **API Client Foundation** (Day 2)
   - [ ] Implement base API client (api/client.py)
   - [ ] Add retry logic with exponential backoff
   - [ ] Implement auth endpoints (api/auth.py)
   - [ ] Create Pydantic models for auth

3. **Authentication UI** (Day 3)
   - [ ] Build login page (app.py)
   - [ ] Implement session state management
   - [ ] Add JWT token storage and refresh
   - [ ] Create logout functionality

4. **Testing & Integration** (Day 4-5)
   - [ ] Write API client tests
   - [ ] Test auth flow end-to-end
   - [ ] Test token refresh mechanism
   - [ ] Integration testing with backend

**Deliverable:** Working authentication with auto-refresh

---

### Phase 2: Core Features (Week 2)

**Goal:** Implement document management and writing styles

#### Tasks

1. **Document Library Page** (Day 1-2)
   - [ ] Create Document Library page (pages/1_📚_Document_Library.py)
   - [ ] Implement document uploader component
   - [ ] Build document list/table with filters
   - [ ] Add document viewer/download
   - [ ] Implement document delete with confirmation

2. **Writing Styles Feature** (Day 3-4)
   - [ ] Create Writing Styles page (pages/2_✍️_Writing_Styles.py)
   - [ ] Build style creator form (sample upload + analysis)
   - [ ] Display existing styles with metrics
   - [ ] Implement style edit/delete
   - [ ] Add style preview functionality

3. **API Integration** (Day 5)
   - [ ] Complete api/documents.py
   - [ ] Complete api/writing_styles.py
   - [ ] Add error handling for all endpoints
   - [ ] Test upload progress indicators

**Deliverable:** Fully functional document and writing style management

---

### Phase 3: AI Assistant (Week 3)

**Goal:** Build the core AI writing assistant interface

#### Tasks

1. **Chat Interface Foundation** (Day 1-2)
   - [ ] Create AI Assistant page (pages/3_💬_AI_Assistant.py)
   - [ ] Build chat message display (user/assistant bubbles)
   - [ ] Implement streaming response handling
   - [ ] Add conversation history display

2. **Context Configuration** (Day 2-3)
   - [ ] Build conversation context sidebar
     - Writing style selector
     - Audience selector
     - Section type selector
     - Tone selector
   - [ ] Implement context persistence per conversation
   - [ ] Add "New Conversation" button

3. **Advanced Features** (Day 4-5)
   - [ ] Implement source citations display
   - [ ] Add "Copy to Clipboard" for responses
   - [ ] Build "Export Conversation" functionality
   - [ ] Add conversation search/filter
   - [ ] Implement conversation delete

**Deliverable:** Fully functional AI writing assistant

---

### Phase 4: Outputs & Admin (Week 4)

**Goal:** Complete outputs tracking and admin features

#### Tasks

1. **Past Outputs Dashboard** (Day 1-2)
   - [ ] Create Past Outputs page (pages/4_📊_Past_Outputs.py)
   - [ ] Build output creation form
   - [ ] Display outputs table with filters
   - [ ] Add success metrics visualization
   - [ ] Implement output edit/update

2. **Settings Page** (Day 3)
   - [ ] Create Settings page (pages/5_⚙️_Settings.py)
   - [ ] User profile editor
   - [ ] Password change form
   - [ ] System prompts viewer (read-only for non-admins)

3. **Admin Features** (Day 4)
   - [ ] Create Admin page (pages/6_🔒_Admin.py)
   - [ ] User management (create, edit, delete, role change)
   - [ ] System prompts editor
   - [ ] Audit log viewer
   - [ ] System health dashboard

4. **Polish & Testing** (Day 5)
   - [ ] End-to-end testing of all workflows
   - [ ] Performance optimization
   - [ ] Error handling review
   - [ ] Documentation updates

**Deliverable:** Complete production-ready application

---

## Component Specifications

### 1. Main Entry Point (app.py)

```python
"""
Main Streamlit application entry point.
Handles authentication and routing.
"""
import streamlit as st
from config.settings import get_settings
from api.auth import AuthAPI
from components.auth import show_login_page
from utils.session import (
    is_authenticated,
    init_session_state,
    check_token_refresh
)


# Page configuration
st.set_page_config(
    page_title="Foundation Historian",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize settings and session
settings = get_settings()
init_session_state()


def main():
    """Main application logic."""

    # Check if user is authenticated
    if not is_authenticated():
        show_login_page()
        return

    # Check if token needs refresh
    check_token_refresh()

    # Show navigation sidebar
    show_navigation()

    # Show main content
    st.title("🏠 Foundation Historian")
    st.markdown("""
    Welcome to the Nebraska Children and Families Foundation's AI-powered grant writing assistant.

    **Getting Started:**
    1. 📚 Upload your source documents to the **Document Library**
    2. ✍️ Create **Writing Styles** from sample documents
    3. 💬 Use the **AI Assistant** to generate grant content
    4. 📊 Track success in **Past Outputs**
    """)

    # Show quick stats
    show_dashboard_stats()


def show_navigation():
    """Show sidebar navigation."""
    with st.sidebar:
        st.title(settings.APP_NAME)
        st.caption(f"Version {settings.APP_VERSION}")

        # User info
        user = st.session_state.user
        st.markdown(f"**Logged in as:** {user.email}")
        st.markdown(f"**Role:** {user.role.value}")

        st.divider()

        # Logout button
        if st.button("🚪 Logout", use_container_width=True):
            logout()


def show_dashboard_stats():
    """Show quick statistics on home page."""
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Documents", st.session_state.get("doc_count", 0))

    with col2:
        st.metric("Writing Styles", st.session_state.get("style_count", 0))

    with col3:
        st.metric("Conversations", st.session_state.get("conversation_count", 0))

    with col4:
        st.metric("Outputs Tracked", st.session_state.get("output_count", 0))


def logout():
    """Handle user logout."""
    # Clear session state
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()


if __name__ == "__main__":
    main()
```

---

### 2. API Client Base (api/client.py)

```python
"""
Base API client with authentication and retry logic.
"""
import httpx
from typing import Optional, Any, Dict
from functools import wraps
import asyncio
import streamlit as st
from config.settings import get_settings


settings = get_settings()


class APIError(Exception):
    """Base exception for API errors."""
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class APIClient:
    """Base API client with common functionality."""

    def __init__(self):
        self.base_url = settings.API_BASE_URL
        self.timeout = settings.API_TIMEOUT

    def _get_headers(self, include_auth: bool = True) -> Dict[str, str]:
        """Get request headers with optional auth token."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

        if include_auth and "access_token" in st.session_state:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"

        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        params: Optional[Dict] = None,
        include_auth: bool = True,
        timeout: Optional[int] = None
    ) -> Any:
        """
        Make an HTTP request to the API.

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint (e.g., "/api/documents")
            data: Request body data
            params: Query parameters
            include_auth: Whether to include auth token
            timeout: Request timeout (defaults to settings.API_TIMEOUT)

        Returns:
            Response data (JSON)

        Raises:
            APIError: If request fails
        """
        url = f"{self.base_url}{endpoint}"
        headers = self._get_headers(include_auth=include_auth)
        timeout_val = timeout or self.timeout

        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    headers=headers,
                    timeout=timeout_val
                )

                # Handle errors
                if response.status_code >= 400:
                    try:
                        error_data = response.json()
                        message = error_data.get("detail", "Unknown error")
                    except:
                        message = response.text or "Unknown error"

                    raise APIError(
                        status_code=response.status_code,
                        message=message,
                        details=error_data if 'error_data' in locals() else {}
                    )

                # Return JSON response
                if response.status_code == 204:
                    return None

                return response.json()

        except httpx.TimeoutException:
            raise APIError(
                status_code=408,
                message="Request timed out"
            )
        except httpx.NetworkError as e:
            raise APIError(
                status_code=503,
                message=f"Network error: {str(e)}"
            )

    async def get(self, endpoint: str, params: Optional[Dict] = None, **kwargs) -> Any:
        """GET request."""
        return await self._request("GET", endpoint, params=params, **kwargs)

    async def post(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Any:
        """POST request."""
        return await self._request("POST", endpoint, data=data, **kwargs)

    async def put(self, endpoint: str, data: Optional[Dict] = None, **kwargs) -> Any:
        """PUT request."""
        return await self._request("PUT", endpoint, data=data, **kwargs)

    async def delete(self, endpoint: str, **kwargs) -> Any:
        """DELETE request."""
        return await self._request("DELETE", endpoint, **kwargs)


# Synchronous wrapper for Streamlit
def sync_api_call(func):
    """Decorator to run async API calls synchronously in Streamlit."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(func(*args, **kwargs))

    return wrapper
```

---

### 3. Authentication API (api/auth.py)

```python
"""
Authentication API client.
"""
from typing import Optional
from datetime import datetime, timedelta
import streamlit as st
from api.client import APIClient, sync_api_call, APIError
from models.auth import (
    LoginRequest,
    TokenResponse,
    User,
    RefreshRequest
)


class AuthAPI:
    """Authentication API client."""

    def __init__(self):
        self.client = APIClient()

    @sync_api_call
    async def login(self, email: str, password: str) -> TokenResponse:
        """
        Authenticate user and get JWT tokens.

        Args:
            email: User email
            password: User password

        Returns:
            TokenResponse with access_token, refresh_token, user data

        Raises:
            APIError: If login fails
        """
        data = {
            "email": email,
            "password": password
        }

        response = await self.client.post(
            "/api/auth/login",
            data=data,
            include_auth=False
        )

        # Parse response
        token_response = TokenResponse(**response)

        # Store in session state
        st.session_state.access_token = token_response.access_token
        st.session_state.refresh_token = token_response.refresh_token
        st.session_state.user = token_response.user
        st.session_state.token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_response.expires_in
        )

        return token_response

    @sync_api_call
    async def refresh_token(self) -> TokenResponse:
        """
        Refresh access token using refresh token.

        Returns:
            New TokenResponse

        Raises:
            APIError: If refresh fails
        """
        if "refresh_token" not in st.session_state:
            raise APIError(401, "No refresh token available")

        data = {
            "refresh_token": st.session_state.refresh_token
        }

        response = await self.client.post(
            "/api/auth/refresh",
            data=data,
            include_auth=False
        )

        # Parse and store new token
        token_response = TokenResponse(**response)

        st.session_state.access_token = token_response.access_token
        st.session_state.refresh_token = token_response.refresh_token
        st.session_state.token_expires_at = datetime.utcnow() + timedelta(
            seconds=token_response.expires_in
        )

        return token_response

    @sync_api_call
    async def get_current_user(self) -> User:
        """
        Get current authenticated user.

        Returns:
            User object
        """
        response = await self.client.get("/api/auth/me")
        return User(**response)

    @sync_api_call
    async def logout(self) -> None:
        """Logout current user (revoke tokens on backend)."""
        try:
            await self.client.post("/api/auth/logout")
        except APIError:
            pass  # Ignore logout errors
        finally:
            # Clear session state
            for key in ["access_token", "refresh_token", "user", "token_expires_at"]:
                if key in st.session_state:
                    del st.session_state[key]

    @sync_api_call
    async def change_password(
        self,
        current_password: str,
        new_password: str
    ) -> None:
        """
        Change user password.

        Args:
            current_password: Current password
            new_password: New password
        """
        data = {
            "current_password": current_password,
            "new_password": new_password
        }

        await self.client.post("/api/auth/change-password", data=data)
```

---

### 4. Login Component (components/auth.py)

```python
"""
Authentication UI components.
"""
import streamlit as st
from api.auth import AuthAPI
from api.client import APIError


def show_login_page():
    """Display login page."""

    st.title("🔐 Foundation Historian Login")
    st.markdown("---")

    # Center the login form
    col1, col2, col3 = st.columns([1, 2, 1])

    with col2:
        with st.form("login_form"):
            st.subheader("Sign In")

            email = st.text_input(
                "Email",
                placeholder="your.email@ncff.org",
                autocomplete="email"
            )

            password = st.text_input(
                "Password",
                type="password",
                autocomplete="current-password"
            )

            submitted = st.form_submit_button(
                "Login",
                use_container_width=True,
                type="primary"
            )

            if submitted:
                if not email or not password:
                    st.error("Please enter both email and password")
                    return

                # Attempt login
                try:
                    with st.spinner("Logging in..."):
                        auth_api = AuthAPI()
                        token_response = auth_api.login(email, password)

                    st.success("Login successful!")
                    st.rerun()

                except APIError as e:
                    if e.status_code == 401:
                        st.error("Invalid email or password")
                    elif e.status_code == 403:
                        st.error("Your account has been disabled. Please contact an administrator.")
                    else:
                        st.error(f"Login failed: {e.message}")

                except Exception as e:
                    st.error(f"An unexpected error occurred: {str(e)}")

        # Help text
        st.caption("Contact your administrator if you need help logging in.")
```

---

### 5. Session Management (utils/session.py)

```python
"""
Session state management utilities.
"""
import streamlit as st
from datetime import datetime, timedelta
from typing import Optional
from config.settings import get_settings
from api.auth import AuthAPI


settings = get_settings()


def init_session_state():
    """Initialize session state variables."""

    # Authentication state
    if "access_token" not in st.session_state:
        st.session_state.access_token = None

    if "refresh_token" not in st.session_state:
        st.session_state.refresh_token = None

    if "user" not in st.session_state:
        st.session_state.user = None

    if "token_expires_at" not in st.session_state:
        st.session_state.token_expires_at = None

    # App state
    if "current_conversation_id" not in st.session_state:
        st.session_state.current_conversation_id = None

    if "conversation_context" not in st.session_state:
        st.session_state.conversation_context = {}


def is_authenticated() -> bool:
    """Check if user is authenticated."""
    return (
        st.session_state.access_token is not None and
        st.session_state.user is not None
    )


def check_token_refresh():
    """Check if access token needs refresh and refresh if necessary."""

    if not is_authenticated():
        return

    # Check if token is expiring soon
    expires_at = st.session_state.token_expires_at
    if not expires_at:
        return

    time_until_expiry = (expires_at - datetime.utcnow()).total_seconds()

    # Refresh if less than threshold remaining
    if time_until_expiry < settings.REFRESH_TOKEN_THRESHOLD:
        try:
            auth_api = AuthAPI()
            auth_api.refresh_token()
        except Exception as e:
            # If refresh fails, force logout
            st.error("Your session has expired. Please login again.")
            clear_session()
            st.rerun()


def clear_session():
    """Clear all session state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def get_user_role() -> Optional[str]:
    """Get current user's role."""
    if is_authenticated():
        return st.session_state.user.role.value
    return None


def has_role(required_role: str) -> bool:
    """Check if user has required role."""
    role = get_user_role()

    # Role hierarchy: admin > editor > writer
    role_levels = {"admin": 3, "editor": 2, "writer": 1}

    if not role or required_role not in role_levels:
        return False

    return role_levels.get(role, 0) >= role_levels[required_role]
```

---

### 6. Document Library Page (pages/1_📚_Document_Library.py)

```python
"""
Document Library page for uploading and managing source documents.
"""
import streamlit as st
from api.documents import DocumentsAPI
from api.client import APIError
from components.document_uploader import show_document_uploader
from utils.session import is_authenticated, has_role
from datetime import datetime


# Require authentication
if not is_authenticated():
    st.error("Please login to access this page")
    st.stop()


st.title("📚 Document Library")
st.markdown("Upload and manage source documents for the AI assistant.")

# Initialize API
docs_api = DocumentsAPI()

# Upload section (editors and admins only)
if has_role("editor"):
    st.subheader("Upload Documents")
    show_document_uploader()
    st.divider()

# Document list section
st.subheader("Your Documents")

# Filters
col1, col2, col3 = st.columns([2, 2, 1])

with col1:
    search_query = st.text_input(
        "Search documents",
        placeholder="Enter keywords...",
        label_visibility="collapsed"
    )

with col2:
    filter_type = st.selectbox(
        "Filter by type",
        ["All Types", "Grant Proposal", "Annual Report", "Program Description", "Other"],
        label_visibility="collapsed"
    )

with col3:
    sort_by = st.selectbox(
        "Sort by",
        ["Upload Date (Newest)", "Upload Date (Oldest)", "Name (A-Z)", "Name (Z-A)"],
        label_visibility="collapsed"
    )

# Fetch documents
try:
    with st.spinner("Loading documents..."):
        # Build query params
        params = {}
        if search_query:
            params["search"] = search_query
        if filter_type != "All Types":
            params["document_type"] = filter_type

        documents = docs_api.list_documents(**params)

    if not documents:
        st.info("No documents found. Upload your first document to get started!")
    else:
        # Display document count
        st.caption(f"Showing {len(documents)} document(s)")

        # Document table
        for doc in documents:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])

                with col1:
                    st.markdown(f"**{doc.filename}**")
                    if doc.metadata and doc.metadata.get("description"):
                        st.caption(doc.metadata["description"])

                with col2:
                    st.text(doc.document_type or "Unknown Type")

                with col3:
                    upload_date = datetime.fromisoformat(doc.created_at.replace('Z', '+00:00'))
                    st.text(upload_date.strftime("%Y-%m-%d %H:%M"))

                with col4:
                    # Action buttons
                    if st.button("👁️", key=f"view_{doc.id}", help="View document"):
                        st.session_state.view_doc_id = doc.id

                    if has_role("editor"):
                        if st.button("🗑️", key=f"delete_{doc.id}", help="Delete document"):
                            if st.confirm(f"Delete '{doc.filename}'?"):
                                try:
                                    docs_api.delete_document(doc.id)
                                    st.success("Document deleted")
                                    st.rerun()
                                except APIError as e:
                                    st.error(f"Delete failed: {e.message}")

                st.divider()

except APIError as e:
    st.error(f"Failed to load documents: {e.message}")

# Document viewer (if selected)
if "view_doc_id" in st.session_state:
    doc_id = st.session_state.view_doc_id

    with st.expander("Document Details", expanded=True):
        try:
            doc = docs_api.get_document(doc_id)

            st.markdown(f"**Filename:** {doc.filename}")
            st.markdown(f"**Type:** {doc.document_type}")
            st.markdown(f"**Size:** {doc.file_size / 1024:.1f} KB")
            st.markdown(f"**Uploaded:** {doc.created_at}")
            st.markdown(f"**Chunks:** {doc.chunk_count}")

            if doc.metadata:
                st.markdown("**Metadata:**")
                st.json(doc.metadata)

            # Download button
            if st.button("⬇️ Download", key="download_doc"):
                # Implement download logic
                st.info("Download functionality coming soon")

            if st.button("Close", key="close_viewer"):
                del st.session_state.view_doc_id
                st.rerun()

        except APIError as e:
            st.error(f"Failed to load document: {e.message}")
```

---

### 7. Chat Interface Component (components/chat_interface.py)

```python
"""
Chat interface components for AI Assistant.
"""
import streamlit as st
from typing import List, Dict, Optional
from datetime import datetime
from api.chat import ChatAPI
from api.client import APIError


def show_chat_interface(conversation_id: Optional[str] = None):
    """
    Display chat interface with message history and input.

    Args:
        conversation_id: ID of conversation to display, or None for new
    """
    chat_api = ChatAPI()

    # Load conversation history if ID provided
    messages = []
    if conversation_id:
        try:
            conversation = chat_api.get_conversation(conversation_id)
            messages = conversation.messages

            # Update context in session state
            if conversation.context:
                st.session_state.conversation_context = conversation.context
        except APIError as e:
            st.error(f"Failed to load conversation: {e.message}")
            return

    # Display messages
    for msg in messages:
        with st.chat_message(msg.role):
            st.markdown(msg.content)

            # Show sources if assistant message
            if msg.role == "assistant" and msg.sources:
                with st.expander("📚 Sources"):
                    for source in msg.sources:
                        st.markdown(f"- **{source.filename}** (score: {source.score:.2f})")
                        st.caption(source.content[:200] + "...")

    # Chat input
    if prompt := st.chat_input("Ask a question or request content..."):
        # Add user message to display
        with st.chat_message("user"):
            st.markdown(prompt)

        # Get context from session state
        context = st.session_state.conversation_context

        # Send to API
        try:
            with st.chat_message("assistant"):
                message_placeholder = st.empty()
                full_response = ""

                # Stream response
                for chunk in chat_api.send_message_stream(
                    conversation_id=conversation_id,
                    message=prompt,
                    context=context
                ):
                    if chunk.get("type") == "content":
                        full_response += chunk.get("content", "")
                        message_placeholder.markdown(full_response + "▌")

                message_placeholder.markdown(full_response)

                # Show sources if available
                if chunk.get("sources"):
                    with st.expander("📚 Sources"):
                        for source in chunk["sources"]:
                            st.markdown(f"- **{source['filename']}** (score: {source['score']:.2f})")
                            st.caption(source['content'][:200] + "...")

        except APIError as e:
            st.error(f"Failed to send message: {e.message}")
        except Exception as e:
            st.error(f"An error occurred: {str(e)}")


def show_conversation_context_sidebar():
    """Display conversation context configuration in sidebar."""

    with st.sidebar:
        st.subheader("📋 Context Settings")
        st.caption("Configure the AI's writing context")

        # Get current context
        context = st.session_state.conversation_context

        # Writing style selector
        writing_style_id = st.selectbox(
            "Writing Style",
            options=get_writing_styles(),
            format_func=lambda x: x["name"] if x else "Default",
            help="Select a writing style to guide tone and voice"
        )

        # Audience selector
        audience = st.selectbox(
            "Audience",
            options=["Federal Agency", "Private Foundation", "Corporate Sponsor", "Individual Donor", "General Public"],
            index=context.get("audience_index", 0)
        )

        # Section type selector
        section_type = st.selectbox(
            "Section Type",
            options=[
                "Executive Summary",
                "Organizational Capacity",
                "Program Description",
                "Impact & Outcomes",
                "Budget Narrative",
                "Sustainability Plan",
                "Evaluation Plan",
                "Other"
            ],
            index=context.get("section_type_index", 0)
        )

        # Tone selector
        tone = st.selectbox(
            "Tone",
            options=["Professional", "Passionate", "Data-Driven", "Storytelling", "Formal", "Conversational"],
            index=context.get("tone_index", 0)
        )

        # Update context
        st.session_state.conversation_context = {
            "writing_style_id": writing_style_id["id"] if writing_style_id else None,
            "audience": audience,
            "section_type": section_type,
            "tone": tone,
            "audience_index": ["Federal Agency", "Private Foundation", "Corporate Sponsor", "Individual Donor", "General Public"].index(audience),
            "section_type_index": ["Executive Summary", "Organizational Capacity", "Program Description", "Impact & Outcomes", "Budget Narrative", "Sustainability Plan", "Evaluation Plan", "Other"].index(section_type),
            "tone_index": ["Professional", "Passionate", "Data-Driven", "Storytelling", "Formal", "Conversational"].index(tone)
        }

        st.divider()

        # New conversation button
        if st.button("➕ New Conversation", use_container_width=True):
            st.session_state.current_conversation_id = None
            st.session_state.conversation_context = {}
            st.rerun()


def get_writing_styles() -> List[Dict]:
    """Fetch available writing styles."""
    # This would call the API - simplified for example
    if "writing_styles_cache" not in st.session_state:
        from api.writing_styles import WritingStylesAPI
        try:
            api = WritingStylesAPI()
            st.session_state.writing_styles_cache = api.list_styles()
        except:
            st.session_state.writing_styles_cache = []

    return [None] + st.session_state.writing_styles_cache
```

---

## Docker Integration

### Updated docker-compose.yml

```yaml
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: org-archivist-postgres
    environment:
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-org_archivist}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant Vector Database
  qdrant:
    image: qdrant/qdrant:latest
    container_name: org-archivist-qdrant
    volumes:
      - qdrant_data:/qdrant/storage
    ports:
      - "6333:6333"
    healthcheck:
      test: ["CMD", "wget", "--spider", "-q", "http://localhost:6333/readiness"]
      interval: 10s
      timeout: 5s
      retries: 5

  # FastAPI Backend
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: org-archivist-backend
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_healthy
    environment:
      # Database
      POSTGRES_HOST: postgres
      POSTGRES_PORT: 5432
      POSTGRES_USER: ${POSTGRES_USER:-postgres}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-postgres}
      POSTGRES_DB: ${POSTGRES_DB:-org_archivist}
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-postgres}:${POSTGRES_PASSWORD:-postgres}@postgres:5432/${POSTGRES_DB:-org_archivist}

      # Qdrant
      QDRANT_HOST: qdrant
      QDRANT_PORT: 6333

      # API
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      SECRET_KEY: ${SECRET_KEY}
      DEBUG: ${DEBUG:-false}
    volumes:
      - ./backend:/app
      - uploaded_documents:/app/uploaded_documents
    ports:
      - "8000:8000"
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

  # Streamlit Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: org-archivist-frontend
    depends_on:
      - backend
    environment:
      API_BASE_URL: http://backend:8000
      DEBUG: ${DEBUG:-false}
    volumes:
      - ./frontend:/app
    ports:
      - "8501:8501"
    command: streamlit run app.py

volumes:
  postgres_data:
  qdrant_data:
  uploaded_documents:
```

### Frontend Dockerfile

```dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## State Management

### Session State Architecture

```python
# Authentication State
st.session_state.access_token: str | None
st.session_state.refresh_token: str | None
st.session_state.user: User | None
st.session_state.token_expires_at: datetime | None

# Navigation State
st.session_state.current_page: str

# Chat State
st.session_state.current_conversation_id: str | None
st.session_state.conversation_context: Dict[str, Any]
st.session_state.chat_messages: List[Dict]

# Document State
st.session_state.selected_documents: List[str]
st.session_state.doc_filters: Dict[str, Any]

# Caching State (for performance)
st.session_state.writing_styles_cache: List[Dict]
st.session_state.conversations_cache: List[Dict]
st.session_state.outputs_cache: List[Dict]
```

### Best Practices

1. **Initialize Early:** Use `init_session_state()` in app.py before any page loads
2. **Cache Expensive Data:** Store API responses that don't change frequently
3. **Clear on Logout:** Always clear all session state on logout
4. **Validate State:** Check for required state before using it
5. **Use Callbacks:** Use Streamlit callbacks for form submissions to update state

---

## Testing Strategy

### Unit Tests

```python
# tests/test_api_client.py
import pytest
from api.client import APIClient, APIError


@pytest.mark.asyncio
async def test_api_client_get():
    """Test API client GET request."""
    client = APIClient()

    # Mock httpx response
    # ... test implementation


@pytest.mark.asyncio
async def test_api_client_auth_header():
    """Test API client includes auth header."""
    # ... test implementation
```

### Integration Tests

```python
# tests/test_auth.py
import pytest
from api.auth import AuthAPI


@pytest.mark.asyncio
async def test_login_success():
    """Test successful login flow."""
    auth_api = AuthAPI()

    # Test with valid credentials
    # ... test implementation


@pytest.mark.asyncio
async def test_token_refresh():
    """Test token refresh mechanism."""
    # ... test implementation
```

### Manual Testing Checklist

- [ ] Authentication flow (login, logout, token refresh)
- [ ] Document upload (all file types)
- [ ] Writing style creation from samples
- [ ] Chat interface (streaming, sources, context)
- [ ] Conversation persistence
- [ ] Outputs tracking
- [ ] Admin features (user management, prompts)
- [ ] Role-based access control
- [ ] Error handling for all API failures
- [ ] Mobile responsiveness

---

## Best Practices & Patterns

### 1. Error Handling

```python
from api.client import APIError

try:
    result = api.some_endpoint()
except APIError as e:
    if e.status_code == 401:
        st.error("Unauthorized. Please login again.")
        # Force logout
    elif e.status_code == 403:
        st.error("You don't have permission for this action.")
    elif e.status_code == 404:
        st.warning("Resource not found.")
    else:
        st.error(f"An error occurred: {e.message}")
except Exception as e:
    st.error(f"Unexpected error: {str(e)}")
    if settings.DEBUG:
        st.exception(e)
```

### 2. Loading States

```python
# Use spinners for operations
with st.spinner("Processing..."):
    result = api.long_running_operation()

# Use progress bars for uploads
progress_bar = st.progress(0)
for i, chunk in enumerate(file_chunks):
    upload_chunk(chunk)
    progress_bar.progress((i + 1) / len(file_chunks))
```

### 3. Form Validation

```python
with st.form("my_form"):
    name = st.text_input("Name")
    email = st.text_input("Email")

    submitted = st.form_submit_button("Submit")

    if submitted:
        # Validate
        errors = []
        if not name:
            errors.append("Name is required")
        if not email or "@" not in email:
            errors.append("Valid email is required")

        if errors:
            for error in errors:
                st.error(error)
        else:
            # Process form
            api.submit_form(name=name, email=email)
```

### 4. Caching API Responses

```python
@st.cache_data(ttl=300)  # Cache for 5 minutes
def get_writing_styles():
    """Fetch writing styles with caching."""
    api = WritingStylesAPI()
    return api.list_styles()
```

### 5. Role-Based UI

```python
from utils.session import has_role

# Show admin-only features
if has_role("admin"):
    st.sidebar.markdown("### Admin Tools")
    if st.sidebar.button("Manage Users"):
        navigate_to("admin/users")

# Show editor features
if has_role("editor"):
    st.button("Upload Document")
```

### 6. Streaming Responses

```python
def stream_chat_response(message: str):
    """Stream chat response with live updates."""

    placeholder = st.empty()
    full_response = ""

    for chunk in chat_api.send_message_stream(message):
        if chunk.get("type") == "content":
            full_response += chunk.get("content", "")
            placeholder.markdown(full_response + "▌")

    placeholder.markdown(full_response)
```

---

## Deployment Checklist

### Pre-Deployment

- [ ] All environment variables documented in `.env.example`
- [ ] Docker images build successfully
- [ ] All tests passing
- [ ] No hardcoded secrets in code
- [ ] Error handling covers all API endpoints
- [ ] Loading states for all async operations
- [ ] Mobile responsive testing complete

### Deployment

- [ ] Set production environment variables
- [ ] Update `docker-compose.yml` for production (remove volumes, set restart policies)
- [ ] Configure reverse proxy (nginx) if needed
- [ ] Set up SSL/TLS certificates
- [ ] Configure logging and monitoring
- [ ] Set up backup strategy for PostgreSQL

### Post-Deployment

- [ ] Verify all pages load correctly
- [ ] Test authentication flow
- [ ] Test document upload
- [ ] Test AI chat generation
- [ ] Monitor logs for errors
- [ ] Set up uptime monitoring
- [ ] Create admin documentation

---

## Timeline & Milestones

### Week 1: Foundation
- **Day 1-2:** Project setup, Docker configuration, API client
- **Day 3-4:** Authentication implementation
- **Day 5:** Testing and integration
- **Milestone:** Working login/logout with token refresh

### Week 2: Core Features
- **Day 1-2:** Document library (upload, list, delete)
- **Day 3-4:** Writing styles (create, manage)
- **Day 5:** Integration testing
- **Milestone:** Complete document and style management

### Week 3: AI Assistant
- **Day 1-2:** Chat interface with streaming
- **Day 3:** Conversation context configuration
- **Day 4-5:** Source citations and advanced features
- **Milestone:** Fully functional AI assistant

### Week 4: Completion
- **Day 1-2:** Outputs tracking dashboard
- **Day 3:** Settings and admin features
- **Day 4:** Polish and testing
- **Day 5:** Documentation and handoff
- **Milestone:** Production-ready application

---

## Appendix

### A. Pydantic Models Reference

```python
# models/auth.py
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    EDITOR = "editor"
    WRITER = "writer"


class User(BaseModel):
    id: str
    email: EmailStr
    role: UserRole
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class RefreshRequest(BaseModel):
    refresh_token: str
```

### B. Environment Variables

```bash
# .env
# API Configuration
API_BASE_URL=http://backend:8000

# App Configuration
APP_NAME=Foundation Historian
APP_VERSION=1.0.0
DEBUG=false

# Session
SESSION_TIMEOUT=3600
REFRESH_TOKEN_THRESHOLD=300

# Uploads
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_TYPES=[".pdf",".docx",".txt"]

# Pagination
DEFAULT_PAGE_SIZE=20
MAX_PAGE_SIZE=100
```

### C. Troubleshooting

**Issue:** Token refresh not working
- Check `token_expires_at` is set correctly
- Verify `REFRESH_TOKEN_THRESHOLD` setting
- Check backend `/api/auth/refresh` endpoint

**Issue:** Streamlit keeps rerunning
- Avoid setting session state inside render functions
- Use `st.cache_data` for expensive operations
- Check for infinite loops in callbacks

**Issue:** API requests timeout
- Increase `API_TIMEOUT` setting
- Check Docker network connectivity
- Verify backend is running and healthy

**Issue:** File uploads fail
- Check `MAX_FILE_SIZE_MB` setting
- Verify MIME type in `ALLOWED_FILE_TYPES`
- Check backend file handling endpoint

---

## Conclusion

This development plan provides a comprehensive roadmap for building a production-ready Streamlit frontend for the Foundation Historian application. The phased approach allows for iterative development, testing, and feedback while maintaining momentum toward the 4-week delivery goal.

Key success factors:
1. **Follow the phases sequentially** to build on solid foundations
2. **Test thoroughly at each milestone** before proceeding
3. **Leverage Streamlit's strengths** (rapid development, built-in widgets)
4. **Maintain separation of concerns** (API client, components, pages)
5. **Prioritize user experience** with loading states, error handling, and clear feedback

With 85% of the backend ready and this detailed plan, the frontend development can proceed in parallel with the final backend AI chat implementation, enabling a complete application launch within the target timeframe.
