from fastapi import status
from DataIngestion.app.exceptions.base_exception import AppException


class RefreshTokenException(AppException):
    pass


class InvalidRefreshTokenException(RefreshTokenException):
    def __init__(self, detail: str = "Invalid refresh token"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class RevokedRefreshTokenException(RefreshTokenException):
    def __init__(self, detail: str = "Refresh token revoked"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class ExpiredRefreshTokenException(RefreshTokenException):
    def __init__(self, detail: str = "Refresh token expired"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )


class RefreshTokenCreationException(RefreshTokenException):
    def __init__(self, detail: str = "Failed to create refresh token"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
