# Frontend Setup Documentation

## Overview

This document provides a comprehensive overview of how the Org Archivist Streamlit frontend is architected and configured. It serves as a reference for developers working on or maintaining the frontend application.

## Architecture Philosophy

The frontend is built as a **multi-page Streamlit application** following these core principles:

1. **Separation of Concerns**: Clear boundaries between UI components, business logic, and API communication
2. **Modularity**: Reusable components and utilities that can be shared across pages
3. **Type Safety**: Extensive use of type hints for better IDE support and fewer runtime errors
4. **Centralized Configuration**: Environment-based settings using Pydantic
5. **Session State Management**: Consistent handling of authentication and user context
6. **API-First Design**: All backend communication through a centralized client

## Directory Structure

### High-Level Organization

```
frontend/
├── app.py                      # Main application entry point
├── pages/                      # Streamlit auto-discovered pages
├── components/                 # Reusable UI components
├── utils/                      # Utility functions and helpers
├── config/                     # Configuration management
├── docs/                       # Documentation
├── assets/                     # Static files (images, icons)
├── styles/                     # Custom CSS stylesheets
├── .streamlit/                 # Streamlit-specific configuration
└── requirements.txt            # Python dependencies
```

### Detailed Structure Explanation

#### `/app.py` - Main Entry Point

**Purpose**: Serves as the landing page and authentication gateway

**Key Responsibilities**:
- Initialize session state variables
- Handle user login/authentication flow
- Display home dashboard for authenticated users
- Provide navigation overview

**Design Decisions**:
- Uses Streamlit's session state for authentication persistence
- Communicates with backend `/api/auth/login` endpoint
- Stores JWT token in session for subsequent API calls
- Implements simple redirect logic based on authentication status

**Session State Variables**:
```python
{
    'authenticated': bool,      # Is user logged in?
    'user': dict,              # User profile data
    'user_role': str,          # Role: administrator/editor/writer
    'api_token': str           # JWT token for API calls
}
```

#### `/pages/` - Multi-Page Application

**Purpose**: Contains individual feature pages auto-discovered by Streamlit

**Naming Convention**: `{number}_{emoji}_{Page_Name}.py`
- Number determines sidebar order (1, 2, 3...)
- Emoji provides visual icon in sidebar
- Page name becomes the display title

**Planned Pages**:
1. `1_📚_Document_Library.py` - Upload and manage organizational documents
2. `2_✍️_Writing_Styles.py` - Create and manage AI writing styles
3. `3_💬_AI_Assistant.py` - Chat interface for content generation
4. `4_📊_Past_Outputs.py` - View and track generated content
5. `5_⚙️_Settings.py` - User preferences and system configuration

**Page Structure Pattern**:
```python
from components.auth import require_authentication

# Require authentication (optionally with specific role)
require_authentication()  # or require_authentication(role="administrator")

# Page content
st.title("Page Title")
# ... page implementation
```

#### `/components/` - Reusable UI Components

**Purpose**: Shared, reusable UI components used across multiple pages

**Current Components**:

1. **`auth.py`** - Authentication utilities
   - `require_authentication(role=None)`: Decorator/check for page access control
   - `require_role(allowed_roles)`: Verify user has required role
   - `get_current_user()`: Retrieve current user from session
   - `is_authenticated()`: Check authentication status

**Design Pattern**:
```python
# components/my_component.py
import streamlit as st
from typing import Optional

def my_component(data: dict, title: Optional[str] = None) -> None:
    """
    Reusable component description.

    Args:
        data: Component data
        title: Optional title
    """
    with st.container():
        if title:
            st.subheader(title)
        st.write(data)
```

**Usage**:
```python
from components.my_component import my_component
my_component({"key": "value"}, title="My Data")
```

#### `/utils/` - Utility Functions

**Purpose**: Business logic, helpers, and shared functionality

**Key Modules**:

1. **`api_client.py`** - Backend API Communication
   - Centralized HTTP client with retry logic
   - Automatic token injection
   - Error handling and response parsing
   - Built on `requests` library with `urllib3.Retry` strategy

2. **`helpers.py`** - General Helper Functions
   - Date formatting (`format_date`, `format_relative_time`)
   - Text utilities (`truncate_text`, `clean_filename`)
   - Validation (`validate_email`)
   - Display helpers (`get_user_role_label`, `get_output_type_icon`)
   - Currency formatting (`format_currency`)

**API Client Architecture**:

```python
class APIClient:
    def __init__(self, base_url: Optional[str] = None, token: Optional[str] = None):
        self.base_url = base_url or settings.API_BASE_URL
        self.token = token
        self.session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create session with retry strategy."""
        # 3 retries with exponential backoff
        # Retry on 429, 500, 502, 503, 504

    def _request(self, method: str, endpoint: str, **kwargs) -> dict:
        """Execute HTTP request with error handling."""
        # Inject auth token
        # Handle errors
        # Parse JSON response

    # CRUD methods: get(), post(), put(), delete()
```

**Usage Pattern**:
```python
from utils.api_client import get_api_client

api = get_api_client()
documents = api.get("/api/documents")
```

#### `/config/` - Configuration Management

**Purpose**: Centralized application settings using Pydantic

**Design**:
- Uses `pydantic-settings` for validation
- Reads from environment variables
- Provides sensible defaults
- Type-safe configuration access

**Settings Structure**:
```python
class Settings(BaseSettings):
    # API Configuration
    API_BASE_URL: str = "http://localhost:8000"
    API_TIMEOUT: int = 30

    # Application Settings
    APP_NAME: str = "Org Archivist"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Session Management
    SESSION_TIMEOUT_MINUTES: int = 60

    # UI Configuration
    ITEMS_PER_PAGE: int = 25
    MAX_FILE_UPLOAD_SIZE_MB: int = 50
```

**Usage**:
```python
from config.settings import get_settings

settings = get_settings()
api_url = settings.API_BASE_URL
```

#### `/.streamlit/config.toml` - Streamlit Configuration

**Purpose**: Configure Streamlit-specific behavior and theming

**Key Sections**:

1. **Theme** - Visual appearance
   - Primary color: `#4F8BF9` (blue for links/buttons)
   - Background: `#FFFFFF` (white)
   - Secondary background: `#F0F2F6` (light gray)
   - Text color: `#262730` (dark gray)

2. **Server** - Runtime configuration
   - Port: `8501`
   - CORS: Disabled (same-origin)
   - XSRF protection: Enabled
   - Max upload size: 50 MB

3. **Browser** - Client-side behavior
   - Usage stats: Disabled (privacy)
   - Server address: `localhost`

4. **Runner** - Execution settings
   - Magic commands: Enabled
   - Fast reruns: Enabled

## Key Design Decisions

### 1. Streamlit Multi-Page App vs. Single Page

**Decision**: Use Streamlit's native multi-page app structure

**Rationale**:
- Automatic sidebar navigation
- Clear separation of features
- URL-based routing out of the box
- Easier to maintain and scale
- Better for code organization

**Alternative Considered**: Single page with tab-based navigation
- Rejected: Less scalable, harder to maintain, poor URL structure

### 2. Session State for Authentication

**Decision**: Use Streamlit's `st.session_state` for auth persistence

**Rationale**:
- Native to Streamlit, no external dependencies
- Persists across page navigation within session
- Simple key-value storage
- Sufficient for MVP requirements

**Limitations**:
- Not persistent across browser refreshes
- Not shared across browser tabs
- Lost when session expires

**Future Consideration**: Implement browser localStorage integration for "Remember Me" functionality

### 3. Centralized API Client

**Decision**: Single `APIClient` class for all backend communication

**Rationale**:
- DRY principle - no duplicate HTTP code
- Consistent error handling
- Easy to add features (logging, metrics, caching)
- Simplified testing
- Automatic token injection

**Implementation Details**:
- Uses `requests.Session` for connection pooling
- Implements exponential backoff retry strategy
- Raises custom exceptions for better error handling
- Returns parsed JSON or raises error

### 4. Pydantic-Based Settings

**Decision**: Use Pydantic `BaseSettings` for configuration

**Rationale**:
- Type validation at runtime
- IDE autocomplete support
- Environment variable parsing
- Default value management
- Easy to extend

**Alternative Considered**: Plain dictionary or `os.getenv()`
- Rejected: No validation, type safety, or IDE support

### 5. Type Hints Throughout

**Decision**: Extensive use of type hints in all functions

**Rationale**:
- Better IDE support and autocomplete
- Catch errors before runtime
- Self-documenting code
- Easier refactoring
- Professional code quality

## API Integration Approach

### Authentication Flow

```
User Login (app.py)
    ↓
POST /api/auth/login
    ↓
Receive JWT Token
    ↓
Store in st.session_state.api_token
    ↓
Inject token in all subsequent API calls
```

### API Request Pattern

```python
# 1. Get API client (with token from session)
api = get_api_client()

# 2. Make request
try:
    data = api.get("/api/documents")
    st.success("Documents loaded!")
    display_documents(data)
except APIError as e:
    st.error(f"Failed to load documents: {e}")
```

### Error Handling Strategy

1. **Network Errors**: Automatic retry (3 attempts with backoff)
2. **4xx Errors**: Display user-friendly message
3. **5xx Errors**: Show generic error, log details
4. **Timeout**: User notification with retry option

## Session Management

### Session Lifecycle

1. **Initialization** (`app.py:init_session_state()`)
   - Set default values for all session variables
   - Happens once per session

2. **Login** (`app.py:login_page()`)
   - User submits credentials
   - Backend validates and returns token
   - Store token and user info in session

3. **Page Navigation**
   - Session state persists across pages
   - Authentication checked via `require_authentication()`

4. **Session Expiration**
   - Configured via `SESSION_TIMEOUT_MINUTES`
   - User must re-login
   - Session state cleared

### Session State Structure

```python
st.session_state = {
    # Authentication
    'authenticated': bool,
    'api_token': str,
    'user': {
        'id': str,
        'email': str,
        'full_name': str,
        'role': str
    },
    'user_role': str,

    # UI State (per-page)
    'current_conversation_id': Optional[str],
    'selected_document_ids': List[str],
    'active_writing_style_id': Optional[str]
}
```

## Component Interaction Patterns

### Pattern 1: Page → API → Display

```python
# Page imports
from utils.api_client import get_api_client
from components.auth import require_authentication

# Protect page
require_authentication()

# Fetch data
api = get_api_client()
documents = api.get("/api/documents")

# Display
for doc in documents:
    st.write(doc['title'])
```

### Pattern 2: User Input → Validation → API → Feedback

```python
# User input
title = st.text_input("Document Title")
file = st.file_uploader("Upload PDF")

if st.button("Upload"):
    # Validation
    if not title or not file:
        st.error("Title and file required!")
        return

    # API call
    api = get_api_client()
    try:
        result = api.post("/api/documents",
            json={"title": title},
            files={"file": file}
        )
        st.success(f"Uploaded: {result['title']}")
    except APIError as e:
        st.error(f"Upload failed: {e}")
```

### Pattern 3: Reusable Component

```python
# components/document_card.py
def document_card(document: dict) -> None:
    with st.container():
        col1, col2 = st.columns([3, 1])
        with col1:
            st.subheader(document['title'])
            st.caption(f"Uploaded {format_relative_time(document['created_at'])}")
        with col2:
            if st.button("View", key=f"view_{document['id']}"):
                st.session_state.selected_doc = document['id']

# Usage in page
from components.document_card import document_card
for doc in documents:
    document_card(doc)
```

## Development Workflow

### Initial Setup

```bash
# 1. Navigate to frontend directory
cd frontend

# 2. Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Create .env file
cat > .env << EOF
API_BASE_URL=http://localhost:8000
DEBUG=true
EOF

# 5. Run application
streamlit run app.py
```

### Adding a New Page

```bash
# 1. Create page file
touch pages/6_🎯_New_Feature.py

# 2. Implement page
cat > pages/6_🎯_New_Feature.py << 'EOF'
from components.auth import require_authentication
import streamlit as st

require_authentication()  # Protect page

st.title("New Feature")
st.write("Feature implementation here...")
EOF

# 3. Page automatically appears in sidebar
```

### Adding a New Component

```bash
# 1. Create component file
touch components/my_component.py

# 2. Implement component
# See "Component Interaction Patterns" above

# 3. Import and use in pages
```

### Adding API Endpoint Integration

```python
# 1. Add method to APIClient (utils/api_client.py)
def get_widgets(self) -> List[dict]:
    """Fetch widgets from backend."""
    return self.get("/api/widgets")

# 2. Use in page
api = get_api_client()
widgets = api.get_widgets()
```

## Environment Variables

### Required Variables

```bash
API_BASE_URL=http://localhost:8000  # Backend API URL
```

### Optional Variables

```bash
DEBUG=false                         # Enable debug mode
API_TIMEOUT=30                      # API request timeout (seconds)
SESSION_TIMEOUT_MINUTES=60          # Session expiration time
ITEMS_PER_PAGE=25                   # Pagination page size
MAX_FILE_UPLOAD_SIZE_MB=50          # Max file upload size
```

### Production Configuration

```bash
API_BASE_URL=https://api.orgarchiv.org
DEBUG=false
API_TIMEOUT=60
SESSION_TIMEOUT_MINUTES=120
```

## Testing Strategy

### Manual Testing Checklist

- [ ] Authentication flow (login, logout)
- [ ] Role-based access control (admin/editor/writer pages)
- [ ] API error handling (network issues, 4xx, 5xx)
- [ ] File upload functionality
- [ ] Session persistence across pages
- [ ] Session expiration behavior
- [ ] Responsive design on mobile/tablet
- [ ] All navigation links work

### Future Automated Testing

- Unit tests for utilities (`utils/helpers.py`)
- Integration tests for API client (`utils/api_client.py`)
- UI tests using Streamlit testing framework

## Deployment Considerations

### Development Deployment

```bash
streamlit run app.py --server.port 8501
```

### Production Deployment Options

1. **Streamlit Community Cloud**
   - Easy GitHub integration
   - Free tier available
   - Automatic deployments

2. **Docker Container**
   ```dockerfile
   FROM python:3.11-slim
   WORKDIR /app
   COPY requirements.txt .
   RUN pip install -r requirements.txt
   COPY . .
   EXPOSE 8501
   CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
   ```

3. **Cloud Platforms** (AWS, GCP, Azure)
   - Use container deployment
   - Configure load balancer
   - Set environment variables
   - Enable HTTPS

### Production Checklist

- [ ] Set `DEBUG=false`
- [ ] Use HTTPS for API_BASE_URL
- [ ] Configure proper CORS on backend
- [ ] Enable rate limiting
- [ ] Set up monitoring/logging
- [ ] Configure session timeout appropriately
- [ ] Implement proper error tracking (Sentry, etc.)

## Security Considerations

### Current Implementation

1. **Authentication**
   - JWT token-based authentication
   - Token stored in session state (memory)
   - Token injected in API requests

2. **Authorization**
   - Role-based access control via `require_authentication()`
   - Backend validates all requests

3. **Data Protection**
   - XSRF protection enabled in Streamlit
   - HTTPS enforced in production
   - No sensitive data in client-side logs

### Known Limitations (MVP)

1. **Session Persistence**: Not persistent across refreshes
2. **Token Refresh**: No automatic token refresh
3. **Remember Me**: Not implemented
4. **Multi-Tab Sessions**: Not synchronized

### Future Enhancements

- [ ] Implement token refresh mechanism
- [ ] Add "Remember Me" with encrypted localStorage
- [ ] Implement session synchronization across tabs
- [ ] Add rate limiting on frontend
- [ ] Implement CAPTCHA for login

## Troubleshooting

### Common Issues

**Issue**: Port 8501 already in use
```bash
# Solution: Use different port
streamlit run app.py --server.port 8502
```

**Issue**: API connection refused
```bash
# Check backend is running
curl http://localhost:8000/api/health

# Verify API_BASE_URL in .env
cat .env | grep API_BASE_URL
```

**Issue**: Session state not persisting
- Session state only persists within the same browser session
- Refresh clears session state
- This is expected behavior

**Issue**: Authentication required error
- Ensure you're logged in
- Check token is in session state
- Verify backend `/api/auth/login` endpoint

**Issue**: File upload fails
- Check file size limit (default 50MB)
- Verify backend accepts multipart/form-data
- Check backend endpoint returns proper response

## Performance Optimization

### Current Optimizations

1. **HTTP Connection Pooling**: `requests.Session` reuses connections
2. **Retry Strategy**: Exponential backoff reduces failed requests
3. **Fast Reruns**: Enabled in Streamlit config
4. **Minimal Dependencies**: Only essential packages

### Future Optimizations

- [ ] Implement caching for API responses (`st.cache_data`)
- [ ] Add lazy loading for large document lists
- [ ] Implement pagination for data tables
- [ ] Optimize image/file loading
- [ ] Add service worker for offline capability

## Maintenance and Updates

### Dependency Updates

```bash
# Check for outdated packages
pip list --outdated

# Update specific package
pip install --upgrade streamlit

# Regenerate requirements.txt
pip freeze > requirements.txt
```

### Streamlit Updates

- Monitor Streamlit changelog for breaking changes
- Test thoroughly before upgrading major versions
- Update `.streamlit/config.toml` if new options available

### Code Quality

- Use `black` for code formatting
- Use `mypy` for type checking
- Use `pylint` for linting
- Document all public functions with docstrings

## Related Documentation

- [Main README](../README.md) - Frontend overview and quick start
- [Backend API Documentation](../../backend/README.md) - API reference
- [Frontend Requirements](../../context/frontend-requirements.md) - Detailed specifications
- [Project Architecture](../../context/architecture.md) - System architecture
- [Streamlit Documentation](https://docs.streamlit.io) - Official Streamlit docs

## Questions and Support

For questions about this setup:

1. Check this documentation first
2. Review related documentation (links above)
3. Check Streamlit documentation
4. Consult project architecture documentation

## Changelog

### Version 0.1.0 (Initial Setup)

**Created**: 2025-11-04

**Components**:
- Basic directory structure
- Authentication system
- API client with retry logic
- Configuration management
- Helper utilities
- Streamlit configuration

**Features**:
- Multi-page application structure
- Role-based access control
- Session state management
- Centralized API communication
- Environment-based configuration

**Next Steps**:
- Implement individual feature pages
- Add comprehensive error handling
- Create additional reusable components
- Implement automated testing
