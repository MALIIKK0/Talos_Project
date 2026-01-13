from fastapi import status
from DataIngestion.app.exceptions.base_exception import AppException


class ErrorEventException(AppException):
    pass


class ErrorEventNotFoundException(ErrorEventException):
    def __init__(self, error_id: int):
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Error event with id {error_id} not found",
        )


class ErrorEventDatabaseException(ErrorEventException):
    def __init__(self, detail: str = "Database error while processing error event"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )


class ErrorEventIngestionException(ErrorEventException):
    def __init__(self, detail: str = "Internal ingestion error"):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=detail,
        )
