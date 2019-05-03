from unittest import TestCase

from pkdb_app.categorials.serializers import CharacteristicTypeSerializer


class AuthenticationAPITestCase(TestCase):
    def setUp(self):
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




    def CharacteristicTypeSerializerTest(self):
        s_instance = CharacteristicTypeSerializer(data = self.characteristica_types[0])
        assert s_instance.is_valid()



