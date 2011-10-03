#!/usr/bin/env python

from django.conf.urls.defaults import include, patterns, url
from tastypie.api import Api

from redd.api import DataResource, DatasetResource, TaskResource, UploadResource
from redd import views

api_1_0 = Api(api_name='1.0')
api_1_0.register(TaskResource())
api_1_0.register(UploadResource())
api_1_0.register(DatasetResource())
api_1_0.register(DataResource())

urlpatterns = patterns('',
    url(r'^test_solr$', views.test_solr, name="test_solr"),

    url(r'^ajax_upload$', views.ajax_upload, name="ajax_upload"),
    url(r'^search$', views.search, name="search"),
    url(r'^upload$', views.upload, name="upload"),

    (r'^api/', include(api_1_0.urls)),
)

