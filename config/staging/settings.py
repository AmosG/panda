from config.settings import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'panda',
        'USER': 'panda',
        'PASSWORD': 'NE3HY2dc16', 
        'HOST': 'localhost',
        'PORT': '5432',
    }
}

# Media
MEDIA_URL = 'http://media.panda.beta.tribapps.com/panda/site_media/'
ADMIN_MEDIA_PREFIX = 'http://media.panda.beta.tribapps.com/panda/admin_media/'

# Predefined domain
MY_SITE_DOMAIN = 'panda.beta.tribapps.com'

# Email
EMAIL_HOST = 'mail'
EMAIL_PORT = 25

# S3
AWS_S3_URL = 's3://media.panda.beta.tribapps.com/panda/'

# Internal IPs for DDT
INTERNAL_IPS = ()

