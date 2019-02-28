import os
from libchebipy import ChebiEntity
from pkdb_app.data_management.utils import _read_json
import numpy as np

SUBSTANCES_BASE_PATH = "../substances/json"

def load_substance(substance):
    substance_dict = {
        "sid": substance.sid,
        "name": substance.name,
    }
    if substance.chebi:
        substance_dict["chebi"] = substance.chebi
        this_substance = ChebiEntity(substance.chebi)

        formula = this_substance.get_formula()

        charge = this_substance.get_charge()
        if np.isnan(charge):
            charge = None

        mass = this_substance.get_mass()
        if np.isnan(mass):
            mass = None

        definition = this_substance.get_definition()


        substance_dict["formula"] = formula
        substance_dict["charge"] = charge
        substance_dict["mass"] = mass
        substance_dict["description"] = definition

    if substance.parents:
        substance_dict["parents"] = substance.parents

    if substance.synonyms:
        substance_dict["synonyms"] = substance.synonyms

    return substance_dict

def read_substances(directory):
    (dirpath, dirnames, filenames) = next(os.walk(directory))
    substances_json = [_read_json(os.path.join(directory,filename)) for filename in filenames]
    return substances_json


if __name__ == "__main__":
    from pkdb_app.substances.substances import SUBSTANCES_DATA
    from pkdb_app.data_management.utils import save_json, clean_filename

    for substance in SUBSTANCES_DATA:
        substance_dict = load_substance(substance)
        substance_path = os.path.join(SUBSTANCES_BASE_PATH,f"{clean_filename(substance.sid)}.json")
        save_json(substance_dict, substance_path)


