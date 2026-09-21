"""Generic utility functions."""

import contextlib
import copy
import os

import pandas as pd
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

CHAR_MAX_LENGTH = 200
CHAR_MAX_LENGTH_LONG = CHAR_MAX_LENGTH * 5


class SlugRelatedField(serializers.SlugRelatedField):
    """SlugRelatedField with the not-found and invalid error messages worded for uploads."""

    default_error_messages = {
        "does_not_exist": _("Object with {slug_name}=<{value}> does not exist."),
        "invalid": _("Invalid value."),
    }


def list_duplicates(seq):
    """Return the items of seq which occur more than once, each one once."""
    # FIXME: use colletions.Counter
    seen = set()
    seen_add = seen.add
    # adds all elements it doesn't know yet to seen and all other to seen_twice
    seen_twice = {x for x in seq if x in seen or seen_add(x)}
    # turn the set into a list (as requested)
    return list(seen_twice)


def create_choices(collection):
    """Create choices from a given list of items.

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
    """Copy src[src_key] to dest[dest_key] when src_key is present in src."""
    if src_key in src:
        dest[dest_key] = src[src_key]
    return dest


def clean_import(data):
    """Drop keys whose value is empty, blank or `nan`, and keep the value of every other key."""
    clean_dict = {}
    for key, value in data.items():
        if str(value).strip() not in ["", "nan"]:
            clean_dict[key] = value

        elif str(value) == "NA":
            clean_dict[key] = None

    return clean_dict


def list_of_pk(field, obj):
    """Return the primary keys of the related objects stored under field on obj."""
    result = []
    try:
        relevant_field = obj.to_dict().get(field)
    except AttributeError:
        relevant_field = obj.get(field)
    if relevant_field:
        result = [int(field_list["pk"]) for field_list in relevant_field]
    return result


def ensure_dir(file_path):
    """Checks for directory and creates if non-existant."""
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def update_or_create_multiple(parent, children, related_name, lookup_fields=None):
    """Update or create each child on parent's related_name manager, recursing into nested relations."""
    for child in children:
        lookup_dict = {}
        instance_child = getattr(parent, related_name)

        if lookup_fields:
            for lookup_field in lookup_fields:
                lookup_dict[lookup_field] = child.pop(lookup_field, None)
        else:
            lookup_dict = child

        try:
            if instance_child.model.__name__ in ["Choice", "Unit"]:
                obj = instance_child.get(**lookup_dict)
            else:
                obj = instance_child.model.objects.get(**lookup_dict)
            for key, value in child.items():
                if key == "annotations":
                    update_or_create_multiple(
                        obj, value, key, lookup_fields=["term", "relation"]
                    )
                elif key == "synonyms":
                    update_or_create_multiple(obj, value, key, lookup_fields=["name"])
                else:
                    setattr(obj, key, value)

            obj.save()

        except instance_child.model.DoesNotExist:
            instance_dict = {**lookup_dict, **child}
            instance_child.create(**instance_dict)


def create_multiple(parent, children, related_name):
    """Create each child on parent's related_name manager and return the created instances."""
    instance_child = getattr(parent, related_name)
    return [instance_child.create(**child) for child in children]


def create_multiple_bulk(parent, related_name_parent, children, class_child):
    """Bulk create class_child instances for each child, linked to parent via related_name_parent."""
    return class_child.objects.bulk_create(
        [class_child(**{related_name_parent: parent, **child}) for child in children]
    )


def create_multiple_bulk_normalized(notnormalized_instances, model_class):
    """Bulk create the normalized copies of the given not-normalized instances."""
    if notnormalized_instances:
        return model_class.objects.bulk_create(
            [
                initialize_normed(notnorm_instance)
                for notnorm_instance in notnormalized_instances
            ]
        )
    return None


def _create(
    validated_data,
    model_manager=None,
    model_serializer=None,
    create_multiple_keys=(),
    add_multiple_keys=(),
    pop=(),
):
    """Create the instance and pop out the related data to be created or added afterwards."""
    popped_data = {related: validated_data.pop(related, []) for related in pop}
    related_data_create = {
        related: validated_data.pop(related, []) for related in create_multiple_keys
    }
    related_data_add = {
        related: validated_data.pop(related, []) for related in add_multiple_keys
    }
    if model_manager is not None:
        instance = model_manager.create(**validated_data)
    elif model_serializer is not None:
        instance = model_serializer.create(validated_data=validated_data)
    else:
        raise ValueError("Either model_manager or model_serializer are required.")

    for key, item in related_data_create.items():
        create_multiple(instance, item, key)

    for key, item in related_data_add.items():
        getattr(instance, key).add(*item)

    return instance, popped_data


def initialize_normed(not_norm_instance):
    """Create the normalized copy of a not-normalized instance and normalize its units."""
    norm = copy.copy(not_norm_instance)
    norm.pk = None
    norm.normed = True
    norm.normalize()
    norm.raw_id = not_norm_instance.pk

    with contextlib.suppress(AttributeError):
        norm.individual_id = not_norm_instance.individual.pk

    with contextlib.suppress(AttributeError):
        norm.group_id = not_norm_instance.group.pk

    # interventions have no add add_error_measures() because they should have no mean,median,sd,se,cv ...
    with contextlib.suppress(AttributeError):
        norm.add_error_measures()
    return norm


def recursive_iter(obj, keys=()):
    """Yield (key path, value) pairs by recursively walking a nested dict/list/tuple structure."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from recursive_iter(v, (*keys, k))
    elif any(isinstance(obj, t) for t in (list, tuple)):
        for idx, item in enumerate(obj):
            yield from recursive_iter(item, (*keys, idx))

        if len(obj) == 0:
            yield keys, None

    else:
        yield keys, obj


def set_keys(d, value, *keys):
    """Changes keys in nested dictionary."""
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value


def _validate_required_key_and_value(attrs, key, details=None, extra_message: str = ""):
    if pd.isnull(attrs.get(key, None)) or pd.isna(attrs.get(key, None)):
        error_json = {key: f"The key <{key}> is required. {extra_message}"}
        if details:
            error_json["details"] = details
        raise serializers.ValidationError(error_json)


def _validate_required_key_and_value_or_nr(
    attrs, key, details=None, extra_message: str = ""
):
    value = attrs.get(key, None)
    if value != "NR":
        _validate_required_key_and_value(attrs, key, details, extra_message)
    else:
        attrs[key] = None


def _validate_required_key(attrs, key, details=None, extra_message: str = ""):
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
