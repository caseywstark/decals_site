"""
Django settings for decals site.

For more information on this file, see
https://docs.djangoproject.com/en/1.6/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.6/ref/settings/

"""

import os
PROJECT_PATH = os.path.normpath(os.path.dirname(__file__))

DEBUG = True
TEMPLATE_DEBUG = DEBUG
SECRET_KEY = 'pt2xc@+_+7g-pcf!4#6%z2383w-vcare05aj3-vv5hunuoq6x3'

TEMPLATE_DIRS = (
    os.path.join(PROJECT_PATH, 'templates'),
)

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': 'database.sqlite3',
    },
}

INSTALLED_APPS = (
    'django.contrib.staticfiles',
    'django.contrib.sessions',
    'decals',
)

MIDDLEWARE_CLASSES = (
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
)

ROOT_URLCONF = 'urls'

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_ROOT = ''
STATIC_URL = '/static/'

STATICFILES_DIRS = ('static',)


#WSGI_APPLICATION = 'unwise.wsgi.application'
#DATABASE_ROUTERS = [ 'unwise.dbrouter.UnwiseDatabaseRouter', ]
