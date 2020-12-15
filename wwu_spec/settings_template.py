"""
Django settings for wwu_spec project.

Generated by 'django-admin startproject' using Django 2.2.5.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os

# SECURITY NOTE: you'll have to generate a new secret key file
# on new deployments.
from .secretkey import SECRET_KEY

SECRET_KEY = SECRET_KEY

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Don't run with this on either!
# ALLOWED_HOSTS = ['*']
# add public-facing ip of host to this
ALLOWED_HOSTS = ['127.0.0.1']

INTERNAL_IPS = ["127.0.0.1"]

# Application definition
# consider removing django-extensions for production
# this is for jupyter during dev
INSTALLED_APPS = [
    'whitenoise.runserver_nostatic',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mars',
    'massadmin',
    'django_extensions'
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'wwu_spec.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'wwu_spec.wsgi.application'

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': os.path.join(BASE_DIR, 'db.sqlite3'),
    }
}


LOGGING = {
     'version': 1,
     'disable_existing_loggers': False,
     'formatters': {
         'verbose': {
             'format' : "[%(asctime)s] %(levelname)s [%(name)s:%(lineno)s] %(message)s",
             'datefmt' : "%d/%b/%Y %H:%M:%S"
         },
         'simple': {
             'format': '%(levelname)s %(message)s'
         },
     },
     'handlers': {
         'file': {
             'level': 'WARNING',
             'class': 'logging.FileHandler',
             'filename': 'wwu_spec.log',
             'formatter': 'verbose'
         },
     },
     'loggers': {
         'django': {
             'handlers':['file'],
             'propagate': True,
             'level':'WARNING',
         },
         'track': {
             'handlers': ['file'],
             'level': 'WARNING',
         },
     }
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/Los_Angeles'

USE_I18N = True

USE_L10N = True

USE_TZ = False

# Static files (CSS, JavaScript, Images)

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")

# Static files are sent to the root file, which could be on a different server
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static_in_pro", "our_static")
]

SAMPLE_IMAGE_PATH = os.path.join(BASE_DIR,
                                 "static_in_pro/our_static/sample_images")

STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'