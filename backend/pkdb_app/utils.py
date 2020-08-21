"""
Generic utility functions.
"""
import copy
import os

from django.http import Http404
from django.shortcuts import _get_queryset
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

CHAR_MAX_LENGTH = 200
CHAR_MAX_LENGTH_LONG = CHAR_MAX_LENGTH * 5


class SlugRelatedField(serializers.SlugRelatedField):
    default_error_messages = {
        'does_not_exist': _('Object with {slug_name}=<{value}> does not exist.'),
        'invalid': _('Invalid value.'),
    }


def list_duplicates(seq):
    seen = set()
    seen_add = seen.add
    # adds all elements it doesn't know yet to seen and all other to seen_twice
    seen_twice = set(x for x in seq if x in seen or seen_add(x))
    # turn the set into a list (as requested)
    return list(seen_twice)


def create_choices(collection):
    """ Creates choices from given list of items.
    In case of dictionaries the keys are used to create choices.
    :param collection: iterable collection from which choices are created.
    :return: list of choice tuples
    """
    choices = []
    for item in collection:
        key = item
        if not isinstance(item, str):
            # get_key interface must be provided by item
            key = item.key
        choices.append((key, key))
    return choices


def create_if_exists(src, src_key, dest, dest_key):
    if src_key in src.keys():
        dest[dest_key] = src[src_key]
    return dest


def clean_import(data):
    clean_dict = {}
    for key, value in data.items():

        if not str(value).strip() in ["", "nan"]:
            clean_dict[key] = value

        elif str(value) == "NA":
            clean_dict[key] = None

    return clean_dict


def list_of_pk(field, obj):
    result = []
    try:
        relevant_field = obj.to_dict().get(field)
    except AttributeError:
        relevant_field = obj.get(field)
    if relevant_field:
        result = [int(field_list["pk"]) for field_list in relevant_field]
    return result


def ensure_dir(file_path):
    """ Checks for directory and creates if non-existant."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def update_or_create_multiple(parent, children, related_name, lookup_fields=[]):
    for child in children:
        lookup_dict = {}
        instance_child = getattr(parent, related_name)

        if lookup_fields:
            for lookup_field in lookup_fields:
                lookup_dict[lookup_field] = child.pop(lookup_field, None)
        else:
            lookup_dict = child

        # instance_child.update_or_create(**lookup_dict, defaults=child)

        try:
            if instance_child.model.__name__ in ["Choice", "Unit"]:
                obj = instance_child.get(**lookup_dict)
            else:
                obj = instance_child.model.objects.get(**lookup_dict)
            for key, value in child.items():
                if key == "annotations":
                    update_or_create_multiple(obj, value, key, lookup_fields=["term", "relation"])
                elif key == "synonyms":
                    update_or_create_multiple(obj, value, key, lookup_fields=["name"])
                else:
                    setattr(obj, key, value)

            obj.save()



        except instance_child.model.DoesNotExist:
            instance_dict = {**lookup_dict, **child}
            instance_child.create(**instance_dict)



def create_multiple(parent, children, related_name):
    instance_child = getattr(parent, related_name)

    return [instance_child.create(**child) for child in children]


def create_multiple_bulk(parent, related_name_parent, children, class_child):
    return class_child.objects.bulk_create(
        [class_child(**{related_name_parent: parent, **child}) for child in children])


def create_multiple_bulk_normalized(notnormalized_instances, model_class):
    if notnormalized_instances:
        return model_class.objects.bulk_create(
            [initialize_normed(notnorm_instance) for notnorm_instance in notnormalized_instances])

def _create(validated_data, model_manager=None, model_serializer= None,  create_multiple_keys=[], add_multiple_keys=[], pop=[]):
    poped_data = {related: validated_data.pop(related, []) for related in pop}
    related_data_create = {related: validated_data.pop(related, []) for related in create_multiple_keys}
    related_data_add = {related: validated_data.pop(related, []) for related in add_multiple_keys}
    if model_manager is not None:
        instance = model_manager.create(**validated_data)
    elif model_serializer is not None:
        instance = model_serializer.create(validated_data=validated_data)
    else:
        raise ValueError("Either model_manager or model_serializer are required.")

    for key, item in related_data_create.items():
        create_multiple(instance, item, key)

    for key, item in related_data_add.items():
        getattr(instance,key).add(*item)

    return instance, poped_data

def initialize_normed(notnorm_instance):
    norm = copy.copy(notnorm_instance)
    norm.pk = None
    norm.normed = True
    norm.normalize()
    norm.raw_id = notnorm_instance.pk

    try:
        norm.individual_id = notnorm_instance.individual.pk

    except AttributeError:
        pass

    try:
        norm.group_id = notnorm_instance.group.pk

    except AttributeError:
        pass

    # interventions have no add add_error_measures() because they should have no mean,median,sd,se,cv ...
    try:
        norm.add_error_measures()
    except AttributeError:
        pass
    return norm


def recursive_iter(obj, keys=()):
    """ Creates dictionary with key:object from nested JSON data structure. """
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from recursive_iter(v, keys + (k,))
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for idx, item in enumerate(obj):
            yield from recursive_iter(item, keys + (idx,))

        if len(obj) == 0:
            yield keys, None

    else:
        yield keys, obj


def set_keys(d, value, *keys):
    """ Changes keys in nested dictionary. """
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value


def _validate_requried_key(attrs, key, details=None, extra_message=""):
    if key not in attrs:
        error_json = {key: f"The key <{key}> is required. {extra_message}"}
        if details:
            error_json["details"] = details
        raise serializers.ValidationError(error_json)

def _validate_not_allowed_key(attrs, key, details=None, extra_message=""):
    if key in attrs:
        error_json = {key: f"The key <{key}> is not allowed. {extra_message}"}
        if details:
            error_json["details"] = details
        raise serializers.ValidationError(error_json)
