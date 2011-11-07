#!/usr/bin/env python

from datetime import datetime

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson as json

from redd.models import TaskStatus
from redd.tests import utils

class TestAPITaskStatus(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True
        
        self.solr = utils.get_test_solr()
        
        self.upload = utils.get_test_upload()
        self.dataset = utils.get_test_dataset(self.upload)

        self.dataset.import_data()

        utils.wait()

        self.client = Client()

    def test_get(self):
        task = TaskStatus.objects.get(id=self.dataset.current_task.id)

        response = self.client.get('/api/1.0/task/%i/' % task.id) 

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertEqual(body['status'], task.status)
        self.assertEqual(body['task_name'], task.task_name)
        start = datetime.strptime(body['start'], "%Y-%m-%dT%H:%M:%S.%f" )
        self.assertEqual(start, task.start)
        end = datetime.strptime(body['end'], "%Y-%m-%dT%H:%M:%S.%f" )
        self.assertEqual(end, task.end)
        self.assertEqual(body['message'], task.message)
        self.assertEqual(body['traceback'], None)

    def test_list(self):
        response = self.client.get('/api/1.0/task/', data={ 'limit': 5 })

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertEqual(len(body['objects']), 1)
        self.assertEqual(body['meta']['total_count'], 1)
        self.assertEqual(body['meta']['limit'], 5)
        self.assertEqual(body['meta']['offset'], 0)
        self.assertEqual(body['meta']['next'], None)
        self.assertEqual(body['meta']['previous'], None)

    def test_create_denied(self):
        new_task = {
            'task_name': 'redd.tasks.ImportDatasetTask'
        }

        response = self.client.post('/api/1.0/task/', content_type='application/json', data=json.dumps(new_task))

        self.assertEqual(response.status_code, 405)

