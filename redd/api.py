#!/usr/bin/env python

from copy import copy
import json

from celery.result import AsyncResult
from celery.states import EXCEPTION_STATES
from celery.task.control import inspect 
from django.conf import settings
from django.conf.urls.defaults import url
from django.http import HttpResponse
from django.core.servers.basehttp import FileWrapper
from django.core.urlresolvers import reverse
from sunburnt import SolrInterface
from sunburnt.search import SolrSearch
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.bundle import Bundle
from tastypie.fields import ApiField, CharField
from tastypie.paginator import Paginator
from tastypie.resources import ModelResource, Resource
from tastypie.utils.urls import trailing_slash

from redd.fields import JSONField
from redd.models import Dataset, Upload

class JSONApiField(ApiField):
    """
    Custom ApiField for dealing with data from custom JSONFields.
    """
    dehydrated_type = 'json'
    help_text = 'JSON structured data.'
    
    def dehydrate(self, obj):
        return self.convert(super(JSONApiField, self).dehydrate(obj))
    
    def convert(self, value):
        if value is None:
            return None
        
        return value

class CustomResource(ModelResource):
    """
    ModelResource subclass that supports JSONFields.
    """
    @classmethod
    def api_field_from_django_field(cls, f, default=CharField):
        """
        Overrides default field handling to support custom ListField and JSONField.
        """
        if isinstance(f, JSONField):
            return JSONApiField
    
        return super(CustomResource, cls).api_field_from_django_field(f, default)

class TaskObject(object):
    """
    A lightweight wrapper around a Celery task object for use when
    checking status via Tastypie.
    """
    def __init__(self, initial=None, **kwargs):
        self.__dict__['_data'] = {}

        if hasattr(initial, 'items'):
            self.__dict__['_data'] = initial

        self.__dict__['_data'].update(kwargs)

    def __getattr__(self, name):
        return self._data.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__['_data'][name] = value

    def __str__(self):
        return str(self.__dict__['_data'])

    def __unicode__(self):
        return unicode(self.__dict__['_data'])

    def to_dict(self):
        return self._data

class TaskResource(CustomResource):
    """
    Simple wrapper around django-celery's task API.

    TKTK: It would be good to support list view for tasks, for dashboard-type applications.
    TKTK: implement authentication/permissions
    """
    id = fields.CharField(attribute='id',
        help_text='Unique id of this task.')
    state = fields.CharField(attribute='state',
        help_text='State the task is currently in--PENDING, STARTED, SUCCESS, FAILURE, etc.')
    result = fields.CharField(attribute='result', null=True,
        help_text='Result of the task, if complete.')
    exc = fields.CharField(attribute='result', null=True, blank=True,
        help_text='Exception that terminated this task, if it raised one.')
    traceback = fields.CharField(attribute='traceback', null=True, blank=True,
        help_text='Traceback of the exception that terminated this task, if it raised one.')

    class Meta:
        resource_name = 'task'
        list_allowed_methods = []
        detail_allowed_methods = ['get']

        authentication = Authentication()
        authorization = Authorization()

    def get_resource_uri(self, bundle_or_obj):
        """
        Build a canonical uri for a datum.
        """
        kwargs = {
            'resource_name': self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.id

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        return self._build_reverse_url('api_dispatch_detail', kwargs=kwargs)

    def obj_get(self, request=None, **kwargs):
        """
        Fetch the status of a task by task_id.
        """
        if 'pk' in kwargs:
            task_id = kwargs['pk']
        else:
            task_id = request.GET.get('id', '')

        task = AsyncResult(task_id)

        obj = {
            'id': task_id,
            'state': task.state,
            'result': task.result,
        }

        if task.state in EXCEPTION_STATES:
            cls = task.result.__class__
            exc = '.'.join([cls.__module__, cls.__name__])

            obj.update({
                'result': repr(task.result),
                'exc': exc,
                'traceback': task.traceback
            })

        return TaskObject(obj) 

class UploadResource(ModelResource):
    """
    API resource for Uploads.

    TKTK: implement authentication
    """
    class Meta:
        queryset = Upload.objects.all()
        resource_name = 'upload'
        allowed_methods = ['get']

        authentication = Authentication()
        authorization = Authorization()

    def override_urls(self):
        """
        Add urls for search endpoint.
        """
        return [
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/download%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('download'), name='api_download_upload'),
        ]

    def download(self, request, **kwargs):
        """
        Download the original file that was uploaded.
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if 'pk' in kwargs:
            get_id = kwargs['pk']
        else:
            get_id = request.GET.get('id', '')

        upload = Upload.objects.get(id=get_id)
        path = upload.get_path()

        self.log_throttled_access(request)

        response = HttpResponse(FileWrapper(open(path, 'r')))
        response['Content-Disposition'] = 'attachment; filename=%s' % upload.original_filename
        response['Content-Length'] = upload.size

        return response

class DatasetResource(CustomResource):
    """
    API resource for Datasets.

    TKTK: implement authentication/permissions
    """
    data_upload = fields.ForeignKey(UploadResource, 'data_upload', full=True)

    class Meta:
        queryset = Dataset.objects.all()
        resource_name = 'dataset'
        always_return_data = True

        authentication = Authentication()
        authorization = Authorization()

    def dehydrate(self, bundle):
        """
        Append TaskResource details as though it were a ForeignKey field with full=True set. 
        """
        if bundle.obj.current_task_id:
            tr = TaskResource()
            current_task = tr.obj_get(pk=bundle.obj.current_task_id)

            bundle.data['current_task'] = current_task.to_dict() 
        else:
            bundle.data['current_task'] = None

        del bundle.data['current_task_id']

        return bundle

    def override_urls(self):
        """
        Add urls for search endpoint.
        """
        return [
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/import%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('import_data'), name='api_import_data'),
        ]

    def import_data(self, request, **kwargs):
        """
        Dummy endpoint for kicking off data import tasks.
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if 'pk' in kwargs:
            get_id = kwargs['pk']
        else:
            get_id = request.GET.get('id', '')

        dataset = Dataset.objects.get(id=get_id)
        dataset.import_data()

        bundle = self.build_bundle(obj=dataset, request=request)
        bundle = self.full_dehydrate(bundle)

        self.log_throttled_access(request)

        return self.create_response(request, bundle)

class SolrObject(object):
    """
    A lightweight wrapper around a Solr response object for use when
    querying Solr via Tastypie.
    """
    def __init__(self, initial=None, **kwargs):
        self.__dict__['_data'] = {}

        if hasattr(initial, 'items'):
            self.__dict__['_data'] = initial

        self.__dict__['_data'].update(kwargs)

    def __getattr__(self, name):
        return self._data.get(name, None)

    def __setattr__(self, name, value):
        self.__dict__['_data'][name] = value

    def __str__(self):
        return str(self.__dict__['_data'])

    def __unicode__(self):
        return unicode(self.__dict__['_data'])

    def to_dict(self):
        return self._data

class DataResource(Resource):
    """
    API resource for row data.

    TKTK: return data for indexed fields
    TKTK: implement filtering
    TKTK: implement write API
    TKTK: implement authentication/permissions
    """
    id = fields.CharField(attribute='id',
        help_text='Unique id of this row of data.')
    dataset_id = fields.IntegerField(attribute='dataset_id',
        help_text='Unique id of the dataset this row of data belongs to.')
    row = fields.IntegerField(attribute='row',
        help_text='Row number of this data in the source dataset.')
    data = fields.CharField(attribute='data',
        help_text='An ordered list of values corresponding to the columns in the parent dataset.')

    class Meta:
        resource_name = 'data'
        allowed_methods = ['get']

        authentication = Authentication()
        authorization = Authorization()

    def _solr(self):
        """
        Create a query interface for Solr.
        """
        return SolrInterface(settings.SOLR_ENDPOINT)

    def dehydrate_data(self, bundle):
        """
        Convert csv data into a proper array for JSON serialization
        """
        return json.loads(bundle.data['data'])

    def dehydrate(self, bundle):
        """
        Trim the dataset_id field and add a proper relationship.

        TKTK -- better way to do this?
        """
        dataset = Dataset.objects.get(id=bundle.data['dataset_id'])
        dr = DatasetResource()
        uri = dr.get_resource_uri(dataset)

        del bundle.data['dataset_id']
        bundle.data['dataset'] = uri

        return bundle

    def get_resource_uri(self, bundle_or_obj):
        """
        Build a canonical uri for a datum.
        """
        kwargs = {
            'resource_name': self._meta.resource_name,
        }

        if isinstance(bundle_or_obj, Bundle):
            kwargs['pk'] = bundle_or_obj.obj.id
        else:
            kwargs['pk'] = bundle_or_obj.id

        if self._meta.api_name is not None:
            kwargs['api_name'] = self._meta.api_name

        return self._build_reverse_url('api_dispatch_detail', kwargs=kwargs)

    def get_object_list(self, request):
        """
        Get all objects.

        TKTK: enforce proper limits from tastypie in solr query
        """
        results = self._solr().query().execute(constructor=SolrObject)

        return results

    def obj_get_list(self, request=None, **kwargs):
        """
        Query Solr with a list of terms.
        """
        q = copy(request.GET)

        if 'format' in q: del q['format']
        if 'limit' in q: del q['limit']
        if 'offset' in q: del q['offset']

        results = self._solr().query(**q).execute(constructor=SolrObject)

        return results

    def obj_get(self, request=None, **kwargs):
        """
        Query Solr for a single item by primary key.
        """
        if 'pk' in kwargs:
            get_id = kwargs['pk']
        else:
            get_id = request.GET.get('id', '')

        obj = self._solr().query(id=get_id).execute(constructor=SolrObject)[0]

        return obj

    def override_urls(self):
        """
        Add urls for search endpoint.
        """
        return [
            url(r'^(?P<resource_name>%s)/search%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('search'), name='api_search'),
        ]

    def search(self, request, **kwargs):
        """
        An endpoint for performing full-text searches.

        TKTK -- implement offset and limit
        TKTK -- implement field searches
        TKTK -- implement wildcard + boolean searches
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)
        
        s = SolrSearch(self._solr())
        s = s.query(full_text=request.GET.get('q'))
        s = s.group_by('dataset_id', limit=20, sort='+row')
        s = s.execute()

        paginator = Paginator(request.GET, s, resource_uri=request.path_info)

        page = paginator.page()

        objects = []
        groups = {}

        for dataset_id, group in s.result.groups.items():
            dataset_url = reverse('api_dispatch_detail', kwargs={'api_name': kwargs['api_name'], 'resource_name': 'dataset', 'pk': dataset_id })

            d = Dataset.objects.get(id=dataset_id)

            groups[dataset_url] = {
                'id': d.id,
                'name': d.name,
                'schema': d.schema,
                'count': group.numFound,
                'offset': group.start
            }

            for obj in group.docs:
                bundle = self.build_bundle(obj=SolrObject(obj), request=request)
                bundle = self.full_dehydrate(bundle)
                objects.append(bundle)

        page['objects'] = objects
        page['groups'] = groups

        self.log_throttled_access(request)

        return self.create_response(request, page)

