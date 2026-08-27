from django.contrib.auth.base_user import BaseUserManager

from .validators import (
    normalize_identifier,
    validate_identifier,
)


class UserManager(BaseUserManager):
    def create_user(
        self,
        identifier: str,
        name: str,
        password: str | None = None,
        **extra_fields,
    ):
        if not identifier or not identifier.strip():
            raise ValueError("ایمیل یا شماره تلفن الزامی است.")

        if not name or not name.strip():
            raise ValueError("نام کاربر الزامی است.")

        if not password or not password.strip():
            raise ValueError("رمز عبور الزامی است.")

        identifier = normalize_identifier(identifier)

        validate_identifier(identifier)

        user = self.model(
            identifier=identifier,
            name=name.strip(),
            **extra_fields,
        )

        user.set_password(password)
        user.save(using=self._db)

        return user

    def create_superuser(
        self,
        identifier: str,
        name: str,
        password: str | None = None,
        **extra_fields,
    ):
        extra_fields.setdefault("is_active", True)
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_active") is not True:
            raise ValueError("Superuser باید is_active=True داشته باشد.")

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser باید is_staff=True داشته باشد.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser باید is_superuser=True داشته باشد.")

        return self.create_user(
            identifier=identifier,
            name=name,
            password=password,
            **extra_fields,
        )
