"""
ASGI entrypoint. Configures Django and then runs the application
defined in the ASGI_APPLICATION setting.
"""

import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "checkemails.settings")
django.setup()