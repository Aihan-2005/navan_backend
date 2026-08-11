from rest_framework.exceptions import (
    APIException,
)


class ListeningConflict(APIException):
    status_code = 409

    default_detail = "The listening resource is not editable in its current state."

    default_code = "listening_conflict"
