#!/usr/bin/env python

from livesettings import config_register, BooleanValue, ConfigurationGroup, FloatValue, PositiveIntegerValue, StringValue

# Site domain settings
DOMAIN_GROUP = ConfigurationGroup(
    'DOMAIN',
    'Site domain settings',
    ordering=0
)

config_register(StringValue(
    DOMAIN_GROUP,
    'SITE_DOMAIN',
    description='Site domain to be referenced in outgoing email.',
    default='localhost:8000'
))

# Email settings
EMAIL_GROUP = ConfigurationGroup(
    'EMAIL',
    'Email settings',
    ordering=1
)

config_register(StringValue(
    EMAIL_GROUP,
    'EMAIL_HOST',
    description='Hostname or IP of the SMTP server.',
    default='localhost',
    ordering=0
))

config_register(PositiveIntegerValue(
    EMAIL_GROUP,
    'EMAIL_PORT',
    description='Port number of the SMTP server.',
    default=1025,
    ordering=1
))

config_register(StringValue(
    EMAIL_GROUP,
    'EMAIL_HOST_USER',
    description='Username for the SMTP server.',
    default='',
    ordering=2
))

config_register(StringValue(
    EMAIL_GROUP,
    'EMAIL_HOST_PASSWORD',
    description='Password for the SMTP server.',
    default='',
    ordering=3
))

config_register(BooleanValue(
    EMAIL_GROUP,
    'EMAIL_USE_TLS',
    description='Use TLS encryption when connecting to the SMTP server?',
    default=False,
    ordering=4
))

config_register(StringValue(
    EMAIL_GROUP,
    'DEFAULT_FROM_EMAIL',
    description='Email address that PANDA messages should appear to come from.',
    default='do.not.reply@pandaproject.net',
    ordering=5
))

# Miscellaneous settings
MISC_GROUP = ConfigurationGroup(
    'MISC',
    'Miscellaneous settings',
    ordering=2
)

config_register(BooleanValue(
    MISC_GROUP,
    'DEMO_MODE',
    description='Enable demo mode? (Displays default credentials on login screen.)',
    default=False,
    ordering=0
))

config_register(FloatValue(
    MISC_GROUP,
    'TASK_THROTTLE',
    description='Number of seconds to throttle between processing batches of data.',
    default=0.5,
    ordering=1
))

