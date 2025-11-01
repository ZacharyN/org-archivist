"""
Success Tracking Service

This module provides business logic for tracking grant output success,
including status transitions, outcome recording, and analytics.
"""

import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, date
from uuid import UUID
from decimal import Decimal

from ..models.output import OutputStatus

logger = logging.getLogger(__name__)


# Status transition rules - defines valid state transitions
VALID_STATUS_TRANSITIONS: Dict[str, List[str]] = {
    "draft": ["submitted"],
    "submitted": ["pending", "draft"],  # Can revert to draft
    "pending": ["awarded", "not_awarded", "submitted"],  # Can go back to submitted
    "awarded": [],  # Terminal state
    "not_awarded": [],  # Terminal state
}


class StatusTransitionError(ValueError):
    """Raised when an invalid status transition is attempted"""
    pass


class SuccessTrackingService:
    """
    Service for managing output success tracking

    Provides:
    - Status transition validation
    - Grant outcome recording helpers
    - Success analytics by various dimensions
    """

    def __init__(self, database_service):
        """
        Initialize success tracking service

        Args:
            database_service: DatabaseService instance for data access
        """
        self.db = database_service

    @staticmethod
    def validate_status_transition(
        current_status: str,
        new_status: str,
        allow_override: bool = False
    ) -> bool:
        """
        Validate if a status transition is allowed

        Args:
            current_status: Current output status
            new_status: Proposed new status
            allow_override: If True, skip validation (for admin overrides)

        Returns:
            True if transition is valid

        Raises:
            StatusTransitionError: If transition is invalid

        Examples:
            >>> validate_status_transition("draft", "submitted")
            True
            >>> validate_status_transition("draft", "awarded")
            StatusTransitionError: Invalid status transition
        """
        if allow_override:
            logger.warning(
                f"Status transition override: {current_status} -> {new_status}"
            )
            return True

        # Same status is always valid (no-op)
        if current_status == new_status:
            return True

        # Check if transition is allowed
        allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, [])

        if new_status not in allowed_transitions:
            raise StatusTransitionError(
                f"Invalid status transition from '{current_status}' to '{new_status}'. "
                f"Allowed transitions: {allowed_transitions or 'none (terminal state)'}"
            )

        return True

    @staticmethod
    def validate_outcome_data(
        status: str,
        funder_name: Optional[str] = None,
        requested_amount: Optional[Decimal] = None,
        awarded_amount: Optional[Decimal] = None,
        submission_date: Optional[date] = None,
        decision_date: Optional[date] = None,
    ) -> Dict[str, str]:
        """
        Validate grant outcome data for consistency

        Args:
            status: Output status
            funder_name: Name of funder
            requested_amount: Requested amount
            awarded_amount: Awarded amount
            submission_date: Submission date
            decision_date: Decision date

        Returns:
            Dictionary of validation warnings (empty if all valid)

        Note:
            This provides warnings but doesn't raise errors, allowing
            for flexible data entry while flagging potential issues.
        """
        warnings = {}

        # Submitted/pending/awarded should have submission data
        if status in ["submitted", "pending", "awarded", "not_awarded"]:
            if not funder_name:
                warnings["funder_name"] = "Funder name recommended for submitted grants"
            if not requested_amount:
                warnings["requested_amount"] = "Requested amount recommended for submitted grants"
            if not submission_date:
                warnings["submission_date"] = "Submission date recommended for submitted grants"

        # Awarded/not_awarded should have decision data
        if status in ["awarded", "not_awarded"]:
            if not decision_date:
                warnings["decision_date"] = "Decision date recommended for decided grants"

        # Awarded should have awarded amount
        if status == "awarded":
            if not awarded_amount:
                warnings["awarded_amount"] = "Awarded amount recommended for awarded grants"
            elif awarded_amount and requested_amount and awarded_amount > requested_amount:
                warnings["awarded_amount"] = "Awarded amount exceeds requested amount"

        # Not awarded should not have awarded amount
        if status == "not_awarded" and awarded_amount and awarded_amount > 0:
            warnings["awarded_amount"] = "Awarded amount should be 0 or null for non-awarded grants"

        # Date consistency
        if submission_date and decision_date and decision_date < submission_date:
            warnings["decision_date"] = "Decision date is before submission date"

        return warnings

    async def calculate_success_rate_by_style(
        self,
        style_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate success rate for outputs using a specific writing style

        Args:
            style_id: Writing style UUID
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with:
            - style_id: Writing style ID
            - total_outputs: Total outputs with this style
            - submitted_count: Number submitted
            - awarded_count: Number awarded
            - not_awarded_count: Number not awarded
            - success_rate: Percentage awarded (awarded / submitted * 100)
            - total_requested: Total amount requested
            - total_awarded: Total amount awarded
            - avg_award_rate: Average award rate (awarded / requested * 100)
        """
        query = """
            SELECT
                COUNT(*) as total_outputs,
                COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) as submitted_count,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                COUNT(*) FILTER (WHERE status = 'not_awarded') as not_awarded_count,
                COALESCE(SUM(requested_amount), 0) as total_requested,
                COALESCE(SUM(awarded_amount), 0) as total_awarded
            FROM outputs
            WHERE writing_style_id = $1
        """

        params = [style_id]
        param_idx = 2

        if start_date:
            query += f" AND created_at >= ${param_idx}"
            params.append(start_date)
            param_idx += 1

        if end_date:
            query += f" AND created_at <= ${param_idx}"
            params.append(end_date)

        try:
            async with self.db.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)

                submitted = row["submitted_count"]
                awarded = row["awarded_count"]
                total_requested = float(row["total_requested"])
                total_awarded = float(row["total_awarded"])

                success_rate = (awarded / submitted * 100) if submitted > 0 else 0.0
                avg_award_rate = (total_awarded / total_requested * 100) if total_requested > 0 else 0.0

                return {
                    "style_id": str(style_id),
                    "total_outputs": row["total_outputs"],
                    "submitted_count": submitted,
                    "awarded_count": awarded,
                    "not_awarded_count": row["not_awarded_count"],
                    "success_rate": round(success_rate, 2),
                    "total_requested": total_requested,
                    "total_awarded": total_awarded,
                    "avg_award_rate": round(avg_award_rate, 2),
                }

        except Exception as e:
            logger.error(f"Failed to calculate success rate by style {style_id}: {e}")
            raise

    async def calculate_success_rate_by_funder(
        self,
        funder_name: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Calculate success rate for a specific funder

        Args:
            funder_name: Name of funder (partial match)
            start_date: Optional start date filter
            end_date: Optional end date filter

        Returns:
            Dictionary with success metrics for the funder
        """
        query = """
            SELECT
                COUNT(*) as total_outputs,
                COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) as submitted_count,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                COUNT(*) FILTER (WHERE status = 'not_awarded') as not_awarded_count,
                COALESCE(SUM(requested_amount), 0) as total_requested,
                COALESCE(SUM(awarded_amount), 0) as total_awarded
            FROM outputs
            WHERE funder_name ILIKE $1
        """

        params = [f"%{funder_name}%"]
        param_idx = 2

        if start_date:
            query += f" AND created_at >= ${param_idx}"
            params.append(start_date)
            param_idx += 1

        if end_date:
            query += f" AND created_at <= ${param_idx}"
            params.append(end_date)

        try:
            async with self.db.pool.acquire() as conn:
                row = await conn.fetchrow(query, *params)

                submitted = row["submitted_count"]
                awarded = row["awarded_count"]
                total_requested = float(row["total_requested"])
                total_awarded = float(row["total_awarded"])

                success_rate = (awarded / submitted * 100) if submitted > 0 else 0.0
                avg_award_rate = (total_awarded / total_requested * 100) if total_requested > 0 else 0.0

                return {
                    "funder_name": funder_name,
                    "total_outputs": row["total_outputs"],
                    "submitted_count": submitted,
                    "awarded_count": awarded,
                    "not_awarded_count": row["not_awarded_count"],
                    "success_rate": round(success_rate, 2),
                    "total_requested": total_requested,
                    "total_awarded": total_awarded,
                    "avg_award_rate": round(avg_award_rate, 2),
                }

        except Exception as e:
            logger.error(f"Failed to calculate success rate by funder {funder_name}: {e}")
            raise

    async def calculate_success_rate_by_year(
        self,
        year: int,
    ) -> Dict[str, Any]:
        """
        Calculate success rate for outputs in a specific year

        Args:
            year: Year to analyze (based on submission_date)

        Returns:
            Dictionary with success metrics for the year
        """
        query = """
            SELECT
                COUNT(*) as total_outputs,
                COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) as submitted_count,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                COUNT(*) FILTER (WHERE status = 'not_awarded') as not_awarded_count,
                COALESCE(SUM(requested_amount), 0) as total_requested,
                COALESCE(SUM(awarded_amount), 0) as total_awarded
            FROM outputs
            WHERE EXTRACT(YEAR FROM submission_date) = $1
        """

        try:
            async with self.db.pool.acquire() as conn:
                row = await conn.fetchrow(query, year)

                submitted = row["submitted_count"]
                awarded = row["awarded_count"]
                total_requested = float(row["total_requested"])
                total_awarded = float(row["total_awarded"])

                success_rate = (awarded / submitted * 100) if submitted > 0 else 0.0
                avg_award_rate = (total_awarded / total_requested * 100) if total_requested > 0 else 0.0

                return {
                    "year": year,
                    "total_outputs": row["total_outputs"],
                    "submitted_count": submitted,
                    "awarded_count": awarded,
                    "not_awarded_count": row["not_awarded_count"],
                    "success_rate": round(success_rate, 2),
                    "total_requested": total_requested,
                    "total_awarded": total_awarded,
                    "avg_award_rate": round(avg_award_rate, 2),
                }

        except Exception as e:
            logger.error(f"Failed to calculate success rate by year {year}: {e}")
            raise

    async def get_success_metrics_summary(
        self,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Get comprehensive success metrics summary

        Args:
            created_by: Optional filter by creator

        Returns:
            Dictionary with comprehensive metrics including:
            - Overall statistics
            - Top performing writing styles
            - Top funders
            - Year-over-year trends
        """
        # Get overall stats from database service
        stats = await self.db.get_outputs_stats(created_by=created_by)

        # Get top writing styles by success rate
        top_styles_query = """
            SELECT
                writing_style_id,
                COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) as submitted_count,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                ROUND(
                    CAST(COUNT(*) FILTER (WHERE status = 'awarded') AS DECIMAL) /
                    NULLIF(COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')), 0) * 100,
                    2
                ) as success_rate
            FROM outputs
            WHERE writing_style_id IS NOT NULL
        """

        params = []
        if created_by:
            top_styles_query += " AND created_by = $1"
            params.append(created_by)

        top_styles_query += """
            GROUP BY writing_style_id
            HAVING COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) > 0
            ORDER BY success_rate DESC
            LIMIT 5
        """

        # Get top funders by success rate
        top_funders_query = """
            SELECT
                funder_name,
                COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) as submitted_count,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                ROUND(
                    CAST(COUNT(*) FILTER (WHERE status = 'awarded') AS DECIMAL) /
                    NULLIF(COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')), 0) * 100,
                    2
                ) as success_rate,
                COALESCE(SUM(awarded_amount), 0) as total_awarded
            FROM outputs
            WHERE funder_name IS NOT NULL
        """

        if created_by:
            top_funders_query += " AND created_by = $1"

        top_funders_query += """
            GROUP BY funder_name
            HAVING COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) > 0
            ORDER BY success_rate DESC, total_awarded DESC
            LIMIT 5
        """

        # Get year-over-year trends
        trends_query = """
            SELECT
                EXTRACT(YEAR FROM submission_date) as year,
                COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')) as submitted_count,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                ROUND(
                    CAST(COUNT(*) FILTER (WHERE status = 'awarded') AS DECIMAL) /
                    NULLIF(COUNT(*) FILTER (WHERE status IN ('submitted', 'pending', 'awarded', 'not_awarded')), 0) * 100,
                    2
                ) as success_rate,
                COALESCE(SUM(awarded_amount), 0) as total_awarded
            FROM outputs
            WHERE submission_date IS NOT NULL
        """

        if created_by:
            trends_query += " AND created_by = $1"

        trends_query += """
            GROUP BY EXTRACT(YEAR FROM submission_date)
            ORDER BY year DESC
            LIMIT 5
        """

        try:
            async with self.db.pool.acquire() as conn:
                # Execute all queries
                top_styles_rows = await conn.fetch(top_styles_query, *params)
                top_funders_rows = await conn.fetch(top_funders_query, *params)
                trends_rows = await conn.fetch(trends_query, *params)

                top_styles = [
                    {
                        "writing_style_id": str(row["writing_style_id"]) if row["writing_style_id"] else None,
                        "submitted_count": row["submitted_count"],
                        "awarded_count": row["awarded_count"],
                        "success_rate": float(row["success_rate"]) if row["success_rate"] else 0.0,
                    }
                    for row in top_styles_rows
                ]

                top_funders = [
                    {
                        "funder_name": row["funder_name"],
                        "submitted_count": row["submitted_count"],
                        "awarded_count": row["awarded_count"],
                        "success_rate": float(row["success_rate"]) if row["success_rate"] else 0.0,
                        "total_awarded": float(row["total_awarded"]),
                    }
                    for row in top_funders_rows
                ]

                year_trends = [
                    {
                        "year": int(row["year"]) if row["year"] else None,
                        "submitted_count": row["submitted_count"],
                        "awarded_count": row["awarded_count"],
                        "success_rate": float(row["success_rate"]) if row["success_rate"] else 0.0,
                        "total_awarded": float(row["total_awarded"]),
                    }
                    for row in trends_rows
                ]

                return {
                    "overall": stats,
                    "top_writing_styles": top_styles,
                    "top_funders": top_funders,
                    "year_over_year_trends": year_trends,
                }

        except Exception as e:
            logger.error(f"Failed to get success metrics summary: {e}")
            raise

    async def get_funder_performance(
        self,
        limit: int = 10,
        created_by: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get performance metrics for all funders, ordered by success rate

        Args:
            limit: Maximum number of funders to return
            created_by: Optional filter by creator

        Returns:
            List of funder performance dictionaries
        """
        query = """
            SELECT
                funder_name,
                COUNT(*) as total_submissions,
                COUNT(*) FILTER (WHERE status = 'awarded') as awarded_count,
                COUNT(*) FILTER (WHERE status = 'not_awarded') as not_awarded_count,
                COUNT(*) FILTER (WHERE status = 'pending') as pending_count,
                ROUND(
                    CAST(COUNT(*) FILTER (WHERE status = 'awarded') AS DECIMAL) /
                    NULLIF(COUNT(*), 0) * 100,
                    2
                ) as success_rate,
                COALESCE(SUM(requested_amount), 0) as total_requested,
                COALESCE(SUM(awarded_amount), 0) as total_awarded,
                ROUND(
                    COALESCE(AVG(awarded_amount), 0),
                    2
                ) as avg_award_amount
            FROM outputs
            WHERE funder_name IS NOT NULL
              AND status IN ('submitted', 'pending', 'awarded', 'not_awarded')
        """

        params = []
        if created_by:
            query += " AND created_by = $1"
            params.append(created_by)

        query += f"""
            GROUP BY funder_name
            ORDER BY success_rate DESC, total_awarded DESC
            LIMIT ${len(params) + 1}
        """
        params.append(limit)

        try:
            async with self.db.pool.acquire() as conn:
                rows = await conn.fetch(query, *params)

                return [
                    {
                        "funder_name": row["funder_name"],
                        "total_submissions": row["total_submissions"],
                        "awarded_count": row["awarded_count"],
                        "not_awarded_count": row["not_awarded_count"],
                        "pending_count": row["pending_count"],
                        "success_rate": float(row["success_rate"]) if row["success_rate"] else 0.0,
                        "total_requested": float(row["total_requested"]),
                        "total_awarded": float(row["total_awarded"]),
                        "avg_award_amount": float(row["avg_award_amount"]),
                    }
                    for row in rows
                ]

        except Exception as e:
            logger.error(f"Failed to get funder performance: {e}")
            raise
