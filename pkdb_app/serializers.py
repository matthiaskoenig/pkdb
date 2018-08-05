from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from collections import OrderedDict
import pandas as pd



class BaseSerializer(serializers.ModelSerializer):
    """
    This Serializer is overwriting a the is_valid method. If sid allready exisits. It adds a instance to the class.
    This triggers the update method instead of the create method of the serializer.
    """

    def is_valid(self, raise_exception=False):
        if "sid" in self.initial_data.keys():
            sid = self.initial_data.get("sid")
            try:
                # Try to get the object in question
                obj = self.Meta.model.objects.get(sid = sid)
            except (ObjectDoesNotExist, MultipleObjectsReturned):
                # Except not finding the object or the data being ambiguous
                # for defining it. Then validate the data as usual
                return super().is_valid(raise_exception)
            else:
                # If the object is found add it to the serializer. Then
                # validate the data as usual
                self.instance = obj
                return super().is_valid(raise_exception)
        else:
            # If the Serializer was instantiated with just an object, and no
            # data={something} proceed as usual
            return super().is_valid(raise_exception)



    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])

class ParserSerializer(serializers.ModelSerializer):

    def generic_parser(self,data,key):

        raw = data.get(key,[])

        def number_raw(data):
            for key, value in data.items():
                try:
                    values = value.split('||')
                except AttributeError:
                    values = [value]

                if len(values) > 1:
                    return len(values)
            return 1


        def list_chara(data):
            n = number_raw(data)
            data_n = {}
            for key, value in data.items():
                # if type(value) == str:
                try:
                    values = value.split('||')
                    values = list(map(str.strip, values))
                except AttributeError:
                    values = [value]
                if len(values) == 1:
                    values = values * n
                data_n[key] = values
            return data_n

        cleaned = []
        for raw_single in raw:
            raw_single = {k: v for k, v in raw_single.items() if v is not None}
            #if any("||" in value for key, value in raw_single.items()):
            print(list_chara(raw_single))
            cleaned += pd.DataFrame(list_chara(raw_single)).to_dict('records')
        data[key] = cleaned
        return data

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])

