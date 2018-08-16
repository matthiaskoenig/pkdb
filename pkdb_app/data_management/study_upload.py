#! /usr/bin/env python
import os, sys
import argparse
from collections import namedtuple
BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from pkdb_app.data_management.fill_database import read_reference_json, read_study_json, upload_reference,upload_study
from pkdb_app.data_management.reference_create import run as create_reference


def run(args):
    ok = True
    study_path = os.path.join(args.study, "study.json")
    _ , study_name = os.path.split(args.study)

    reference_path = os.path.join(args.study, "reference.json")
    reference_pdf = os.path.join(args.study, f"{study_name}.pdf")

    if read_study_json(study_path) and hasattr(args, 'r'):
        study = read_study_json(study_path)
        Reference = namedtuple("Reference",["reference", "name", "pmid"])
        ref = Reference(reference=args.study,name=study_name, pmid=study["json"]["reference"])
        create_reference(ref)


    if os.path.isfile(reference_path):
        reference_dict = {"json": reference_path, "pdf": reference_pdf}
        if read_reference_json(reference_dict):
            ok_ref = upload_reference(read_reference_json(reference_dict))
            if not ok_ref:
                ok = ok_ref
        else:
            ok = False

    if os.path.isfile(study_path):
        if read_study_json(study_path):
            ok_study = upload_study(read_study_json(study_path))
            if not ok_study:
                ok = ok_study
        else:
            ok = False


    if ok:
        print("everthing is fine")

def main():
    parser = argparse.ArgumentParser(description="Upload a file to PKDB")
    parser.add_argument("-s", help="directory of a study", dest="study", type=str, required=True)
    parser.add_argument("--r", help="directory of a study", action="store_true")

    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__=="__main__":
    main()