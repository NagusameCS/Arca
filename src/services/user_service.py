"""
User Service
Handles user management, linking, and permissions
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from ..config import permissions
from ..models.user import User, UserRole


class UserService:
    """
    Service for managing users and permissions
    """

    def __init__(self, db: Session):
        self.db = db

    # ==================== USER LOOKUP ====================

    def get_by_discord_id(self, discord_id: str) -> Optional[User]:
        """Get user by Discord ID"""
        return self.db.query(User).filter(User.discord_id == discord_id).first()

    def get_by_minecraft_uuid(self, mc_uuid: str) -> Optional[User]:
        """Get user by Minecraft UUID"""
        return self.db.query(User).filter(User.minecraft_uuid == mc_uuid).first()

    def get_by_minecraft_username(self, mc_username: str) -> Optional[User]:
        """Get user by Minecraft username (case-insensitive)"""
        return self.db.query(User).filter(User.minecraft_username.ilike(mc_username)).first()

    def get_by_id(self, user_id: int) -> Optional[User]:
        """Get user by internal ID"""
        return self.db.query(User).filter(User.id == user_id).first()

    # ==================== USER CREATION ====================

    def create_user(
        self,
        discord_id: str,
        discord_username: str,
        minecraft_uuid: Optional[str] = None,
        minecraft_username: Optional[str] = None,
    ) -> User:
        """Create a new user"""
        # Check if user already exists
        existing = self.get_by_discord_id(discord_id)
        if existing:
            raise ValueError(f"User with Discord ID {discord_id} already exists")

        if minecraft_uuid:
            existing_mc = self.get_by_minecraft_uuid(minecraft_uuid)
            if existing_mc:
                raise ValueError(f"Minecraft account already linked to another user")

        user = User(
            discord_id=discord_id,
            discord_username=discord_username,
            minecraft_uuid=minecraft_uuid,
            minecraft_username=minecraft_username,
            role=UserRole.USER,
        )
        self.db.add(user)
        self.db.flush()
        return user

    def get_or_create_user(self, discord_id: str, discord_username: str) -> User:
        """Get existing user or create new one"""
        user = self.get_by_discord_id(discord_id)
        if not user:
            user = self.create_user(discord_id, discord_username)
        return user

    # ==================== MINECRAFT LINKING ====================

    def link_minecraft(self, user: User, minecraft_uuid: str, minecraft_username: str) -> User:
        """Link a Minecraft account to a user"""
        # Check if MC account is already linked
        existing = self.get_by_minecraft_uuid(minecraft_uuid)
        if existing and existing.id != user.id:
            raise ValueError("Minecraft account already linked to another Discord user")

        user.minecraft_uuid = minecraft_uuid
        user.minecraft_username = minecraft_username
        user.updated_at = datetime.utcnow()
        return user

    def unlink_minecraft(self, user: User) -> User:
        """Unlink Minecraft account from user"""
        user.minecraft_uuid = None
        user.minecraft_username = None
        user.updated_at = datetime.utcnow()
        return user

    def update_minecraft_username(self, user: User, new_username: str) -> User:
        """Update Minecraft username (for name changes)"""
        user.minecraft_username = new_username
        user.updated_at = datetime.utcnow()
        return user

    # ==================== ROLE MANAGEMENT ====================

    def set_role(self, user: User, role: UserRole, admin: User) -> User:
        """
        Set user's role (requires admin permissions)
        """
        if not admin.can_mint():
            raise PermissionError("Only Head Banker can change roles")

        # Cannot demote head banker
        if user.role == UserRole.HEAD_BANKER and role != UserRole.HEAD_BANKER:
            raise PermissionError("Cannot demote Head Banker through this method")

        user.role = role
        user.updated_at = datetime.utcnow()
        return user

    def promote_to_banker(self, user: User, admin: User) -> User:
        """Promote user to banker"""
        return self.set_role(user, UserRole.BANKER, admin)

    def demote_to_user(self, user: User, admin: User) -> User:
        """Demote banker to regular user"""
        if user.role == UserRole.HEAD_BANKER:
            raise PermissionError("Cannot demote Head Banker")
        return self.set_role(user, UserRole.USER, admin)

    def resign_as_banker(self, user: User) -> User:
        """
        Allow a banker to voluntarily resign their position.
        Head Bankers cannot resign through this method.
        """
        if user.role == UserRole.HEAD_BANKER:
            raise PermissionError("Head Banker cannot resign through this method")
        if user.role != UserRole.BANKER:
            raise PermissionError("Only bankers can resign")

        user.role = UserRole.USER
        user.updated_at = datetime.utcnow()
        return user

    def set_active(self, user: User, is_active: bool) -> User:
        """Activate or deactivate a user"""
        user.is_active = is_active
        user.updated_at = datetime.utcnow()
        return user

    # ==================== USER QUERIES ====================

    def get_all_bankers(self) -> List[User]:
        """Get all users with banker role or higher"""
        return (
            self.db.query(User)
            .filter(User.role.in_([UserRole.BANKER, UserRole.HEAD_BANKER]), User.is_active == True)
            .all()
        )

    def get_head_banker(self) -> Optional[User]:
        """Get the head banker"""
        return (
            self.db.query(User)
            .filter(User.role == UserRole.HEAD_BANKER, User.is_active == True)
            .first()
        )

    def get_all_active_users(self) -> List[User]:
        """Get all active users"""
        return self.db.query(User).filter(User.is_active == True).all()

    def get_linked_users(self) -> List[User]:
        """Get all users with linked Minecraft accounts"""
        return (
            self.db.query(User)
            .filter(User.minecraft_uuid.isnot(None), User.is_active == True)
            .all()
        )

    def search_users(self, query: str) -> List[User]:
        """Search users by Discord or Minecraft username"""
        search_pattern = f"%{query}%"
        return (
            self.db.query(User)
            .filter(
                (User.discord_username.ilike(search_pattern))
                | (User.minecraft_username.ilike(search_pattern))
            )
            .limit(25)
            .all()
        )

    # ==================== PERMISSION CHECKS ====================

    def require_banker(self, user: User) -> None:
        """Raise error if user is not a banker"""
        if not user.can_write():
            raise PermissionError("This action requires Banker permissions")

    def require_head_banker(self, user: User) -> None:
        """Raise error if user is not head banker"""
        if not user.can_mint():
            raise PermissionError("This action requires Head Banker permissions")

    def update_activity(self, user: User) -> None:
        """Update user's last activity timestamp"""
        user.last_activity = datetime.utcnow()
