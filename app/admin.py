from django.utils import timezone
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.encoding import force_str
from django.db.models import Q
from accounts.models import User, UserRole
from app.middleware import get_current_user
from checkemails.core.admin import CheckEmailsBaseModelAdmin
from django.utils.translation import gettext_lazy as _
from dateutil.relativedelta import relativedelta
