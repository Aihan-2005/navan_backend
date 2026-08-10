import re

from django.contrib.auth.base_user import BaseUserManager
from django.core.exceptions import ValidationError
from django.core.validators import validate_email


PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
ARABIC_DIGITS = "٠١٢٣٤٥٦٧٨٩"
ENGLISH_DIGITS = "0123456789"

DIGIT_TRANSLATION_TABLE = str.maketrans(
    PERSIAN_DIGITS + ARABIC_DIGITS,
    ENGLISH_DIGITS + ENGLISH_DIGITS,
)

IRANIAN_MOBILE_PATTERN = re.compile(
    r"^\+989\d{9}$"
)


def normalize_iranian_mobile(phone_number: str) -> str:

    phone_number = phone_number.strip()
    phone_number = phone_number.translate(
        DIGIT_TRANSLATION_TABLE
    )
    phone_number = re.sub(
        r"[\s()-]",
        "",
        phone_number,
    )

    if phone_number.startswith("0098"):
        return f"+98{phone_number[4:]}"

    if phone_number.startswith("+98"):
        return phone_number

    if phone_number.startswith("98"):
        return f"+{phone_number}"

    if phone_number.startswith("0"):
        return f"+98{phone_number[1:]}"

    if phone_number.startswith("9"):
        return f"+98{phone_number}"

    return phone_number


def validate_iranian_mobile(phone_number: str) -> None:
    if not IRANIAN_MOBILE_PATTERN.fullmatch(phone_number):
        raise ValidationError(
            "شماره موبایل ایرانی معتبر نیست."
        )


def normalize_identifier(identifier: str) -> str:
    identifier = identifier.strip()

    if "@" in identifier:
        return BaseUserManager.normalize_email(
            identifier
        )

    return normalize_iranian_mobile(identifier)


def validate_identifier(identifier: str) -> None:
    if "@" in identifier:
        try:
            validate_email(identifier)
        except ValidationError as exc:
            raise ValidationError(
                "ایمیل واردشده معتبر نیست."
            ) from exc

        return

    validate_iranian_mobile(identifier)