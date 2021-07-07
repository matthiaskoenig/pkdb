from django.core.exceptions import ObjectDoesNotExist, MultipleObjectsReturned
from django.db.models import Q
from drf_yasg.utils import swagger_serializer_method
from pkdb_app.info_nodes.models import InfoNode
from rest_framework import serializers

from pkdb_app.behaviours import map_field, MEASUREMENTTYPE_FIELDS, EX_MEASUREMENTTYPE_FIELDS
from pkdb_app.info_nodes.serializers import MeasurementTypeableSerializer
from pkdb_app.serializers import StudySmallElasticSerializer, SidNameLabelSerializer
from .models import (
    Group,
    GroupSet,
    IndividualEx,
    IndividualSet,
    Characteristica,
    DataFile,
    Individual,
    CharacteristicaEx,
    GroupEx)
from ..comments.serializers import DescriptionSerializer, CommentSerializer, DescriptionElasticSerializer, \
    CommentElasticSerializer
from ..serializers import WrongKeyValidationSerializer, ExSerializer, ReadSerializer
from ..utils import list_of_pk, _validate_required_key, create_multiple, _create

CHARACTERISTICA_FIELDS = ['count']
CHARACTERISTICA_MAP_FIELDS = map_field(CHARACTERISTICA_FIELDS)
SUBJECT_FIELDS = ['name', 'count']
SUBJECT_MAP_FIELDS = map_field(SUBJECT_FIELDS)

GROUP_FIELDS = ['name', 'count']
GROUP_MAP_FIELDS = ['name_map', 'count_map', 'parent_ex_map', 'parent_map']
EXTERN_FILE_FIELDS = ['source', 'subset_map', 'source_map','image', 'image_map']


# todo: move datafile from subjects module
# ----------------------------------
# DataFile
# ----------------------------------
class DataFileSerializer(WrongKeyValidationSerializer):
    class Meta:
        model = DataFile
        fields = ['file', 'filetype', 'id']
        extra_kwargs = {'id': {'allow_null': False}}

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data


# ----------------------------------
# Characteristica
# ----------------------------------
class CharacteristicaExSerializer(WrongKeyValidationSerializer):
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = CharacteristicaEx
        fields = ['comments', 'descriptions']

    def to_internal_value(self, data):
        drop_fields =  CHARACTERISTICA_FIELDS + CHARACTERISTICA_MAP_FIELDS + EX_MEASUREMENTTYPE_FIELDS
        [data.pop(field, None) for field in drop_fields]
        data = super().to_internal_value(data)
        return data

    def to_representation(self, instance):
        return super().to_representation(instance)


class CharacteristicaSerializer(MeasurementTypeableSerializer):
    count = serializers.IntegerField(required=False)

    class Meta:
        model = Characteristica
        fields = CHARACTERISTICA_FIELDS + MEASUREMENTTYPE_FIELDS

    def to_internal_value(self, data):
        data.pop('comments', None)
        data.pop('descriptions', None)
        self._is_required(data, 'measurement_type')
        self.validate_wrong_keys(data, additional_fields=CharacteristicaExSerializer.Meta.fields)
        return super(serializers.ModelSerializer, self).to_internal_value(data)

    @staticmethod
    def validate_count(count):
        if count < 1:
            raise serializers.ValidationError(f"count <{count}> has to be greater or equal to 1. ")
        return count

    def validate(self, attrs):
        try:
            # perform via dedicated function on categorials
            for info_node in ['substance', 'measurement_type', 'calculation_type']:
                if info_node in attrs:
                    if attrs[info_node] is not None:
                        attrs[info_node] = getattr(attrs[info_node], info_node)
            print(attrs)
            attrs["choice"] = attrs["measurement_type"].validate_complete(data=attrs, time_allowed=False)["choice"]

        except ValueError as err:
            raise serializers.ValidationError(err)

        return super().validate(attrs)


# ----------------------------------
# Group
# ----------------------------------
class GroupSerializer(ExSerializer):
    characteristica = CharacteristicaSerializer(
        many=True, read_only=False, required=False
    )
    parent = serializers.CharField(allow_null=True)

    class Meta:
        model = Group
        fields = GROUP_FIELDS + ['parent', 'characteristica']

    def to_internal_value(self, data):
        data.pop('comments', None)
        data.pop('descriptions', None)
        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data, additional_fields=GroupExSerializer.Meta.fields)
        _validate_required_key(data, 'count')


        return super(serializers.ModelSerializer, self).to_internal_value(data)

    @staticmethod
    def _validate_required_measurement_type(measurement_type, characteristica):
        is_measurement_type = [characteristica_single.get('measurement_type').info_node.name == measurement_type for
                               characteristica_single in
                               characteristica]

        if not any(is_measurement_type):
            raise serializers.ValidationError(
                {
                    'characteristica': f"A characteristica with `'measurement_type' = '{measurement_type}'` is required "
                                       f"on the `all` group.",
                    'details': characteristica}
            )
    @staticmethod
    def _validate_group_characteristica_count(characteristica, group_count):
        if int(characteristica.get("count", group_count)) > int(group_count):
            raise serializers.ValidationError(
                {
                    'characteristica': f"A characteristica count has to be smaller or equal to its group 'count'.",
                    'details': {
                        "characteristica": characteristica,
                        "group_count": group_count,
                    }
                }
            )



    def validate(self, attrs):
        ''' validates species information on group with name all
        :param attrs:
        :return:
        '''
        if attrs.get('name') == 'all':
            characteristica = attrs.get('characteristica', [])
            for measurement_type in ['species', 'healthy', 'sex']:
                self._validate_required_measurement_type(measurement_type, characteristica)

        for characteristica_single in attrs.get('characteristica', []):
            disabled = ['value']
            self._validate_disabled_data(characteristica_single, disabled)
            self._validate_group_characteristica_count(characteristica_single, attrs.get("count"))
            if not characteristica_single.get("calculation_type"):
                characteristica_single["calculation_type"] = InfoNode.objects.get(pk="sample-mean").calculation_type

        return super().validate(attrs)

    def to_representation(self, instance):

        rep = super().to_representation(instance)
        return rep


class GroupExSerializer(ExSerializer):

    characteristica_ex = CharacteristicaExSerializer(
        many=True, read_only=False, required=False
    )
    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    image = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    # internal data
    groups = GroupSerializer(
        many=True, write_only=True, required=False, allow_null=True
    )

    class Meta:
        model = GroupEx
        fields = (
                EXTERN_FILE_FIELDS +['characteristica_ex', 'groups', 'comments', 'descriptions']
        )

    def to_internal_value(self, data):

        # ----------------------------------
        # decompress external format
        # ----------------------------------
        temp_groups = self.split_entry(data)
        groups = []
        for group in temp_groups:
            characteristica = group.get('characteristica')
            if characteristica:
                temp_characteristica = []
                for characteristica_single in characteristica:
                    temp_characteristica.extend(
                        self.split_entry(characteristica_single)
                    )
                group['characteristica'] = temp_characteristica

            groups_from_file = self.entries_from_file(group)
            groups.extend(groups_from_file)


        data = self.transform_ex_fields(data)
        drop_fields = GROUP_FIELDS + GROUP_MAP_FIELDS+ ['parent_ex']
        [data.pop(field, None) for field in drop_fields]

        data = self.transform_map_fields(data)



        data['groups'] = groups

        # ----------------------------------
        # finished
        # ----------------------------------

        self.validate_wrong_keys(data)
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        return rep

    def create(self, validated_data):
        group_set = validated_data.pop("group_set")
        group_ex, popped_data =  _create(validated_data=validated_data, model_manager=group_set.group_exs, create_multiple_keys=["comments", "descriptions"],pop=["characteristica_ex","groups","study_groups", "parent_ex"])


        for characteristica_ex_single in popped_data["characteristica_ex"]:
            group_ex.characteristica_ex.create(**characteristica_ex_single)

        for group in popped_data["groups"]:
            group["study_groups"] = popped_data["study_groups"]
            group["study"] = self.context["study"]
            dj_group = group_ex.groups.create(**group)
            popped_data["study_groups"].add(dj_group.pk)

        group_ex.save()
        return group_ex

    def validate_image(self, value):
        self._validate_image(value)
        return value



class GroupSetSerializer(ExSerializer):
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    group_exs = GroupExSerializer(many=True, read_only=False)
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = GroupSet
        fields = ['descriptions', 'group_exs', 'comments']

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        groups = []
        for group_ex in data.get('group_exs', []):
            groups.extend(group_ex.get('groups'))
        self._group_validation(groups)
        return data

    def create(self, validated_data):
        groupset, poped_data = _create(model_manager=self.Meta.model.objects,
                                              validated_data=validated_data,
                                              create_multiple_keys=['descriptions', 'comments'],
                                              pop=["group_exs"])

        study_group_exs = []
        study_groups = set()

        group_exs = poped_data["group_exs"]
        for group_ex in group_exs:
            group_ex["group_set"] = groupset

        for group_ex in poped_data["group_exs"]:
            if "parent_ex" in group_ex:
                for study_group_ex in study_group_exs:
                    if study_group_ex.name == group_ex["parent_ex"]:
                        group_ex["parent_ex"] = study_group_ex

            ###################################
            # create single group_ex
            group_ex["study_groups"] = study_groups
            study_group_ex = GroupExSerializer(context=self.context).create(validated_data=group_ex)
            study_group_exs.append(study_group_ex)
        groupset.save()

        # add characteristica from parents to the all_characteristica_normed if each group
        for group in groupset.groups:
            group.characteristica_all_normed.add(*group._characteristica_all_normed)
        return groupset

    @staticmethod
    def _group_validation(groups):

        if not isinstance(groups, list):
            raise serializers.ValidationError(
                {'groups': f'groups must be a list and not a {type(groups)}', 'detail': groups})

        parents_name = set()
        groups_name = set()

        for group in groups:
            group_name = group.get('name')
            if group_name:
                if group_name in groups_name:
                    msg = {
                        'groups': f'Group names have to be unique. The group name  <{group_name}> was used more than once.'
                    }
                    raise serializers.ValidationError(msg)
                groups_name.add(group_name)

            parent_name = group.get('parent')
            if parent_name:
                parents_name.add(parent_name)
                if parent_name not in groups_name:
                    msg = {
                        'groups': f'The group <{parent_name}> have been used as a parent in group <{group_name}>. '
                                  f'But it was not yet defined (order matters: add first the parent)'
                    }
                    raise serializers.ValidationError(msg)

            if group_name == 'all' and parent_name is not None:
                raise serializers.ValidationError({'groups': 'parent is not allowed for group all'})

            elif group_name != 'all' and parent_name is None:
                raise serializers.ValidationError(
                    {
                        'groups': f"'parent' field missing on group '{group_name}'. "
                                  f"For all groups the parent group must be specified via "
                                  f"the 'parent' field (with exception of the <all> group)."
                    })
            elif group_name == parent_name:
                raise serializers.ValidationError(
                    {
                        'groups': "'parent' field cannot be identical with 'name' field."
                    })

        if 'all' not in groups_name:
            raise serializers.ValidationError(
                {
                    'group':
                        'A group with the name `all` is missing (studies without such a group cannot be uploaded). '
                        'The `all` group is the group of all subjects which was studied and defines common '
                        'characteristica for all groups and individuals. Species information are requirement '
                        'on the all group. Create the `all` group or rename group to `all`. '
                }
            )


# ----------------------------------
# Individual
# ----------------------------------


class IndividualSerializer(ExSerializer):
    name = serializers.CharField(required=True, allow_blank=False, allow_null=False)
    group = serializers.PrimaryKeyRelatedField(queryset=Group.objects.all())
    characteristica = CharacteristicaSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = Individual
        fields = ['name', 'group', 'characteristica']

    @staticmethod
    def group_to_internal_value(group, study_sid):
        if group:
            try:
                group = Group.objects.get(
                    Q(study__sid=study_sid) & Q(name=group)
                ).pk
            except ObjectDoesNotExist:
                msg = f'group: {group} in study: {study_sid} does not exist'
                raise serializers.ValidationError(msg)
            except MultipleObjectsReturned:
                msg = f'group: {group} in study: {study_sid} has been defined multiple times.'
                raise serializers.ValidationError(msg)

        else:
            msg = {'group': f'group is required on individual', 'detail': group}
            raise serializers.ValidationError(msg)
        return group

    def to_internal_value(self, data):
        self._is_required(data, 'group')
        data.pop('comments', None)
        data.pop('descriptions', None)
        study_sid = self.context['request'].path.split('/')[-2]
        if 'group' in data:
            data['group'] = self.group_to_internal_value(data['group'], study_sid)

        data = self.retransform_map_fields(data)
        data = self.retransform_ex_fields(data)
        self.validate_wrong_keys(data,additional_fields=IndividualExSerializer.Meta.fields)


        for characteristica_single in data.get('characteristica', []):
            disabled = ['mean', 'median', 'sd', 'se', 'cv']
            self._validate_disabled_data(characteristica_single, disabled)

        return super(serializers.ModelSerializer, self).to_internal_value(data)


class IndividualExSerializer(ExSerializer):
    characteristica_ex = CharacteristicaExSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    source = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    image = serializers.PrimaryKeyRelatedField(
        queryset=DataFile.objects.all(), required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    # internal data
    individuals = IndividualSerializer(
        many=True, write_only=True, required=False, allow_null=True
    )

    def validate_image(self, value):
        self._validate_image(value)
        return value


    class Meta:
        model = IndividualEx
        fields = EXTERN_FILE_FIELDS + [
            'characteristica_ex',
            'individuals',
            'comments',
            'descriptions'
        ]

    @staticmethod
    def group_to_internal_value(group, study_sid):
        if group:
            try:
                group = Group.objects.get(
                    Q(study__sid=study_sid) & Q(name=group)
                ).pk
            except ObjectDoesNotExist:
                msg = f'group: {group} in study: {study_sid} does not exist'
                raise serializers.ValidationError(msg)
        return group

    def to_internal_value(self, data):

        # ----------------------------------
        # decompress external format
        # ----------------------------------

        temp_individuals = self.split_entry(data)
        individuals = []
        for individual in temp_individuals:
            characteristica = individual.get('characteristica')
            if characteristica:
                temp_characteristica = []
                for characteristica_single in characteristica:
                    temp_characteristica.extend(
                        self.split_entry(characteristica_single)
                    )
                individual['characteristica'] = temp_characteristica

            individuals_from_file = self.entries_from_file(individual)
            individuals.extend(individuals_from_file)

        # ----------------------------------
        # finished external format
        # ----------------------------------
        drop_fields = ['name','name_map','group','group_map']
        [data.pop(field, None) for field in drop_fields]

        data = self.transform_ex_fields(data)
        data = self.transform_map_fields(data)

        data['individuals'] = individuals

        study_sid = self.context['request'].path.split('/')[-2]

        if 'group' in data:
            data['group'] = self.group_to_internal_value(data.get('group'), study_sid)
        return super(WrongKeyValidationSerializer, self).to_internal_value(data)

    def to_representation(self, instance):

        rep = super().to_representation(instance)
        if 'group' in rep:
            if rep['group']:
                if instance.group:
                    rep['group'] = instance.group.name
                if instance.group_map:
                    rep['group'] = instance.group_map
        return rep

    def create(self, validated_data):
        individual_set = validated_data.pop("individual_set")
        individual_ex, poped_data = _create(model_manager=individual_set.individual_exs,
                                              validated_data=validated_data,
                                              create_multiple_keys=['descriptions', 'comments', 'characteristica_ex'],
                                              pop=['individuals'])

        individuals = poped_data["individuals"]
        for individual in individuals:
            individual["study"] = self.context["study"]
        individuals = create_multiple(individual_ex, individuals, "individuals")

        # add characteristica from parents to the all_characteristica_normed if each individual
        for individual in individuals:
            individual.characteristica_all_normed.add(*individual._characteristica_all_normed)

        individual_ex.save()
        return individual_ex


class IndividualSetSerializer(ExSerializer):
    individual_exs = IndividualExSerializer(many=True, read_only=False, required=False)
    descriptions = DescriptionSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )
    comments = CommentSerializer(
        many=True, read_only=False, required=False, allow_null=True
    )

    class Meta:
        model = IndividualSet
        fields = ['descriptions', 'individual_exs', 'comments']

    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        self.validate_wrong_keys(data)
        return data

    def create(self, validated_data):
        individualset, poped_data = _create(model_manager=self.Meta.model.objects,
                                       validated_data=validated_data,
                                       create_multiple_keys=['descriptions', 'comments'],
                                       pop=["study", "individual_exs"])

        individual_exs = poped_data['individual_exs']
        for individual_ex in individual_exs:
            individual_ex["individual_set"] = individualset

        IndividualExSerializer(context=self.context, many=True).create(validated_data=poped_data["individual_exs"])

        return individualset


###############################################################################################
# Read Serializer
###############################################################################################
class CharacteristicaElasticBigSerializer(ReadSerializer):
    measurement_type = serializers.CharField()
    substance = serializers.CharField(allow_null=True)
    calculation_type = serializers.CharField(allow_null=True)

    pk = serializers.IntegerField(source='id')

    class Meta:
        model = Characteristica
        fields = ['pk', 'raw_pk', 'normed', 'study_sid', 'study_name',
                  'subject_type'] + CHARACTERISTICA_FIELDS + MEASUREMENTTYPE_FIELDS + ['group_pk', 'group_name',
                                                                                       'group_count',
                                                                                       'group_parent_pk'] + [
                     'individual_pk', 'individual_name', 'individual_group_pk']


###############################################################################################
# Elastic Search Serializer
###############################################################################################
# maybe depreciated
class DataFileElasticSerializer(serializers.ModelSerializer):
    file = serializers.CharField()

    class Meta:
        model = DataFile
        fields = ['pk', 'name', 'file']


class CharacteristicaElasticSerializer(serializers.ModelSerializer):
    value = serializers.FloatField(allow_null=True)
    mean = serializers.FloatField(allow_null=True)
    median = serializers.FloatField(allow_null=True)
    min = serializers.FloatField(allow_null=True)
    max = serializers.FloatField(allow_null=True)
    sd = serializers.FloatField(allow_null=True)
    se = serializers.FloatField(allow_null=True)
    cv = serializers.FloatField(allow_null=True)
    measurement_type = SidNameLabelSerializer()
    calculation_type = SidNameLabelSerializer(allow_null=True)
    substance = SidNameLabelSerializer(allow_null=True)
    choice = SidNameLabelSerializer(allow_null=True)
    group_count = serializers.IntegerField(allow_null=True)
    class Meta:
        model = Characteristica
        fields = ['pk'] + CHARACTERISTICA_FIELDS + MEASUREMENTTYPE_FIELDS + ['group_count']+['normed']  # + ['access','allowed_users']
        read_only_fields = fields


# Group related Serializer
class GroupSetElasticSmallSerializer(serializers.ModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    groups = serializers.SerializerMethodField()

    class Meta:
        model = GroupSet
        fields = ['pk', 'descriptions', 'comments', 'groups']

    def get_groups(self, obj):
        return list_of_pk('groups', obj)


class GroupSmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Group
        fields = ['pk', 'name', 'count']


class GroupElasticSerializer(serializers.ModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    parent = GroupSmallElasticSerializer(read_only=True)
    characteristica = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = (
            'pk',
            'name',
            'parent',
            'count',
            'study',
            'characteristica',
        )

    @swagger_serializer_method(CharacteristicaElasticSerializer(many=True))
    def get_characteristica(self, instance):
        if instance.characteristica_all_normed:
            return CharacteristicaElasticSerializer(instance.characteristica_all_normed, many=True, read_only=True).data
        return []


# Individual related Serializer
class IndividualSmallElasticSerializer(serializers.ModelSerializer):
    class Meta:
        model = Individual
        fields = ['pk', 'name']


class IndividualSetElasticSmallSerializer(serializers.ModelSerializer):
    descriptions = DescriptionElasticSerializer(many=True, read_only=True)
    comments = CommentElasticSerializer(many=True, read_only=True)
    individuals = serializers.SerializerMethodField()

    class Meta:
        model = IndividualSet
        fields = ['pk', 'descriptions', 'comments', 'individuals']

    def get_individuals(self, obj):
        return list_of_pk('individuals', obj)


class IndividualElasticSerializer(serializers.ModelSerializer):
    study = StudySmallElasticSerializer(read_only=True)
    group = GroupSmallElasticSerializer(read_only=True)
    characteristica = serializers.SerializerMethodField()

    @swagger_serializer_method(serializer_or_field=CharacteristicaElasticSerializer)
    def get_characteristica(self, instance):
        if instance.characteristica_all_normed:
            return CharacteristicaElasticSerializer(instance.characteristica_all_normed, many=True, read_only=True).data
        return []

    class Meta:
        model = Individual
        fields = (
            'pk',
            'name',
            'study',
            'group',
            'characteristica',
        )


class GroupCharacteristicaSerializer(serializers.Serializer):
    study_sid = serializers.CharField()
    study_name = serializers.CharField()
    group_pk = serializers.IntegerField()
    group_name = serializers.CharField()
    group_count = serializers.IntegerField()
    group_parent_pk = serializers.IntegerField()
    characteristica_pk = serializers.IntegerField()
    count = serializers.IntegerField()

    measurement_type = serializers.CharField()
    calculation_type = serializers.CharField()

    choice = serializers.CharField()
    substance = serializers.CharField()

    value = serializers.FloatField()
    mean = serializers.FloatField()
    median = serializers.FloatField()
    min = serializers.FloatField()
    max = serializers.FloatField()
    sd = serializers.FloatField()
    se = serializers.FloatField()
    cv = serializers.FloatField()
    unit = serializers.CharField()

    class Meta:
        fields = ['study_sid', 'study_name', 'group_pk', 'group_name', 'group_count', 'group_parent_pk',
                  'characteristica_pk', 'count'] + MEASUREMENTTYPE_FIELDS


class IndividualCharacteristicaSerializer(serializers.Serializer):

    study_sid = serializers.CharField()
    study_name = serializers.CharField()
    individual_pk = serializers.IntegerField()
    individual_name = serializers.CharField()
    individual_group_pk = serializers.IntegerField()
    characteristica_pk = serializers.IntegerField()
    count = serializers.IntegerField()

    measurement_type = serializers.CharField()
    calculation_type = serializers.CharField()

    choice = serializers.CharField()
    substance = serializers.CharField()

    value = serializers.FloatField()
    mean = serializers.FloatField()
    median = serializers.FloatField()
    min = serializers.FloatField()
    max = serializers.FloatField()
    sd = serializers.FloatField()
    se = serializers.FloatField()
    cv = serializers.FloatField()
    unit = serializers.CharField()

    class Meta:
        fields = ['study_sid', 'study_name', 'individual_pk', 'individual_name', 'individual_group_pk',
                  'characteristica_pk', 'count'] + MEASUREMENTTYPE_FIELDS
