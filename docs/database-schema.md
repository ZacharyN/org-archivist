# Database Schema Documentation

## Overview

This document provides a comprehensive reference for the org-archivist PostgreSQL database schema. All schema elements are now managed through Alembic migrations.

**Database:** org_archivist
**Schema Management:** Alembic
**Baseline Migration:** `2e0140e533a8_baseline_schema.py`

---

## PostgreSQL Extensions

### uuid-ossp
**Purpose:** Generate UUIDs for primary keys
**Usage:** `uuid_generate_v4()` function used as default for ID columns

### pg_trgm
**Purpose:** Text search optimization using trigram matching
**Usage:** Enables fast LIKE queries and text similarity searches

---

## Tables

### 1. documents

**Purpose:** Stores metadata for all uploaded documents

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| doc_id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique document identifier |
| filename | VARCHAR(255) | NOT NULL | Original filename |
| doc_type | VARCHAR(50) | NOT NULL, CHECK | Document category |
| year | INTEGER | CHECK | Document year (2000-current+1) |
| outcome | VARCHAR(50) | CHECK | Grant outcome status |
| notes | TEXT | | Free-text notes |
| upload_date | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | When uploaded |
| file_size | INTEGER | | File size in bytes |
| chunks_count | INTEGER | DEFAULT 0 | Number of vector chunks |
| created_by | VARCHAR(100) | | User who uploaded |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |

**Constraints:**
- `valid_year`: year >= 2000 AND year <= EXTRACT(YEAR FROM CURRENT_DATE) + 1
- `valid_doc_type`: doc_type IN ('Grant Proposal', 'Annual Report', 'Program Description', 'Impact Report', 'Strategic Plan', 'Other')
- `valid_outcome`: outcome IN ('N/A', 'Funded', 'Not Funded', 'Pending', 'Final Report')

**Indexes:**
- `idx_documents_filename` ON (filename)
- `idx_documents_doc_type` ON (doc_type)
- `idx_documents_year` ON (year)
- `idx_documents_upload_date` ON (upload_date)

**Triggers:**
- `update_documents_updated_at` BEFORE UPDATE: Auto-updates updated_at timestamp

---

### 2. document_programs

**Purpose:** Associates documents with one or more programs (many-to-many)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| doc_id | UUID | PRIMARY KEY, FOREIGN KEY REFERENCES documents(doc_id) ON DELETE CASCADE | Document reference |
| program | VARCHAR(100) | PRIMARY KEY, NOT NULL, CHECK | Program name |

**Constraints:**
- `valid_program`: program IN ('Early Childhood', 'Youth Development', 'Family Support', 'Education', 'Health', 'General')
- Composite PRIMARY KEY: (doc_id, program)

**Indexes:**
- `idx_document_programs_program` ON (program)

**Relationships:**
- Many-to-Many relationship between documents and programs
- Cascade delete: Deleting a document removes all program associations

---

### 3. document_tags

**Purpose:** Associates documents with user-defined tags (many-to-many)

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| doc_id | UUID | PRIMARY KEY, FOREIGN KEY REFERENCES documents(doc_id) ON DELETE CASCADE | Document reference |
| tag | VARCHAR(100) | PRIMARY KEY, NOT NULL | Tag name |

**Constraints:**
- Composite PRIMARY KEY: (doc_id, tag)

**Indexes:**
- `idx_document_tags_tag` ON (tag)

**Relationships:**
- Many-to-Many relationship between documents and tags
- Cascade delete: Deleting a document removes all tag associations

---

### 4. prompt_templates

**Purpose:** Stores reusable prompt templates for content generation

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| prompt_id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique prompt identifier |
| name | VARCHAR(100) | NOT NULL, UNIQUE | Template name |
| category | VARCHAR(50) | NOT NULL, CHECK | Template category |
| content | TEXT | NOT NULL | Prompt text content |
| variables | JSONB | | Template variables |
| active | BOOLEAN | DEFAULT TRUE | Is template active? |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update time |
| version | INTEGER | DEFAULT 1 | Template version number |

**Constraints:**
- `valid_category`: category IN ('Brand Voice', 'Audience-Specific', 'Section-Specific', 'General')

**Indexes:**
- `idx_prompt_templates_category` ON (category)
- `idx_prompt_templates_active` ON (active)

**Triggers:**
- `update_prompt_templates_updated_at` BEFORE UPDATE: Auto-updates updated_at timestamp

---

### 5. conversations

**Purpose:** Stores conversation sessions for chat interface

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| conversation_id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique conversation identifier |
| name | VARCHAR(255) | | Conversation name |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update time |
| user_id | VARCHAR(100) | | User identifier |
| metadata | JSONB | | Additional metadata |

**Indexes:**
- `idx_conversations_user_id` ON (user_id)
- `idx_conversations_updated_at` ON (updated_at)

**Triggers:**
- `update_conversations_updated_at` BEFORE UPDATE: Auto-updates updated_at timestamp

---

### 6. messages

**Purpose:** Stores individual messages within conversations

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| message_id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique message identifier |
| conversation_id | UUID | FOREIGN KEY REFERENCES conversations(conversation_id) ON DELETE CASCADE | Conversation reference |
| role | VARCHAR(20) | NOT NULL, CHECK | Message sender role |
| content | TEXT | NOT NULL | Message text content |
| sources | JSONB | | RAG sources used |
| metadata | JSONB | | Additional metadata |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Message timestamp |

**Constraints:**
- `valid_role`: role IN ('user', 'assistant')

**Indexes:**
- `idx_messages_conversation_id` ON (conversation_id)
- `idx_messages_created_at` ON (created_at)

**Relationships:**
- Cascade delete: Deleting a conversation removes all messages

---

### 7. system_config

**Purpose:** Stores system-wide configuration settings

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| key | VARCHAR(100) | PRIMARY KEY | Configuration key |
| value | JSONB | NOT NULL | Configuration value (JSON) |
| description | TEXT | | Key description |
| updated_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Last update time |

**Triggers:**
- `update_system_config_updated_at` BEFORE UPDATE: Auto-updates updated_at timestamp

---

### 8. audit_log

**Purpose:** Tracks important system events for auditing

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| log_id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique log identifier |
| event_type | VARCHAR(50) | NOT NULL | Type of event |
| entity_type | VARCHAR(50) | | Type of entity affected |
| entity_id | UUID | | ID of entity affected |
| user_id | VARCHAR(100) | | User who triggered event |
| details | JSONB | | Additional event details |
| created_at | TIMESTAMP | NOT NULL, DEFAULT CURRENT_TIMESTAMP | Event timestamp |

**Indexes:**
- `idx_audit_log_event_type` ON (event_type)
- `idx_audit_log_entity_type` ON (entity_type)
- `idx_audit_log_created_at` ON (created_at)

---

## 9. writing_styles (Added in migration 3f8d9a1c5e2b)

**Purpose:** Stores AI-analyzed writing styles and brand voice patterns for the organization

| Column | Type | Constraints | Description |
|--------|------|-------------|-------------|
| style_id | UUID | PRIMARY KEY, DEFAULT uuid_generate_v4() | Unique style identifier |
| name | VARCHAR(255) | NOT NULL | Style name |
| description | TEXT | | Style description |
| category | VARCHAR(100) | | Style category (audience, section, tone) |
| style_analysis | JSONB | NOT NULL | AI-generated style analysis |
| example_texts | JSONB | | Example texts exhibiting this style |
| source_documents | JSONB | | Documents used to derive this style |
| is_active | BOOLEAN | DEFAULT TRUE | Is style active for use? |
| created_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | DEFAULT CURRENT_TIMESTAMP | Last update time |
| created_by | VARCHAR(100) | | User/system who created |

**Indexes:**
- `idx_writing_styles_category` ON (category)
- `idx_writing_styles_is_active` ON (is_active)
- `idx_writing_styles_name` ON (name)

**Triggers:**
- `update_writing_styles_updated_at` BEFORE UPDATE: Auto-updates updated_at timestamp

**Notes:**
- Added as part of Phase 3: Writing Style Analysis feature
- Enables AI-powered analysis of organizational writing patterns
- Supports dynamic brand voice and audience-specific style recommendations

---

## Database Functions

### update_updated_at_column()

**Purpose:** Automatically update the `updated_at` column when a row is modified

**Returns:** TRIGGER

**Language:** plpgsql

**Logic:**
```sql
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
```

**Usage:** Applied as BEFORE UPDATE trigger on tables:
- documents
- prompt_templates
- conversations
- system_config
- writing_styles

---

## Seed Data

### system_config

Initial configuration values:

| Key | Value | Description |
|-----|-------|-------------|
| app_version | "1.0.0" | Application version |
| embedding_model | "bge-large-en-v1.5" | Default embedding model |
| default_chunk_size | 500 | Default chunk size for document processing |
| default_chunk_overlap | 50 | Default chunk overlap |
| default_top_k | 5 | Default number of sources to retrieve |

### prompt_templates

Default templates:

1. **Brand Voice - Foundation**
   - Category: Brand Voice
   - Content: Brand voice guidelines for Nebraska Children and Families Foundation
   - Active: TRUE

2. **Audience - Federal RFP**
   - Category: Audience-Specific
   - Content: Federal RFP style requirements
   - Active: TRUE

3. **Section - Organizational Capacity**
   - Category: Section-Specific
   - Content: Required elements for organizational capacity sections
   - Active: TRUE

---

## Relationships Diagram

```
documents (1) ──────┬───────> (M) document_programs
                    │
                    └───────> (M) document_tags

conversations (1) ─────────> (M) messages

[Independent tables]
prompt_templates
system_config
audit_log
writing_styles
```

---

## Migration History

| Revision | Description | Date | File |
|----------|-------------|------|------|
| 2e0140e533a8 | Baseline schema (all 8 core tables) | 2025-10-21 | `2e0140e533a8_baseline_schema.py` |
| 3f8d9a1c5e2b | Add writing_styles table | 2025-10-30 | `3f8d9a1c5e2b_add_writing_styles_table.py` |

---

## Schema Size Estimates

**Empty Database:** ~50 KB
**With 100 documents:** ~5-10 MB (metadata only, excludes vector embeddings in Qdrant)
**With 1000 documents:** ~50-100 MB

**Notes:**
- Vector embeddings are stored in Qdrant, not PostgreSQL
- JSONB columns (metadata, sources, details) can grow significantly with use
- Audit log will grow continuously; consider archiving strategy

---

## Backup & Restore

### Backup Schema Only
```bash
docker exec org-archivist-postgres pg_dump -U user -d org_archivist \
  --schema-only --no-owner --no-privileges > schema-backup.sql
```

### Backup Schema + Data
```bash
docker exec org-archivist-postgres pg_dump -U user -d org_archivist \
  --no-owner --no-privileges > full-backup.sql
```

### Restore
```bash
docker exec -i org-archivist-postgres psql -U user -d org_archivist < backup.sql
```

---

## Maintenance

### Vacuum Tables (Reclaim Space)
```sql
VACUUM FULL documents;
VACUUM FULL messages;
VACUUM FULL audit_log;
```

### Analyze Tables (Update Statistics)
```sql
ANALYZE documents;
ANALYZE messages;
```

### Check Table Sizes
```sql
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

---

## Version History

- **v1.0** (2025-10-30): Initial documentation created during Alembic migration
- Schema reflects state at migration baseline + writing_styles table
