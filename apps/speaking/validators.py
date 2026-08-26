from django.core.exceptions import (
    ValidationError,
)
from django.utils.deconstruct import (
    deconstructible,
)


@deconstructible
class StringListValidator:
    def __init__(
        self,
        *,
        max_items: int,
        max_item_length: int,
    ) -> None:
        self.max_items = max_items
        self.max_item_length = max_item_length

    def __call__(
        self,
        value: object,
    ) -> None:
        if not isinstance(value, list):
            raise ValidationError(
                "Expected a list of strings.",
                code="invalid_list",
            )

        if len(value) > self.max_items:
            raise ValidationError(
                (f"This list cannot contain more than {self.max_items} items."),
                code="too_many_items",
            )

        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValidationError(
                    ("Every list item must be a non-empty string."),
                    code="invalid_item",
                )

            if len(item) > self.max_item_length:
                raise ValidationError(
                    (f"Each item cannot exceed {self.max_item_length} characters."),
                    code="item_too_long",
                )
