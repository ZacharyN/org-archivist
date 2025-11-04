"""
Helper utility functions for the frontend.
"""

from datetime import datetime
from typing import Any, Optional
import re


def format_date(date: datetime, format: str = "%Y-%m-%d") -> str:
    """
    Format datetime object to string.

    Args:
        date: Datetime object to format
        format: strftime format string

    Returns:
        Formatted date string
    """
    if isinstance(date, str):
        date = datetime.fromisoformat(date.replace('Z', '+00:00'))
    return date.strftime(format)


def format_relative_time(date: datetime) -> str:
    """
    Format datetime as relative time (e.g., "2 hours ago").

    Args:
        date: Datetime object

    Returns:
        Relative time string
    """
    if isinstance(date, str):
        date = datetime.fromisoformat(date.replace('Z', '+00:00'))

    now = datetime.now(date.tzinfo) if date.tzinfo else datetime.now()
    diff = now - date

    seconds = diff.total_seconds()

    if seconds < 60:
        return "just now"
    elif seconds < 3600:
        minutes = int(seconds / 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    elif seconds < 86400:
        hours = int(seconds / 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    elif seconds < 604800:
        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    else:
        return format_date(date)


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate
        max_length: Maximum length
        suffix: Suffix to add if truncated

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)].rstrip() + suffix


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.

    Args:
        size_bytes: Size in bytes

    Returns:
        Formatted size string (e.g., "1.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} PB"


def clean_filename(filename: str) -> str:
    """
    Clean filename by removing special characters.

    Args:
        filename: Original filename

    Returns:
        Cleaned filename
    """
    # Remove special characters except dots and hyphens
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    # Remove multiple consecutive underscores
    filename = re.sub(r'_+', '_', filename)
    return filename


def validate_email(email: str) -> bool:
    """
    Validate email address format.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def get_user_role_label(role: str) -> str:
    """
    Get human-readable label for user role.

    Args:
        role: Role name (e.g., 'administrator')

    Returns:
        Human-readable label (e.g., 'Administrator')
    """
    role_labels = {
        'administrator': 'Administrator',
        'editor': 'Editor',
        'writer': 'Writer'
    }
    return role_labels.get(role.lower(), role.title())


def get_output_type_icon(output_type: str) -> str:
    """
    Get emoji icon for output type.

    Args:
        output_type: Output type (grant, proposal, report, etc.)

    Returns:
        Emoji icon
    """
    icons = {
        'grant': '💰',
        'proposal': '📄',
        'report': '📊',
        'letter': '✉️',
        'other': '📝'
    }
    return icons.get(output_type.lower(), '📝')


def get_status_color(status: str) -> str:
    """
    Get color for status indicator.

    Args:
        status: Status value

    Returns:
        Color name or hex code
    """
    colors = {
        'draft': '#gray',
        'submitted': '#blue',
        'pending': '#orange',
        'awarded': '#green',
        'not_awarded': '#red',
        'unknown': '#gray',
        'active': '#green',
        'inactive': '#gray'
    }
    return colors.get(status.lower(), '#gray')


def calculate_confidence_color(score: float) -> str:
    """
    Get color for confidence score.

    Args:
        score: Confidence score (0.0 - 1.0)

    Returns:
        Color name
    """
    if score >= 0.8:
        return "green"
    elif score >= 0.6:
        return "orange"
    else:
        return "red"


def format_currency(amount: float, currency: str = "USD") -> str:
    """
    Format amount as currency.

    Args:
        amount: Monetary amount
        currency: Currency code (default: USD)

    Returns:
        Formatted currency string
    """
    if currency == "USD":
        return f"${amount:,.2f}"
    else:
        return f"{amount:,.2f} {currency}"
