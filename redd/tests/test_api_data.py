#!/usr/bin/env python

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.utils import simplejson as json

from redd.models import Dataset
from redd.tests import utils

class TestAPIData(TestCase):
    def setUp(self):
        settings.CELERY_ALWAYS_EAGER = True

        self.solr = utils.get_test_solr() 

        self.upload = utils.get_test_upload()
        self.dataset = utils.get_test_dataset(self.upload)

        self.client = Client()
    
    def test_get(self):
        self.dataset.import_data()

        utils.wait()

        response = self.client.get('/api/1.0/data/')
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)

        list_result = body['objects'][0]

        response = self.client.get('/api/1.0/data/%s/' % list_result['id'])
        self.assertEqual(response.status_code, 200)
        get_result = json.loads(response.content)

        self.assertEqual(list_result, get_result)

    def test_list(self):
        self.dataset.import_data()

        utils.wait()

        response = self.client.get('/api/1.0/data/')

        self.assertEqual(response.status_code, 200)

        body = json.loads(response.content)

        self.assertEqual(body['meta']['total_count'], 4)
        self.assertEqual(body['objects'][0]['dataset'], '/api/1.0/dataset/%i/' % self.dataset.id)
        self.assertIn('data', body['objects'][0])
        self.assertIn('id', body['objects'][0])
        self.assertIn('resource_uri', body['objects'][0])
        self.assertIn('row', body['objects'][0])

    def test_create_denied(self):
        new_data = {
            'dataset': '/api/1.0/dataset/%i/' % self.dataset.id,
            'data': ['1', '2', '3']
        }

        response = self.client.post('/api/1.0/data/', content_type='application/json', data=json.dumps(new_data))

        self.assertEqual(response.status_code, 405)

    def test_search(self):
        pass

