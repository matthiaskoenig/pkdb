
from django.test import RequestFactory
from pkdb_app.categorials.models import CharacteristicType
from pkdb_app.categorials.serializers import CharacteristicTypeSerializer
from pkdb_app.users.models import User
from rest_framework.test import APITestCase


class AuthenticationAPITestCase(APITestCase):
    def setUp(self):
        self.password = "pkdb"
        self.factory = RequestFactory()
        self.request = self.factory.get('/api/v1/')
        self.user = User.objects.create_superuser(username="admin", password=self.password, email="")

        self.request.user = self.user



        self.intervention_attributes = {


        }
        self.characteristica_types = [
        {
            "key": "sex",
            "category": "demographics",
            "dtype": "categorial",
            "choices": [
                "M",
                "F",
                "Mixed",
                "NaN"
            ],
            "units": [],
            "url_slug": "sex"
        },
        {
            "key": "healthy",
            "category": "patient status",
            "dtype": "boolean",
            "choices": [
                "Y",
                "N",
                "Mixed",
                "NaN"
            ],
            "units": [],
            "url_slug": "healthy"
        },
        {
            "key": "age",
            "category": "demographics",
            "dtype": "numeric",
            "choices": None,
            "units": [
                "yr"
            ],
            "url_slug": "age"
        }
        ]




    def test_characteristic_type_serializer(self):
        for instance in self.characteristica_types:
            s_instance = CharacteristicTypeSerializer(data = instance, context={'request':self.request})

            assert s_instance.is_valid()
            s_instance.create(s_instance.validated_data)
        assert len(CharacteristicType.objects.all()) == 3, CharacteristicType.objects.all()




