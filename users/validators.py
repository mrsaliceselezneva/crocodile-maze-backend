import re

from django.core.exceptions import ValidationError


class PasswordCharactersValidator:
    def validate(self, password, user=None):
        if re.fullmatch(r"[A-Za-z0-9!@#$%_-]+", password) is None:
            raise ValidationError(
                self.get_help_text(),
                code="invalid_password_characters",
            )

    def get_help_text(self):
        return "Допустимы латинские буквы, цифры и символы !@#$%_-. Пробелы запрещены."
