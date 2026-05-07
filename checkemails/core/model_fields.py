from django.db import models, connection
from django.contrib.contenttypes.models import ContentType
from .validators import validate_file_size_ext, validate_image_height

CURSOR_QUERY = "SELECT size_limit FROM app_fileuploadlimit WHERE file_type = %s LIMIT 1"
def db_table_exists(table_name):
    return table_name in connection.introspection.table_names()

class DocumentField(models.FileField):

    def __init__(self, *args, **kwargs):
        allowed_exts = kwargs.pop('allowed_exts', None)
        super(DocumentField, self).__init__(*args, **kwargs)
        self.validators = kwargs.get('validators', None)
        if not self.validators:
            existing_limit = None
            if db_table_exists('app_fileuploadlimit'):
                with connection.cursor() as cursor:
                    cursor.execute(CURSOR_QUERY, [1])
                    existing_limit = cursor.fetchone()
            if existing_limit:
                size_limit_mb = existing_limit[0]
            else:
                size_limit_mb = 30
            allowed_extension = allowed_exts if allowed_exts else ['doc',
                                'docx', 'xls', 'xlsx', 'pdf', 'png', 'jpg',
                                'jpeg']
            self.validators = [validate_file_size_ext(size_limit_mb,
                                 *allowed_extension)]


class ImageField(models.FileField):

    def __init__(self, *args, **kwargs):
        allowed_exts = kwargs.pop('allowed_exts', None)
        super(ImageField, self).__init__(*args, **kwargs)
        self.validators = kwargs.get('validators', None)
        if not self.validators:
            existing_limit = None
            if db_table_exists('app_fileuploadlimit'):
                with connection.cursor() as cursor:
                    cursor.execute(CURSOR_QUERY, [2])
                    existing_limit = cursor.fetchone()
            if existing_limit:
                size_limit_mb = existing_limit[0]
            else:
                size_limit_mb = 30
            allowed_extension = allowed_exts if allowed_exts else ['png', 'jpg', 'jpeg']
            self.validators = [validate_file_size_ext(size_limit_mb,
                                 *allowed_extension),]


class VideoDocumentField(models.FileField):

    def __init__(self, *args, **kwargs):
        allowed_exts = kwargs.pop('allowed_exts', None)
        super(VideoDocumentField, self).__init__(*args, **kwargs)
        self.validators = kwargs.get('validators', None)
        if not self.validators:
            existing_limit = None
            if db_table_exists('app_fileuploadlimit'):
                with connection.cursor() as cursor:
                    cursor.execute(CURSOR_QUERY, [3])
                    existing_limit = cursor.fetchone()
            if existing_limit:
                size_limit_mb = existing_limit[0]
            else:
                size_limit_mb = 30
            allowed_extension = allowed_exts if allowed_exts else ['doc', 'docx', 'xls', 'xlsx',
                                'pdf', 'png', 'jpg', 'jpeg', 'mp4', 'mkv',
                                'avi', 'flv', 'mov', 'wmv']
            self.validators = [validate_file_size_ext(size_limit_mb,
                                 *allowed_extension)]

