from django.db import models, connection
from app.models import FileUploadLimit


def db_table_exists(table_name):
    return table_name in connection.introspection.table_names()