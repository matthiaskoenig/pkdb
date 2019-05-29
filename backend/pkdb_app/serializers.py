import copy
import numpy as np
import numbers
import pandas as pd
from django.contrib.sites.shortcuts import get_current_site
from django.db.models import Q
from rest_framework import serializers
from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from collections import OrderedDict, namedtuple
from rest_framework.settings import api_settings
from pkdb_app.interventions.models import DataFile, Intervention
from pkdb_app.normalization import get_se, get_sd, get_cv
from pkdb_app.subjects.models import Group, Individual
from pkdb_app.utils import recursive_iter, set_keys
ITEM_SEPARATOR = "||"
ITEM_MAPPER = "=="
NA_VALUES = ["na","NA","nan","NAN"]


# ---------------------------------------------------
# File formats
# ---------------------------------------------------
FileFormat = namedtuple("FileFormat", ["name", "delimiter"])

FORMAT_MAPPING = {"TSV": FileFormat("TSV", "\t"), "CSV": FileFormat("CSV", ",")}

# ---------------------------------------------------
#
# ---------------------------------------------------
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
                msg = {payload_key: f"`{payload_key}` is a wrong field, allowed fields are {serializer_fields}"}
                raise serializers.ValidationError(msg)

    def get_or_val_error(self, model, *args, **kwargs):
        """ Checks if object exists or raised ValidationError."""
        try:
            instance = model.objects.get(*args, **kwargs)
        except model.DoesNotExist:
            instance = None
        if not instance:
            raise serializers.ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: "instance does not exist",
                    "detail": {**kwargs},
                }
            )

        return instance

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

        rep = OrderedDict(
            [
                (key, rep[key])
                for key in rep
                if not all([isinstance(rep[key], list), not rep[key]])
            ]
        )
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
            #if v is None:
            #    continue
            transformed_data[k] = v
        return transformed_data

    def _retransform_map_list(self, data_list):
        unmap_list = []
        for item in data_list:
            if "_map" in item:
                item = item[:-4]

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

        if len(n_set) == 0:
            raise serializers.ValidationError(
                f"Empty characteristica are not allowed", entry
            )

        elif len(n_set) not in [1, 2]:
            raise serializers.ValidationError(
                f"Fields have different length, check || separators", entry
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

                    if values[k] in ["NA", "NAN", "na", "nan"]:
                        values[k] = None
                    elif values[k] == "[]":
                        values[k] = []




            # --- validation ---
            # names must be split in a split entry
            if field == "name" and len(values) != n:
                if len(values) == 1:
                    raise serializers.ValidationError(
                        f"names have to be splitted and not left as <{values}>. Otherwise UniqueConstrain  of name is violated."
                    )

            # check for old syntax
            for value in values:
                if isinstance(value, str):

                    if "{{" in value or "}}" in value:
                        raise serializers.ValidationError(
                            f"Splitting via '{{ }}' syntax not allowed, use '||' in count."
                        )
            # ------------------

            # extend entries
            if len(values) == 1:
                values = values * n

            if len(values) is not n:
                raise serializers.ValidationError(
                    ["Values do not have correct length", field, values, entry]
                )

            for k in range(n):
                # if field in ["count"]:
                #    entries[k][field] = int(values[k])
                # else:
                entries[k][field] = values[k]

        return entries

    # ----------------------------------
    # helper for export of entries from file
    # ----------------------------------
    def subset_pd(self, subset, df):
        values = subset.split(ITEM_MAPPER)
        values = [v.strip() for v in values]
        if len(values) != 2:
            raise serializers.ValidationError(
                ["field has wrong pattern 'col_value'=='cell_value'", subset]
            )

        try:
            df[values[0]]
        except KeyError:
            raise serializers.ValidationError(
                {"subset": f"your source file has no column <{values[0]}>"}
            )
        try:
            df = df.loc[df[values[0]] == values[1]]
        except TypeError:
            df = df.loc[df[values[0]] == float(values[1])]

        if len(df) == 0:
            raise serializers.ValidationError(
                [
                    f"the cell value <{values[1]}>' is missing in column <{values[0]}>",
                    subset,
                ]
            )
        return df



    def df_from_file(self, source, format, subset):
        delimiter = FORMAT_MAPPING[format].delimiter


        if isinstance(source,int):
            pass

        elif isinstance(source,str):
            if source.isnumeric():
                pass
            else:
                raise serializers.ValidationError(
                    {"source": f"<{str(source)}> is not existing", "detail": type(source)})
        else:
            raise serializers.ValidationError({"source":f"<{str(source)}> is not existing","detail":type(source)})
        src = DataFile.objects.get(pk=source)
        try:
            df = pd.read_csv(
                src.file,
                delimiter=delimiter,
                keep_default_na=False,
                na_values=["NA", "NAN", "na", "nan"],
            )

            df.columns = df.columns.str.strip()



        except Exception as e:
            raise serializers.ValidationError(
                {
                    "source": "cannot read csv",
                    "detail": {"source": source, "format": format, "subset": subset},
                }
            )
        if subset:
            if "&" in subset:
                for subset_single in [s.strip() for s in subset.split("&")]:
                    df = self.subset_pd(subset_single, df)
            else:
                df = self.subset_pd(subset, df)


        return df

    def make_entry(self, entry, template,data, source):
        entry_dict = copy.deepcopy(template)
        recursive_entry_dict = list(recursive_iter(entry_dict))


        for keys, value in recursive_entry_dict:
            if isinstance(value, str):
                if ITEM_MAPPER in value:
                    values = value.split(ITEM_MAPPER)
                    values = [v.strip() for v in values]

                    if len(values) != 2 or values[0] != "col":
                        raise serializers.ValidationError(
                            ["field has wrong pattern col=='col_value'", data]
                        )
                    try:
                        entry_value = getattr(entry, values[1])

                    except AttributeError:

                        raise serializers.ValidationError(

                            [
                                f"key <{values[1]}> is missing in file <{DataFile.objects.get(pk=source).file}> ",
                                data
                            ]
                        )
                    if isinstance(entry_value, numbers.Number):
                        if np.isnan(entry_value):
                            entry_value = None

                    if isinstance(entry_value, str):
                            entry_value = entry_value.strip()

                    if keys[0] == "interventions":
                        entry_value = [v.strip() for v in entry_value.split(",")]
                        set_keys(entry_dict, entry_value, *keys[:1])
                    else:
                        set_keys(entry_dict, entry_value, *keys)
        return entry_dict

    def entries_from_file(self, data):
        entries = []
        source = data.get("source")
        template = copy.deepcopy(data)
        # get data
        template.pop("source", None)
        template.pop("figure", None)
        format = template.pop("format", None)
        subset = template.pop("subset", None)

        if source:

            if format is None:
                raise serializers.ValidationError({"format": "format is missing!"})
            df = self.df_from_file(source, format, subset)



            template = copy.deepcopy(template)

            mappings = []
            for key, value in template.items():
                if isinstance(value,str):
                    if "==" in value:
                        mappings.append(value)

            if len(mappings) == 0:
                raise serializers.ValidationError({"source": "source is provided but the mapping operator == is not used in any field"})

            if data.get("groupby"):
                groupby = template.pop("groupby")
                if not isinstance(groupby, str):
                    raise serializers.ValidationError({"groupby": "groupby has to be a string"})
                groupby = [v.strip() for v in groupby.split("&")]
                for group_name, group_df in df.groupby(groupby):
                    for entry in group_df.itertuples():
                        entry_dict = self.make_entry(entry, template, data, source)
                        entries.append(entry_dict)
            else:
                for entry in df.itertuples():
                    entry_dict = self.make_entry(entry, template, data,source)
                    entries.append(entry_dict)

        else:
            entries.append(template)

        return entries


    def array_from_file(self, data):
        """ Handle conversion of time course data.

        :param data:
        :return:
        """

        source = data.get("source")
        if source:
            template = copy.deepcopy(data)
            # get data
            template.pop("source")
            template.pop("figure", None)
            format = template.pop("format", None)
            if format is None:
                raise serializers.ValidationError({"format": "format is missing!"})
            subset = template.pop("subset", None)
            # read dataframe subset
            df = self.df_from_file(source, format, subset)
            template = copy.deepcopy(template)

            if data.get("groupby"):
                groupby = template.pop("groupby")
                if not isinstance(groupby, str):
                    raise serializers.ValidationError({"groupby":"groupby has to be a string"})
                groupby = [v.strip() for v in groupby.split("&")]
                array_dicts = []
                try:
                    df[groupby]
                except KeyError:
                    raise serializers.ValidationError({"groupby":f"keys <{groupby}> used for groupby are missing in source file <{DataFile.objects.get(pk=source).file.name}>. To group by more then one column you can use the & operator e.g. 'col1 & col2 & col3'"})

                for group_name, group_df in df.groupby(groupby):
                    array_dict = copy.deepcopy(template)
                    self.dict_from_array(array_dict, group_df, data, source)

                    array_dicts.append(array_dict)


            else:
                array_dict = copy.deepcopy(template)
                self.dict_from_array(array_dict, df, data, source)
                array_dicts =[array_dict]

        else:
            raise serializers.ValidationError(
                "For timecourse data a source file has to be provided."
            )
        return array_dicts


    def dict_from_array(self,array_dict,df,data,source):
        recursive_array_dict = list(recursive_iter(array_dict))

        for keys, value in recursive_array_dict:
            if isinstance(value, str):
                if ITEM_MAPPER in value:
                    values = value.split(ITEM_MAPPER)
                    values = [v.strip() for v in values]

                    if len(values) != 2 or values[0] != "col":
                        raise serializers.ValidationError(
                            ["field has wrong pattern col=='col_value'", data]
                        )

                    try:
                        value_array = df[values[1]]



                    except KeyError:
                        raise serializers.ValidationError(
                            [
                                f"key <{values[1]}> is missing in file <{DataFile.objects.get(pk=source).file}> ",
                                data,
                            ]
                        )
                    #to get rid of dict

                    if keys[0] in ["individual", "group","interventions","substance","tissue","time_unit","unit","measurement_type"]:
                        unqiue_values = value_array.unique()
                        if len(unqiue_values) != 1:
                            raise serializers.ValidationError(
                                [
                                f"{values[1]} has to be a unique for one timecourse. <{unqiue_values}>",
                                data,
                                ])
                        if keys[0] == "interventions":
                            entry_value = [v.strip() for v in unqiue_values[0].split(",")]
                            set_keys(array_dict, entry_value, *keys[:1])
                            #array_dict[keys[0]] = [v.strip() for v in unqiue_values[0].split(",")]
                        else:
                            set_keys(array_dict, unqiue_values[0], *keys)


                    else:
                        set_keys(array_dict, value_array.values.tolist(), *keys)


    # ----------------------------------
    #
    # ----------------------------------

    def to_internal_value(self, data):
        data = self.transform_map_fields(data)
        return super().to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep = self.retransform_map_fields(rep)


        # url representation of file
        for file in ["source", "figure"]:
            if file in rep:
                current_site = (
                    f'http://{get_current_site(self.context["request"]).domain}'
                )
                rep[file] = current_site + getattr(instance, file).file.url
        return rep


class ExSerializer(MappingSerializer):


    def to_internal_related_fields(self, data):
        study_sid = self.context["request"].path.split("/")[-2]

        if "group" in data:

            if data["group"]:
                try:
                    data["group"] = Group.objects.get(
                        Q(ex__groupset__study__sid=study_sid)
                        & Q(name=data.get("group"))
                    ).pk
                except ObjectDoesNotExist:
                    msg = f'group: {data.get("group")} in study: {study_sid} does not exist'
                    raise serializers.ValidationError(msg)

        if "individual" in data:

            if data["individual"]:

                try:
                    study_individuals = Individual.objects.filter(
                        ex__individualset__study__sid=study_sid
                    )
                    data["individual"] = study_individuals.get(
                        name=data.get("individual")
                    ).pk

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
                        interventions.append(
                            Intervention.objects.get(
                                Q(ex__interventionset__study__sid=study_sid)
                                & Q(name=intervention, normed=True)
                            ).pk
                        )
                    except ObjectDoesNotExist:
                        msg = f"intervention: {intervention} in study: {study_sid} does not exist"
                        raise serializers.ValidationError(msg)
                data["interventions"] = interventions
        return data

    ##########################
    # helpers
    ##########################
    def _validate_figure(self,datafile):
        if datafile:
            allowed_endings = ['png','jpg','jpeg','tif','tiff']
            if not any([datafile.file.name.endswith(ending)for ending in allowed_endings]):
                raise serializers.ValidationError({"figure":f"{datafile.file.name} has to end with {allowed_endings}"})

    def _validate_requried_key(self,attrs, key):
        if key not in attrs:
            raise serializers.ValidationError({key: f"{key} is required"})

    def _validate_disabled_data(self, data_dict, disabled):
        disabled = set(disabled)
        wrong_keys = disabled.intersection(set(data_dict.keys()))
        if wrong_keys:
            wrong_keys = self._retransform_map_list(wrong_keys)
            raise serializers.ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: f"The following keys are not allowed {wrong_keys} due to restricted keys on indivdual or group.",
                    "detail": data_dict,
                }
            )

    def _validate_individual_characteristica(self, data_dict):
        disabled = ["sd", "se", "min", "max", "cv", "mean", "median"]
        disabled += [
            "sd_map",
            "se_map",
            "min_map",
            "max_map",
            "cv_map",
            "mean_map",
            "median_map",
        ]

        self._validate_disabled_data(data_dict, disabled)

    def _validate_individual_output(self, data):
        if data.get("individual") or data.get("individual_map"):
            self._validate_individual_characteristica(data)

    def _validate_group_output(self, data):
        if data.get("group") or data.get("group_map"):
            disabled = ["value", "value_map"]
            self._validate_disabled_data(data, disabled)

    def validate_group_individual_output(self, output):
        is_group = output.get("group") or output.get("group_map")
        is_individual = output.get("individual") or output.get("individual_map")

        if is_individual and is_group:
            raise serializers.ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: f"Either group or individual allowed on output, remove group from output. "
                    f"The group of an individual is set on the individualset"
                }
            )
        elif not (is_individual or is_group):
            raise serializers.ValidationError(
                {
                    api_settings.NON_FIELD_ERRORS_KEY: f"group or individual is required on output"
                }
            )

    def _key_is(self, data, key):
        return data.get(key) or data.get(f"{key}_map")

    def _is_required(self, data, key):
        is_data = self._key_is(data, key)
        if not is_data:
            raise serializers.ValidationError(
                {key: f"{key} is required", "detail": data}
            )

    def _validate_time_unit(self, data):
        time = data.get("time")
        if time:
            self._is_required(data, "time_unit")

    def _to_internal_se(self, data):
        input_names = ["count", "sd", "mean", "cv"]
        se_input = {name: data.get(name) for name in input_names}
        return get_se(**se_input)

    def _to_internal_sd(self, data):
        input_names = ["count", "se", "mean", "cv"]
        sd_input = {name: data.get(name) for name in input_names}
        return get_sd(**sd_input)

    def _to_internal_cv(self, data):
        input_names = ["count", "sd", "mean", "se"]
        cv_input = {name: data.get(name) for name in input_names}
        return get_cv(**cv_input)

    def _add_statistic_values(self, data, count):

        se = data.get("se")
        sd = data.get("sd")
        cv = data.get("cv")
        mean = data.get("mean")
        temp_data = {"se": se, "sd": sd, "cv": cv, "mean": mean, "count": count}
        temp_data = pd.to_numeric(pd.Series(temp_data))

        if not data.get("se"):
            data["se"] = self._to_internal_se(temp_data)

        if not data.get("sd"):
            data["sd"] = self._to_internal_sd(temp_data)

        if not data.get("cv"):
            data["cv"] = self._to_internal_cv(temp_data)

        return data



    @staticmethod
    def ex_mapping():
        return {
            "individual_exs": "individuals",
            "individual_ex": "individual",
            "intervention_exs": "interventions",
            "group_exs": "groups",
            "characteristica_ex": "characteristica",
            "parent_ex": "parent",
            "output_exs": "outputs",
            "timecourse_exs": "timecourses",
        }

    @classmethod
    def rev_ex_mapping(cls):
        return dict((v, k) for k, v in cls.ex_mapping().items())

    @classmethod
    def transform_ex_fields(cls, data):
        transform_data = {}
        for key, value in data.items():
            ex_key = cls.rev_ex_mapping().get(key)
            if ex_key:
                transform_data[ex_key] = value
            else:
                transform_data[key] = value
        return transform_data

    @classmethod
    def retransform_ex_fields(cls, data):
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

class ReadSerializer(serializers.HyperlinkedModelSerializer):

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        for key,value in rep.items():
            if isinstance(value,float):
                rep[key] = round(value,2)
        return rep

class PkSerializer(serializers.Serializer):
    pk = serializers.IntegerField()

    class Meta:
        fields = ["pk",]