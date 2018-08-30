import copy
import pandas as pd
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from collections import OrderedDict
from rest_framework.settings import api_settings
from django.forms.models import model_to_dict
from pkdb_app.categoricals import FORMAT_MAPPING
from pkdb_app.interventions.models import  DataFile, Intervention
from pkdb_app.subjects.models import Group, Individual
from pkdb_app.utils import recursive_iter, set_keys

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


    def get_or_val_error(self, model, *args, **kwargs):
        """ Checks if object exists or raised ValidationError."""
        try:
            instance =  model.objects.get(*args, **kwargs)
        except model.DoesNotExist:
            instance = None
        if not instance:
            raise serializers.ValidationError({api_settings.NON_FIELD_ERRORS_KEY:"instance does not exist","detail":{**kwargs}})

        return instance

    # ----------------------------------
    #
    # ----------------------------------


    def to_internal_value(self, data):

        self.validate_wrong_keys(data)
        return super().to_internal_value(data)

    def validate(self, attrs):
        errors = super().validate(attrs)
        return errors


    def to_representation(self, instance):
        """
        display only keys, which are not None
        """
        rep = super().to_representation(instance)
        rep = OrderedDict([(key, rep[key]) for key in rep if rep[key] is not None])

        rep = OrderedDict([(key, rep[key]) for key in rep if not all([isinstance(rep[key],list), not rep[key]])])
        return rep


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

    def _retransform_map_list(self, data_list):
        unmap_list = []
        for item in data_list:
            if "_map" in item:
                item = item[:-4]
            else:
                item

            unmap_list.append(item)
        return unmap_list




    # ----------------------------------
    # helper for splitting
    # ----------------------------------

    def number_of_entries(self, entry):
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

    def split_entry(self, entry):
        """ Splits entry fields based on separator.

        :param entry:
        :return: list of entries
        """

        n = self.number_of_entries(entry)
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
                    if field == "interventions":
                        values[k] = [v.strip() for v in value.split(",")]


            # --- validation ---
            # names must be split in a split entry
            if field == "name" and len(values) != n:
                raise serializers.ValidationError(
                    f"names have to be splitted and not left as <{values}>. Otherwise UniqueConstrain  of name is violated.")


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
                #if field in ["count"]:
                #    entries[k][field] = int(values[k])
                #else:
                    entries[k][field] = values[k]

        return entries

    def split_entries(self, data):
        internal = []
        for entry in data.items():  # output
            entries = self.split_entry(entry)
            internal.extend(entries)
        return internal

    def split_entries_for_key(self, data, key):
        """ Splits entries in multiple if separators found.

        Gets the subset of data for the key, splits the entries in multiple
        and overwrites the data in the original data dict!

        :param data:
        :param key:
        :return:
        """
        # get data for key
        external = data.get(key, [])  # outputs
        data[key] = self.split_entries(external)

        return data

    # ----------------------------------
    # helper for export of entries from file
    # ----------------------------------
    def subset_pd(self,subset, df):
        values = subset.split("==")
        values = [v.strip() for v in values]
        if len(values) != 2:
            raise serializers.ValidationError(["field has wrong pattern 'col_value'=='cell_value'", subset])

        try:
            df[values[0]]
        except KeyError:
            raise serializers.ValidationError({"subset": f"source <{src.file.url}> has no column <{values[0]}>"})
        try:
            df = df.loc[df[values[0]] == values[1]]
        except TypeError:
            df = df.loc[df[values[0]] == float(values[1])]

        if len(df) == 0:
            raise serializers.ValidationError(
                [f"the cell value <{values[1]}>' is missing in column <{values[0]}>", subset])
        return df

    def df_from_file(self, source, format, subset):
        delimiter = FORMAT_MAPPING[format].delimiter
        src = DataFile.objects.get(pk=source)
        try:
            df = pd.read_csv(src.file, delimiter=delimiter, keep_default_na=False, na_values=['NA','NAN','na','nan',""])

        except Exception as e:
            raise serializers.ValidationError({"source": "cannot read csv", "detail": {"source": source,
                                                                                       "format": format,
                                                                                       "subset": subset}
                                               })
        if subset:
            if "&" in subset:
                for subset_single in [s.strip() for s in subset.split("&")]:
                    df = self.subset_pd(subset_single,df)
            else:
                df = self.subset_pd(subset,df)


        return df

    def entries_from_file(self, data):
        entries = []
        source = data.get("source")
        if source:
            template = copy.deepcopy(data)
            # get data
            template.pop("source")
            template.pop("figure",None)
            format = template.pop("format",None)
            if format is None:
                raise serializers.ValidationError({"format":"format is missing!"})
            subset = template.pop("subset", None)

            df = self.df_from_file(source, format, subset)

            for entry in df.itertuples():
                entry_dict = copy.deepcopy(template)
                recursive_entry_dict = list(recursive_iter(entry_dict))

                for keys, value in recursive_entry_dict:

                    if isinstance(value, str):
                        if "==" in value:
                            values = value.split("==")
                            values = [v.strip() for v in values]

                            if len(values) != 2 or values[0] != "col":
                                raise serializers.ValidationError(
                                    ["field has wrong pattern col=='col_value'", data])
                            try:
                                entry_value = getattr(entry, values[1])

                            except AttributeError:
                                raise serializers.ValidationError(
                                    [f"key <{values[1]}> is missing in file <{DataFile.objects.get(pk=source).file}> ", data])

                            set_keys(entry_dict, entry_value, *keys)

                entries.append(entry_dict)

        else:
            entries.append(data)

        return entries

    def array_from_file(self, data):
        """ Handle conversion of time course data.

        :param data:
        :return:
        """

        source = data.get("source")
        if source:
            array_dict = copy.deepcopy(data)
            # get data
            array_dict.pop("source")
            array_dict.pop("figure", None)
            format = array_dict.pop("format", None)
            if format is None:
                raise serializers.ValidationError({"format": "format is missing!"})
            subset = array_dict.pop("subset", None)
            # read dataframe subset
            df = self.df_from_file(source, format, subset)
            recursive_array_dict = list(recursive_iter(array_dict))

            for keys, value in recursive_array_dict:

                if isinstance(value, str):
                    if "==" in value:
                        values = value.split("==")
                        values = [v.strip() for v in values]

                        if len(values) != 2 or values[0] != "col":
                            raise serializers.ValidationError(
                                ["field has wrong pattern col=='col_value'", data])
                        try:
                            value_array = df[values[1]]

                        except KeyError:
                            raise serializers.ValidationError(
                                [f"key <{values[1]}> is missing in file <{DataFile.objects.get(pk=source).file}> ",
                                 data])

                        set_keys(array_dict, value_array.values.tolist(), *keys)

        else:
            raise serializers.ValidationError("For timecourse data a source file has to be provided.")


        return array_dict


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

    def to_internal_related_fields(self, data):
        study_sid = self.context['request'].path.split("/")[-2]

        if "group" in data:

            if data["group"]:
                try:
                    data["group"] = Group.objects.get(
                        Q(ex__groupset__study__sid=study_sid) & Q(name=data.get("group"))).pk
                except ObjectDoesNotExist:
                    msg = f'group: {data.get("group")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "individual" in data:

            if data["individual"]:

                study_individuals = Individual.objects.filter(ex__individualset__study__sid=study_sid)
                # for i in study_individuals:
                #    print(i.name)
                try:
                    study_individuals = Individual.objects.filter(ex__individualset__study__sid=study_sid)

                    data["individual"] = study_individuals.get(name=data.get("individual")).pk

                    # data["individual"] = Individual.objects.get(
                    #    Q(ex__individualset__study__sid=study_sid) & Q(name=data.get("individual"))).pk
                except ObjectDoesNotExist:
                    msg = f'individual: individual <{data.get("individual")}>  in study: <{study_sid}> does not exist'
                    raise serializers.ValidationError(msg)
                except MultipleObjectsReturned:
                    msg = f'individual: Multiple individuals with the name <{data.get("individual")}>  have been declared on study.'
                    raise serializers.ValidationError(msg)

        if "interventions" in data:

            if data["interventions"]:
                interventions = []
                for intervention in data["interventions"]:
                    try:
                        interventions.append(Intervention.objects.get(
                            Q(ex__interventionset__study__sid=study_sid) & Q(name=intervention)).pk)
                    except ObjectDoesNotExist:
                        msg = f'intervention: {intervention} in study: {study_sid} does not exist'
                        raise serializers.ValidationError(msg)
                data["interventions"] = interventions
        return data

    ##########################
    # helpers
    ##########################
    def _validate_disabled_data(self, data_dict,disabled):
        disabled = set(disabled)
        wrong_keys = disabled.intersection(set(data_dict.keys()))
        if wrong_keys:
            wrong_keys = self._retransform_map_list(wrong_keys)
            raise serializers.ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: f"The following keys are not allowed<{wrong_keys}>, because of indivdual or group",
                "detail": data_dict})

    def _validate_individual_characteristica(self, data_dict):
        disabled = ['sd', 'se', 'min', 'max', 'cv','mean','median']
        disabled += ['sd_map', 'se_map', 'min_map', 'max_map', 'cv_map','mean_map','median_map']

        self._validate_disabled_data(data_dict,disabled)

    def _validate_individual_output(self, data):
        if data.get("individual") or data.get("individual_map"):
            self._validate_individual_characteristica(data)

    def _validate_group_output(self, data):
        if data.get("group") or data.get("group_map"):
            disabled = ['value','value_map']
            self._validate_disabled_data(data, disabled)

    def validate_group_individual_output(self,output):
        is_group = output.get("group") or output.get("group_map")
        is_individual = output.get("individual") or output.get("individual_map")

        if (is_individual and is_group):
            raise serializers.ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: f"group and individual is not allowed"})
        elif not (is_individual or is_group):
            raise serializers.ValidationError({
                api_settings.NON_FIELD_ERRORS_KEY: f"group or individual is required"})


    @staticmethod
    def ex_mapping():
        return {"individual_exs":"individuals",
                "individual_ex": "individual",
                "intervention_exs": "interventions",
                "group_exs": "groups",
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

    def to_representation(self, instance):

        rep = super().to_representation(instance)

        if "group" in rep:
            if rep["group"]:
                if instance.group:
                    rep["group"] = instance.group.name
                if instance.group_map:
                     rep["group"] = instance.group_map

        if "interventions" in rep:
            rep["interventions"] = [intervention.name for intervention in instance.interventions.all()]

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
