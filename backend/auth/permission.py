from fastapi import Depends, HTTPException, status

from backend.auth.services.auth_service import get_current_user
from backend.core.security.roles import UserRole
from backend.user.models.user import User


def require_roles(*allowed_roles: UserRole):
    def role_checker(current_user: User = Depends(get_current_user)):
        if current_user.role not in [role.value for role in allowed_roles]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return role_checker
