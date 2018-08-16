import argparse

import os
import sys

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)

from pkdb_app.data_management.create_reference_caffeine import load_from_biopython, xml_to_data,create_json,add_doi,save_json

def run(args):

    ref_dict = {"reference_path":args.reference,
                    "name":args.name,
                    "pmid":args.pmid}
    save_json(add_doi(create_json(xml_to_data(load_from_biopython(ref_dict)))))

def main():
    parser = argparse.ArgumentParser(description="create reference folder")
    parser.add_argument("-s", help="directory of a reference", dest="reference", type=str, required=True)
    parser.add_argument("-n", help="name of reference", dest="name", type=str, required=True)
    parser.add_argument("-p", help="pmid", dest="pmid", type=str, required=True)


    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__=="__main__":
    main()