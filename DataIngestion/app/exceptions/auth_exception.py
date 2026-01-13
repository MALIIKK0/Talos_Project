from fastapi import status
from DataIngestion.app.exceptions.base_exception import AppException


class AuthException(AppException):
    """Base class for authentication / authorization errors"""
    pass


class InvalidCredentialsException(AuthException):
    def __init__(self, detail: str = "Incorrect email or password"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class InvalidTokenException(AuthException):
    def __init__(self, detail: str = "Invalid token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class TokenExpiredException(AuthException):
    def __init__(self, detail: str = "Token expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class InactiveUserException(AuthException):
    def __init__(self, detail: str = "User account is inactive"):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class UserFromTokenNotFoundException(AuthException):
    def __init__(self, detail: str = "User not found from token"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )
