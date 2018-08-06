from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from collections import OrderedDict
import pandas as pd
import string
from pkdb_app.categoricals import FORMAT_MAPPING


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

    @staticmethod
    def generic_parser(data,key):

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


                    if key == "name" and n > 1:
                        ialpha = iter(string.ascii_uppercase)
                        values = [f"{value}_{next(ialpha)}" for value in values]

                    data_n[key] = values

            return data_n

        cleaned = []
        for raw_single in raw:
            raw_single = {k: v for k, v in raw_single.items() if v is not None}
            cleaned += pd.DataFrame(list_chara(raw_single)).to_dict('records')
        data[key] = cleaned
        return data


    @staticmethod
    def mapping_parser(mapping,table):

        resulting_keys = []
        for key, value in mapping.items():
            if "==" in value:
                values = value.split("==")
                if not values[0].strip() == "col":
                    raise Exception(f"Value provided does not match pattern 'col==<file_mapping>', with key:{key} and  value:{values}")
                resulting_keys.append(values[1].strip())


            else:
                table[key] = value
                resulting_keys.append(key)

        #resulting_data = table[resulting_keys].to_dict("records")
        #return resulting_data
        return table[resulting_keys]

    @staticmethod
    def split_to_map(data):
        splitted_data = {}
        for key,value in data.items():
            if "==" in value:
                splitted_data[f"{key}_map"] = data.get(key)
            else:
                splitted_data[key] = data.get(key)
        return splitted_data



    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])

