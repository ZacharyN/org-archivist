"""
Writing Style Sample Collection Wizard

This page provides a multi-step wizard for creating new writing styles:
- Step 1: Select style type (Grant, Proposal, Report)
- Step 2: Collect 3-7 writing samples with validation
- Step 3: AI analysis and prompt generation (future)
- Step 4: Review and finalization (future)
"""

import streamlit as st
import sys
from pathlib import Path
import logging
from typing import List, Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.api_client import get_api_client, APIError, AuthenticationError, ValidationError
from components.auth import require_auth
from components.ui import (
    show_loading_spinner,
    show_error_message,
    show_success_message,
    show_warning_message,
)
from config.settings import settings

logger = logging.getLogger(__name__)


# Page configuration
st.set_page_config(
    page_title="Create Writing Style - Org Archivist",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for wizard styling
st.markdown("""
<style>
    /* Main container styling */
    .main > div {
        padding-top: 2rem;
    }

    /* Step indicator styling */
    .step-indicator {
        display: flex;
        justify-content: center;
        align-items: center;
        margin: 2rem 0;
    }

    .step {
        display: flex;
        align-items: center;
        color: #9ca3af;
        font-weight: 500;
    }

    .step-number {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background-color: #e5e7eb;
        color: #6b7280;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: 600;
        margin-right: 0.5rem;
    }

    .step-active .step-number {
        background-color: #3b82f6;
        color: white;
    }

    .step-completed .step-number {
        background-color: #10b981;
        color: white;
    }

    .step-active {
        color: #1f2937;
    }

    .step-completed {
        color: #059669;
    }

    .step-line {
        width: 100px;
        height: 2px;
        background-color: #e5e7eb;
        margin: 0 1rem;
    }

    .step-line-active {
        background-color: #10b981;
    }

    /* Style type card styling */
    .style-type-card {
        border: 2px solid #e5e7eb;
        border-radius: 12px;
        padding: 2rem;
        text-align: center;
        cursor: pointer;
        transition: all 0.2s;
        background-color: white;
    }

    .style-type-card:hover {
        border-color: #3b82f6;
        box-shadow: 0 4px 6px rgba(59, 130, 246, 0.1);
    }

    .style-type-card-selected {
        border-color: #3b82f6;
        background-color: #eff6ff;
    }

    .style-type-icon {
        font-size: 3rem;
        margin-bottom: 1rem;
    }

    .style-type-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }

    .style-type-description {
        color: #6b7280;
        font-size: 0.95rem;
    }

    /* Sample input styling */
    .sample-container {
        border: 1px solid #e5e7eb;
        border-radius: 8px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        background-color: #f9fafb;
    }

    .sample-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1rem;
    }

    .sample-title {
        font-weight: 600;
        color: #1f2937;
        font-size: 1.1rem;
    }

    .word-count {
        font-size: 0.9rem;
        color: #6b7280;
        font-weight: 500;
    }

    .word-count-valid {
        color: #059669;
    }

    .word-count-invalid {
        color: #dc2626;
    }

    /* Navigation buttons */
    .nav-buttons {
        margin-top: 2rem;
        padding-top: 2rem;
        border-top: 1px solid #e5e7eb;
    }

    /* Hide Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def init_session_state():
    """Initialize session state variables for the wizard."""
    if 'wizard_step' not in st.session_state:
        st.session_state.wizard_step = 1
    if 'selected_style_type' not in st.session_state:
        st.session_state.selected_style_type = None
    if 'writing_samples' not in st.session_state:
        st.session_state.writing_samples = {}
    if 'num_samples' not in st.session_state:
        st.session_state.num_samples = 3  # Default to minimum


def count_words(text: str) -> int:
    """
    Count words in text.

    Args:
        text: Text to count words in

    Returns:
        Number of words
    """
    if not text or not text.strip():
        return 0
    return len(text.split())


def validate_sample(text: str, min_words: int = 200) -> tuple[bool, str]:
    """
    Validate a writing sample.

    Args:
        text: Sample text to validate
        min_words: Minimum word count required

    Returns:
        Tuple of (is_valid, message)
    """
    if not text or not text.strip():
        return False, "Sample cannot be empty"

    word_count = count_words(text)
    if word_count < min_words:
        return False, f"Sample must be at least {min_words} words (current: {word_count})"

    return True, f"Valid ({word_count} words)"


def render_step_indicator(current_step: int, total_steps: int = 4):
    """
    Render the step indicator at the top of the wizard.

    Args:
        current_step: Current step number (1-indexed)
        total_steps: Total number of steps
    """
    steps = [
        {"number": 1, "label": "Select Type"},
        {"number": 2, "label": "Add Samples"},
        {"number": 3, "label": "AI Analysis"},
        {"number": 4, "label": "Finalize"},
    ]

    # Build HTML for step indicator
    html_parts = ['<div class="step-indicator">']

    for i, step in enumerate(steps):
        step_num = step["number"]
        step_label = step["label"]

        # Determine step state
        if step_num < current_step:
            step_class = "step step-completed"
        elif step_num == current_step:
            step_class = "step step-active"
        else:
            step_class = "step"

        # Add step
        html_parts.append(f'''
        <div class="{step_class}">
            <div class="step-number">{'✓' if step_num < current_step else step_num}</div>
            <span>{step_label}</span>
        </div>
        ''')

        # Add line between steps (except after last step)
        if i < len(steps) - 1:
            line_class = "step-line step-line-active" if step_num < current_step else "step-line"
            html_parts.append(f'<div class="{line_class}"></div>')

    html_parts.append('</div>')

    st.markdown(''.join(html_parts), unsafe_allow_html=True)


def render_step1_select_type():
    """Render Step 1: Select style type."""
    st.markdown("## Step 1: Select Writing Style Type")
    st.markdown("Choose the type of writing style you want to create. This helps the AI understand the context and purpose of your writing.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Style type options with descriptions
    style_types = [
        {
            "type": "grant",
            "display_name": "Grant",
            "icon": "💰",
            "description": "For grant proposals and applications to funding organizations",
            "examples": "Federal grants, foundation grants, corporate giving applications"
        },
        {
            "type": "proposal",
            "display_name": "Proposal",
            "icon": "📋",
            "description": "For general proposals and business documents (non-grant)",
            "examples": "Partnership proposals, program proposals, project plans"
        },
        {
            "type": "report",
            "display_name": "Report",
            "icon": "📊",
            "description": "For reports, communications, and narrative documents",
            "examples": "Annual reports, impact reports, program updates, donor communications"
        },
    ]

    # Create 3 columns for the style type cards
    cols = st.columns(3)

    for i, style_type in enumerate(style_types):
        with cols[i]:
            # Determine if this type is selected
            is_selected = st.session_state.selected_style_type == style_type["type"]
            card_class = "style-type-card style-type-card-selected" if is_selected else "style-type-card"

            # Render card (using container to capture click)
            container = st.container()
            with container:
                st.markdown(f"""
                <div class="{card_class}">
                    <div class="style-type-icon">{style_type['icon']}</div>
                    <div class="style-type-title">{style_type['display_name']}</div>
                    <div class="style-type-description">{style_type['description']}</div>
                </div>
                """, unsafe_allow_html=True)

                # Button to select this type
                if st.button(
                    f"Select {style_type['display_name']}" if not is_selected else f"✓ Selected",
                    key=f"select_{style_type['type']}",
                    use_container_width=True,
                    type="primary" if is_selected else "secondary"
                ):
                    st.session_state.selected_style_type = style_type["type"]
                    st.rerun()

                # Show examples in expander
                with st.expander("📝 Example Use Cases"):
                    st.caption(style_type["examples"])

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Show guidance for selected type
    if st.session_state.selected_style_type:
        selected = next((s for s in style_types if s["type"] == st.session_state.selected_style_type), None)
        if selected:
            st.info(f"""
            ℹ️ **{selected['display_name']} Style Selected**

            When providing writing samples in the next step, make sure they represent the style you want the AI to learn.
            Include samples that demonstrate:
            - Your organization's voice and tone
            - Typical vocabulary and phrasing
            - Sentence structure and paragraph organization
            - How you present data and evidence
            """)

    # Navigation buttons
    st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("« Cancel", use_container_width=True):
            # Navigate back to writing styles list
            st.switch_page("pages/7_✍️_Writing_Styles.py")

    with col3:
        # Only allow proceeding if a type is selected
        can_proceed = st.session_state.selected_style_type is not None
        if st.button(
            "Next: Add Samples »",
            use_container_width=True,
            type="primary",
            disabled=not can_proceed
        ):
            st.session_state.wizard_step = 2
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def render_step2_collect_samples():
    """Render Step 2: Collect writing samples."""
    st.markdown("## Step 2: Add Writing Samples")
    st.markdown(f"""
    Paste 3-7 representative writing samples that demonstrate your desired **{st.session_state.selected_style_type.title()}** style.

    **Requirements:**
    - Minimum **3 samples**, maximum **7 samples**
    - Each sample must be at least **200 words**
    - Total recommended: **1,000 - 10,000 words** across all samples
    """)

    st.markdown("---")

    # Number of samples selector
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### How many samples will you provide?")
    with col2:
        num_samples = st.number_input(
            "Number of samples",
            min_value=3,
            max_value=7,
            value=st.session_state.num_samples,
            step=1,
            label_visibility="collapsed",
            key="num_samples_input"
        )
        if num_samples != st.session_state.num_samples:
            st.session_state.num_samples = num_samples
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Track validation status
    all_samples_valid = True
    total_word_count = 0
    valid_samples_count = 0

    # Render input areas for each sample
    for i in range(st.session_state.num_samples):
        sample_num = i + 1
        sample_key = f"sample_{sample_num}"

        # Get existing sample text if available
        existing_text = st.session_state.writing_samples.get(sample_key, "")

        st.markdown(f"""
        <div class="sample-container">
            <div class="sample-header">
                <div class="sample-title">Sample {sample_num}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Text area for sample input
        sample_text = st.text_area(
            f"Paste writing sample {sample_num} here",
            value=existing_text,
            height=200,
            key=f"sample_input_{sample_num}",
            placeholder=f"Paste your {st.session_state.selected_style_type} writing sample here...\n\nThis should be at least 200 words and representative of the style you want to teach the AI.",
            label_visibility="collapsed"
        )

        # Store in session state
        st.session_state.writing_samples[sample_key] = sample_text

        # Validate sample
        is_valid, message = validate_sample(sample_text)
        word_count = count_words(sample_text)
        total_word_count += word_count

        if is_valid:
            valid_samples_count += 1
        else:
            all_samples_valid = False

        # Display word count and validation status
        word_count_class = "word-count-valid" if is_valid else "word-count-invalid"
        status_icon = "✓" if is_valid else "⚠"

        col1, col2 = st.columns([3, 1])
        with col2:
            st.markdown(f'<div class="word-count {word_count_class}">{status_icon} {message}</div>', unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

    # Summary statistics
    st.markdown("---")
    st.markdown("### Summary")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Valid Samples", f"{valid_samples_count}/{st.session_state.num_samples}")
    with col2:
        st.metric("Total Words", f"{total_word_count:,}")
    with col3:
        # Check if within recommended range
        in_range = 1000 <= total_word_count <= 10000
        range_color = "🟢" if in_range else "🟡"
        st.metric("Recommended Range", f"{range_color} 1,000 - 10,000")
    with col4:
        can_proceed = all_samples_valid and valid_samples_count >= 3
        status = "✅ Ready" if can_proceed else "⚠️ Incomplete"
        st.metric("Status", status)

    # Guidance message
    if not all_samples_valid:
        st.warning("⚠️ Please ensure all samples meet the minimum 200-word requirement before proceeding.")
    elif total_word_count < 1000:
        st.info("ℹ️ Your total word count is below the recommended 1,000 words. Consider adding more content or additional samples for better AI analysis.")
    elif total_word_count > 10000:
        st.info("ℹ️ Your total word count exceeds the recommended 10,000 words. While this is fine, the AI may take longer to process.")
    else:
        st.success("✅ Your samples look good! You're ready to proceed to AI analysis.")

    # Navigation buttons
    st.markdown('<div class="nav-buttons">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 3, 1])

    with col1:
        if st.button("« Back", use_container_width=True):
            st.session_state.wizard_step = 1
            st.rerun()

    with col3:
        # Only allow proceeding if all samples are valid
        can_proceed = all_samples_valid and valid_samples_count >= 3
        if st.button(
            "Next: AI Analysis »",
            use_container_width=True,
            type="primary",
            disabled=not can_proceed
        ):
            # Future: Move to Step 3 (AI Analysis)
            st.info("AI Analysis step will be implemented in the next phase")
            # st.session_state.wizard_step = 3
            # st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)


def show_wizard_page():
    """Display the writing style creation wizard."""
    st.title("✍️ Create New Writing Style")
    st.markdown("Follow this wizard to create a new AI-powered writing style based on your organization's samples")

    st.markdown("<br>", unsafe_allow_html=True)

    # Render step indicator
    render_step_indicator(st.session_state.wizard_step)

    st.markdown("<br>", unsafe_allow_html=True)

    # Render current step
    if st.session_state.wizard_step == 1:
        render_step1_select_type()
    elif st.session_state.wizard_step == 2:
        render_step2_collect_samples()
    else:
        st.warning(f"Step {st.session_state.wizard_step} is not yet implemented")


def main():
    """Main entry point for the create writing style page."""
    # Require authentication
    require_auth()

    # Initialize session state
    init_session_state()

    # Show wizard
    show_wizard_page()


if __name__ == "__main__":
    main()
