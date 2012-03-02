#!/usr/bin/env python

from datetime import datetime

from celery.contrib.abortable import AbortableAsyncResult
from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.dispatch import receiver

from panda import solr, utils
from panda.exceptions import DataImportError, DatasetLockedError
from panda.fields import JSONField
from panda.models.category import Category
from panda.models.slugged_model import SluggedModel
from panda.models.task_status import TaskStatus
from panda.tasks import get_import_task_type_for_upload, ExportCSVTask, PurgeDataTask, ReindexTask 

class Dataset(SluggedModel):
    """
    A PANDA dataset (one table & associated metadata).
    """
    name = models.CharField(max_length=256,
        help_text='User-supplied dataset name.')
    description = models.TextField(blank=True,
        help_text='User-supplied dataset description.')
    # related_uploads =  models.ToMany(RelatedUpload, null=True)
    # data_uploads =  models.ToMany(DataUpload, null=True)
    initial_upload = models.ForeignKey('DataUpload', null=True, blank=True, related_name='initial_upload_for',
        help_text='The data upload used to create this dataset, if any was used.')
    columns = JSONField(null=True, default=None,
        help_text='A list of names for this dataset\'s columns.')
    typed_columns = JSONField(null=True, default=None,
        help_text='A list of boolean values corresponding to each column in the dataset. If true that column will be indexed in its own typed column.')
    column_types = JSONField(null=True, default=None,
        help_text='A list of types corresponding to the datasets\'s columns. May be inferred or user-specified')
    typed_column_names = JSONField(null=True, default=None,
        help_text='A list of column names used to store typed data on the backend. Each column will have a corresponding column name or None.')
    sample_data = JSONField(null=True, default=None,
        help_text='Example data rows from the dataset.')
    row_count = models.IntegerField(null=True, blank=True,
        help_text='The number of rows in this dataset. Null if no data has been added/imported.')
    current_task = models.ForeignKey(TaskStatus, blank=True, null=True,
        help_text='The currently executed or last finished task related to this dataset.') 
    creation_date = models.DateTimeField(null=True,
        help_text='The date this dataset was initially created.')
    creator = models.ForeignKey(User, related_name='datasets',
        help_text='The user who created this dataset.')
    categories = models.ManyToManyField(Category, related_name='datasets', blank=True, null=True,
        help_text='Categories containing this Dataset.')
    last_modified = models.DateTimeField(null=True, blank=True, default=None,
        help_text='When, if ever, was this dataset last modified via the API?')
    last_modification = models.TextField(null=True, blank=True, default=None,
        help_text='Description of the last modification made to this Dataset.')
    last_modified_by = models.ForeignKey(User, null=True, blank=True,
        help_text='The user, if any, who last modified this dataset.')
    locked = models.BooleanField(default=False,
        help_text='Is this table locked for writing?')
    locked_at = models.DateTimeField(null=True, default=None,
        help_text='Time this dataset was last locked.')

    class Meta:
        app_label = 'panda'
        ordering = ['-creation_date']

    def __unicode__(self):
        return self.name

    def save(self, *args, **kwargs):
        """
        Save the date of creation.
        """
        if not self.creation_date:
            self.creation_date = datetime.utcnow()

        super(Dataset, self).save(*args, **kwargs)

    def _generate_typed_column_names(self):
        """
        Generate Solr names for typed columns, de-duplicating as necessary.
        """
        self.typed_column_names = []

        for i, c in enumerate(self.columns):
            if not self.typed_columns[i]:
                self.typed_column_names.append(None)
                continue

            name = 'column_%s_%s' % (self.column_types[i], self.columns[i])

            # Deduplicate within dataset
            if name in self.typed_column_names:
                i = 2
                test_name = '%s%i' % (name, i)

                while test_name in self.typed_column_names:
                    i += 1
                    test_name = '%s%i' % (name, i)

                name = test_name

            self.typed_column_names.append(name)

    def lock(self):
        """
        Obtain an editing lock on this dataset.
        """
        # Ensure latest state has come over from the database
        before_lock = self.__class__.objects.get(pk=self.pk)
        self.locked = before_lock.locked
        self.locked_at = before_lock.locked_at

        if self.locked:
            # Already locked
            raise DatasetLockedError('This dataset is currently locked by another process.')

        new_locked_at = datetime.now()

        self.locked = True
        self.locked_at = new_locked_at

        self.save()

        # Refresh from database
        after_lock = Dataset.objects.get(id=self.id)
        self.locked = after_lock.locked
        self.locked_at = after_lock.locked_at

        if self.locked_at != new_locked_at:
            # Somebody else got the lock
            raise DatasetLockedError('This dataset is currently locked by another process.')

    def unlock(self):
        """
        Unlock this dataset so it can be edited.
        """
        self.locked = False
        self.lock_id = None

        self.save()

    def update_full_text(self, commit=True):
        """
        Update the full-text search metadata for this dataset stored in Solr.
        """
        category_ids = []

        full_text_data = [
            self.name,
            self.description,
            '%s %s' % (self.creator.first_name, self.creator.last_name),
            self.creator.email
        ]

        for category in self.categories.all():
            category_ids.append(category.id)
            full_text_data.append(category.name)

        if not category_ids:
            category_ids.append(settings.PANDA_UNCATEGORIZED_ID)
            full_text_data.append(settings.PANDA_UNCATEGORIZED_NAME)

        for data_upload in self.data_uploads.all():
            full_text_data.append(data_upload.original_filename)

        for related_upload in self.related_uploads.all():
            full_text_data.append(related_upload.original_filename)

        if self.columns is not None:
            full_text_data.extend(self.columns)

        full_text = '\n'.join(full_text_data)

        solr.add(settings.SOLR_DATASETS_CORE, [{
            'slug': self.slug,
            'creation_date': self.creation_date.isoformat() + 'Z',
            'categories': category_ids,
            'full_text': full_text
        }], commit=commit)

    def delete(self, *args, **kwargs):
        """
        Purge data from Solr when a dataset is deleted.
        """
        # Cancel import if necessary 
        if self.current_task and self.current_task.end is None: 
            async_result = AbortableAsyncResult(self.current_task.id)
            async_result.abort()

        super(Dataset, self).delete(*args, **kwargs)

    def import_data(self, user, upload, external_id_field_index=None, typed_columns=[]):
        """
        Import data into this ``Dataset`` from a given ``DataUpload``.
        """
        self.lock()

        try:
            if upload.imported:
                raise DataImportError('This file has already been imported.')

            task_type = get_import_task_type_for_upload(upload)

            if not task_type:
                # This is normally caught on the client.
                raise DataImportError('This file type is not supported for data import.')
            
            if self.columns:
                # This is normally caught on the client.
                if upload.columns != self.columns:
                    raise DataImportError('The columns in this file do not match those in the dataset.')
            else:
                self.columns = upload.columns

            if self.column_types is None:
                self.column_types = upload.guessed_types

            if typed_columns:
                self.typed_columns = typed_columns
            elif self.typed_columns is None:
                self.typed_columns = [False for c in self.columns]

            self._generate_typed_column_names()

            if self.typed_column_names is None:
                self.typed_column_names = [None for c in self.columns]

            if self.sample_data is None:
                self.sample_data = upload.sample_data

            # If this is the first import and the API hasn't been used, save that information
            if self.initial_upload is None and self.row_count is None:
                self.initial_upload = upload

            self.current_task = TaskStatus.objects.create(task_name=task_type.name, creator=user)
            self.save()

            task_type.apply_async(
                args=[self.slug, upload.id],
                kwargs={ 'external_id_field_index': external_id_field_index },
                task_id=self.current_task.id
            )
        except:
            self.unlock()
            raise

    def reindex_data(self, user, external_id_field_index=None, typed_columns=[]):
        """
        Reindex the data currently stored for this ``Dataset``.
        """
        self.lock()

        try:
            if typed_columns:
                self.typed_columns = typed_columns
            elif self.typed_columns is None:
                self.typed_columns = [False for c in self.columns]

            self._generate_typed_column_names()

            self.current_task = TaskStatus.objects.create(task_name='panda.tasks.reindex', creator=user)

            self.save()

            ReindexTask.apply_async(
                args=[self.slug],
                kwargs={ 'external_id_field_index': external_id_field_index },
                task_id=self.current_task.id
            )
        except:
            self.unlock()
            raise

    def export_data(self, user, filename=None):
        """
        Execute the data export task for this ``Dataset``.
        """
        self.lock()

        try:
            task_type = ExportCSVTask

            self.current_task = TaskStatus.objects.create(task_name=task_type.name, creator=user)
            self.save()

            task_type.apply_async(
                args=[self.slug],
                kwargs={ 'filename': filename },
                task_id=self.current_task.id
            )
        except:
            self.unlock()
            raise

    def get_row(self, external_id):
        """
        Fetch a row from this dataset.
        """
        response = solr.query(settings.SOLR_DATA_CORE, 'dataset_slug:%s AND external_id:%s' % (self.slug, external_id), limit=1)

        if len(response['response']['docs']) < 1:
            return None

        return response['response']['docs'][0]

    def add_row(self, user, data, external_id=None):
        """
        Add (or overwrite) a row to this dataset.
        """
        solr_row = utils.solr.make_data_row(self, data, external_id=external_id)

        solr.add(settings.SOLR_DATA_CORE, [solr_row], commit=True)

        if not self.sample_data:
            self.sample_data = []
        
        if len(self.sample_data) < 5:
            self.sample_data.append(data)

        old_row_count = self.row_count
        self.row_count = self._count_rows()
        added = self.row_count - (old_row_count or 0)
        self.last_modified = datetime.utcnow()
        self.last_modified_by = user
        self.last_modification = '1 row %s' % ('added' if added else 'updated')
        self.save()

        return solr_row

    def add_many_rows(self, user, data):
        """
        Shortcut for adding rows in bulk. 

        ``data`` must be an array of tuples in the format (data_array, external_id)
        """
        solr_rows = [utils.solr.make_data_row(self, d[0], external_id=d[1]) for d in data]

        solr.add(settings.SOLR_DATA_CORE, solr_rows, commit=True)

        if not self.sample_data:
            self.sample_data = []
        
        if len(self.sample_data) < 5:
            needed = 5 - len(self.sample_data)
            self.sample_data.extend([d[0] for d in data[:needed]])

        old_row_count = self.row_count
        self.row_count = self._count_rows()
        added = self.row_count - (old_row_count or 0)
        updated = len(data) - added
        self.last_modified = datetime.utcnow()
        self.last_modified_by = user

        if added and updated: 
            self.last_modification = '%i rows added and %i updated' % (added, updated)
        elif added:
            self.last_modification = '%i rows added' % added
        else:
            self.last_modification = '%i rows updated' % updated

        self.save()

        return solr_rows
        
    def delete_row(self, user, external_id):
        """
        Delete a row in this dataset.
        """
        solr.delete(settings.SOLR_DATA_CORE, 'dataset_slug:%s AND external_id:%s' % (self.slug, external_id), commit=True)
    
        self.row_count = self._count_rows()
        self.last_modified = datetime.utcnow()
        self.last_modified_by = user
        self.last_modification = '1 row deleted'
        self.save()

    def delete_all_rows(self, user,):
        """
        Delete all rows in this dataset.
        """
        solr.delete(settings.SOLR_DATA_CORE, 'dataset_slug:%s' % self.slug, commit=True)

        old_row_count = self.row_count
        self.row_count = 0
        self.last_modified = datetime.utcnow()
        self.last_modification = 'All %i rows deleted' % old_row_count
        self.save()

    def _count_rows(self):
        """
        Count the number of rows currently stored in Solr for this Dataset.
        Useful for sanity checks.
        """
        return solr.query(settings.SOLR_DATA_CORE, 'dataset_slug:%s' % self.slug)['response']['numFound']

@receiver(models.signals.post_delete, sender=Dataset)
def on_dataset_delete(sender, **kwargs):
    """
    When a Dataset is deleted, purge its data and metadata from Solr.
    """
    dataset = kwargs['instance']
    PurgeDataTask.apply_async(args=[dataset.slug])
    solr.delete(settings.SOLR_DATASETS_CORE, 'slug:%s' % dataset.slug)

