class ReadingDomainError(Exception):
    """
    Base exception for reading domain/service errors.

    These exceptions belong to the business layer and intentionally
    do not depend on Django REST Framework.
    """


class ReadingResourceNotFoundError(ReadingDomainError):
    pass


class ReadingResourceAccessDeniedError(ReadingDomainError):
    pass


class ActiveReadingConflictError(ReadingDomainError):
    def __init__(
        self,
        message: str,
        *,
        analysis_id: int | None = None,
    ):
        super().__init__(message)
        self.analysis_id = analysis_id


class ReadingRetryNotAllowedError(ReadingDomainError):
    pass
