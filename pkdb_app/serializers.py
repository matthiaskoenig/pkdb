import re
from lark import UnexpectedCharacters, Lark

from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from collections import OrderedDict
import pandas as pd
from rest_framework.settings import api_settings

from pkdb_app.interventions.models import Substance, InterventionSet, OutputSet, DataFile
from pkdb_app.studies.models import Reference
from pkdb_app.subjects.models import GroupSet, IndividualSet
from pkdb_app.users.models import User
from pkdb_app.utils import get_or_val_error


RELATED_SETS = {"groupset":GroupSet ,"individualset": IndividualSet,"interventionset":InterventionSet,"outputset":OutputSet}

class WrongKeySerializer(serializers.ModelSerializer):

    def validate_wrong_keys(self,data):
        serializer_fields = self.Meta.fields
        payload_keys = data.keys()
        for payload_key in payload_keys:
            if payload_key not in serializer_fields:
                msg = {payload_key:f"<{payload_key}> is a wrong key"}
                raise ValidationError(msg)

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)

class BaseSerializer(WrongKeySerializer):
    """
    This Serializer is overwriting a the is_valid method. If sid allready exisits. It adds a instance to the class.
    This triggers the update method instead of the create method of the serializer.
    """

    def is_valid(self, raise_exception=False):

        if "sid" in self.initial_data.keys():
            sid = self.initial_data.get("sid")
            self.context["study"] = sid
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






    @staticmethod
    def create_relations(study, related):
        for name,model in RELATED_SETS.items():
            if related[name] is not None:
                 instance = model.objects.create(**related[name])
                 instance.save()
                 setattr(study,name,instance)

        for curator_data in related["curators"]:
            curator = get_or_val_error(User, username=curator_data)
            study.curators.add(curator)

        for substance_data in related["substances"]:

            substance = get_or_val_error(Substance, name=substance_data)
            study.substances.add(substance)

        if related["files"] :
            print(related["files"])
            study.files.all().delete()
            for file_pk in related["files"]:
                study.files.add(file_pk)

        study.save()

        return study

    @staticmethod
    def pop_relations(validated_data):

        related_foreinkeys = RELATED_SETS.copy()
        related_foreinkeys["reference"] = Reference
        related_many2many = {"substances": Substance,"curators": User,"files": DataFile}
        related_foreinkeys_dict = {name:validated_data.pop(name, None) for name,_ in related_foreinkeys.items()}
        related_many2many_dict = {name:validated_data.pop(name, []) for name,_  in related_many2many.items()}
        related = {**related_foreinkeys_dict,**related_many2many_dict}
        return related


class ParserSerializer(WrongKeySerializer):

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

        def split_string_count(string,key):

            l = Lark('''start: WORD "{{" NUMBER "}}"
                    %import common.NUMBER
                    %import common.WORD

                   %ignore " "           // Disregard spaces in text
                ''')

            try:
                data = l.parse(string)
            # except UnexpectedCharacters as e:
            # msg = f"{string} is not maching pattern:\{{(.?[0-9]+)\}}"
            #    raise ValidationError(str(e))
            except UnexpectedCharacters:
                raise ValidationError({key:f"UnexpectedCharacters in {string}"})
            return data

        def list_chara(data):
            n = number_raw(data)
            data_n = {}

            for key, value in data.items():
                try:
                    values = value.split('||')
                    values = list(map(str.strip, values))

                except AttributeError:
                    values = [value]

                if (key == "name" and len(values) != n):
                    msg = {f"names have to be splitted and not left as <{values}>. Otherwise UniqueConstrain is violated."}
                    raise ValidationError({"name": msg})

                if len(values) == 1:
                    values = values * n

                else:
                    values_n = []
                    count_n = []
                    for value in values:
                        if "{{" in value:
                            splitted_data = split_string_count(value,key)
                            values_n.append(splitted_data.children[0].value)
                            count_n.append(splitted_data.children[1].value)
                        else:
                            values_n.append(value)
                            count_n.append(data.get("count", None))
                    values = values_n
                    data_n["count"] = count_n

                    # if key == "name" and n > 1:
                    #    ialpha = iter(string.ascii_uppercase)
                    #    values = [f"{value}_{next(ialpha)}" for value in values]

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
            try:
                if "==" in value:
                    splitted_data[f"{key}_map"] = data.get(key)
                else:
                    splitted_data[key] = data.get(key)
            except :
                    splitted_data[key] = data.get(key)

        return splitted_data

    @staticmethod
    def drop_blank(data):
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def drop_empty(data):
        dropped_empty = {}
        for k,v in data.items():
            if isinstance(v,str):
                if not v:
                    continue
            dropped_empty[k] = v
        #return {k:v for k, v in data.items() if (not v and isinstance(v, str))}
        return dropped_empty

    @staticmethod
    def strip(data):
        data_stripped = {}

        for k, v in data.items():
            if isinstance(v, str):# and not k=="name"):
                v = v.strip()
            data_stripped[k] = v

        return data_stripped

    def to_representation(self, instance):
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


