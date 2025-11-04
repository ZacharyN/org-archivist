# Org Archivist Frontend

Streamlit-based frontend for the Org Archivist AI writing assistant.

## Overview

This is the user interface for Org Archivist, built using Streamlit as a multi-page application. It provides an intuitive interface for nonprofit organizations to manage documents, create AI-powered writing styles, and generate grant proposals and other content.

## Directory Structure

```
frontend/
├── app.py                     # Main application entry point
├── pages/                     # Streamlit pages (auto-discovered)
│   ├── 1_📚_Document_Library.py
│   ├── 2_✍️_Writing_Styles.py
│   ├── 3_💬_AI_Assistant.py
│   ├── 4_📊_Past_Outputs.py
│   └── 5_⚙️_Settings.py
├── components/                # Reusable UI components
│   ├── __init__.py
│   └── auth.py               # Authentication components
├── utils/                     # Utility functions
│   ├── __init__.py
│   ├── api_client.py         # Backend API client
│   └── helpers.py            # Helper functions
├── config/                    # Configuration
│   ├── __init__.py
│   └── settings.py           # Application settings
├── assets/                    # Static assets (images, etc.)
├── styles/                    # Custom CSS styles
├── .streamlit/               # Streamlit configuration
│   └── config.toml
└── requirements.txt          # Python dependencies
```

## Features

### User Roles & Permissions
- **Administrator**: Full system access including user management
- **Editor**: Document and writing style management
- **Writer**: Content creation and AI assistant access

### Core Features (MVP)
1. **Document Library**: Upload and manage organizational documents
2. **Writing Styles**: AI-powered style analysis and generation
3. **AI Writing Assistant**: Chat-based content generation
4. **Past Outputs**: Track and manage generated content with success metrics
5. **Settings**: User preferences and system configuration

## Installation

### Prerequisites
- Python 3.11+
- Backend API running (see ../backend/README.md)

### Setup

1. **Install dependencies**:
   ```bash
   cd frontend
   pip install -r requirements.txt
   ```

2. **Configure environment**:
   Create a `.env` file in the frontend directory:
   ```env
   API_BASE_URL=http://localhost:8000
   DEBUG=false
   ```

3. **Run the application**:
   ```bash
   streamlit run app.py
   ```

   The application will be available at `http://localhost:8501`

## Development

### Adding a New Page

1. Create a new file in the `pages/` directory following the naming convention:
   ```
   pages/6_🎯_New_Feature.py
   ```

2. The number prefix determines the order in the sidebar

3. Use the authentication decorator to protect the page:
   ```python
   from components.auth import require_authentication

   require_authentication()  # or require_authentication(role="administrator")
   ```

### Creating Reusable Components

Place reusable components in the `components/` directory:

```python
# components/my_component.py
import streamlit as st

def my_component(data):
    """Reusable component description."""
    with st.container():
        st.write(data)
```

### API Integration

Use the centralized API client for all backend communications:

```python
from utils.api_client import get_api_client

api = get_api_client()
documents = api.get_documents()
```

## Configuration

### Streamlit Settings

Edit `.streamlit/config.toml` to customize:
- Theme colors
- Server settings
- Upload limits
- Browser behavior

### Application Settings

Edit `config/settings.py` or use environment variables:

```python
API_BASE_URL=http://localhost:8000
API_TIMEOUT=30
ITEMS_PER_PAGE=25
MAX_FILE_UPLOAD_SIZE_MB=50
```

## Testing

### Manual Testing

1. Start the backend server
2. Run the frontend application
3. Navigate through each page
4. Test authentication flows
5. Test API integrations

### UI Testing (Future)

- Streamlit supports testing with pytest
- Tests will be added in `frontend/tests/`

## Deployment

### Local Development
```bash
streamlit run app.py
```

### Production

For production deployment, consider:

1. **Streamlit Community Cloud**: Easy deployment from GitHub
2. **Docker**: Containerize the application
3. **Cloud Platforms**: Deploy to AWS, GCP, or Azure

Example Dockerfile:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0"]
```

## Architecture

### Session State Management

Streamlit session state is used for:
- User authentication status
- Current conversation context
- UI state persistence

### API Communication

All backend communication goes through the `APIClient` class:
- Centralized error handling
- Automatic retry logic
- Token-based authentication

### Page Navigation

Streamlit's multi-page app feature automatically:
- Discovers pages in the `pages/` directory
- Creates sidebar navigation
- Manages page routing

## Troubleshooting

### Common Issues

**Port already in use**:
```bash
streamlit run app.py --server.port 8502
```

**API connection refused**:
- Ensure backend is running at the configured `API_BASE_URL`
- Check network connectivity
- Verify CORS settings if using different domains

**Session state not persisting**:
- Session state is cleared on page refresh
- Implement proper session management with backend

## Contributing

1. Follow the established directory structure
2. Use type hints for all functions
3. Add docstrings to all modules and functions
4. Test thoroughly before committing
5. Follow git best practices (see /CLAUDE.md)

## Related Documentation

- Backend API: `/backend/README.md`
- Frontend Requirements: `/context/frontend-requirements.md`
- Project Architecture: `/context/architecture.md`
- Development Guide: `/DEVELOPMENT.md`

## License

Proprietary - All rights reserved
