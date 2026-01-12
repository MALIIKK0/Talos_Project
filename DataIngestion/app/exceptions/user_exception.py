from fastapi import status
from DataIngestion.app.exceptions.base_exception import AppException


class UserException(AppException):
    pass


class UserNotFoundException(UserException):
    def __init__(self, detail: str = "User not found"):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
        )


class UserAlreadyExistsException(UserException):
    def __init__(self, detail: str = "User already exists"):
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class UserCreationException(UserException):
    def __init__(self, detail: str = "Failed to create user"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class UserUpdateException(UserException):
    def __init__(self, detail: str = "Failed to update user"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class UserDeleteException(UserException):
    def __init__(self, detail: str = "Failed to delete user"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
