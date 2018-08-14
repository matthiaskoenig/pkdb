#! /usr/bin/env python
import os, sys
import argparse

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from pkdb_app.data_management.fill_database import open_reference, open_study, upload_reference,upload_study



def run(args):
    ok = True
    study_path = os.path.join(args.study, "study.json")
    _ , study_name = os.path.split(args.study)

    reference_path = os.path.join(args.study, "reference.json")
    reference_pdf = os.path.join(args.study, f"{study_name}.pdf")

    if os.path.isfile(reference_path):
        reference_dict = {"json": reference_path, "pdf": reference_pdf}
        if open_reference(reference_dict):
            ok_ref = upload_reference(open_reference(reference_dict))
            if not ok_ref:
                ok = ok_ref
        else:
            ok = False

    if os.path.isfile(study_path):
        if open_study(study_path):
            ok_study = upload_study(open_study(study_path))
            if not ok_study:
                ok = ok_study
        else:
            ok = False


    if ok:
        print("everthing is fine")

def main():
    parser = argparse.ArgumentParser(description="Upload a file to PKDB")
    parser.add_argument("-s", help="directory of a study", dest="study", type=str, required=True)
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__=="__main__":
    main()