from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from collections import OrderedDict

from pkdb_app.interventions.models import Substance, InterventionSet, OutputSet, DataFile, InterventionEx
from pkdb_app.studies.models import Reference
from pkdb_app.subjects.models import GroupSet, IndividualSet, GroupEx, IndividualEx
from pkdb_app.users.models import User
from pkdb_app.utils import get_or_val_error

ITEM_SEPARATOR = '||'
ITEM_MAPPER = '=='

class WrongKeyValidationSerializer(serializers.ModelSerializer):

    # ----------------------------------
    # helper
    # ----------------------------------
    def validate_wrong_keys(self, data):
        """
        validate that all keys correspond to a model field.
        """
        serializer_fields = self.Meta.fields
        payload_keys = data.keys()
        for payload_key in payload_keys:
            if payload_key not in serializer_fields:
                msg = {payload_key: f"<{payload_key}> is a wrong key"}
                raise serializers.ValidationError(msg)

    # ----------------------------------
    #
    # ----------------------------------

    def to_internal_value(self, data):
        self.validate_wrong_keys(data)
        return super().to_internal_value(data)


    def to_representation(self, instance):
        """
        display only keys, which are not None
        """
        result = super().to_representation(instance)
        return OrderedDict([(key, result[key]) for key in result if result[key] is not None])


class MappingSerializer(WrongKeyValidationSerializer):
    # ----------------------------------
    # helper
    # ----------------------------------
    @staticmethod
    def transform_map_fields(data):
        """
        replaces key with f"{key}_map" if value contains special syntax.( ==, || )
        """
        transformed_data = {}
        for key, value in data.items():
            if isinstance(value, str):
                if ITEM_MAPPER in value or ITEM_SEPARATOR in value:
                    transformed_data[f"{key}_map"] = data.get(key)
                else:
                    transformed_data[key] = data.get(key)
            else:
                transformed_data[key] = data.get(key)

        return transformed_data

    @staticmethod
    def retransform_map_fields(data):
        transformed_data = {}
        for k, v in data.items():
            if "_map" in k:
                k = k[:-4]
            if v is None:
                continue
            transformed_data[k] = v
        return transformed_data

    # ----------------------------------
    #
    # ----------------------------------

    def to_internal_value(self, data):


        data = self.transform_map_fields(data)
        return super().to_internal_value(data)

    def to_representation(self, instance):
        rep = self.retransform_map_fields(super().to_representation(instance))

        #url representation of file
        for file in ["source", "figure"]:
            if file in rep:
                current_site = f'http://{get_current_site(self.context["request"]).domain}'
                rep[file] = current_site + getattr(instance, file).file.url

        return rep


class ExSerializer(MappingSerializer):

    @staticmethod
    def ex_mapping():
        return {"individual_exs":"individuals",
                "individual_ex": "individual",
                "intervention_exs": "interventions",
                "group_exs": "groups",
                "group_ex": "group",
                "characteristica_ex": "characteristica",
                "parent_ex": "parent",
                "output_exs":"outputs",
                "timecourse_exs": "timecourses",}

    @classmethod
    def rev_ex_mapping(cls):
        return dict((v, k) for k, v in cls.ex_mapping().items())

    @classmethod
    def transform_ex_fields(cls,data):
        transform_data = {}
        for key, value in data.items():
            ex_key = cls.rev_ex_mapping().get(key)
            if ex_key:
                transform_data[ex_key] = value
            else:
                transform_data[key] = value
        return transform_data

    @classmethod
    def retransform_ex_fields(cls,data):
        transform_data = {}
        for key, value in data.items():
            ex_key = cls.ex_mapping().get(key)
            if ex_key:
                transform_data[ex_key] = value
            else:
                transform_data[key] = value
        return transform_data


    def to_internal_value(self, data):
        # change keys
        data = self.transform_ex_fields(data)
        return super().to_internal_value(data)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # change keys
        return self.retransform_ex_fields(representation)


class BaseOutputExSerializer(ExSerializer):

    def to_internal_value(self, data):

        data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        study_sid = self.context['request'].path.split("/")[-2]

        if "group_ex" in data:

            if data["group_ex"]:
                try:
                    data["group_ex"] = GroupEx.objects.get(
                        Q(groupset__study__sid=study_sid) & Q(name=data.get("group_ex"))).pk
                except ObjectDoesNotExist:
                    msg = f'group: {data.get("group_ex")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "individual_ex" in data:

            if data["individual_ex"]:
                try:
                    data["individual_ex"] = IndividualEx.objects.get(
                        Q(individualset__study__sid=study_sid) & Q(name=data.get("individual_ex"))).pk
                except ObjectDoesNotExist:
                    msg = f'individual_ex: individual <{data.get("individual_ex")}>  in study: <{study_sid}> does not exist'
                    raise serializers.ValidationError(msg)

        if "intervention_exs" in data:

            if data["intervention_exs"]:
                intervention_exs = []
                for intervention_ex in data["intervention_exs"]:
                    try:
                        intervention_exs.append(InterventionEx.objects.get(
                            Q(interventionset__study__sid=study_sid) & Q(name=intervention_ex)).pk)
                    except ObjectDoesNotExist:
                        msg = f'intervention_ex: {intervention_ex} in study: {study_sid} does not exist'
                        raise serializers.ValidationError(msg)
                data["intervention_exs"] = intervention_exs

        return super(WrongKeyValidationSerializer,self).to_internal_value(data)

    def to_representation(self, instance):

        rep = super().to_representation(instance)

        if "group" in rep:
            if rep["group"]:
                if instance.group_ex:
                    rep["group"] = instance.group_ex.name
                if instance.group_ex_map:
                     rep["group"] = instance.group_ex_map

        if "interventions" in rep:
            rep["interventions"] = [intervention_ex.name for intervention_ex in instance.intervention_exs.all()]

        return rep



class SidSerializer(WrongKeyValidationSerializer):
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

'''


class ParserValidationSerializer(WrongKeyValidationSerializer):

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
'''
