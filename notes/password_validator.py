import re
from django.core.exceptions import ValidationError


class StrongPasswordValidator:
    def validate(self, password, user=None):

        errors = []

        if not re.search(r"[A-Z]", password):
            errors.append("Password must contain an uppercase letter.")

        if not re.search(r"[a-z]", password):
            errors.append("Password must contain a lowercase letter.")

        if not re.search(r"\d", password):
            errors.append("Password must contain a number.")

        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            errors.append("Password must contain a special character.")

        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return (
            "Password must contain uppercase, lowercase, number, "
            "and special character."
        )
