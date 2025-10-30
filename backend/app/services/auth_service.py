"""
Authentication Service for Org Archivist

Provides secure authentication functionality including:
- Password hashing with bcrypt
- JWT token generation and validation
- Session management
- Login/logout logic
- Support for three user roles: administrator, editor, writer
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.app.db.models import User, UserSession, UserRole
from backend.app.config import get_settings

settings = get_settings()

# Password hashing configuration with bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT configuration
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = settings.session_timeout_minutes


class AuthService:
    """
    Authentication service for secure user authentication and session management
    """

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt with automatic salt generation

        Args:
            password: Plain text password

        Returns:
            Hashed password with salt
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash

        Args:
            plain_password: Plain text password to verify
            hashed_password: Hashed password to check against

        Returns:
            True if password matches, False otherwise
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
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

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)

        return encoded_jwt

    @staticmethod
    def create_refresh_token(
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
            # Refresh tokens last 7 days by default
            expire = datetime.utcnow() + timedelta(days=7)

        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)

        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
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
        except JWTError:
            return None

    @staticmethod
    async def authenticate_user(
        db: AsyncSession,
        email: str,
        password: str
    ) -> Optional[User]:
        """
        Authenticate a user by email and password

        Args:
            db: Database session
            email: User's email address
            password: User's plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        # Query user by email
        stmt = select(User).where(User.email == email)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return None

        # Check if user is active
        if not user.is_active:
            return None

        # Verify password
        if not AuthService.verify_password(password, user.hashed_password):
            return None

        return user

    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: UUID,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> UserSession:
        """
        Create a new user session with access and refresh tokens

        Args:
            db: Database session
            user_id: User's UUID
            ip_address: Client IP address (optional)
            user_agent: Client user agent string (optional)

        Returns:
            Created UserSession object
        """
        # Create access token
        access_token = AuthService.create_access_token(
            data={"sub": str(user_id)}
        )

        # Create refresh token
        refresh_token = AuthService.create_refresh_token(
            data={"sub": str(user_id)}
        )

        # Calculate expiration time
        expires_at = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

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

        return session

    @staticmethod
    async def validate_session(
        db: AsyncSession,
        access_token: str
    ) -> Optional[User]:
        """
        Validate a session by access token and return the user

        Args:
            db: Database session
            access_token: JWT access token

        Returns:
            User object if session is valid, None otherwise
        """
        # Decode token
        payload = AuthService.decode_token(access_token)
        if not payload:
            return None

        # Extract user ID from token
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            return None

        # Query session from database
        stmt = select(UserSession).where(UserSession.access_token == access_token)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return None

        # Check if session is expired
        if session.expires_at < datetime.utcnow():
            # Delete expired session
            await db.delete(session)
            await db.commit()
            return None

        # Get user
        stmt = select(User).where(User.user_id == user_id)
        result = await db.execute(stmt)
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            return None

        return user

    @staticmethod
    async def refresh_session(
        db: AsyncSession,
        refresh_token: str
    ) -> Optional[UserSession]:
        """
        Refresh a session using a refresh token

        Args:
            db: Database session
            refresh_token: JWT refresh token

        Returns:
            New UserSession object if refresh successful, None otherwise
        """
        # Decode refresh token
        payload = AuthService.decode_token(refresh_token)
        if not payload:
            return None

        # Check token type
        if payload.get("type") != "refresh":
            return None

        # Extract user ID
        user_id_str = payload.get("sub")
        if not user_id_str:
            return None

        try:
            user_id = UUID(user_id_str)
        except ValueError:
            return None

        # Query old session
        stmt = select(UserSession).where(UserSession.refresh_token == refresh_token)
        result = await db.execute(stmt)
        old_session = result.scalar_one_or_none()

        if not old_session:
            return None

        # Delete old session
        await db.delete(old_session)
        await db.commit()

        # Create new session
        new_session = await AuthService.create_session(
            db=db,
            user_id=user_id,
            ip_address=old_session.ip_address,
            user_agent=old_session.user_agent
        )

        return new_session

    @staticmethod
    async def logout(
        db: AsyncSession,
        access_token: str
    ) -> bool:
        """
        Logout a user by deleting their session

        Args:
            db: Database session
            access_token: JWT access token

        Returns:
            True if logout successful, False otherwise
        """
        # Query session
        stmt = select(UserSession).where(UserSession.access_token == access_token)
        result = await db.execute(stmt)
        session = result.scalar_one_or_none()

        if not session:
            return False

        # Delete session
        await db.delete(session)
        await db.commit()

        return True

    @staticmethod
    async def login(
        db: AsyncSession,
        email: str,
        password: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Complete login flow: authenticate user and create session

        Args:
            db: Database session
            email: User's email address
            password: User's plain text password
            ip_address: Client IP address (optional)
            user_agent: Client user agent string (optional)

        Returns:
            Dictionary with user info, access_token, and refresh_token if successful,
            None if authentication failed
        """
        # Authenticate user
        user = await AuthService.authenticate_user(db, email, password)
        if not user:
            return None

        # Create session
        session = await AuthService.create_session(
            db=db,
            user_id=user.user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )

        # Return user info and tokens
        return {
            "user_id": str(user.user_id),
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role.value,  # Convert enum to string
            "access_token": session.access_token,
            "refresh_token": session.refresh_token,
            "expires_at": session.expires_at.isoformat(),
            "token_type": "bearer"
        }

    @staticmethod
    async def get_current_user(
        db: AsyncSession,
        token: str
    ) -> Optional[User]:
        """
        Get the current authenticated user from a token

        Args:
            db: Database session
            token: JWT access token

        Returns:
            User object if valid, None otherwise
        """
        return await AuthService.validate_session(db, token)

    @staticmethod
    def has_role(user: User, required_role: UserRole) -> bool:
        """
        Check if a user has a specific role or higher privileges

        Role hierarchy: ADMIN > EDITOR > WRITER

        Args:
            user: User object
            required_role: Required role to check

        Returns:
            True if user has required role or higher
        """
        role_hierarchy = {
            UserRole.WRITER: 1,
            UserRole.EDITOR: 2,
            UserRole.ADMIN: 3
        }

        user_level = role_hierarchy.get(user.role, 0)
        required_level = role_hierarchy.get(required_role, 0)

        return user_level >= required_level

    @staticmethod
    def is_admin(user: User) -> bool:
        """
        Check if user is an administrator

        Args:
            user: User object

        Returns:
            True if user is admin or superuser
        """
        return user.role == UserRole.ADMIN or user.is_superuser
