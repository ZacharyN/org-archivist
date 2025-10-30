"""add_seed_data

Inserts default seed data for system configuration and prompt templates.

This migration populates:
- system_config: Default LLM, RAG, and user preference settings
- prompt_templates: Brand voice, audience-specific, and section-specific prompts

Revision ID: d160586f5e0f
Revises: 3f8d9a1c5e2b
Create Date: 2025-10-30 20:45:04.362941

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd160586f5e0f'
down_revision: Union[str, None] = '3f8d9a1c5e2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert default seed data"""

    # =========================================================================
    # Insert system configuration defaults
    # =========================================================================
    system_config = table('system_config',
        column('key', sa.String),
        column('value', postgresql.JSONB),
        column('description', sa.Text)
    )

    op.bulk_insert(system_config, [
        {
            'key': 'llm_config',
            'value': {
                'model_name': 'claude-sonnet-4-5-20250929',
                'temperature': 0.3,
                'max_tokens': 4096
            },
            'description': 'Default LLM model configuration'
        },
        {
            'key': 'rag_config',
            'value': {
                'embedding_model': 'text-embedding-3-small',
                'chunk_size': 500,
                'chunk_overlap': 50,
                'default_retrieval_count': 5,
                'similarity_threshold': 0.7,
                'recency_weight': 0.7
            },
            'description': 'Default RAG pipeline configuration'
        },
        {
            'key': 'user_preferences',
            'value': {
                'default_audience': None,
                'default_section': None,
                'default_tone': None,
                'citation_style': 'numbered',
                'auto_save_interval': 60
            },
            'description': 'Default user preferences'
        }
    ])

    # =========================================================================
    # Insert default prompt templates
    # =========================================================================
    prompt_templates = table('prompt_templates',
        column('name', sa.String),
        column('category', sa.String),
        column('content', sa.Text),
        column('variables', postgresql.JSONB),
        column('active', sa.Boolean)
    )

    op.bulk_insert(prompt_templates, [
        # Brand Voice
        {
            'name': 'Default Brand Voice',
            'category': 'Brand Voice',
            'content': '''You are the Foundation Historian for Nebraska Children and Families Foundation. Your role is to help staff write grant proposals, RFP responses, and donor communications by drawing on the organization's extensive document library.

Brand Voice Guidelines:
- Professional yet warm and accessible
- Data-driven but story-focused
- Emphasize impact and outcomes for children and families
- Use active voice and clear, direct language
- Avoid jargon unless appropriate for technical audiences
- Balance optimism about potential with realism about challenges
- Center the communities and families served, not the organization''',
            'variables': [],
            'active': True
        },

        # Audience-Specific Prompts
        {
            'name': 'Federal RFP',
            'category': 'Audience-Specific',
            'content': '''Federal RFP Style Requirements:
- Highly structured with clear sections matching RFP requirements
- Technical, formal language
- Third-person perspective
- Heavy emphasis on data, metrics, and evidence-based practices
- Explicit connections to federal priorities and regulations
- Comprehensive detail on evaluation and sustainability
- Budget justification with clear cost-benefit analysis''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Foundation Grant',
            'category': 'Audience-Specific',
            'content': '''Foundation Grant Style Requirements:
- Clear theory of change and logic model
- Balance of quantitative data and qualitative stories
- Emphasis on community partnerships and engagement
- Professional but accessible tone
- First-person organizational voice acceptable
- Focus on innovation and lessons learned
- Realistic about challenges and mitigation strategies''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Corporate Sponsor',
            'category': 'Audience-Specific',
            'content': '''Corporate Sponsor Style Requirements:
- Clear business case and ROI for corporate partner
- Emphasis on brand alignment and visibility opportunities
- Professional, results-oriented tone
- Highlight employee engagement and team-building opportunities
- Focus on measurable community impact
- Clear deliverables and recognition benefits
- Concise and easy to scan format''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Individual Donor',
            'category': 'Audience-Specific',
            'content': '''Individual Donor Style Requirements:
- Warm, engaging, personal tone
- Lead with compelling stories, support with data
- Make donor feel like a partner in the work
- Use "you" and "your support" language
- Emphasize tangible, concrete outcomes
- Show impact of donations at multiple levels
- Create emotional connection while remaining professional''',
            'variables': [],
            'active': True
        },
        {
            'name': 'General Public',
            'category': 'Audience-Specific',
            'content': '''General Public Style Requirements:
- Clear, accessible language avoiding jargon
- Conversational yet professional tone
- Lead with human interest and community impact
- Use concrete examples and relatable scenarios
- Balance emotional appeal with factual information
- Short paragraphs and easy-to-scan format
- Call to action that invites engagement''',
            'variables': [],
            'active': True
        },

        # Section-Specific Prompts
        {
            'name': 'Organizational Capacity',
            'category': 'Section-Specific',
            'content': '''Required Elements:
- Organizational history and mission alignment
- Governance structure and board composition
- Staff qualifications and expertise
- Organizational track record and past successes
- Financial stability and management
- Administrative systems and infrastructure
- Quality assurance and continuous improvement processes

Structure: Start with brief organizational overview, then address each capacity area with specific evidence.''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Program Description',
            'category': 'Section-Specific',
            'content': '''Required Elements:
- Clear program goals and objectives (SMART)
- Target population and eligibility criteria
- Program activities and service delivery model
- Timeline and milestones
- Staffing and organizational structure
- Logic model or theory of change
- Evidence base or best practices foundation

Structure: Begin with program overview and goals, describe activities in logical sequence, conclude with expected outcomes.''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Impact & Outcomes',
            'category': 'Section-Specific',
            'content': '''Required Elements:
- Clear measurable outcomes and success metrics
- Quantitative data demonstrating impact
- Qualitative evidence and success stories
- Evaluation methodology and data collection approach
- Baseline data and progress tracking
- Long-term impact and sustainability of results
- Lessons learned and continuous improvement

Structure: Lead with key outcomes and data, support with stories, conclude with evaluation approach.''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Budget Narrative',
            'category': 'Section-Specific',
            'content': '''Required Elements:
- Clear justification for each budget line item
- Cost-effectiveness and value demonstration
- Personnel qualifications and time allocation
- Indirect costs and overhead explanation
- Matching funds or cost-sharing details
- Sustainability plan beyond grant period
- Budget alignment with program activities

Structure: Organized by budget categories, with clear rationale for each expense.''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Sustainability Plan',
            'category': 'Section-Specific',
            'content': '''Required Elements:
- Long-term funding strategy and diverse revenue sources
- Plans for program continuation beyond grant period
- Community ownership and local capacity building
- Cost reduction strategies over time
- Partnership development and resource leverage
- Institutionalization within organization
- Exit strategy if applicable

Structure: Present realistic, multi-year sustainability approach with specific strategies.''',
            'variables': [],
            'active': True
        },
        {
            'name': 'Evaluation Plan',
            'category': 'Section-Specific',
            'content': '''Required Elements:
- Clear evaluation questions aligned with objectives
- Both process and outcome evaluation components
- Data collection methods and tools
- Timeline for data collection and analysis
- Responsible parties and expertise
- How findings will be used for improvement
- Dissemination plan for results

Structure: Present comprehensive evaluation framework showing how success will be measured and learning applied.''',
            'variables': [],
            'active': True
        }
    ])


def downgrade() -> None:
    """Remove seed data"""

    # Delete prompt templates
    op.execute("""
        DELETE FROM prompt_templates
        WHERE name IN (
            'Default Brand Voice',
            'Federal RFP',
            'Foundation Grant',
            'Corporate Sponsor',
            'Individual Donor',
            'General Public',
            'Organizational Capacity',
            'Program Description',
            'Impact & Outcomes',
            'Budget Narrative',
            'Sustainability Plan',
            'Evaluation Plan'
        )
    """)

    # Delete system config
    op.execute("""
        DELETE FROM system_config
        WHERE key IN ('llm_config', 'rag_config', 'user_preferences')
    """)
