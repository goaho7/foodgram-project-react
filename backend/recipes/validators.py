import re

from django.core.exceptions import ValidationError


def username_validator(value):
    """Проверка поля slug"""

    pattern = r'^[-a-zA-Z0-9_]+$'
    error_chars = ', '.join(set(re.sub(pattern, '', value)))
    error_message = f'Строка содержит запрещенные символы: {error_chars}'
    if error_chars:
        raise ValidationError(error_message)

    return value
