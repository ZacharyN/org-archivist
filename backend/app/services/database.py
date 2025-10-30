"""
Database Service for PostgreSQL Operations

This module provides async database operations for the Org Archivist application,
including document metadata storage and retrieval.
"""

import logging
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
                file_size, chunks_count, created_by, upload_date, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
            )
            RETURNING doc_id, filename, doc_type, year, outcome, upload_date, chunks_count
        """

        try:
            now = datetime.utcnow()
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow(
                    query,
                    doc_id, filename, doc_type, year, outcome, notes,
                    file_size, chunks_count, created_by, now, now
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
