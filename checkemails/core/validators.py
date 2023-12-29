from django.core.exceptions import ValidationError
from django.core.files.images import get_image_dimensions
from django.core.validators import RegexValidator


REGEX_MOBILE_NUMBER = r'^\+1 \([\d]{3}\)-[\d]{3}-[\d]{4}'
MOBILE_NUMBER_VALIDATOR = RegexValidator(REGEX_MOBILE_NUMBER)


def validate_file_size_ext(max_size_mb=2, *allowed_extensions):
    def validator(file):
        max_size = max_size_mb * 1024 * 1024
        if file.size <= max_size:
            if not file.name.split('.')[-1].lower() in allowed_extensions:
                raise ValidationError('File format not supported')
        else:
            raise ValidationError('Image cannot be more than %d MB in size' % (max_size_mb))
        return file
    return validator

def validate_image_height(max_height=30):
    def validator(file):
        (w, h) = get_image_dimensions(file)
        if h > max_height:
            raise ValidationError('The image is {0}px high. The maximum allowed height is {1}px.'.format(h, max_height))
        return file
    return validator     
