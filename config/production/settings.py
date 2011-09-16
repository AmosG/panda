from config.settings import *

DEBUG = False
TEMPLATE_DEBUG = DEBUG

# Database
DATABASES['default']['HOST'] = 'db'
DATABASES['default']['PORT'] = '5433'
DATABASES['default']['USER'] = 'panda'
DATABASES['default']['PASSWORD'] = 'NE3HY2dc16'

# URL that handles the media served from MEDIA_ROOT. Make sure to use a
# trailing slash if there is a path component (optional in other cases).
# Examples: "http://media.lawrence.com", "http://example.com/media/"
MEDIA_URL = 'http://media.panda.tribapps.com/panda/site_media/'

# URL prefix for admin media -- CSS, JavaScript and images. Make sure to use a
# trailing slash.
# Examples: "http://foo.com/media/", "/media/".
ADMIN_MEDIA_PREFIX = 'http://media.panda.tribapps.com/panda/admin_media/'

# Predefined domain
MY_SITE_DOMAIN = 'panda.tribapps.com'

# Email
EMAIL_HOST = 'mail'
EMAIL_PORT = 25

# S3
AWS_S3_URL = 's3://media.panda.tribapps.com/panda/'

# Internal IPs for security
INTERNAL_IPS = ()

