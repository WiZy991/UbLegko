from django.contrib.auth.tokens import PasswordResetTokenGenerator


class EmailConfirmTokenGenerator(PasswordResetTokenGenerator):
    """Токен подтверждения email при регистрации."""

    def _make_hash_value(self, user, timestamp):
        return f'{user.pk}{user.email}{user.is_active}{timestamp}'


email_confirm_token = EmailConfirmTokenGenerator()
