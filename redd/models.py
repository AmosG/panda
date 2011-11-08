#!/usr/bin/env python

import os.path

from celery.contrib.abortable import AbortableAsyncResult
from celery import states
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from djcelery.models import TASK_STATE_CHOICES
from tastypie.models import create_api_key

from redd.fields import JSONField
from redd.tasks import DatasetImportTask, dataset_purge_data
from redd.utils import infer_schema, sample_data, sniff

models.signals.post_save.connect(create_api_key, sender=User)

class TaskStatus(models.Model):
    """
    An object to track the status of a Celery task, as the
    data available in AsyncResult is not sufficient.
    """
    task_name = models.CharField(max_length=255,
        help_text='Identifying name for this task.')
    status = models.CharField(max_length=50, default=states.PENDING, choices=TASK_STATE_CHOICES,
        help_text='Current state of this task.')
    message = models.CharField(max_length=255, blank=True,
        help_text='A human-readable message indicating the progress of this task.')
    start = models.DateTimeField(null=True,
        help_text='Date and time that this task began processing.')
    end = models.DateTimeField(null=True,
        help_text='Date and time that this task ceased processing (either complete or failed).')
    traceback = models.TextField(blank=True, null=True, default=None,
        help_text='Traceback that exited this task, if it failed.')

    def __unicode__(self):
        return u'%s (%i)' % (self.task_name, self.id)

class Upload(models.Model):
    """
    A file uploaded to PANDA (either a table or metadata file).
    """
    filename = models.CharField(max_length=256,
        help_text='Filename as stored in PANDA.')
    original_filename = models.CharField(max_length=256,
        help_text='Filename as originally uploaded.')
    size = models.IntegerField(
        help_text='Size of the file in bytes.')

    def __unicode__(self):
        return self.filename

    def get_path(self):
        """
        Get the absolute path to this upload on disk.
        """
        return os.path.join(settings.MEDIA_ROOT, self.filename)

class Dataset(models.Model):
    """
    A PANDA dataset (one table & associated metadata).
    """
    name = models.CharField(max_length=256,
        help_text='User-supplied dataset name.')
    description = models.TextField(
        help_text='User-supplied dataset description.')
    data_upload = models.ForeignKey(Upload,
        help_text='The upload corresponding to the data file for this dataset.')
    schema = JSONField(null=True, blank=True,
        help_text='An ordered list of dictionaries describing the attributes of this dataset\'s columns.')
    imported = models.BooleanField(default=False,
        help_text='Has this dataset been imported yet?')
    row_count = models.IntegerField(null=True, blank=True,
        help_text='The number of rows in this dataset. Only available once the dataset has been imported.')
    sample_data = JSONField(null=True, blank=True,
        help_text='Example data from the first few rows of the dataset.')
    current_task = models.ForeignKey(TaskStatus, blank=True, null=True,
        help_text='The currently executed or last finished task related to this dataset.') 
    creation_date = models.DateTimeField(auto_now=True,
        help_text='The date this dataset was initially created.')
    dialect = JSONField(
        help_text='Description of the format of the input CSV.')

    class Meta:
        ordering = ['-creation_date']

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Override save to do fast, first-N type inference on the data and populated the schema.
        """
        if not self.dialect:
            with open(self.data_upload.get_path(), 'r') as f:
                csv_dialect = sniff(f)
                self.dialect = {
                    'lineterminator': csv_dialect.lineterminator,
                    'skipinitialspace': csv_dialect.skipinitialspace,
                    'quoting': csv_dialect.quoting,
                    'delimiter': csv_dialect.delimiter,
                    'quotechar': csv_dialect.quotechar,
                    'doublequote': csv_dialect.doublequote
                }

        if not self.schema:
            with open(self.data_upload.get_path(), 'r') as f:
                self.schema = infer_schema(f, self.dialect)

        if not self.sample_data:
            with open(self.data_upload.get_path(), 'r') as f:
                self.sample_data = sample_data(f, self.dialect)

        super(Dataset, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        """
        Purge data from Solr when a dataset is deleted.
        """
        dataset_id = self.id

        # Cancel import if necessary 
        if self.current_task and self.current_task.end is None and self.current_task.task_name == 'redd.tasks.DatasetImportTask': 
            async_result = AbortableAsyncResult(self.current_task.id)
            async_result.abort()

        super(Dataset, self).delete(*args, **kwargs)

        # Execute solr delete
        dataset_purge_data.apply_async(args=[dataset_id])

    def import_data(self):
        """
        Execute the data import task for this Dataset. Will use the currently configured schema.
        """
        self.current_task = TaskStatus.objects.create(
            task_name=DatasetImportTask.name)
        self.save()

        DatasetImportTask.apply_async([self.id], task_id=self.current_task.id)

