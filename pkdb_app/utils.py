
import os
from django.core.exceptions import ValidationError

from pkdb_app.categoricals import CHARACTERISTIC_DICT, CATEGORIAL_TYPE, BOOLEAN_TYPE, NUMERIC_TYPE, INTERVENTION_DICT

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

def validate_input(data,model_name):
    model_categoricals = {"characteristica":CHARACTERISTIC_DICT,"intervention":INTERVENTION_DICT}
    category = data.get("category", None)
    if category:
        model_categorical = model_categoricals[model_name][data.get("category")]
        choice = data.get("choice",None)
        unit = data.get("unit",None)

        if choice:
            if (model_categorical.dtype == CATEGORIAL_TYPE or model_categorical.dtype == BOOLEAN_TYPE):
                if not choice in model_categorical.choices:
                    msg = f"{choice} is not part of {model_categorical.choices} for {model_categorical.value}"
                    raise ValidationError(msg)

        elif model_categorical.dtype == NUMERIC_TYPE:
            if not unit in model_categorical.units:
                msg = f"{unit} is not allowed but required. For {model_categorical.value} allowed units are {model_categorical.units}"
                raise ValidationError(msg)

    return data

def un_map(data):
    cleaned_result = {}
    for k, v in data.items():
        if "_map" in k:
            k = k[:-4]
        if v is None:
            continue
        cleaned_result[k] = v
    return cleaned_result

