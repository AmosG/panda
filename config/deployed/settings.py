#!/usr/bin/env python

from config.settings import *

# Running in deployed mode
SETTINGS = 'deployed'

# Debug
DEBUG = True    # TEMP 
TEMPLATE_DEBUG = DEBUG

# Static media
STATIC_ROOT = '/var/lib/panda/media'

# Uploads 
MEDIA_ROOT = '/var/lib/panda/uploads' 

# Django-compressor
COMPRESS_ENABLED = True 

