"""
Creates JSON substance information.
"""
import os
from libchebipy import ChebiEntity
import numpy as np
from slugify import slugify

SUBSTANCES_BASE_PATH = "../substances/"


def load_substance(substance):
    substance_dict = {
        "sid": substance.sid,
        "url_slug": slugify(substance.sid,
                            replacements=[['*', '-times-'],
                                          ['/', '-over-'],
                                          ['+', '-plus-']
                                          ]),
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


if __name__ == "__main__":
    from pkdb_app.substances.substances import SUBSTANCES_DATA
    from pkdb_app.data_management.utils import save_json

    substances = [load_substance(substance) for substance in SUBSTANCES_DATA]
    substance_path = os.path.join(SUBSTANCES_BASE_PATH, "substances.json")
    save_json(substances, substance_path)
