import re

from django.core.exceptions import ValidationError


def username_validator(value):
    """Проверка поля username"""

    pattern = r'^[\w.@+-]+'
    error_chars = ', '.join(set(re.sub(pattern, '', value)))
    error_message = f'Строка содержит запрещенные символы: {error_chars}'
    if error_chars:
        raise ValidationError(error_message)

    if value.lower() == 'me':
        raise ValidationError(
            f'Нельзя использовать {value} как имя пользователя'
        )

    return value
