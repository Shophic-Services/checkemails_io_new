from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _


REGEX_MOBILE_NUMBER = r'^\+1 \([\d]{3}\)-[\d]{3}-[\d]{4}'
MOBILE_NUMBER_VALIDATOR = RegexValidator(REGEX_MOBILE_NUMBER)

VERSION_VALIDATOR = RegexValidator(
    r'^(\*|\d+(\.\d+){0,2}(\.\*)?)$',
    "Version number should be of correct format.")


def validate_file_size_ext(max_size_mb=2, *allowed_extensions):
    def validator(file):
        max_size = max_size_mb * 1024 * 1024
        try:
            if file.size <= max_size:
                if not file.name.split('.')[-1].lower() in allowed_extensions:
                    raise ValidationError('File format not supported')
            else:
                raise ValidationError('Image cannot be more than %d MB in size' % (max_size_mb))
            return file
        except Exception as ex:
            return file
    return validator

def validate_image_height(max_height=30):
    def validator(file):
        (w, h) = get_image_dimensions(file)
        if h > max_height:
            raise ValidationError('The image is {0}px high. The maximum allowed height is {1}px.'.format(h, max_height))
        return file
    return validator


def validate_empty_string(value):
    if len(value.strip()) == 0:
        raise ValidationError(
            _("This field is required"),
            code='empty field',
        )

class MaximumLengthValidator:
    def __init__(self, max_length=30):
        self.max_length = max_length

    def validate(self, password, user=None):
        if len(password) > self.max_length:
            raise ValidationError(
                _("This password must contain at max %(max_length)d characters."),
                code='password_too_long',
                params={'max_length': self.max_length},
            )

    def get_help_text(self):
        return _(
            "Your password must contain at max %(max_length)d characters."
            % {'max_length': self.max_length}
        )   
