from datetime import timedelta

from rest_framework_simplejwt.tokens import Token


class PasswordResetToken(Token):
    token_type = "password_reset"
    lifetime = timedelta(minutes=5)


def issue_password_reset_token(user, otp) -> str:
    token = PasswordResetToken.for_user(user)
    token["otp_id"] = otp.pk

    return str(token)
