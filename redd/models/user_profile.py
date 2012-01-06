#!/user/bin/env python

from django.contrib.auth.models import User
from django.db import models

class UserProfile(models.Model):
    user = models.OneToOneField(User)

    activation_key = models.CharField(max_length=40)

    class Meta:
        app_label = 'redd'

