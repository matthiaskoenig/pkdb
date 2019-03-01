"""
Utils for data management.
"""
import logging
import os
import json


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


def remove_keys(d, value, *keys):
    """ Changes keys in nested dictionary. """
    for key in keys[:-1]:
        d = d[key]
    d[keys[-1]] = value

def clean_filename(s):
    return s.replace("/", "over")

def save_json(d, file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(file_path, "w") as fp:
        json.dump(d, fp, indent=4)


def _read_json(path):
    """ Reads json.

    :param path: returns json, or None if parsing failed.
    :return:
    """
    with open(path) as f:
        try:
            json_data = json.loads(f.read(), object_pairs_hook=dict_raise_on_duplicates)
        except json.decoder.JSONDecodeError as err:
            logging.warning(f"{err}\nin {path}")
            return
        except ValueError as err:
            logging.warning(f"{err}\nin {path}")
            return

    return json_data


def dict_raise_on_duplicates(ordered_pairs):
    """Reject duplicate keys."""
    d = {}
    for k, v in ordered_pairs:
        if k in d:
            raise ValueError("duplicate key: %r" % (k,))
        else:
            d[k] = v
    return d