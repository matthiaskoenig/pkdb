"""
Generic utility functions.
"""

import os
import copy

CHAR_MAX_LENGTH = 200


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

def list_of_pk(field,obj):
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


def update_or_create_multiple(parent, children, related_name):
    for child in children:
        instance_cild = getattr(parent, related_name)
        instance_cild.update_or_create(**child)


def create_multiple(parent, children, related_name):
    instance_child = getattr(parent, related_name)
    return [instance_child.create(**child) for child in children]


def create_multiple_bulk(parent,related_name_parent,children,class_child):
    return class_child.objects.bulk_create([class_child(**{related_name_parent:parent,**child}) for child in children])

def create_multiple_bulk_normalized(notnormalized_instances, model_class):
    if notnormalized_instances:
        return model_class.objects.bulk_create([initialize_normed(notnorm_instance) for notnorm_instance in notnormalized_instances])

def initialize_normed(notnorm_instance):
    norm = copy.copy(notnorm_instance)
    norm.pk = None
    norm.final = True
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

    #interventions have no add statistics because they should have no mean,median,sd,se,cv ...
    try:
        norm.add_statistics()
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
