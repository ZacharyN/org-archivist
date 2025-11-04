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


def format_word_count(count: int) -> str:
    """
    Format word count with appropriate suffix.

    Args:
        count: Number of words

    Returns:
        Formatted word count string

    Example:
        format_word_count(1547) -> "1.5K words"
        format_word_count(847) -> "847 words"
    """
    if count >= 1000:
        return f"{count / 1000:.1f}K words"
    else:
        return f"{count} word{'s' if count != 1 else ''}"


def format_percentage(value: float, decimals: int = 1) -> str:
    """
    Format value as percentage.

    Args:
        value: Value to format (0.0 to 1.0)
        decimals: Number of decimal places

    Returns:
        Formatted percentage string

    Example:
        format_percentage(0.847) -> "84.7%"
    """
    return f"{value * 100:.{decimals}f}%"


def sanitize_filename(filename: str, max_length: int = 255) -> str:
    """
    Sanitize filename for safe storage.

    Args:
        filename: Original filename
        max_length: Maximum filename length

    Returns:
        Sanitized filename

    Example:
        sanitize_filename("My Document (v2).pdf") -> "my_document_v2.pdf"
    """
    # Convert to lowercase
    filename = filename.lower()

    # Remove extension temporarily
    name, ext = filename.rsplit('.', 1) if '.' in filename else (filename, '')

    # Remove special characters and spaces
    name = re.sub(r'[^a-z0-9_-]', '_', name)

    # Remove multiple consecutive underscores
    name = re.sub(r'_+', '_', name)

    # Remove leading/trailing underscores
    name = name.strip('_')

    # Truncate if needed
    if ext:
        max_name_length = max_length - len(ext) - 1
        name = name[:max_name_length]
        return f"{name}.{ext}"
    else:
        return name[:max_length]


def parse_api_error(error: Exception) -> tuple[str, Optional[str]]:
    """
    Parse API error into user-friendly message and details.

    Args:
        error: Exception object from API call

    Returns:
        Tuple of (user_message, technical_details)

    Example:
        message, details = parse_api_error(api_error)
    """
    error_str = str(error)

    # Common error patterns
    if "connection" in error_str.lower() or "timeout" in error_str.lower():
        return ("Unable to connect to server", error_str)
    elif "401" in error_str or "unauthorized" in error_str.lower():
        return ("Authentication failed. Please log in again.", error_str)
    elif "403" in error_str or "forbidden" in error_str.lower():
        return ("You don't have permission to perform this action.", error_str)
    elif "404" in error_str or "not found" in error_str.lower():
        return ("The requested resource was not found.", error_str)
    elif "500" in error_str or "internal server" in error_str.lower():
        return ("Server error occurred. Please try again later.", error_str)
    else:
        return ("An error occurred. Please try again.", error_str)


def debounce_key(base_key: str, value: Any) -> str:
    """
    Create a debounced key for Streamlit widgets.

    Args:
        base_key: Base key name
        value: Value to include in key

    Returns:
        Unique debounced key

    Example:
        key = debounce_key("search", search_term)
    """
    import hashlib
    value_hash = hashlib.md5(str(value).encode()).hexdigest()[:8]
    return f"{base_key}_{value_hash}"


def chunk_list(items: list, chunk_size: int) -> list[list]:
    """
    Split list into chunks of specified size.

    Args:
        items: List to chunk
        chunk_size: Size of each chunk

    Returns:
        List of chunked lists

    Example:
        chunks = chunk_list(items, 10)  # Split into groups of 10
    """
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]


def safe_get(dictionary: dict, *keys, default=None) -> Any:
    """
    Safely get nested dictionary value.

    Args:
        dictionary: Dictionary to access
        *keys: Sequence of keys to traverse
        default: Default value if key not found

    Returns:
        Value at nested key or default

    Example:
        value = safe_get(data, "user", "profile", "email", default="")
    """
    result = dictionary
    for key in keys:
        if isinstance(result, dict):
            result = result.get(key)
            if result is None:
                return default
        else:
            return default
    return result if result is not None else default


def format_time_ago(date: datetime) -> str:
    """
    Format datetime as "time ago" string (alias for format_relative_time).

    Args:
        date: Datetime object

    Returns:
        Time ago string
    """
    return format_relative_time(date)


def is_valid_url(url: str) -> bool:
    """
    Validate URL format.

    Args:
        url: URL string to validate

    Returns:
        True if valid URL, False otherwise
    """
    import re
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None


def generate_unique_id(prefix: str = "") -> str:
    """
    Generate a unique ID for use in Streamlit keys.

    Args:
        prefix: Optional prefix for the ID

    Returns:
        Unique ID string

    Example:
        id = generate_unique_id("widget")  # "widget_a3f9c2d1"
    """
    import uuid
    unique_hash = str(uuid.uuid4())[:8]
    return f"{prefix}_{unique_hash}" if prefix else unique_hash


def mask_sensitive_data(text: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data (e.g., API keys, tokens).

    Args:
        text: Text to mask
        visible_chars: Number of characters to keep visible at end

    Returns:
        Masked string

    Example:
        mask_sensitive_data("sk_test_1234567890abcdef") -> "**************cdef"
    """
    if len(text) <= visible_chars:
        return "*" * len(text)

    masked_part = "*" * (len(text) - visible_chars)
    visible_part = text[-visible_chars:]
    return f"{masked_part}{visible_part}"


def calculate_reading_time(word_count: int, words_per_minute: int = 200) -> str:
    """
    Calculate estimated reading time.

    Args:
        word_count: Number of words
        words_per_minute: Average reading speed (default: 200)

    Returns:
        Reading time string

    Example:
        calculate_reading_time(1500) -> "8 min read"
    """
    minutes = max(1, round(word_count / words_per_minute))
    return f"{minutes} min read"


def format_list(items: list, separator: str = ", ", last_separator: str = " and ") -> str:
    """
    Format list as human-readable string.

    Args:
        items: List of items to format
        separator: Separator between items
        last_separator: Separator before last item

    Returns:
        Formatted string

    Example:
        format_list(["apples", "oranges", "bananas"]) -> "apples, oranges and bananas"
    """
    if not items:
        return ""
    if len(items) == 1:
        return str(items[0])
    if len(items) == 2:
        return f"{items[0]}{last_separator}{items[1]}"

    return f"{separator.join(str(i) for i in items[:-1])}{last_separator}{items[-1]}"


def sort_by_date(items: list, date_key: str, reverse: bool = True) -> list:
    """
    Sort list of dictionaries by date field.

    Args:
        items: List of dictionaries
        date_key: Key containing date value
        reverse: Sort descending (newest first) if True

    Returns:
        Sorted list

    Example:
        sorted_items = sort_by_date(items, "created_at", reverse=True)
    """
    def get_date(item):
        date_val = item.get(date_key)
        if isinstance(date_val, str):
            try:
                return datetime.fromisoformat(date_val.replace('Z', '+00:00'))
            except:
                return datetime.min
        elif isinstance(date_val, datetime):
            return date_val
        else:
            return datetime.min

    return sorted(items, key=get_date, reverse=reverse)


def pluralize(count: int, singular: str, plural: Optional[str] = None) -> str:
    """
    Pluralize word based on count.

    Args:
        count: Number of items
        singular: Singular form of word
        plural: Plural form (optional, defaults to singular + 's')

    Returns:
        Pluralized string with count

    Example:
        pluralize(1, "document") -> "1 document"
        pluralize(5, "document") -> "5 documents"
        pluralize(3, "child", "children") -> "3 children"
    """
    if plural is None:
        plural = f"{singular}s"

    word = singular if count == 1 else plural
    return f"{count} {word}"
