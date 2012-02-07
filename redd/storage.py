#!/usr/bin/env python

from io import BufferedWriter, FileIO
import os

from ajaxuploader.backends.base import AbstractUploadBackend
from django.conf import settings

from redd.api import DataUploadResource, RelatedUploadResource, UserResource
from redd.models import Dataset, DataUpload, RelatedUpload

class PANDAAbstractUploadBackend(AbstractUploadBackend):
    """
    Customized backend to handle AJAX uploads.
    """
    def update_filename(self, request, filename):
        """
        Verify that the filename is unique, if it isn't append and iterate
        a counter until it is.
        """
        self._original_filename = filename

        filename = self._original_filename
        root, ext = os.path.splitext(self._original_filename)
        path = os.path.join(settings.MEDIA_ROOT, filename)

        i = 1

        while os.path.exists(path):
            filename = '%s%i%s' % (root, i, ext)
            path = os.path.join(settings.MEDIA_ROOT, filename)
            i += 1

        return filename 

    def setup(self, filename):
        """
        Open the destination file for writing.
        """
        self._path = os.path.join(settings.MEDIA_ROOT, filename)

        try:
            os.makedirs(os.path.realpath(os.path.dirname(self._path)))
        except:
            pass

        self._dest = BufferedWriter(FileIO(self._path, "w"))

    def upload_chunk(self, chunk):
        """
        Write a chunk of data to the destination.
        """
        self._dest.write(chunk)

    def upload_complete(self, request, filename):
        """
        Close the destination file.
        """
        self._dest.close()

class PANDADataUploadBackend(PANDAAbstractUploadBackend):
    """
    Backend specifically for DataUploads.
    """
    def upload_complete(self, request, filename):
        """
        Create a DataUpload object.
        """
        super(PANDADataUploadBackend, self).upload_complete(request, filename)

        root, ext = os.path.splitext(filename)
        path = os.path.join(settings.MEDIA_ROOT, filename)
        size = os.path.getsize(path)

        if 'dataset_slug' in request.REQUEST:
            dataset = Dataset.objects.get(slug=request.REQUEST['dataset_slug'])
        else:
            dataset = None

        upload = DataUpload.objects.create(
            filename=filename,
            original_filename=self._original_filename,
            size=size,
            creator=request.user,
            dataset=dataset)

        if dataset:
            dataset.update_full_text()

        resource = DataUploadResource()
        bundle = resource.build_bundle(obj=upload, request=request)
        data = resource.full_dehydrate(bundle).data

        # django-ajax-upoader does not use the Tastypie serializer
        # so we must 'manually' serialize the embedded resource bundle
        resource = UserResource()
        bundle = data['creator']
        user_data = resource.full_dehydrate(bundle).data

        data['creator'] = user_data

        return data

class PANDARelatedUploadBackend(PANDAAbstractUploadBackend):
    """
    Backend specifically for RelatedUploads.
    """
    def upload_complete(self, request, filename):
        """
        Create a RelatedUpload object.
        """
        super(PANDARelatedUploadBackend, self).upload_complete(request, filename)

        root, ext = os.path.splitext(filename)
        path = os.path.join(settings.MEDIA_ROOT, filename)
        size = os.path.getsize(path)

        dataset = Dataset.objects.get(slug=request.REQUEST['dataset_slug'])

        upload = RelatedUpload.objects.create(
            filename=filename,
            original_filename=self._original_filename,
            size=size,
            creator=request.user,
            dataset=dataset)

        dataset.update_full_text()

        resource = RelatedUploadResource()
        bundle = resource.build_bundle(obj=upload, request=request)
        data = resource.full_dehydrate(bundle).data

        # django-ajax-upoader does not use the Tastypie serializer
        # so we must 'manually' serialize the embedded resource bundle
        resource = UserResource()
        bundle = data['creator']
        user_data = resource.full_dehydrate(bundle).data

        data['creator'] = user_data

        return data

