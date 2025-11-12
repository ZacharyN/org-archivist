"""
Session Management Service for Org Archivist

Provides session lifecycle management including:
- Session creation with JWT tokens
- Session validation and user retrieval
- Token refresh with rotation
- Session expiration and cleanup
- Automatic cleanup of expired sessions
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from uuid import UUID
import logging

from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete

from app.db.models import User, UserSession
from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.session_timeout_minutes
REFRESH_TOKEN_EXPIRE_DAYS = 7  # Refresh tokens last 7 days


class SessionService:
    """
    Service for managing user sessions and JWT tokens
    Handles session lifecycle from creation to cleanup
    """

    @staticmethod
    def _create_access_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token

        Args:
            data: Dictionary of claims to encode in the token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)

        return encoded_jwt

    @staticmethod
    def _create_refresh_token(
        data: Dict[str, Any],
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT refresh token (longer expiration)

        Args:
            data: Dictionary of claims to encode in the token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT refresh token string
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)

        return encoded_jwt

    @staticmethod
    def _decode_token(token: str) -> Optional[Dict[str, Any]]:
        """
        Decode and validate a JWT token

        Args:
            token: JWT token string

        Returns:
            Decoded token payload or None if invalid
        """
        try:
            payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
            return payload
        except JWTError as e:
            logger.debug(f"Token decode error: {e}")
            return None

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        expires_minutes: Optional[int] = None
    ) -> UserSession:
        """
        Create a new user session with access and refresh tokens

        Args:
            db: Database session
            user_id: User's UUID
            ip_address: Client IP address (optional)
            user_agent: Client user agent string (optional)
            expires_minutes: Custom expiration time in minutes (optional)

        Returns:
            Created UserSession object with tokens

        Raises:
            ValueError: If user_id is invalid
        """
        # Verify user exists
        stmt = select(User).where(User.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ValueError(f"User not found: {user_id}")

        if not user.is_active:
            raise ValueError(f"User is inactive: {user_id}")

        # Create access token
        access_token = SessionService._create_access_token(
            data={"sub": str(user_id)},
            expires_delta=timedelta(minutes=expires_minutes) if expires_minutes else None
        )

        # Create refresh token
        refresh_token = SessionService._create_refresh_token(
            data={"sub": str(user_id)}
        )

        # Calculate expiration time
        expiration_minutes = expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
        expires_at = datetime.utcnow() + timedelta(minutes=expiration_minutes)

        # Create session record
        session = UserSession(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
            expires_at=expires_at,
            ip_address=ip_address,
            user_agent=user_agent
        )

        db.add(session)
        await db.commit()
        await db.refresh(session)

        logger.info(f"Created session for user {user_id}: {session.session_id}")
        return session

    @staticmethod
    async def validate_session(
        db: AsyncSession,
        access_token: str,
        refresh_activity: bool = True
    ) -> Optional[User]:
        """
        Validate a session by access token and return the user
        Optionally refreshes session activity to extend expiration

        Args:
            db: Database session
            access_token: JWT access token
            refresh_activity: If True, extend session expiration on successful validation

        Returns:
            User object if session is valid, None otherwise
        """
        # Decode token
        payload = SessionService._decode_token(access_token)
        if not payload:
            logger.debug("Invalid token payload")
            return None

        # Check token type
        if payload.get("type") != "access":
            logger.debug(f"Invalid token type: {payload.get('type')}")
            return None

        # Extract user ID from token
        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.debug("Missing user ID in token")
            return None

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.debug(f"Invalid user ID format: {user_id_str}")
            return None

        # Query session from database
        stmt = select(UserSession).where(UserSession.access_token == access_token)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            logger.debug(f"Session not found for token")
            return None

        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            logger.info(f"Session expired for user {user_id}")
            # Delete expired session
            await db.delete(session)
            await db.commit()
            return None

        # Refresh session activity if requested
        if refresh_activity:
            # Extend expiration by the configured timeout
            session.expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            await db.commit()
            logger.debug(f"Refreshed session activity for user {user_id}")

        # Get user
        stmt = select(User).where(User.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            logger.warning(f"User not found or inactive: {user_id}")
            return None

        return user

    @staticmethod
    async def refresh_session(
        db: AsyncSession,
        refresh_token: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[UserSession]:
        """
        Refresh a session using a refresh token
        Implements token rotation - old session is deleted, new one created

        Args:
            db: Database session
            refresh_token: JWT refresh token
            ip_address: New IP address (optional, uses old if not provided)
            user_agent: New user agent (optional, uses old if not provided)

        Returns:
            New UserSession object if refresh successful, None otherwise
        """
        # Decode refresh token
        payload = SessionService._decode_token(refresh_token)
        if not payload:
            logger.debug("Invalid refresh token payload")
            return None

        # Check token type
        if payload.get("type") != "refresh":
            logger.debug(f"Invalid token type for refresh: {payload.get('type')}")
            return None

        # Extract user ID
        user_id_str = payload.get("sub")
        if not user_id_str:
            logger.debug("Missing user ID in refresh token")
            return None

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            logger.debug(f"Invalid user ID format in refresh token: {user_id_str}")
            return None

        # Query old session
        stmt = select(UserSession).where(UserSession.refresh_token == refresh_token)
        result = await db.execute(stmt)
        old_session = result.scalar_one_or_none()

        if not old_session:
            logger.warning(f"Refresh token not found in database")
            return None

        # Use provided IP/user agent or fall back to old session values
        new_ip = ip_address or old_session.ip_address
        new_user_agent = user_agent or old_session.user_agent

        # Delete old session (token rotation)
        await db.delete(old_session)
        await db.commit()

        # Create new session
        try:
            new_session = await SessionService.create_session(
                db=db,
                user_id=user_id,
                ip_address=new_ip,
                user_agent=new_user_agent
            )
            logger.info(f"Refreshed session for user {user_id}")
            return new_session
        except ValueError as e:
            logger.error(f"Failed to create new session during refresh: {e}")
            return None

    @staticmethod
    async def expire_session(
        db: AsyncSession,
        access_token: Optional[str] = None,
        session_id: Optional[UUID] = None
    ) -> bool:
        """
        Expire/logout a session by deleting it from the database
        Can identify session by access token or session ID

        Args:
            db: Database session
            access_token: JWT access token (optional)
            session_id: Session UUID (optional)

        Returns:
            True if session was found and deleted, False otherwise

        Raises:
            ValueError: If neither access_token nor session_id provided
        """
        if not access_token and not session_id:
            raise ValueError("Must provide either access_token or session_id")

        # Build query based on provided identifier
        if access_token:
            stmt = select(UserSession).where(UserSession.access_token == access_token)
        else:
            stmt = select(UserSession).where(UserSession.session_id == session_id)

        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            logger.debug("Session not found for expiration")
            return False

        # Delete session
        user_id = session.user_id
        await db.delete(session)
        await db.commit()

        logger.info(f"Expired session for user {user_id}")
        return True

    @staticmethod
    async def cleanup_expired(
        db: AsyncSession,
        batch_size: int = 100
    ) -> int:
        """
        Clean up all expired sessions from the database
        Should be run periodically (e.g., via scheduled task)

        Args:
            db: Database session
            batch_size: Maximum number of sessions to delete in one operation

        Returns:
            Number of expired sessions deleted
        """
        # Find expired sessions
        stmt = select(UserSession).where(
            UserSession.expires_at < datetime.utcnow()
        ).limit(batch_size)

        result = await db.execute(stmt)
        expired_sessions = result.scalars().all()

        if not expired_sessions:
            logger.debug("No expired sessions to clean up")
            return 0

        # Delete expired sessions
        count = len(expired_sessions)
        for session in expired_sessions:
            await db.delete(session)

        await db.commit()
        logger.info(f"Cleaned up {count} expired sessions")

        return count

    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: UUID,
        include_expired: bool = False
    ) -> List[UserSession]:
        """
        Get all sessions for a specific user

        Args:
            db: Database session
            user_id: User's UUID
            include_expired: If True, include expired sessions

        Returns:
            List of UserSession objects
        """
        stmt = select(UserSession).where(UserSession.user_id == user_id)

        if not include_expired:
            stmt = stmt.where(UserSession.expires_at >= datetime.utcnow())

        result = await db.execute(stmt)
        sessions = result.scalars().all()

        return list(sessions)

    @staticmethod
    async def expire_all_user_sessions(
        db: AsyncSession,
        user_id: UUID
    ) -> int:
        """
        Expire all sessions for a specific user (useful for forced logout)

        Args:
            db: Database session
            user_id: User's UUID

        Returns:
            Number of sessions expired
        """
        stmt = delete(UserSession).where(UserSession.user_id == user_id)
        result = await db.execute(stmt)
        await db.commit()

        count = result.rowcount
        logger.info(f"Expired {count} sessions for user {user_id}")
        return count
