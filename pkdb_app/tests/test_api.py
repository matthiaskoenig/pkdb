#from pkdb_app.data_management.fill_database import setup_database , API_URL

from django.test import TestCase

from pkdb_app.users.models import User


class ApiTestCase(TestCase):

    def setUp(self):
        self.this = 2

    def test_setup_database(self):
        self.assertEqual(self.this,2)


