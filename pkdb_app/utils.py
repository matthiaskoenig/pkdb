"""
Generic utility functions.
"""

import os

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
    for child in children:
        instance_cild = getattr(parent, related_name)
        instance_cild.create(**child)


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
