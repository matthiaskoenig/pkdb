import json

import os
import sys

import requests
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient, RequestsClient

from pkdb_app.data_management.setup_database import setup_database
from pkdb_app.data_management.upload_studies import upload_study_from_dir, read_reference_json, \
    upload_reference_json, upload_files

from pkdb_app.interventions.models import Substance
from pkdb_app.studies.models import Study
from pkdb_app.subjects.models import DataFile
from pkdb_app.users.models import User

BASEPATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../")
)
sys.path.append(BASEPATH)


class AuthenticationAPITestCase(APITestCase):
    def setUp(self):
        self.client = APIClient()
        self.api = reverse('user-list')
        self.password = "test"
    def test_api_token_auth(self):

        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})
        assert json.loads(response.content) == {"non_field_errors":["Unable to log in with provided credentials."]} , json.loads(response.content)


    def test_create_superuser(self):
        User.objects.create_superuser(username="admin", password=self.password, email="")
        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})

        assert response.status_code == 200, response.status_code
        assert "token" in json.loads(response.content) ,json.loads(response.content)


class UploadStudy(APITestCase):

    def setUp(self):
        self.client =  APIClient()
        self.password = "test"
        User.objects.create_superuser(username="admin", password=self.password, email="")
        response = self.client.post("/api-token-auth/", data={"username": "admin", "password": self.password})
        self.token = json.loads(response.content)["token"]
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token)
        self.header = {'Authorization': f'token {self.token}','Content-type': 'application/json'}
        self.api_url="/api/v1"


    def test_setup_database(self):
        setup_database(api_url=self.api_url, auth_headers=self.header, client=self.client)
        assert hasattr(Substance.objects.first(),"name")


    def test_upload_reference_json(self):
        study_name = "test_study"
        study_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), study_name)
        reference_path = os.path.join(study_dir, "reference.json")
        reference_pdf = os.path.join(study_dir, f"{study_name}.pdf")

        reference_dict = {"reference_path": reference_path, "pdf": reference_pdf}
        json_reference = read_reference_json(reference_dict)
        success = upload_reference_json(json_reference, api_url=self.api_url, auth_headers=self.header, client=self.client)
        assert success

    def test_upload_files(self):
        study_name = "test_study"
        study_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), study_name)
        upload_files(file_path=study_dir, api_url=self.api_url, auth_headers=self.header, client=self.client)
        assert hasattr(DataFile.objects.first(),"file"), DataFile.objects.first()

    def test_upload_study_from_dir(self):
        study_test_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)),"test_study")
        setup_database(api_url=self.api_url, auth_headers=self.header, client=self.client)
        upload_study_from_dir(study_dir=study_test_dir, auth_headers=self.header, api_url=self.api_url, client=self.client)
        assert  Study.objects.filter(name="test_study").count() == 1 ,Study.objects.filter(name="test_study")
        test_study = Study.objects.get(name="test_study")
        assert test_study.


