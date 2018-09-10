import json

import requests
from django.test import TestCase, Client
import os
import sys
from django.urls import reverse

from pkdb_app.users.models import User

BASEPATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../")
)
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import get_token,get_header, setup_database



class AuthenticationAPITestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.api = reverse('user-list')
        self.password = "test"
    def test_api_token_auth(self):

        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})

        #response = self.browser(f"{self.api_base}/api-token-auth/", data={"username": "admin", "password": self.password})

        assert json.loads(response.content) == {"non_field_errors":["Unable to log in with provided credentials."]} , json.loads(response.content)


    def test_create_superuser(self):
        User.objects.create_superuser(username="admin", password=self.password, email="")
        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})


        assert response.status_code == 200, response.status_code
        assert "token" in json.loads(response.content) ,json.loads(response.content)


class UploadStudy(TestCase):
    def setUp(self):
        self.client = Client()
        self.password = "test"
        User.objects.create_superuser(username="admin", password=self.password, email="")
        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})
        self.token = json.loads(response.content)["token"]










