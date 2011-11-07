#!/usr/bin/env python

from django.conf import settings
from django.conf.urls.defaults import url
from sunburnt import SolrInterface
from tastypie import fields
from tastypie.authentication import Authentication
from tastypie.authorization import Authorization
from tastypie.utils.urls import trailing_slash

from redd.api.utils import CustomResource
from redd.models import Dataset

class DatasetResource(CustomResource):
    """
    API resource for Datasets.

    TKTK: implement authentication/permissions
    """
    from redd.api.tasks import TaskResource
    from redd.api.uploads import UploadResource

    data_upload = fields.ForeignKey(UploadResource, 'data_upload', full=True)
    current_task = fields.ToOneField(TaskResource, 'current_task', full=True, null=True)

    class Meta:
        queryset = Dataset.objects.all()
        resource_name = 'dataset'
        always_return_data = True
                
        authentication = Authentication()
        authorization = Authorization()
    
    def _solr(self):
        """
        Create a query interface for Solr.
        """
        return SolrInterface(settings.SOLR_ENDPOINT)

    def override_urls(self):
        """
        Add urls for search endpoint.
        """
        return [
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/import%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('import_data'), name='api_import_data'),
            url(r'^(?P<resource_name>%s)/(?P<pk>\w[\w/-]*)/search%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('search'), name='api_search_dataset')
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
            get_id = request.GET.get('id')

        dataset = Dataset.objects.get(id=get_id)
        dataset.import_data()

        bundle = self.build_bundle(obj=dataset, request=request)
        bundle = self.full_dehydrate(bundle)

        self.log_throttled_access(request)

        return self.create_response(request, bundle)

    def search(self, request, **kwargs):
        """
        Endpoint to search a single dataset. Delegates to DataResource.search_dataset.
        """
        from redd.api.data import DataResource
        
        data_resource = DataResource()
        
        return data_resource.search_dataset(request, **kwargs)

