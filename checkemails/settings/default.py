"""
Django settings for project.

Generated by 'django-admin startproject' using Django 1.11.

For more information on this file, see
https://docs.djangoproject.com/en/1.11/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.11/ref/settings/
"""

import os
import time

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.11/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '3$b)s72656ab2f9&q#hr(u6dqr@lt+@y^p$&@w+_tzw)#bpp7^' #os.environ.get('SECRET_KEY')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']


# Application definition

INSTALLED_APPS = [
    'admin_tools',
    # 'admin_tools.theming',
    # 'admin_tools.menu',
    'admin_tools.dashboard',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.humanize',
    'django.contrib.sites',
    'django.contrib.flatpages',
]

THIRD_PARTY_APP = [
    'corsheaders',
    'mathfilters',
    'django_filters',    
    "import_export_celery",
    'import_export',
    'django_admin_listfilter_dropdown',
    'django_ckeditor_5',
    'debug_toolbar',
    'adminsortable2',
    'rangefilter',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.google', 
]

LOCAL_APPS = [
    'accounts',
    'app',
    'subscription',
    'log',
    'emailtool',
]

INSTALLED_APPS += THIRD_PARTY_APP + LOCAL_APPS

SITE_ID = 1

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.contrib.flatpages.middleware.FlatpageFallbackMiddleware',
    'debug_toolbar.middleware.DebugToolbarMiddleware',
    'app.middleware.AppMiddleware',
    'log.middleware.LoggingMiddleware',
    'app.middleware.ThreadLocalMiddleware',
    'checkemails.core.subscriptionmiddleware.SubscriptionMiddleware',
]

ROOT_URLCONF = 'checkemails.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates'), ],
        # 'APP_DIRS': True,
        'OPTIONS': {
            'loaders': [
                'admin_tools.template_loaders.Loader',
                'django.template.loaders.filesystem.Loader',
                'django.template.loaders.app_directories.Loader',
            ],
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'checkemails.core.context_processors.load_user_data'
            ]
        },
    },
]

WSGI_APPLICATION = 'checkemails.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.11/ref/settings/#databases

CHECK_EMAILS_DATABASE_USER="sophic"
CHECK_EMAILS_DATABASE_NAME="checkemails"
CHECK_EMAILS_DATABASE_PASSWORD="x4J9K5dbx8Tv"
CHECK_EMAILS_DATABASE_HOST="localhost"
CHECK_EMAILS_DATABASE_PORT=5432

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        # 'NAME': os.environ.get('CHECK_EMAILS_DATABASE_NAME'),
        # 'USER': os.environ.get('CHECK_EMAILS_DATABASE_USER'),
        # 'PASSWORD': os.environ.get('CHECK_EMAILS_DATABASE_PASSWORD'),
        # 'HOST': os.environ.get('CHECK_EMAILS_DATABASE_HOST', 'localhost'),
        # 'PORT': os.environ.get('CHECK_EMAILS_DATABASE_PORT', 5432),
        'NAME': CHECK_EMAILS_DATABASE_NAME,
        'USER': CHECK_EMAILS_DATABASE_USER,
        'PASSWORD': CHECK_EMAILS_DATABASE_PASSWORD,
        'HOST': CHECK_EMAILS_DATABASE_HOST,
        'PORT': CHECK_EMAILS_DATABASE_PORT,
    }
}
# Auth User Model
AUTH_USER_MODEL = 'accounts.User'
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600
FILE_UPLOAD_MAX_MEMORY_SIZE = 104857600

# Password validation
# https://docs.djangoproject.com/en/1.11/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

STATIC_ROOT = os.path.join(BASE_DIR, 'public', 'static' )

MEDIA_ROOT = os.path.join(BASE_DIR, 'public', 'media')

STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]
STATIC_URL = '/static/'

MEDIA_URL = '/media/'


## Email Configuration
FROM_EMAIL_DEFAULT = 'no-reply@sophic.com'

EMAIL_USE_TLS = True
EMAIL_HOST = os.environ.get('CHECK_EMAILS_EMAIL_HOST')
EMAIL_PORT = os.environ.get('CHECK_EMAILS_EMAIL_PORT')
EMAIL_HOST_USER = os.environ.get('CHECK_EMAILS_EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('CHECK_EMAILS_EMAIL_HOST_PASSWORD')
EMAIL_DEFAULT = 'marketing@sophicservices.com'

# Internationalization
# https://docs.djangoproject.com/en/1.11/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'Asia/Kolkata'

USE_I18N = True

USE_L10N = True

USE_TZ = False


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.11/howto/static-files/

STATIC_URL = '/static/'

STATICFILES_FINDERS = (
    'django.contrib.staticfiles.finders.FileSystemFinder',
    'django.contrib.staticfiles.finders.AppDirectoriesFinder',
#    'django.contrib.staticfiles.finders.DefaultStorageFinder',
)

# Security Definitions


SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True

HttpOnly = True

DEFAULT_LOGIN = 'accounts:login'
DEFAULT_LOGOUT = 'accounts:logout'

LOGIN_URL = 'accounts:login'

LOGIN_REDIRECT_URL = 'emailtool:app_dashboard'

SESSION_COOKIE_AGE = 1296000 # 15 days to seconds
CELERY = False

# (seconds for 24 hours)
USER_TOKEN_EXPIRES_IN_HOURS = 1
USER_TOKEN_EXPIRES = 30

HTTP_API_ERROR = 111

APPLICATION_NAME = 'PROJECT'

LOG_PATTERN = r'(?:"password"|"confirm_new_password"|"confirm_password"|"old_password"|"new_password"|"token")\s?:\s*("[^\"]+")'

LST_APP_FOR_LOGGING = [
    'admin',
    'accounts',
    'log',
    'app'
]

PAGINATION_PAGE_SIZE = 20


WEBAPP_NOCACHE_TOKEN = "?" + str(int(time.time()))


CHECK_EMAILS_LOCAL_IP = os.environ.get('CHECK_EMAILS_LOCAL_IP')
REDIS_DB_IP = os.environ.get('REDIS_SERVER_IP', CHECK_EMAILS_LOCAL_IP)

REQUIRE_SUPERUSER = False
USE_HTTP_REFERER = True
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000
FILE_UPLOAD_MAX_MEMORY_SIZE = 524288000

DATA_UPLOAD_MAX_NUMBER_FIELDS = 10000

ADMIN_TOOLS_INDEX_DASHBOARD = 'checkemails.core.dashboard.CustomIndexDashboard'

DJANGO_ADMIN_GLOBAL_SIDEBAR_MENUS="checkemails.core.menu.get_menus_by_user"


CACHEOPS_REDIS = "redis://localhost:6379/1"

CACHEOPS_DEFAULTS = {
    'timeout': 2592000
}
CACHEOPS = {
    'app.people': {'ops': 'all'},
    'app.company': {'ops': 'all'},
}
customColorPalette = [
        {
            'color': 'hsl(4, 90%, 58%)',
            'label': 'Red'
        },
        {
            'color': 'hsl(340, 82%, 52%)',
            'label': 'Pink'
        },
        {
            'color': 'hsl(291, 64%, 42%)',
            'label': 'Purple'
        },
        {
            'color': 'hsl(262, 52%, 47%)',
            'label': 'Deep Purple'
        },
        {
            'color': 'hsl(231, 48%, 48%)',
            'label': 'Indigo'
        },
        {
            'color': 'hsl(207, 90%, 54%)',
            'label': 'Blue'
        },
    ]
CKEDITOR_5_CONFIGS = {
    'default': {
        'toolbar': ['heading', '|', 'bold', 'italic', 'link',
                    'bulletedList', 'numberedList', 'blockQuote', 'imageUpload', ],

    },
    'extends': {
        'blockToolbar': [
            'paragraph', 'heading1', 'heading2', 'heading3',
            '|',
            'bulletedList', 'numberedList',
            '|',
            'blockQuote',
        ],
        'toolbar': ['heading', '|', 'outdent', 'indent', '|', 'bold', 'italic', 'link', 'underline', 'strikethrough',
        'code','subscript', 'superscript', 'highlight', '|', 'codeBlock', 'sourceEditing', 'insertImage',
                    'bulletedList', 'numberedList', 'todoList', '|',  'blockQuote', 'imageUpload', '|',
                    'fontSize', 'fontFamily', 'fontColor', 'fontBackgroundColor', 'mediaEmbed', 'removeFormat',
                    'insertTable',],
        'image': {
            'toolbar': ['imageTextAlternative', '|', 'imageStyle:alignLeft',
                        'imageStyle:alignRight', 'imageStyle:alignCenter', 'imageStyle:side',  '|'],
            'styles': [
                'full',
                'side',
                'alignLeft',
                'alignRight',
                'alignCenter',
            ]

        },
        'table': {
            'contentToolbar': [ 'tableColumn', 'tableRow', 'mergeTableCells',
            'tableProperties', 'tableCellProperties' ],
            'tableProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            },
            'tableCellProperties': {
                'borderColors': customColorPalette,
                'backgroundColors': customColorPalette
            }
        },
        'heading' : {
            'options': [
                { 'model': 'paragraph', 'title': 'Paragraph', 'class': 'ck-heading_paragraph' },
                { 'model': 'heading1', 'view': 'h1', 'title': 'Heading 1', 'class': 'ck-heading_heading1' },
                { 'model': 'heading2', 'view': 'h2', 'title': 'Heading 2', 'class': 'ck-heading_heading2' },
                { 'model': 'heading3', 'view': 'h3', 'title': 'Heading 3', 'class': 'ck-heading_heading3' }
            ]
        }
    },
    'list': {
        'properties': {
            'styles': 'true',
            'startIndex': 'true',
            'reversed': 'true',
        }
    }
}
TIME_ZONE = 'Asia/Kolkata'


DEBUG = False
CELERY = True
CELERY_ENABLED = True


SITE_PROTOCOL = 'https'
SITE_DOMAIN = os.environ.get('SITE_DOMAIN')
SESSION_COOKIE_SECURE = True

# These persons receive error notification
SERVER_EMAIL = 'sophic.services@gmail.com'

ADMINS = (
    ('Anjali', 'anjali.dhingra@sophicservices.com')
)

MANAGERS = ADMINS

CELERY_TIMEZONE = 'Asia/Kolkata'
TIME_ZONE = 'Asia/Kolkata'

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend'
]

SOCIALACCOUNT_QUERY_EMAIL = True
ACCOUNT_LOGOUT_ON_GET= True
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_EMAIL_VERIFICATION = 'none'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_AUTHENTICATION_METHOD = 'email'

SOCIALACCOUNT_PROVIDERS = {
    'google': {
        'SCOPE': [
            'profile',
            'email',
        ],
        'AUTH_PARAMS': {
            'access_type': 'online',
        }
    }
}
ACCOUNT_USER_MODEL_USERNAME_FIELD = None
SIGNUP_REDIRECT_URL = LOGIN_REDIRECT_URL
SOCIAL_AUTH_LOGIN_ERROR_URL = SOCIAL_AUTH_LOGIN_URL = SOCIAL_AUTH_DISCONNECT_REDIRECT_URL = SOCIAL_AUTH_INACTIVE_USER_URL  = LOGIN_URL

# ACCOUNT_ADAPTER = 'accounts.adapters.AccountAdapter'
SOCIALACCOUNT_ADAPTER = 'accounts.adapters.SocialAccountAdapter'
PAYMENT_RECEIPT_PATH = 'payments/'


CHECK_EMAILS_EMAIL_HOST='smtp.gmail.com'
CHECK_EMAILS_EMAIL_PORT=587
CHECK_EMAILS_EMAIL_HOST_USER='marketing@sophicservices.com'
CHECK_EMAILS_EMAIL_HOST_PASSWORD='8e=CHBg98e=CHBg9'
CHECK_EMAILS_EMAIL_DEFAULT='marketing@sophicservices.com'

EMAIL_HOST = CHECK_EMAILS_EMAIL_HOST
EMAIL_PORT = CHECK_EMAILS_EMAIL_PORT
EMAIL_HOST_USER = CHECK_EMAILS_EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = CHECK_EMAILS_EMAIL_HOST_PASSWORD
EMAIL_DEFAULT = 'marketing@sophicservices.com'
REDIS_DB=2
CELERY = False
CELERY_ENABLED = False