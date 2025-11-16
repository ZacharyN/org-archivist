# Streamlit Frontend Backup

**Backup Date**: 2025-11-16
**Reason**: Transition to Nuxt 4 frontend

## Backup Contents

This directory contains the complete Streamlit frontend application that was previously located at `frontend/`.

### Key Components

- **app.py** - Main Streamlit application entry point
- **components/** - Reusable UI components
- **pages/** - Page modules
- **utils/** - Utility functions
- **config/** - Configuration files
- **assets/** - Static assets
- **styles/** - CSS styling
- **.streamlit/** - Streamlit configuration

### Dependencies

See `requirements.txt` for complete list. Key dependencies include:

- streamlit >= 1.31.0
- requests >= 2.31.0
- pandas >= 2.1.0
- plotly >= 5.18.0
- extra-streamlit-components >= 0.1.60

### Restoration

To restore this frontend:
```bash
# From project root
mv frontend-streamlit-backup frontend
```

### Total Files: 30

All original files and directory structure preserved.
