#!/usr/bin/env python

from django.conf import settings
from django.conf.urls.defaults import url
from tastypie import fields
from tastypie.authorization import DjangoAuthorization
from tastypie.utils.urls import trailing_slash
from tastypie.validation import Validation

from redd import solr
from redd.api.utils import CustomApiKeyAuthentication, CustomPaginator, SlugResource, CustomSerializer
from redd.models import Dataset

class DatasetValidation(Validation):
    def is_valid(self, bundle, request=None):
        errors = {}

        if 'name' not in bundle.data or not bundle.data['name']:
            errors['name'] = ['This field is required.']

        return errors

class DatasetResource(SlugResource):
    """
    API resource for Datasets.
    """
    from redd.api.category import CategoryResource
    from redd.api.tasks import TaskResource
    from redd.api.uploads import UploadResource
    from redd.api.users import UserResource

    categories = fields.ToManyField(CategoryResource, 'categories', full=True, null=True)
    creator = fields.ForeignKey(UserResource, 'creator', full=True)
    current_task = fields.ToOneField(TaskResource, 'current_task', full=True, null=True)
    data_upload = fields.ForeignKey(UploadResource, 'data_upload', full=True)

    class Meta:
        queryset = Dataset.objects.all()
        resource_name = 'dataset'
        always_return_data = True

        filtering = {
            'categories': ('exact', )
        }
                
        authentication = CustomApiKeyAuthentication()
        authorization = DjangoAuthorization()
        validation = DatasetValidation()
        serializer = CustomSerializer()

    def obj_create(self, bundle, request=None, **kwargs):
        """
        Set creating user on create.
        """
        return super(DatasetResource, self).obj_create(bundle, request=request, creator=request.user, **kwargs)

    def simplify_bundle(self, bundle):
        """
        Takes a dehydrated bundle and removes attributes to create a "simple"
        view that is faster over the wire.
        """
        del bundle.data['data_upload']
        del bundle.data['sample_data']
        del bundle.data['current_task']
        del bundle.data['dialect']

        return bundle

    def override_urls(self):
        """
        Add urls for search endpoint.
        """
        return [
            url(r'^(?P<resource_name>%s)%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('search'), name='api_dispatch_list'),
            url(r"^(?P<resource_name>%s)/(?P<slug>[\w\d_-]+)/$" % self._meta.resource_name, self.wrap_view('dispatch_detail'), name="api_dispatch_detail"),
            url(r'^(?P<resource_name>%s)/(?P<slug>[\w\d_-]+)/import%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('import_data'), name='api_import_data'),
            url(r'^(?P<resource_name>%s)/(?P<slug>[\w\d_-]+)/search%s$' % (self._meta.resource_name, trailing_slash()), self.wrap_view('search_dataset'), name='api_search_dataset')
        ]

    def import_data(self, request, **kwargs):
        """
        Dummy endpoint for kicking off data import tasks.
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        if 'slug' in kwargs:
            slug = kwargs['slug']
        else:
            slug = request.GET.get('slug')

        dataset = Dataset.objects.get(slug=slug)
        dataset.import_data()

        bundle = self.build_bundle(obj=dataset, request=request)
        bundle = self.full_dehydrate(bundle)

        self.log_throttled_access(request)

        return self.create_response(request, bundle)

    def search_dataset(self, request, **kwargs):
        """
        Endpoint to search a single dataset. Delegates to DataResource.search_dataset.
        """
        from redd.api.data import DataResource
        
        data_resource = DataResource()
        
        return data_resource.search_dataset(request, **kwargs)

    def search(self, request, **kwargs):
        """
        Full-text search over dataset metadata.
        """
        self.method_check(request, allowed=['get'])
        self.is_authenticated(request)
        self.throttle_check(request)

        limit = int(request.GET.get('limit', settings.PANDA_DEFAULT_SEARCH_ROWS))
        offset = int(request.GET.get('offset', 0))
        categories = request.GET.get('categories', 0)
        query = request.GET.get('q', '')
        simple = True if request.GET.get('simple', 'false').lower() == 'true' else False

        if categories and query:
            q = 'categories:%s %s' % (categories, query)
        elif categories:
            q = 'categories:%s' % categories
        else:
            q = query

        response = solr.query(settings.SOLR_DATASETS_CORE, q, offset=offset, limit=limit, sort='id asc')
        dataset_ids = [d['id'] for d in response['response']['docs']]

        datasets = Dataset.objects.filter(id__in=dataset_ids)

        paginator = CustomPaginator(request.GET, datasets, resource_uri=request.path_info, count=response['response']['numFound'])
        page = paginator.page()

        objects = []

        for obj in datasets:
            bundle = self.build_bundle(obj=obj, request=request)
            bundle = self.full_dehydrate(bundle)

            # Prune attributes we don't care about
            if simple:
                bundle = self.simplify_bundle(bundle)

            objects.append(bundle)

        page['objects'] = objects

        self.log_throttled_access(request)

        return self.create_response(request, page)

