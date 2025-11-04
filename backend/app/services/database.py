"""
Database Service for PostgreSQL Operations

This module provides async database operations for the Org Archivist application,
including document metadata storage and retrieval.
"""

import logging
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
import asyncpg

from app.config import get_settings

logger = logging.getLogger(__name__)


class DatabaseService:
    """
    Async PostgreSQL database service

    Handles all database operations for document metadata storage and retrieval.
    Uses asyncpg for high-performance async operations.
    """

    def __init__(self):
        """Initialize database service"""
        self.pool: Optional[asyncpg.Pool] = None
        settings = get_settings()
        self.connection_url = (
            f"postgresql://{settings.postgres_user}:{settings.postgres_password}"
            f"@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"
        )
        logger.info("DatabaseService initialized")

    async def connect(self) -> None:
        """
        Create connection pool

        Should be called during application startup.
        """
        if self.pool is None:
            try:
                self.pool = await asyncpg.create_pool(
                    self.connection_url,
                    min_size=2,
                    max_size=10,
                    command_timeout=60
                )
                logger.info("Database connection pool created")
            except Exception as e:
                logger.error(f"Failed to create database pool: {e}")
                raise

    async def disconnect(self) -> None:
        """
        Close connection pool

        Should be called during application shutdown.
        """
        if self.pool:
            await self.pool.close()
            self.pool = None
            logger.info("Database connection pool closed")

    async def insert_document(
        self,
        doc_id: UUID,
        filename: str,
        doc_type: str,
        year: Optional[int],
        outcome: Optional[str],
        notes: Optional[str],
        file_size: int,
        chunks_count: int,
        programs: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        # Phase 5: Document sensitivity fields
        is_sensitive: bool = False,
        sensitivity_level: Optional[str] = None,
        sensitivity_confirmed_at: Optional[datetime] = None,
        sensitivity_confirmed_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Insert a new document record

        Args:
            doc_id: Unique document identifier
            filename: Original filename
            doc_type: Document type (Grant Proposal, Annual Report, etc.)
            year: Year of document
            outcome: Outcome status (Funded, Not Funded, etc.)
            notes: Additional notes
            file_size: File size in bytes
            chunks_count: Number of chunks created
            programs: List of programs
            tags: List of tags
            created_by: User who uploaded the document
            is_sensitive: Whether document contains sensitive information (Phase 5)
            sensitivity_level: Sensitivity classification level (Phase 5)
            sensitivity_confirmed_at: When sensitivity was confirmed (Phase 5)
            sensitivity_confirmed_by: User who confirmed sensitivity (Phase 5)

        Returns:
            Dictionary with inserted document data

        Raises:
            Exception: If insertion fails
        """
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO documents (
                doc_id, filename, doc_type, year, outcome, notes,
                file_size, chunks_count, created_by, upload_date, updated_at,
                is_sensitive, sensitivity_level, sensitivity_confirmed_at, sensitivity_confirmed_by
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
            )
            RETURNING doc_id, filename, doc_type, year, outcome, upload_date, chunks_count
        """

        try:
            now = datetime.utcnow()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    doc_id, filename, doc_type, year, outcome, notes,
                    file_size, chunks_count, created_by, now, now,
                    is_sensitive, sensitivity_level, sensitivity_confirmed_at, sensitivity_confirmed_by
                )

                # Insert programs into junction table if provided
                if programs:
                    await self._insert_document_programs(conn, doc_id, programs)

                # Insert tags into junction table if provided
                if tags:
                    await self._insert_document_tags(conn, doc_id, tags)

                logger.info(f"Inserted document: {doc_id} ({filename})")

                return {
                    "doc_id": str(row["doc_id"]),
                    "filename": row["filename"],
                    "doc_type": row["doc_type"],
                    "year": row["year"],
                    "outcome": row["outcome"],
                    "upload_date": row["upload_date"].isoformat(),
                    "chunks_count": row["chunks_count"],
                }

        except Exception as e:
            logger.error(f"Failed to insert document {doc_id}: {e}")
            raise

    async def _insert_document_programs(
        self,
        conn: asyncpg.Connection,
        doc_id: UUID,
        programs: List[str]
    ) -> None:
        """Insert document-program associations"""
        for program in programs:
            await conn.execute(
                """
                INSERT INTO document_programs (doc_id, program_name)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                doc_id, program
            )

    async def _insert_document_tags(
        self,
        conn: asyncpg.Connection,
        doc_id: UUID,
        tags: List[str]
    ) -> None:
        """Insert document-tag associations"""
        for tag in tags:
            await conn.execute(
                """
                INSERT INTO document_tags (doc_id, tag_name)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
                """,
                doc_id, tag
            )

    async def get_document(self, doc_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve document by ID

        Args:
            doc_id: Document identifier

        Returns:
            Document data dictionary or None if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT
                doc_id, filename, doc_type, year, outcome, notes,
                upload_date, file_size, chunks_count, created_by, updated_at
            FROM documents
            WHERE doc_id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, doc_id)

                if not row:
                    return None

                # Get programs
                programs = await self._get_document_programs(conn, doc_id)

                # Get tags
                tags = await self._get_document_tags(conn, doc_id)

                return {
                    "doc_id": str(row["doc_id"]),
                    "filename": row["filename"],
                    "doc_type": row["doc_type"],
                    "year": row["year"],
                    "outcome": row["outcome"],
                    "notes": row["notes"],
                    "upload_date": row["upload_date"].isoformat(),
                    "file_size": row["file_size"],
                    "chunks_count": row["chunks_count"],
                    "created_by": row["created_by"],
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "programs": programs,
                    "tags": tags,
                }

        except Exception as e:
            logger.error(f"Failed to get document {doc_id}: {e}")
            raise

    async def _get_document_programs(
        self,
        conn: asyncpg.Connection,
        doc_id: UUID
    ) -> List[str]:
        """Get programs for a document"""
        rows = await conn.fetch(
            "SELECT program_name FROM document_programs WHERE doc_id = $1",
            doc_id
        )
        return [row["program_name"] for row in rows]

    async def _get_document_tags(
        self,
        conn: asyncpg.Connection,
        doc_id: UUID
    ) -> List[str]:
        """Get tags for a document"""
        rows = await conn.fetch(
            "SELECT tag_name FROM document_tags WHERE doc_id = $1",
            doc_id
        )
        return [row["tag_name"] for row in rows]

    async def delete_document(self, doc_id: UUID) -> bool:
        """
        Delete document record

        Args:
            doc_id: Document identifier

        Returns:
            True if deleted, False if not found

        Note:
            Related records in junction tables are deleted automatically
            via CASCADE constraints.
        """
        if not self.pool:
            await self.connect()

        query = "DELETE FROM documents WHERE doc_id = $1"

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, doc_id)
                deleted = result.split()[-1] == "1"  # "DELETE 1" means one row deleted

                if deleted:
                    logger.info(f"Deleted document: {doc_id}")
                else:
                    logger.warning(f"Document not found for deletion: {doc_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            raise

    async def list_documents(
        self,
        skip: int = 0,
        limit: int = 100,
        doc_type: Optional[str] = None,
        year: Optional[int] = None,
        outcome: Optional[str] = None,
        search: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        List documents with optional filtering

        Args:
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return
            doc_type: Filter by document type
            year: Filter by year
            outcome: Filter by outcome
            search: Search in filename (case-insensitive)

        Returns:
            List of document dictionaries
        """
        if not self.pool:
            await self.connect()

        # Build query with filters
        conditions = []
        params = []
        param_count = 0

        if doc_type:
            param_count += 1
            conditions.append(f"doc_type = ${param_count}")
            params.append(doc_type)

        if year:
            param_count += 1
            conditions.append(f"year = ${param_count}")
            params.append(year)

        if outcome:
            param_count += 1
            conditions.append(f"outcome = ${param_count}")
            params.append(outcome)

        if search:
            param_count += 1
            conditions.append(f"filename ILIKE ${param_count}")
            params.append(f"%{search}%")

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        query = f"""
            SELECT
                doc_id, filename, doc_type, year, outcome,
                upload_date, file_size, chunks_count
            FROM documents
            WHERE {where_clause}
            ORDER BY upload_date DESC
            LIMIT ${param_count + 1} OFFSET ${param_count + 2}
        """

        params.extend([limit, skip])

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

                documents = []
                for row in rows:
                    # Get programs and tags for each document
                    programs = await self._get_document_programs(conn, row["doc_id"])
                    tags = await self._get_document_tags(conn, row["doc_id"])

                    documents.append({
                        "doc_id": str(row["doc_id"]),
                        "filename": row["filename"],
                        "doc_type": row["doc_type"],
                        "year": row["year"],
                        "outcome": row["outcome"],
                        "upload_date": row["upload_date"].isoformat(),
                        "file_size": row["file_size"],
                        "chunks_count": row["chunks_count"],
                        "programs": programs,
                        "tags": tags,
                    })

                return documents

        except Exception as e:
            logger.error(f"Failed to list documents: {e}")
            raise

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get document library statistics

        Returns:
            Dictionary with statistics
        """
        if not self.pool:
            await self.connect()

        try:
            async with self.pool.acquire() as conn:
                # Total counts
                total_row = await conn.fetchrow(
                    "SELECT COUNT(*) as count, SUM(chunks_count) as chunks FROM documents"
                )
                total_documents = total_row["count"] or 0
                total_chunks = total_row["chunks"] or 0

                # By type
                type_rows = await conn.fetch(
                    "SELECT doc_type, COUNT(*) as count FROM documents GROUP BY doc_type"
                )
                by_type = {row["doc_type"]: row["count"] for row in type_rows}

                # By year
                year_rows = await conn.fetch(
                    "SELECT year, COUNT(*) as count FROM documents WHERE year IS NOT NULL GROUP BY year ORDER BY year DESC"
                )
                by_year = {row["year"]: row["count"] for row in year_rows}

                # By outcome
                outcome_rows = await conn.fetch(
                    "SELECT outcome, COUNT(*) as count FROM documents WHERE outcome IS NOT NULL GROUP BY outcome"
                )
                by_outcome = {row["outcome"]: row["count"] for row in outcome_rows}

                avg_chunks = total_chunks / total_documents if total_documents > 0 else 0.0

                return {
                    "total_documents": total_documents,
                    "total_chunks": total_chunks,
                    "by_type": by_type,
                    "by_year": by_year,
                    "by_outcome": by_outcome,
                    "avg_chunks_per_doc": round(avg_chunks, 2),
                }

        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            raise

    # =========================================================================
    # Writing Styles Methods
    # =========================================================================

    async def create_writing_style(
        self,
        style_id: UUID,
        name: str,
        style_type: str,
        prompt_content: str,
        description: Optional[str] = None,
        samples: Optional[List[str]] = None,
        analysis_metadata: Optional[Dict[str, Any]] = None,
        sample_count: int = 0,
        created_by: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """
        Create a new writing style record

        Args:
            style_id: Unique style identifier
            name: Style name
            style_type: Type (grant, proposal, report, general)
            prompt_content: The actual style prompt content
            description: Optional style description
            samples: List of original writing samples
            analysis_metadata: AI analysis results
            sample_count: Number of samples used
            created_by: User who created the style

        Returns:
            Dictionary with created style data

        Raises:
            Exception: If creation fails
        """
        if not self.pool:
            await self.connect()

        import json

        query = """
            INSERT INTO writing_styles (
                style_id, name, type, description, prompt_content,
                samples, analysis_metadata, sample_count, active,
                created_at, updated_at, created_by
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12
            )
            RETURNING style_id, name, type, description, sample_count, active, created_at
        """

        try:
            now = datetime.utcnow()
            samples_json = json.dumps(samples) if samples else None
            metadata_json = json.dumps(analysis_metadata) if analysis_metadata else None

            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    style_id, name, style_type, description, prompt_content,
                    samples_json, metadata_json, sample_count, True,
                    now, now, created_by
                )

                logger.info(f"Created writing style: {style_id} ({name})")

                return {
                    "style_id": str(row["style_id"]),
                    "name": row["name"],
                    "type": row["type"],
                    "description": row["description"],
                    "sample_count": row["sample_count"],
                    "active": row["active"],
                    "created_at": row["created_at"].isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to create writing style {style_id}: {e}")
            raise

    async def get_writing_style(self, style_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve writing style by ID

        Args:
            style_id: Style identifier

        Returns:
            Style data dictionary or None if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT
                style_id, name, type, description, prompt_content,
                samples, analysis_metadata, sample_count, active,
                created_at, updated_at, created_by
            FROM writing_styles
            WHERE style_id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, style_id)

                if not row:
                    return None

                return {
                    "style_id": str(row["style_id"]),
                    "name": row["name"],
                    "type": row["type"],
                    "description": row["description"],
                    "prompt_content": row["prompt_content"],
                    "samples": row["samples"],
                    "analysis_metadata": row["analysis_metadata"],
                    "sample_count": row["sample_count"],
                    "active": row["active"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "created_by": str(row["created_by"]) if row["created_by"] else None,
                }

        except Exception as e:
            logger.error(f"Failed to get writing style {style_id}: {e}")
            raise

    async def list_writing_styles(
        self,
        style_type: Optional[str] = None,
        active: Optional[bool] = None,
        search: Optional[str] = None,
        created_by: Optional[str] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        List writing styles with optional filtering

        Args:
            style_type: Filter by type (grant, proposal, report, general)
            active: Filter by active status (true/false)
            search: Search in name and description
            created_by: Filter by creator user ID
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of style data dictionaries
        """
        if not self.pool:
            await self.connect()

        # Build query with filters
        conditions = []
        params = []
        param_idx = 1

        if style_type:
            conditions.append(f"type = ${param_idx}")
            params.append(style_type)
            param_idx += 1

        if active is not None:
            conditions.append(f"active = ${param_idx}")
            params.append(active)
            param_idx += 1

        if search:
            conditions.append(f"(name ILIKE ${param_idx} OR description ILIKE ${param_idx})")
            params.append(f"%{search}%")
            param_idx += 1

        if created_by:
            conditions.append(f"created_by = ${param_idx}")
            params.append(UUID(created_by))
            param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                style_id, name, type, description, sample_count, active,
                created_at, updated_at, created_by
            FROM writing_styles
            {where_clause}
            ORDER BY created_at DESC
            OFFSET ${param_idx} LIMIT ${param_idx + 1}
        """

        params.extend([skip, limit])

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

                styles = []
                for row in rows:
                    styles.append({
                        "style_id": str(row["style_id"]),
                        "name": row["name"],
                        "type": row["type"],
                        "description": row["description"],
                        "sample_count": row["sample_count"],
                        "active": row["active"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                        "created_by": str(row["created_by"]) if row["created_by"] else None,
                    })

                return styles

        except Exception as e:
            logger.error(f"Failed to list writing styles: {e}")
            raise

    async def update_writing_style(
        self,
        style_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        prompt_content: Optional[str] = None,
        active: Optional[bool] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        Update writing style fields

        Args:
            style_id: Style identifier
            name: Updated name
            description: Updated description
            prompt_content: Updated prompt content
            active: Updated active status

        Returns:
            Updated style data dictionary or None if not found
        """
        if not self.pool:
            await self.connect()

        # Build update query dynamically based on provided fields
        updates = []
        params = []
        param_idx = 1

        if name is not None:
            updates.append(f"name = ${param_idx}")
            params.append(name)
            param_idx += 1

        if description is not None:
            updates.append(f"description = ${param_idx}")
            params.append(description)
            param_idx += 1

        if prompt_content is not None:
            updates.append(f"prompt_content = ${param_idx}")
            params.append(prompt_content)
            param_idx += 1

        if active is not None:
            updates.append(f"active = ${param_idx}")
            params.append(active)
            param_idx += 1

        if not updates:
            # No fields to update
            return await self.get_writing_style(style_id)

        # Always update updated_at
        updates.append(f"updated_at = ${param_idx}")
        params.append(datetime.utcnow())
        param_idx += 1

        # Add style_id as last parameter
        params.append(style_id)

        query = f"""
            UPDATE writing_styles
            SET {', '.join(updates)}
            WHERE style_id = ${param_idx}
            RETURNING style_id, name, type, description, sample_count, active, created_at, updated_at
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)

                if not row:
                    logger.warning(f"Writing style not found for update: {style_id}")
                    return None

                logger.info(f"Updated writing style: {style_id}")

                return {
                    "style_id": str(row["style_id"]),
                    "name": row["name"],
                    "type": row["type"],
                    "description": row["description"],
                    "sample_count": row["sample_count"],
                    "active": row["active"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to update writing style {style_id}: {e}")
            raise

    async def delete_writing_style(self, style_id: UUID) -> bool:
        """
        Delete writing style record

        Args:
            style_id: Style identifier

        Returns:
            True if deleted, False if not found
        """
        if not self.pool:
            await self.connect()

        query = "DELETE FROM writing_styles WHERE style_id = $1"

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, style_id)
                deleted = result.split()[-1] == "1"

                if deleted:
                    logger.info(f"Deleted writing style: {style_id}")
                else:
                    logger.warning(f"Writing style not found for deletion: {style_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete writing style {style_id}: {e}")
            raise

    async def activate_writing_style(self, style_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Activate a writing style

        Args:
            style_id: Style identifier

        Returns:
            Updated style data or None if not found
        """
        return await self.update_writing_style(style_id, active=True)

    async def deactivate_writing_style(self, style_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Deactivate a writing style

        Args:
            style_id: Style identifier

        Returns:
            Updated style data or None if not found
        """
        return await self.update_writing_style(style_id, active=False)

    async def get_writing_style_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve writing style by name

        Args:
            name: Style name

        Returns:
            Style data dictionary or None if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT
                style_id, name, type, description, prompt_content,
                samples, analysis_metadata, sample_count, active,
                created_at, updated_at, created_by
            FROM writing_styles
            WHERE name = $1
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, name)

                if not row:
                    return None

                return {
                    "style_id": str(row["style_id"]),
                    "name": row["name"],
                    "type": row["type"],
                    "description": row["description"],
                    "prompt_content": row["prompt_content"],
                    "samples": row["samples"],
                    "analysis_metadata": row["analysis_metadata"],
                    "sample_count": row["sample_count"],
                    "active": row["active"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    "created_by": str(row["created_by"]) if row["created_by"] else None,
                }

        except Exception as e:
            logger.error(f"Failed to get writing style by name '{name}': {e}")
            raise

    # ======================
    # Outputs Methods
    # ======================

    async def create_output(
        self,
        output_id: UUID,
        output_type: str,
        title: str,
        content: str,
        conversation_id: Optional[UUID] = None,
        word_count: Optional[int] = None,
        status: str = "draft",
        writing_style_id: Optional[UUID] = None,
        funder_name: Optional[str] = None,
        requested_amount: Optional[float] = None,
        awarded_amount: Optional[float] = None,
        submission_date: Optional[str] = None,
        decision_date: Optional[str] = None,
        success_notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new output record

        Args:
            output_id: Unique output identifier
            output_type: Type of output (grant_proposal, budget_narrative, etc.)
            title: Output title
            content: Output content
            conversation_id: Optional conversation ID this output belongs to
            word_count: Word count of content
            status: Output status (draft, submitted, pending, awarded, not_awarded)
            writing_style_id: Optional writing style used
            funder_name: Name of funder
            requested_amount: Amount requested
            awarded_amount: Amount awarded
            submission_date: Date submitted
            decision_date: Date decision received
            success_notes: Notes about success/failure
            metadata: Additional metadata (sources, confidence, etc.)
            created_by: User who created the output

        Returns:
            Dictionary with created output data

        Raises:
            Exception: If creation fails
        """
        if not self.pool:
            await self.connect()

        import json

        query = """
            INSERT INTO outputs (
                output_id, conversation_id, output_type, title, content,
                word_count, status, writing_style_id, funder_name,
                requested_amount, awarded_amount, submission_date, decision_date,
                success_notes, metadata, created_by, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, $17, $18
            )
            RETURNING output_id, output_type, title, status, created_at
        """

        try:
            now = datetime.utcnow()
            metadata_json = json.dumps(metadata) if metadata else None

            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    output_id, conversation_id, output_type, title, content,
                    word_count, status, writing_style_id, funder_name,
                    requested_amount, awarded_amount, submission_date, decision_date,
                    success_notes, metadata_json, created_by, now, now
                )

                logger.info(f"Created output: {output_id} ({title})")

                return {
                    "output_id": str(row["output_id"]),
                    "output_type": row["output_type"],
                    "title": row["title"],
                    "status": row["status"],
                    "created_at": row["created_at"].isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to create output {output_id}: {e}")
            raise

    async def get_output(self, output_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Retrieve output by ID

        Args:
            output_id: Output ID to retrieve

        Returns:
            Output data dictionary or None if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT
                output_id, conversation_id, output_type, title, content,
                word_count, status, writing_style_id, funder_name,
                requested_amount, awarded_amount, submission_date, decision_date,
                success_notes, metadata, created_by, created_at, updated_at
            FROM outputs
            WHERE output_id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, output_id)

                if not row:
                    return None

                return {
                    "output_id": str(row["output_id"]),
                    "conversation_id": str(row["conversation_id"]) if row["conversation_id"] else None,
                    "output_type": row["output_type"],
                    "title": row["title"],
                    "content": row["content"],
                    "word_count": row["word_count"],
                    "status": row["status"],
                    "writing_style_id": str(row["writing_style_id"]) if row["writing_style_id"] else None,
                    "funder_name": row["funder_name"],
                    "requested_amount": float(row["requested_amount"]) if row["requested_amount"] else None,
                    "awarded_amount": float(row["awarded_amount"]) if row["awarded_amount"] else None,
                    "submission_date": row["submission_date"].isoformat() if row["submission_date"] else None,
                    "decision_date": row["decision_date"].isoformat() if row["decision_date"] else None,
                    "success_notes": row["success_notes"],
                    "metadata": row["metadata"],
                    "created_by": row["created_by"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                }

        except Exception as e:
            logger.error(f"Failed to get output {output_id}: {e}")
            raise

    async def list_outputs(
        self,
        output_type: Optional[List[str]] = None,
        status: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        writing_style_id: Optional[str] = None,
        funder_name: Optional[str] = None,
        date_range: Optional[tuple] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        List outputs with optional filtering

        Args:
            output_type: Filter by output types (list)
            status: Filter by statuses (list)
            created_by: Filter by creator user
            writing_style_id: Filter by writing style
            funder_name: Filter by funder (partial match)
            date_range: Tuple of (start_date, end_date) for filtering by created_at
            skip: Number of records to skip (pagination)
            limit: Maximum number of records to return

        Returns:
            List of output data dictionaries
        """
        if not self.pool:
            await self.connect()

        # Build query with filters
        conditions = []
        params = []
        param_idx = 1

        if output_type:
            placeholders = ", ".join([f"${param_idx + i}" for i in range(len(output_type))])
            conditions.append(f"output_type IN ({placeholders})")
            params.extend(output_type)
            param_idx += len(output_type)

        if status:
            placeholders = ", ".join([f"${param_idx + i}" for i in range(len(status))])
            conditions.append(f"status IN ({placeholders})")
            params.extend(status)
            param_idx += len(status)

        if created_by:
            conditions.append(f"created_by = ${param_idx}")
            params.append(created_by)
            param_idx += 1

        if writing_style_id:
            conditions.append(f"writing_style_id = ${param_idx}")
            params.append(UUID(writing_style_id))
            param_idx += 1

        if funder_name:
            conditions.append(f"funder_name ILIKE ${param_idx}")
            params.append(f"%{funder_name}%")
            param_idx += 1

        if date_range:
            start_date, end_date = date_range
            if start_date:
                conditions.append(f"created_at >= ${param_idx}")
                params.append(start_date)
                param_idx += 1
            if end_date:
                conditions.append(f"created_at <= ${param_idx}")
                params.append(end_date)
                param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                output_id, conversation_id, output_type, title, content,
                word_count, status, writing_style_id, funder_name,
                requested_amount, awarded_amount, submission_date, decision_date,
                success_notes, metadata, created_by, created_at, updated_at
            FROM outputs
            {where_clause}
            ORDER BY created_at DESC
            OFFSET ${param_idx} LIMIT ${param_idx + 1}
        """

        params.extend([skip, limit])

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

                outputs = []
                for row in rows:
                    outputs.append({
                        "output_id": str(row["output_id"]),
                        "conversation_id": str(row["conversation_id"]) if row["conversation_id"] else None,
                        "output_type": row["output_type"],
                        "title": row["title"],
                        "content": row["content"],
                        "word_count": row["word_count"],
                        "status": row["status"],
                        "writing_style_id": str(row["writing_style_id"]) if row["writing_style_id"] else None,
                        "funder_name": row["funder_name"],
                        "requested_amount": float(row["requested_amount"]) if row["requested_amount"] else None,
                        "awarded_amount": float(row["awarded_amount"]) if row["awarded_amount"] else None,
                        "submission_date": row["submission_date"].isoformat() if row["submission_date"] else None,
                        "decision_date": row["decision_date"].isoformat() if row["decision_date"] else None,
                        "success_notes": row["success_notes"],
                        "metadata": row["metadata"],
                        "created_by": row["created_by"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    })

                return outputs

        except Exception as e:
            logger.error(f"Failed to list outputs: {e}")
            raise

    async def update_output(
        self,
        output_id: UUID,
        **updates
    ) -> Optional[Dict[str, Any]]:
        """
        Update output fields

        Args:
            output_id: Output ID to update
            **updates: Fields to update (any output field except output_id)

        Returns:
            Updated output data or None if not found
        """
        if not self.pool:
            await self.connect()

        if not updates:
            return await self.get_output(output_id)

        import json

        # Build SET clause dynamically
        set_clauses = []
        params = []
        param_idx = 1

        # Handle metadata specially (needs JSON serialization)
        if "metadata" in updates:
            set_clauses.append(f"metadata = ${param_idx}")
            params.append(json.dumps(updates["metadata"]) if updates["metadata"] else None)
            param_idx += 1
            del updates["metadata"]

        # Add other fields
        for field, value in updates.items():
            set_clauses.append(f"{field} = ${param_idx}")
            params.append(value)
            param_idx += 1

        # Always update updated_at
        set_clauses.append(f"updated_at = ${param_idx}")
        params.append(datetime.utcnow())
        param_idx += 1

        # Add output_id as last parameter
        params.append(output_id)

        query = f"""
            UPDATE outputs
            SET {', '.join(set_clauses)}
            WHERE output_id = ${param_idx}
            RETURNING output_id, output_type, title, status, updated_at
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)

                if not row:
                    return None

                logger.info(f"Updated output: {output_id}")

                return {
                    "output_id": str(row["output_id"]),
                    "output_type": row["output_type"],
                    "title": row["title"],
                    "status": row["status"],
                    "updated_at": row["updated_at"].isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to update output {output_id}: {e}")
            raise

    async def delete_output(self, output_id: UUID) -> bool:
        """
        Delete an output

        Args:
            output_id: Output ID to delete

        Returns:
            True if deleted, False if not found
        """
        if not self.pool:
            await self.connect()

        query = "DELETE FROM outputs WHERE output_id = $1"

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, output_id)

                # Check if any rows were deleted
                deleted = result.split()[-1] == "1"

                if deleted:
                    logger.info(f"Deleted output: {output_id}")
                else:
                    logger.warning(f"Output not found for deletion: {output_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete output {output_id}: {e}")
            raise

    async def get_outputs_stats(
        self,
        output_type: Optional[List[str]] = None,
        created_by: Optional[str] = None,
        date_range: Optional[tuple] = None,
    ) -> Dict[str, Any]:
        """
        Get statistics about outputs

        Args:
            output_type: Filter by output types
            created_by: Filter by creator
            date_range: Tuple of (start_date, end_date)

        Returns:
            Dictionary with statistics:
            - total_outputs: Total count
            - by_type: Count by output type
            - by_status: Count by status
            - success_rate: Percentage of awarded grants
            - total_requested: Sum of requested amounts
            - total_awarded: Sum of awarded amounts
        """
        if not self.pool:
            await self.connect()

        # Build WHERE clause for filtering
        conditions = []
        params = []
        param_idx = 1

        if output_type:
            placeholders = ", ".join([f"${param_idx + i}" for i in range(len(output_type))])
            conditions.append(f"output_type IN ({placeholders})")
            params.extend(output_type)
            param_idx += len(output_type)

        if created_by:
            conditions.append(f"created_by = ${param_idx}")
            params.append(created_by)
            param_idx += 1

        if date_range:
            start_date, end_date = date_range
            if start_date:
                conditions.append(f"created_at >= ${param_idx}")
                params.append(start_date)
                param_idx += 1
            if end_date:
                conditions.append(f"created_at <= ${param_idx}")
                params.append(end_date)
                param_idx += 1

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        query = f"""
            SELECT
                COUNT(*) as total_outputs,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                COUNT(*) FILTER (WHERE status = 'submitted' OR status = 'pending' OR status = 'awarded' OR status = 'not_awarded') as submitted_count,
                COALESCE(SUM(requested_amount), 0) as total_requested,
                COALESCE(SUM(awarded_amount), 0) as total_awarded
            FROM outputs
            {where_clause}
        """

        query_by_type = f"""
            SELECT output_type, COUNT(*) as count
            FROM outputs
            {where_clause}
            GROUP BY output_type
        """

        query_by_status = f"""
            SELECT status, COUNT(*) as count
            FROM outputs
            {where_clause}
            GROUP BY status
        """

        try:
            async with self.pool.acquire() as conn:
                # Get overall stats
                overall = await conn.fetchrow(query, *params)

                # Get counts by type
                by_type_rows = await conn.fetch(query_by_type, *params)
                by_type = {row["output_type"]: row["count"] for row in by_type_rows}

                # Get counts by status
                by_status_rows = await conn.fetch(query_by_status, *params)
                by_status = {row["status"]: row["count"] for row in by_status_rows}

                # Calculate success rate
                submitted = overall["submitted_count"]
                awarded = overall["awarded_count"]
                success_rate = (awarded / submitted * 100) if submitted > 0 else 0.0

                # Calculate averages
                total_outputs = overall["total_outputs"]
                avg_requested = (float(overall["total_requested"]) / total_outputs) if total_outputs > 0 else 0.0
                avg_awarded = (float(overall["total_awarded"]) / total_outputs) if total_outputs > 0 else 0.0

                return {
                    "total_outputs": total_outputs,
                    "by_type": by_type,
                    "by_status": by_status,
                    "success_rate": round(success_rate, 2),
                    "total_requested": float(overall["total_requested"]),
                    "total_awarded": float(overall["total_awarded"]),
                    "avg_requested": round(avg_requested, 2),
                    "avg_awarded": round(avg_awarded, 2),
                }

        except Exception as e:
            logger.error(f"Failed to get outputs stats: {e}")
            raise

    async def search_outputs(
        self,
        query: str,
        output_type: Optional[List[str]] = None,
        status: Optional[List[str]] = None,
        skip: int = 0,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Full-text search on outputs

        Args:
            query: Search query (searches title, content, funder_name, success_notes)
            output_type: Filter by output types
            status: Filter by statuses
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of matching output data dictionaries
        """
        if not self.pool:
            await self.connect()

        # Build conditions
        conditions = [
            "(title ILIKE $1 OR content ILIKE $1 OR funder_name ILIKE $1 OR success_notes ILIKE $1)"
        ]
        params = [f"%{query}%"]
        param_idx = 2

        if output_type:
            placeholders = ", ".join([f"${param_idx + i}" for i in range(len(output_type))])
            conditions.append(f"output_type IN ({placeholders})")
            params.extend(output_type)
            param_idx += len(output_type)

        if status:
            placeholders = ", ".join([f"${param_idx + i}" for i in range(len(status))])
            conditions.append(f"status IN ({placeholders})")
            params.extend(status)
            param_idx += len(status)

        where_clause = f"WHERE {' AND '.join(conditions)}"

        sql_query = f"""
            SELECT
                output_id, conversation_id, output_type, title, content,
                word_count, status, writing_style_id, funder_name,
                requested_amount, awarded_amount, submission_date, decision_date,
                success_notes, metadata, created_by, created_at, updated_at
            FROM outputs
            {where_clause}
            ORDER BY created_at DESC
            OFFSET ${param_idx} LIMIT ${param_idx + 1}
        """

        params.extend([skip, limit])

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(sql_query, *params)

                outputs = []
                for row in rows:
                    outputs.append({
                        "output_id": str(row["output_id"]),
                        "conversation_id": str(row["conversation_id"]) if row["conversation_id"] else None,
                        "output_type": row["output_type"],
                        "title": row["title"],
                        "content": row["content"],
                        "word_count": row["word_count"],
                        "status": row["status"],
                        "writing_style_id": str(row["writing_style_id"]) if row["writing_style_id"] else None,
                        "funder_name": row["funder_name"],
                        "requested_amount": float(row["requested_amount"]) if row["requested_amount"] else None,
                        "awarded_amount": float(row["awarded_amount"]) if row["awarded_amount"] else None,
                        "submission_date": row["submission_date"].isoformat() if row["submission_date"] else None,
                        "decision_date": row["decision_date"].isoformat() if row["decision_date"] else None,
                        "success_notes": row["success_notes"],
                        "metadata": row["metadata"],
                        "created_by": row["created_by"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
                    })

                return outputs

        except Exception as e:
            logger.error(f"Failed to search outputs: {e}")
            raise
    # ==========================================
    # Conversation Management Methods
    # ==========================================

    async def create_conversation(
        self,
        conversation_id: UUID,
        name: Optional[str] = None,
        user_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create a new conversation

        Args:
            conversation_id: Unique conversation identifier
            name: Optional conversation name
            user_id: Optional user identifier
            metadata: Optional conversation metadata
            context: Optional conversation context (writing_style, audience, etc.)

        Returns:
            Dictionary with created conversation data

        Raises:
            Exception: If creation fails
        """
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO conversations (
                conversation_id, name, user_id, metadata, context, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7
            )
            RETURNING conversation_id, name, user_id, metadata, context, created_at, updated_at
        """

        try:
            now = datetime.utcnow()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    conversation_id,
                    name,
                    user_id,
                    json.dumps(metadata or {}),
                    json.dumps(context or {}),
                    now,
                    now
                )

                logger.info(f"Created conversation: {conversation_id}")

                return {
                    "conversation_id": str(row["conversation_id"]),
                    "name": row["name"],
                    "user_id": row["user_id"],
                    "metadata": row["metadata"],
                    "context": row["context"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to create conversation {conversation_id}: {e}")
            raise

    async def get_conversation(
        self,
        conversation_id: UUID
    ) -> Optional[Dict[str, Any]]:
        """
        Get conversation by ID with all messages

        Args:
            conversation_id: Conversation identifier

        Returns:
            Conversation data with messages, or None if not found
        """
        if not self.pool:
            await self.connect()

        query = """
            SELECT
                conversation_id, name, user_id, metadata, context,
                created_at, updated_at
            FROM conversations
            WHERE conversation_id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(query, conversation_id)

                if not row:
                    return None

                # Get messages for this conversation
                messages = await self._get_conversation_messages(conn, conversation_id)

                return {
                    "conversation_id": str(row["conversation_id"]),
                    "name": row["name"],
                    "user_id": row["user_id"],
                    "metadata": row["metadata"],
                    "context": row["context"],
                    "created_at": row["created_at"].isoformat(),
                    "updated_at": row["updated_at"].isoformat(),
                    "messages": messages,
                }

        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id}: {e}")
            raise

    async def _get_conversation_messages(
        self,
        conn: asyncpg.Connection,
        conversation_id: UUID
    ) -> List[Dict[str, Any]]:
        """Get all messages for a conversation"""
        rows = await conn.fetch(
            """
            SELECT
                message_id, role, content, sources, metadata, created_at
            FROM messages
            WHERE conversation_id = $1
            ORDER BY created_at ASC
            """,
            conversation_id
        )

        return [
            {
                "message_id": str(row["message_id"]),
                "role": row["role"],
                "content": row["content"],
                "sources": row["sources"],
                "metadata": row["metadata"],
                "created_at": row["created_at"].isoformat(),
            }
            for row in rows
        ]

    async def list_conversations(
        self,
        user_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        List conversations with pagination

        Args:
            user_id: Optional filter by user ID
            skip: Number of records to skip
            limit: Maximum number of records to return

        Returns:
            List of conversation metadata (without full messages)
        """
        if not self.pool:
            await self.connect()

        where_clause = ""
        params = []

        if user_id:
            where_clause = "WHERE user_id = $1"
            params.append(user_id)
            skip_idx = 2
        else:
            skip_idx = 1

        query = f"""
            SELECT
                c.conversation_id, c.name, c.user_id, c.metadata, c.context,
                c.created_at, c.updated_at,
                COUNT(m.message_id) as message_count
            FROM conversations c
            LEFT JOIN messages m ON c.conversation_id = m.conversation_id
            {where_clause}
            GROUP BY c.conversation_id, c.name, c.user_id, c.metadata, c.context, c.created_at, c.updated_at
            ORDER BY c.updated_at DESC
            OFFSET ${skip_idx} LIMIT ${skip_idx + 1}
        """

        params.extend([skip, limit])

        try:
            async with self.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

                conversations = []
                for row in rows:
                    conversations.append({
                        "conversation_id": str(row["conversation_id"]),
                        "name": row["name"],
                        "user_id": row["user_id"],
                        "metadata": row["metadata"],
                        "context": row["context"],
                        "created_at": row["created_at"].isoformat(),
                        "updated_at": row["updated_at"].isoformat(),
                        "message_count": row["message_count"],
                    })

                return conversations

        except Exception as e:
            logger.error(f"Failed to list conversations: {e}")
            raise

    async def update_conversation(
        self,
        conversation_id: UUID,
        name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update conversation fields

        Args:
            conversation_id: Conversation identifier
            name: Optional new name
            context: Optional new context
            metadata: Optional new metadata

        Returns:
            True if updated, False if not found
        """
        if not self.pool:
            await self.connect()

        # Build SET clause dynamically based on provided fields
        set_clauses = []
        params = [conversation_id]
        param_idx = 2

        if name is not None:
            set_clauses.append(f"name = ${param_idx}")
            params.append(name)
            param_idx += 1

        if context is not None:
            set_clauses.append(f"context = ${param_idx}")
            params.append(context)
            param_idx += 1

        if metadata is not None:
            set_clauses.append(f"metadata = ${param_idx}")
            params.append(metadata)
            param_idx += 1

        if not set_clauses:
            # Nothing to update
            return True

        # Always update updated_at
        set_clauses.append(f"updated_at = ${param_idx}")
        params.append(datetime.utcnow())

        query = f"""
            UPDATE conversations
            SET {', '.join(set_clauses)}
            WHERE conversation_id = $1
        """

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, *params)
                updated = result.split()[-1] == "1"

                if updated:
                    logger.info(f"Updated conversation: {conversation_id}")
                else:
                    logger.warning(f"Conversation not found for update: {conversation_id}")

                return updated

        except Exception as e:
            logger.error(f"Failed to update conversation {conversation_id}: {e}")
            raise

    async def delete_conversation(
        self,
        conversation_id: UUID
    ) -> bool:
        """
        Delete conversation and all associated messages

        Args:
            conversation_id: Conversation identifier

        Returns:
            True if deleted, False if not found

        Note:
            Associated messages are deleted automatically via CASCADE constraint
        """
        if not self.pool:
            await self.connect()

        query = "DELETE FROM conversations WHERE conversation_id = $1"

        try:
            async with self.pool.acquire() as conn:
                result = await conn.execute(query, conversation_id)
                deleted = result.split()[-1] == "1"

                if deleted:
                    logger.info(f"Deleted conversation: {conversation_id}")
                else:
                    logger.warning(f"Conversation not found for deletion: {conversation_id}")

                return deleted

        except Exception as e:
            logger.error(f"Failed to delete conversation {conversation_id}: {e}")
            raise

    async def add_message(
        self,
        message_id: UUID,
        conversation_id: UUID,
        role: str,
        content: str,
        sources: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Add a message to a conversation

        Args:
            message_id: Unique message identifier
            conversation_id: Conversation this message belongs to
            role: Message role ('user' or 'assistant')
            content: Message content
            sources: Optional list of sources (for RAG responses)
            metadata: Optional message metadata

        Returns:
            Dictionary with created message data

        Raises:
            Exception: If creation fails
        """
        if not self.pool:
            await self.connect()

        query = """
            INSERT INTO messages (
                message_id, conversation_id, role, content, sources, metadata, created_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7
            )
            RETURNING message_id, conversation_id, role, content, sources, metadata, created_at
        """

        try:
            now = datetime.utcnow()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    message_id,
                    conversation_id,
                    role,
                    content,
                    json.dumps(sources or []),
                    json.dumps(metadata or {}),
                    now
                )

                # Update conversation's updated_at timestamp
                await conn.execute(
                    "UPDATE conversations SET updated_at = $1 WHERE conversation_id = $2",
                    now,
                    conversation_id
                )

                logger.info(f"Added message {message_id} to conversation {conversation_id}")

                return {
                    "message_id": str(row["message_id"]),
                    "conversation_id": str(row["conversation_id"]),
                    "role": row["role"],
                    "content": row["content"],
                    "sources": row["sources"],
                    "metadata": row["metadata"],
                    "created_at": row["created_at"].isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to add message to conversation {conversation_id}: {e}")
            raise


# Singleton instance
_db_service: Optional[DatabaseService] = None


def get_database_service() -> DatabaseService:
    """
    Get or create database service singleton

    Returns:
        DatabaseService instance
    """
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService()
    return _db_service
