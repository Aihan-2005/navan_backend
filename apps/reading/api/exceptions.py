from rest_framework.exceptions import APIException


class ReadingConflictAPIException(APIException):
    status_code = 409

    default_detail = "A conflicting reading operation is already in progress."

    default_code = "reading_conflict"


class ReadingRetryNotAllowedAPIException(APIException):
    status_code = 409

    default_detail = "This reading analysis cannot be retried."

    default_code = "reading_retry_not_allowed"
