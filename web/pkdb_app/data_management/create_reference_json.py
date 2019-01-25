#!python3.6
"""
Creates reference.json from given PMID id.
"""
import argparse
import os
import sys
import xml.etree.ElementTree as ET
from Bio import Entrez
import json
import requests

from pkdb_app.data_management.utils import recursive_iter, set_keys

# FIXME: get proper email
ENTREZ_EMAIL = "janekg89@hotmail.de"


def run(args):
    ref_dict = {"reference_path": args.reference, "name": args.name, "pmid": args.pmid}
    save_json(add_doi(create_json(xml_to_data(load_from_biopython(ref_dict)))))


def load_from_biopython(d):
    """ Retrieves pubmed information.

    :param d:
    :return:
    """
    Entrez.email = ENTREZ_EMAIL
    handle = Entrez.efetch(db="pubmed", id=d["pmid"], retmode="xml")
    all_info = handle.read()
    handle.close()
    return {**d, "xml": all_info}


def xml_to_data(d):
    return {**d, "data": ET.fromstring(d["xml"])}


def create_json(d):
    """ Creates reference.json"""
    json_dict = {}
    json_dict["pmid"] = d["pmid"]
    json_dict["name"] = d["name"]
    json_dict["sid"] = d["pmid"]
    for date in d["data"].iter("DateCompleted"):
        year = date.find("Year").text
        month = date.find("Month").text
        day = date.find("Day").text
        json_dict["date"] = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        continue
    for journal in d["data"].iter("Title"):
        json_dict["journal"] = journal.text
        continue
    for title in d["data"].iter("ArticleTitle"):
        json_dict["title"] = title.text
        continue
    for abstract in d["data"].iter("AbstractText"):
        json_dict["abstract"] = abstract.text
        continue

    authors = []
    for author in d["data"].iter("Author"):
        author_dict = {}
        author_dict["first_name"] = author.find("ForeName").text
        author_dict["last_name"] = author.find("LastName").text
        authors.append(author_dict)
    json_dict["authors"] = authors

    for keys, item in recursive_iter(json_dict):
        if item == "":
            set_keys(json_dict, None, *keys)

    return {"json": json_dict, "reference_path": d["reference_path"]}


def add_doi(d):
    """ Try to get DOI.

    :param d:
    :return:
    """
    json_dict = d["json"]
    response = requests.get(
        f'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=my_tool&email=my_email@example.com&ids={json_dict["pmid"]}'
    )
    pmcids = ET.fromstring(response.content)
    for records in pmcids.iter("record"):
        json_dict["doi"] = records.get("doi", None)

    return {"json": json_dict, "reference_path": d["reference_path"]}


def save_json(d):
    json_file = os.path.join(d["reference_path"], "reference.json")
    directory = os.path.dirname(json_file)
    if not os.path.exists(directory):
        os.makedirs(directory)
    with open(json_file, "w") as fp:
        json.dump(d["json"], fp, indent=4)


def main():
    parser = argparse.ArgumentParser(description="Get Pubmed information as JSON")
    parser.add_argument(
        "-s", help="directory of a reference", dest="reference", type=str, required=True
    )
    parser.add_argument(
        "-n", help="name of reference", dest="name", type=str, required=True
    )
    parser.add_argument("-p", help="pmid", dest="pmid", type=str, required=True)

    # call run function
    parser.set_defaults(func=run)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
