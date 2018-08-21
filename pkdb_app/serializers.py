import numpy as np
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from collections import OrderedDict
from rest_framework.settings import api_settings

from pkdb_app.interventions.models import Substance, InterventionSet, OutputSet, DataFile
from pkdb_app.studies.models import Reference
from pkdb_app.subjects.models import GroupSet, IndividualSet
from pkdb_app.users.models import User
from pkdb_app.utils import get_or_val_error

import traceback
import logging

ITEM_SEPARATOR = '||'
RELATED_SETS = {
    "groupset": GroupSet,
    "individualset": IndividualSet,
    "interventionset": InterventionSet,
    "outputset": OutputSet
}


class WrongKeySerializer(serializers.ModelSerializer):


    def replace_NA(self,dict):
        for key, value in dict.items():
            if isinstance(value,str):
                dict[key].replace("NA","nan")


    def validate_wrong_keys(self, data):
        serializer_fields = self.Meta.fields
        payload_keys = data.keys()
        for payload_key in payload_keys:
            if payload_key not in serializer_fields:
                msg = {payload_key: f"<{payload_key}> is a wrong key"}
                raise serializers.ValidationError(msg)

    # def to_internal_value(self, data):
    #    self.validate_wrong_keys(data)
    #    return super().to_internal_value(data)

    def validate(self, attrs):
        self.validate_wrong_keys(attrs)
        return super().validate(attrs)


class BaseSerializer(WrongKeySerializer):
    """
    This Serializer is overwriting a the is_valid method. If sid already exists. It adds a instance to the class.
    This triggers the update method instead of the create method of the serializer.
    """

    def is_valid(self, raise_exception=False):

        if "sid" in self.initial_data.keys():
            sid = self.initial_data.get("sid")
            try:
                # Try to get the object in question
                obj = self.Meta.model.objects.get(sid=sid)
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
        for name, model in RELATED_SETS.items():
            if related[name] is not None:
                 if getattr(study,name):
                    getattr(study,name).delete()
                 instance = model.objects.create(**related[name])
                 instance.save()
                 setattr(study, name, instance)

        for curator_data in related["curators"]:
            curator = get_or_val_error(User, username=curator_data)
            study.curators.add(curator)

        for substance_data in related["substances"]:

            substance = get_or_val_error(Substance, name=substance_data)
            study.substances.add(substance)

        if related["files"]:
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
    def split_entries_for_key(data, key):
        """ Splits entries in multiple if separators found.

        Gets the subset of data for the key, splits the entries in multiple
        and overwrites the data in the original data dict!

        :param data:
        :param key:
        :return:
        """

        def number_of_entries(entry):
            """ Splits the data to get number of entries. """

            n_values = []
            for field, value in entry.items():
                n = 1
                try:
                    values = value.split(ITEM_SEPARATOR)
                    n = len(values)
                except AttributeError:
                    pass

                n_values.append(n)

            # validation (either 1 or max length)
            n_set = set(n_values)
            if len(n_set) not in [1, 2]:
                serializers.ValidationError(
                    f"Fields have different length, check || separators",
                    entry,
                )

            return max(n_values)

        def split_entry(entry):
            """ Splits entry fields based on separator.

            :param entry:
            :return: list of entries
            """

            n = number_of_entries(entry)
            if n == 1:
                return [entry]

            # create entries by splitting separators
            entries = [dict() for k in range(n)]

            for field in entry.keys():
                value = entry[field]
                try:
                    values = value.split(ITEM_SEPARATOR)
                except AttributeError:
                    values = [value]
                for k, value in enumerate(values):
                    if isinstance(value, str):
                        values[k] = value.strip()


                # --- validation ---
                # names must be split in a split entry
                if field == "name" and len(values) != n:
                    raise serializers.ValidationError(f"names have to be splitted and not left as <{values}>. Otherwise UniqueConstrain is violated.")
                # check for old syntax
                for value in values:
                    if isinstance(value, str):
                        if "{{" in value or "}}" in value:
                            raise serializers.ValidationError(
                                f"Splitting via '{{ }}' syntax not allowed, use '||' in count.")
                # ------------------

                # extend entries
                if len(values) == 1:
                    values = values * n

                if len(values) is not n:
                    raise serializers.ValidationError(
                        ["Values do not have correct length",
                        field, values, entry]
                    )

                for k in range(n):
                    entries[k][field] = values[k]

            return entries

        # get data for key
        raw = data.get(key, [])  # outputs

        cleaned = []
        for entry in raw:  # output
            entries = split_entry(entry)
            cleaned.extend(entries)
            '''
            try:
                entries = split_entry(entry)
                cleaned.extend(entries)
            except Exception as err:
                raise serializers.ValidationError([
                    f"ValueError in splitting entries",
                    entry,
                    traceback.format_exc()]) from err
            '''

        # overwrite data
        data[key] = cleaned

        return data

    @staticmethod
    def mapping_parser(mapping, table):

        resulting_keys = []
        for key, value in mapping.items():
            if "==" in value:
                values = value.split("==")
                if not values[0].strip() == "col":
                    raise serializers.ValidationError(f"Value provided does not match pattern 'col==<file_mapping>', with key:{key} and  value:{values}")
                resulting_keys.append(values[1].strip())

            else:
                table[key] = value
                resulting_keys.append(key)

        return table[resulting_keys]

    @staticmethod
    def split_to_map(data):
        splitted_data = {}
        for key, value in data.items():
            try:
                if "==" in value:
                    splitted_data[f"{key}_map"] = data.get(key)
                else:
                    splitted_data[key] = data.get(key)
            except:
                splitted_data[key] = data.get(key)

        return splitted_data

    @staticmethod
    def drop_blank(data):
        return {k: v for k, v in data.items() if v is not None}

    @staticmethod
    def drop_empty(data):
        dropped_empty = {}
        for k, v in data.items():
            if isinstance(v, str):
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
