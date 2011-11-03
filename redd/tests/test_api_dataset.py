#!/usr/bin/env python

from time import sleep

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson as json

from redd.models import Dataset, TaskStatus
from redd.tests import utils

class TestAPIDataset(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True

        self.solr = utils.get_test_solr() 

        self.upload = utils.get_test_upload()
        self.dataset = utils.get_test_dataset(self.upload)

        self.client = Client()

    def test_get(self):
        # Import so that there will be a task object
        self.dataset.import_data()

        sleep(utils.SLEEP_DELAY)

        # Refetch dataset so that attributes will be updated
        self.dataset = Dataset.objects.get(id=self.dataset.id)

        response = self.client.get('/api/1.0/dataset/%i/' % self.dataset.id)

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertEqual(body['name'], self.dataset.name)
        self.assertEqual(body['description'], self.dataset.description)
        self.assertEqual(body['row_count'], self.dataset.row_count)
        self.assertEqual(body['sample_data'], self.dataset.sample_data)
        self.assertEqual(body['schema'], self.dataset.schema)

        task_response = self.client.get('/api/1.0/task/%i/' % self.dataset.current_task.id)

        self.assertEqual(task_response.status_code, 200)

        self.assertEqual(body['current_task'], json.loads(task_response.content))

        upload_response = self.client.get('/api/1.0/upload/%i/' % self.dataset.data_upload.id)

        self.assertEqual(upload_response.status_code, 200)

        self.assertEqual(body['data_upload'], json.loads(upload_response.content))

    def test_list(self):
        response = self.client.get('/api/1.0/dataset/', data={ 'limit': 5 })

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertEqual(len(body['objects']), 1)
        self.assertEqual(body['meta']['total_count'], 1)
        self.assertEqual(body['meta']['limit'], 5)
        self.assertEqual(body['meta']['offset'], 0)
        self.assertEqual(body['meta']['next'], None)
        self.assertEqual(body['meta']['previous'], None)

    def test_create(self):
        new_dataset = {
            'name': 'New dataset!',
            'description': 'Its got yummy data!',
            'data_upload': '/api/1.0/upload/%i/' % self.upload.id
        }

        response = self.client.post('/api/1.0/dataset/', content_type='application/json', data=json.dumps(new_dataset))

        self.assertEqual(response.status_code, 201)

        # TODO -- verify content

    def test_import_data(self):
        response = self.client.get('/api/1.0/dataset/%i/import/' % self.dataset.id)

        sleep(utils.SLEEP_DELAY)

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertNotEqual(body['current_task'], None)
        self.assertEqual(body['current_task']['task_name'], 'redd.tasks.DatasetImportTask')
        
        # Refetch dataset so that attributes will be updated
        self.dataset = Dataset.objects.get(id=self.dataset.id)

        self.assertEqual(self.dataset.row_count, 4)
        self.assertNotEqual(self.dataset.schema, None)

        task = self.dataset.current_task

        self.assertNotEqual(task, None)
        self.assertEqual(task.status, 'SUCCESS')
        self.assertEqual(task.task_name, 'redd.tasks.DatasetImportTask')
        self.assertNotEqual(task.start, None)
        self.assertNotEqual(task.end, None)
        self.assertEqual(task.traceback, None)

        self.assertEqual(self.solr.query('Christopher').execute().result.numFound, 1)

    def test_search(self):
        # TODO
        pass

