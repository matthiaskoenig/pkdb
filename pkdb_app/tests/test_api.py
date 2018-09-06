from unittest import TestCase

import os
import sys
from selenium import webdriver
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities

import requests
from coreapi import Client
from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from rest_framework.reverse import reverse
import socket

from pkdb_app.users.models import User

BASEPATH = os.path.abspath(
    os.path.join(os.path.dirname(os.path.realpath(__file__)), "../../")
)
sys.path.append(BASEPATH)

from pkdb_app.data_management.fill_database import get_token,get_header, setup_database



class UserAPITestCase(StaticLiveServerTestCase):
    live_server_url = socket.gethostbyname(socket.gethostname())

    def setUp(self):
        self.browser = webdriver.Remote(
            command_executor="http://selenium:4444/wd/hub",
            desired_capabilities=DesiredCapabilities.CHROME
        )

    def test_api_token_auth(self):

        response = self.browser.post(f"{self.api_base}/api-token-auth/", data={"username": "admin", "password": "test"})
        assert response.json() == {"non_field_errors":["Unable to log in with provided credentials."]}

    def test_create_superuser(self):
        #os.system(f"docker-compose run --rm web ./manage.py createsuperuser2 "
        #          f"--username admin --password {self.password} --email Janekg89@hotmail.de --noinput")
        User.objects.create_superuser(username="admin", password="test", email="Janekg89@hotmail.de")

        response = self.browser.post(f"{self.api_base}/api-token-auth/", data={"username": "admin", "password": "test"})
        assert response.json() == {"non_field_errors":"hi"}, response.json()

    #def test_get_token(self):
    #    token = get_token(self.api_base)
    #    assert token is not None, f"no Token"





    #def test_can_get_user_list(self):
    #    """GET /user returns a list of users"""
    #    url = reverse("user-list")
    #    response = requests.get("http://web:8000"+url, headers=self.header)
    #    print(response)
    #
    #   assert response.status_code == 200, \
    #        "Expect 200 OK. got: {}".format(response.status_code)
