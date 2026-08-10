from django.core.exceptions import ValidationError
from django.utils.deconstruct import deconstructible

from .choices import ListeningPracticeMode

MAX_AUDIO_SIZE_BYTES = 25 * 1024 * 1024

MAX_PRACTICE_MODES = 5


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

    def __call__(self, value: object) -> None:
        if not isinstance(value, list):
            raise ValidationError(
                "Expected a list of strings.",
                code="invalid_list",
            )

        if len(value) > self.max_items:
            raise ValidationError(
                f"This list cannot contain more than {self.max_items} items.",
                code="too_many_items",
            )

        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValidationError(
                    "Every list item must be a non-empty string.",
                    code="invalid_item",
                )

            if len(item) > self.max_item_length:
                raise ValidationError(
                    f"Each item cannot exceed {self.max_item_length} characters.",
                    code="item_too_long",
                )


@deconstructible
class PracticeModesValidator:
    def __call__(self, value: object) -> None:
        StringListValidator(
            max_items=MAX_PRACTICE_MODES,
            max_item_length=32,
        )(value)

        if not value:
            raise ValidationError(
                "At least one practice mode is required.",
                code="practice_mode_required",
            )

        allowed_modes = {choice.value for choice in ListeningPracticeMode}
        invalid_modes = sorted(set(value) - allowed_modes)

        if invalid_modes:
            raise ValidationError(
                (f"Unsupported practice modes: {', '.join(invalid_modes)}."),
                code="invalid_practice_mode",
            )

        if len(value) != len(set(value)):
            raise ValidationError(
                "Practice modes cannot contain duplicate values.",
                code="duplicate_practice_mode",
            )


def validate_audio_file_size(
    uploaded_file: object,
) -> None:
    size = getattr(uploaded_file, "size", None)

    if size is None:
        raise ValidationError(
            "Unable to determine the audio file size.",
            code="unknown_file_size",
        )

    if size > MAX_AUDIO_SIZE_BYTES:
        raise ValidationError(
            "Audio files cannot be larger than 25 MiB.",
            code="audio_file_too_large",
        )
