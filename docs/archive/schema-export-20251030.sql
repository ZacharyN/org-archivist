--
-- PostgreSQL database dump
--

\restrict WBFwBIwNVGJ10HVQmvFP70gfgW8cUFrkQOspQJBBuUZRGhN1Scji9uOnDxifqtK

-- Dumped from database version 15.14
-- Dumped by pg_dump version 15.14

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pg_trgm; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pg_trgm WITH SCHEMA public;


--
-- Name: EXTENSION pg_trgm; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pg_trgm IS 'text similarity measurement and index searching based on trigrams';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    log_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    event_type character varying(50) NOT NULL,
    entity_type character varying(50),
    entity_id uuid,
    user_id character varying(100),
    details jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE audit_log; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_log IS 'Tracks important system events for auditing';


--
-- Name: conversations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.conversations (
    conversation_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(255),
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_id character varying(100),
    metadata jsonb
);


--
-- Name: TABLE conversations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.conversations IS 'Stores conversation sessions for chat interface';


--
-- Name: document_programs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_programs (
    doc_id uuid NOT NULL,
    program character varying(100) NOT NULL,
    CONSTRAINT valid_program CHECK (((program)::text = ANY ((ARRAY['Early Childhood'::character varying, 'Youth Development'::character varying, 'Family Support'::character varying, 'Education'::character varying, 'Health'::character varying, 'General'::character varying])::text[])))
);


--
-- Name: TABLE document_programs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.document_programs IS 'Associates documents with one or more programs';


--
-- Name: document_tags; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.document_tags (
    doc_id uuid NOT NULL,
    tag character varying(100) NOT NULL
);


--
-- Name: TABLE document_tags; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.document_tags IS 'Associates documents with user-defined tags';


--
-- Name: documents; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.documents (
    doc_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    filename character varying(255) NOT NULL,
    doc_type character varying(50) NOT NULL,
    year integer,
    outcome character varying(50),
    notes text,
    upload_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    file_size integer,
    chunks_count integer DEFAULT 0,
    created_by character varying(100),
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT valid_doc_type CHECK (((doc_type)::text = ANY ((ARRAY['Grant Proposal'::character varying, 'Annual Report'::character varying, 'Program Description'::character varying, 'Impact Report'::character varying, 'Strategic Plan'::character varying, 'Other'::character varying])::text[]))),
    CONSTRAINT valid_outcome CHECK (((outcome)::text = ANY ((ARRAY['N/A'::character varying, 'Funded'::character varying, 'Not Funded'::character varying, 'Pending'::character varying, 'Final Report'::character varying])::text[]))),
    CONSTRAINT valid_year CHECK (((year >= 2000) AND ((year)::numeric <= (EXTRACT(year FROM CURRENT_DATE) + (1)::numeric))))
);


--
-- Name: TABLE documents; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.documents IS 'Stores metadata for all uploaded documents';


--
-- Name: messages; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.messages (
    message_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    conversation_id uuid,
    role character varying(20) NOT NULL,
    content text NOT NULL,
    sources jsonb,
    metadata jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    CONSTRAINT valid_role CHECK (((role)::text = ANY ((ARRAY['user'::character varying, 'assistant'::character varying])::text[])))
);


--
-- Name: TABLE messages; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.messages IS 'Stores individual messages within conversations';


--
-- Name: prompt_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.prompt_templates (
    prompt_id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    name character varying(100) NOT NULL,
    category character varying(50) NOT NULL,
    content text NOT NULL,
    variables jsonb,
    active boolean DEFAULT true,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    version integer DEFAULT 1,
    CONSTRAINT valid_category CHECK (((category)::text = ANY ((ARRAY['Brand Voice'::character varying, 'Audience-Specific'::character varying, 'Section-Specific'::character varying, 'General'::character varying])::text[])))
);


--
-- Name: TABLE prompt_templates; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.prompt_templates IS 'Stores reusable prompt templates for content generation';


--
-- Name: system_config; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.system_config (
    key character varying(100) NOT NULL,
    value jsonb NOT NULL,
    description text,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: TABLE system_config; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.system_config IS 'Stores system-wide configuration settings';


--
-- Name: writing_styles; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.writing_styles (
    style_id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    type character varying(50) NOT NULL,
    description text,
    prompt_content text NOT NULL,
    samples jsonb,
    analysis_metadata jsonb,
    sample_count integer DEFAULT 0,
    active boolean DEFAULT true NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    created_by uuid,
    CONSTRAINT valid_style_type CHECK (((type)::text = ANY ((ARRAY['grant'::character varying, 'proposal'::character varying, 'report'::character varying, 'general'::character varying])::text[])))
);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (log_id);


--
-- Name: conversations conversations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.conversations
    ADD CONSTRAINT conversations_pkey PRIMARY KEY (conversation_id);


--
-- Name: document_programs document_programs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_programs
    ADD CONSTRAINT document_programs_pkey PRIMARY KEY (doc_id, program);


--
-- Name: document_tags document_tags_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_tags
    ADD CONSTRAINT document_tags_pkey PRIMARY KEY (doc_id, tag);


--
-- Name: documents documents_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.documents
    ADD CONSTRAINT documents_pkey PRIMARY KEY (doc_id);


--
-- Name: messages messages_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_pkey PRIMARY KEY (message_id);


--
-- Name: prompt_templates prompt_templates_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_name_key UNIQUE (name);


--
-- Name: prompt_templates prompt_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.prompt_templates
    ADD CONSTRAINT prompt_templates_pkey PRIMARY KEY (prompt_id);


--
-- Name: system_config system_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.system_config
    ADD CONSTRAINT system_config_pkey PRIMARY KEY (key);


--
-- Name: writing_styles writing_styles_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writing_styles
    ADD CONSTRAINT writing_styles_name_key UNIQUE (name);


--
-- Name: writing_styles writing_styles_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.writing_styles
    ADD CONSTRAINT writing_styles_pkey PRIMARY KEY (style_id);


--
-- Name: idx_audit_log_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_created_at ON public.audit_log USING btree (created_at);


--
-- Name: idx_audit_log_entity_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_entity_type ON public.audit_log USING btree (entity_type);


--
-- Name: idx_audit_log_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_event_type ON public.audit_log USING btree (event_type);


--
-- Name: idx_conversations_updated_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_updated_at ON public.conversations USING btree (updated_at);


--
-- Name: idx_conversations_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_conversations_user_id ON public.conversations USING btree (user_id);


--
-- Name: idx_document_programs_program; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_programs_program ON public.document_programs USING btree (program);


--
-- Name: idx_document_tags_tag; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_document_tags_tag ON public.document_tags USING btree (tag);


--
-- Name: idx_documents_doc_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_doc_type ON public.documents USING btree (doc_type);


--
-- Name: idx_documents_filename; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_filename ON public.documents USING btree (filename);


--
-- Name: idx_documents_upload_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_upload_date ON public.documents USING btree (upload_date);


--
-- Name: idx_documents_year; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_documents_year ON public.documents USING btree (year);


--
-- Name: idx_messages_conversation_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_conversation_id ON public.messages USING btree (conversation_id);


--
-- Name: idx_messages_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_messages_created_at ON public.messages USING btree (created_at);


--
-- Name: idx_prompt_templates_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_prompt_templates_active ON public.prompt_templates USING btree (active);


--
-- Name: idx_prompt_templates_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_prompt_templates_category ON public.prompt_templates USING btree (category);


--
-- Name: idx_writing_styles_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_writing_styles_active ON public.writing_styles USING btree (active);


--
-- Name: idx_writing_styles_created_by; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_writing_styles_created_by ON public.writing_styles USING btree (created_by);


--
-- Name: idx_writing_styles_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_writing_styles_type ON public.writing_styles USING btree (type);


--
-- Name: conversations update_conversations_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_conversations_updated_at BEFORE UPDATE ON public.conversations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: documents update_documents_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON public.documents FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: prompt_templates update_prompt_templates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_prompt_templates_updated_at BEFORE UPDATE ON public.prompt_templates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: system_config update_system_config_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_system_config_updated_at BEFORE UPDATE ON public.system_config FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: document_programs document_programs_doc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_programs
    ADD CONSTRAINT document_programs_doc_id_fkey FOREIGN KEY (doc_id) REFERENCES public.documents(doc_id) ON DELETE CASCADE;


--
-- Name: document_tags document_tags_doc_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.document_tags
    ADD CONSTRAINT document_tags_doc_id_fkey FOREIGN KEY (doc_id) REFERENCES public.documents(doc_id) ON DELETE CASCADE;


--
-- Name: messages messages_conversation_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.messages
    ADD CONSTRAINT messages_conversation_id_fkey FOREIGN KEY (conversation_id) REFERENCES public.conversations(conversation_id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict WBFwBIwNVGJ10HVQmvFP70gfgW8cUFrkQOspQJBBuUZRGhN1Scji9uOnDxifqtK

