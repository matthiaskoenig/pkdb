
import os
from django.core.exceptions import ValidationError

CHAR_MAX_LENGTH = 30

def create_if_exists(src,src_key,dest,dest_key):
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
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def update_or_create_multiple(parent,children,related_name):
    for child in children:
            instance_cild =  getattr(parent,related_name)
            instance_cild.update_or_create(**child)

def get_or_val_error(model, *args, **kwargs):
    try:
        return model.objects.get(*args, **kwargs)
    except model.DoesNotExist:
        msg = f"{model} instance with args:{args}, kwargs:{kwargs} does not exist"
        return ValidationError(msg)

def un_map(data):
    cleaned_result = {}
    for k, v in data.items():
        if "_map" in k:
            k = k[:-4]
        if v is None:
            continue
        cleaned_result[k] = v
    return cleaned_result