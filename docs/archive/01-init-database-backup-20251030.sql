-- =============================================================================
-- Org Archivist - PostgreSQL Database Initialization Script
-- =============================================================================
-- This script runs automatically when the PostgreSQL container starts
-- for the first time. It sets up the database schema, extensions, and
-- initial tables required for the application.
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For text search optimization

-- Set timezone
SET timezone = 'UTC';

-- =============================================================================
-- Documents Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS documents (
    doc_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    filename VARCHAR(255) NOT NULL,
    doc_type VARCHAR(50) NOT NULL,
    year INTEGER,
    outcome VARCHAR(50),
    notes TEXT,
    upload_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    file_size INTEGER,
    chunks_count INTEGER DEFAULT 0,
    created_by VARCHAR(100),
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_year CHECK (year >= 2000 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1),
    CONSTRAINT valid_doc_type CHECK (doc_type IN (
        'Grant Proposal',
        'Annual Report',
        'Program Description',
        'Impact Report',
        'Strategic Plan',
        'Other'
    )),
    CONSTRAINT valid_outcome CHECK (outcome IN (
        'N/A',
        'Funded',
        'Not Funded',
        'Pending',
        'Final Report'
    ))
);

-- Create index on filename for faster lookups
CREATE INDEX IF NOT EXISTS idx_documents_filename ON documents(filename);
CREATE INDEX IF NOT EXISTS idx_documents_doc_type ON documents(doc_type);
CREATE INDEX IF NOT EXISTS idx_documents_year ON documents(year);
CREATE INDEX IF NOT EXISTS idx_documents_upload_date ON documents(upload_date);

-- Add comment to table
COMMENT ON TABLE documents IS 'Stores metadata for all uploaded documents';

-- =============================================================================
-- Document Programs Junction Table (Many-to-Many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS document_programs (
    doc_id UUID REFERENCES documents(doc_id) ON DELETE CASCADE,
    program VARCHAR(100) NOT NULL,
    PRIMARY KEY (doc_id, program),

    -- Constraints
    CONSTRAINT valid_program CHECK (program IN (
        'Early Childhood',
        'Youth Development',
        'Family Support',
        'Education',
        'Health',
        'General'
    ))
);

-- Create index for faster program-based queries
CREATE INDEX IF NOT EXISTS idx_document_programs_program ON document_programs(program);

COMMENT ON TABLE document_programs IS 'Associates documents with one or more programs';

-- =============================================================================
-- Document Tags Junction Table (Many-to-Many)
-- =============================================================================
CREATE TABLE IF NOT EXISTS document_tags (
    doc_id UUID REFERENCES documents(doc_id) ON DELETE CASCADE,
    tag VARCHAR(100) NOT NULL,
    PRIMARY KEY (doc_id, tag)
);

-- Create index for faster tag-based queries
CREATE INDEX IF NOT EXISTS idx_document_tags_tag ON document_tags(tag);

COMMENT ON TABLE document_tags IS 'Associates documents with user-defined tags';

-- =============================================================================
-- Prompt Templates Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS prompt_templates (
    prompt_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    category VARCHAR(50) NOT NULL,
    content TEXT NOT NULL,
    variables JSONB,
    active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    version INTEGER DEFAULT 1,

    -- Constraints
    CONSTRAINT valid_category CHECK (category IN (
        'Brand Voice',
        'Audience-Specific',
        'Section-Specific',
        'General'
    ))
);

-- Create indexes for prompt lookups
CREATE INDEX IF NOT EXISTS idx_prompt_templates_category ON prompt_templates(category);
CREATE INDEX IF NOT EXISTS idx_prompt_templates_active ON prompt_templates(active);

COMMENT ON TABLE prompt_templates IS 'Stores reusable prompt templates for content generation';

-- =============================================================================
-- Conversations Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS conversations (
    conversation_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    user_id VARCHAR(100),
    metadata JSONB
);

-- Create index for user-based queries
CREATE INDEX IF NOT EXISTS idx_conversations_user_id ON conversations(user_id);
CREATE INDEX IF NOT EXISTS idx_conversations_updated_at ON conversations(updated_at);

COMMENT ON TABLE conversations IS 'Stores conversation sessions for chat interface';

-- =============================================================================
-- Messages Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS messages (
    message_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID REFERENCES conversations(conversation_id) ON DELETE CASCADE,
    role VARCHAR(20) NOT NULL,
    content TEXT NOT NULL,
    sources JSONB,
    metadata JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    -- Constraints
    CONSTRAINT valid_role CHECK (role IN ('user', 'assistant'))
);

-- Create indexes for message queries
CREATE INDEX IF NOT EXISTS idx_messages_conversation_id ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at);

COMMENT ON TABLE messages IS 'Stores individual messages within conversations';

-- =============================================================================
-- System Configuration Table
-- =============================================================================
CREATE TABLE IF NOT EXISTS system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE system_config IS 'Stores system-wide configuration settings';

-- =============================================================================
-- Audit Log Table (for tracking important operations)
-- =============================================================================
CREATE TABLE IF NOT EXISTS audit_log (
    log_id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    event_type VARCHAR(50) NOT NULL,
    entity_type VARCHAR(50),
    entity_id UUID,
    user_id VARCHAR(100),
    details JSONB,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for audit log queries
CREATE INDEX IF NOT EXISTS idx_audit_log_event_type ON audit_log(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity_type ON audit_log(entity_type);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at);

COMMENT ON TABLE audit_log IS 'Tracks important system events for auditing';

-- =============================================================================
-- Functions and Triggers
-- =============================================================================

-- Function to update the updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Trigger for documents table
CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for prompt_templates table
CREATE TRIGGER update_prompt_templates_updated_at BEFORE UPDATE ON prompt_templates
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for conversations table
CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON conversations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger for system_config table
CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON system_config
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- Initial Data / Seed Data
-- =============================================================================

-- Insert default system configuration
INSERT INTO system_config (key, value, description) VALUES
    ('app_version', '"1.0.0"', 'Application version'),
    ('embedding_model', '"bge-large-en-v1.5"', 'Default embedding model'),
    ('default_chunk_size', '500', 'Default chunk size for document processing'),
    ('default_chunk_overlap', '50', 'Default chunk overlap'),
    ('default_top_k', '5', 'Default number of sources to retrieve')
ON CONFLICT (key) DO NOTHING;

-- Insert default prompt templates
INSERT INTO prompt_templates (name, category, content, variables, active) VALUES
    (
        'Brand Voice - Foundation',
        'Brand Voice',
        'Brand Voice Guidelines:
- Professional yet warm and accessible
- Data-driven but story-focused
- Emphasize impact and outcomes for children and families
- Use active voice and clear, direct language
- Avoid jargon unless appropriate for technical audiences
- Balance optimism about potential with realism about challenges
- Center the communities and families served, not the organization',
        '[]',
        TRUE
    ),
    (
        'Audience - Federal RFP',
        'Audience-Specific',
        'Federal RFP Style Requirements:
- Highly structured with clear sections matching RFP requirements
- Technical, formal language
- Third-person perspective
- Heavy emphasis on data, metrics, and evidence-based practices
- Explicit connections to federal priorities and regulations
- Comprehensive detail on evaluation and sustainability
- Budget justification with clear cost-benefit analysis',
        '[]',
        TRUE
    ),
    (
        'Section - Organizational Capacity',
        'Section-Specific',
        'Required Elements:
- Organizational history and mission alignment
- Governance structure and board composition
- Staff qualifications and expertise
- Organizational track record and past successes
- Financial stability and management
- Administrative systems and infrastructure
- Quality assurance and continuous improvement processes

Structure: Start with brief organizational overview, then address each capacity area with specific evidence.',
        '[]',
        TRUE
    )
ON CONFLICT (name) DO NOTHING;

-- =============================================================================
-- Grant necessary permissions (if using specific database user)
-- =============================================================================

-- This section can be customized based on your database user setup
-- For now, we'll grant all privileges to the default user

-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO your_app_user;

-- =============================================================================
-- Database Initialization Complete
-- =============================================================================

-- Log initialization
DO $$
BEGIN
    RAISE NOTICE 'Database initialization completed successfully';
    RAISE NOTICE 'Created tables: documents, document_programs, document_tags, prompt_templates, conversations, messages, system_config, audit_log';
    RAISE NOTICE 'Enabled extensions: uuid-ossp, pg_trgm';
END $$;
