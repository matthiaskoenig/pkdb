"""
Creates json files in master folder
"""
import os
import shutil
import csv
import sys
import bonobo
import xml.etree.ElementTree as ET
from Bio import Entrez
import json
import requests

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../../'))
sys.path.append(BASEPATH)
from pkdb_app.utils import ensure_dir

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pkdb_app.config.local")

CAFFEINE = "caffeine"

Master = os.path.join(BASEPATH, "Master")
if BASEPATH not in sys.path:
    sys.path.append(BASEPATH)

DATABASEPATH = os.path.join(BASEPATH, "data")
REFERENCESPATH = os.path.join(DATABASEPATH, CAFFEINE, "Studies.tsv")
SUBJECTSPATH = os.path.join(DATABASEPATH, CAFFEINE, "Subjects.tsv")
LITERATUREPATH = os.path.join(DATABASEPATH, CAFFEINE, "literature")
PHARMACOKINETICSPATH = os.path.join(DATABASEPATH, CAFFEINE, "Pharmacokinetics.tsv")
INTERVENTIONSPATH = os.path.join(DATABASEPATH, CAFFEINE, "Interventions.tsv")
DOSINGPATH = os.path.join(DATABASEPATH, CAFFEINE, "Dosing.tsv")
MASTERPATH = os.path.join(DATABASEPATH, "Master")
REFERENCESMASTERPATH = os.path.join(MASTERPATH, "Studies")
INDIVIDUALPATH = os.path.join(DATABASEPATH, CAFFEINE, "Individuals.tsv")
TIMECOURSEPATH = os.path.join(DATABASEPATH, CAFFEINE, "Timecourse.tsv")
OUTPUTINDIVIDUALPATH = os.path.join(DATABASEPATH, CAFFEINE, "OutputIndividuals.tsv")



def extract_references(path):
    reader = csv.DictReader(open(path), delimiter='\t')
    for line in reader:
        yield dict(line)


def pmid_to_int(d):
    d['sid'] = int(d['pmid'])
    d['pmid'] = int(d['pmid'])

    yield d


def add_reference_sid(d):
    sid = str(d["study"])
    yield {**d , 'name': sid}


def add_reference_path(d):
    reference_path = os.path.join(REFERENCESMASTERPATH, d['name'])
    return {**d, "reference_path":reference_path}


def load_from_biopython(d):

    Entrez.email = 'janekg89@hotmail.de'
    handle = Entrez.efetch(db='pubmed', id=d['pmid'], retmode='xml')
    all_info = handle.read()
    handle.close()
    return {**d, 'xml': all_info}


def xml_to_data(d):
    return {**d, 'data': ET.fromstring(d['xml'])}



def create_json(d):
    json_dict = {}
    json_dict["pmid"] = d["pmid"]
    json_dict["name"] = d["name"]
    json_dict["sid"] = d["pmid"]
    for date in d["data"].iter("DateCompleted"):
        year = date.find('Year').text
        month = date.find('Month').text
        day = date.find('Day').text
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
    return {'json': json_dict, 'reference_path' : d["reference_path"]}


def add_doi(d):
    json_dict = d["json"]
    response = requests.get(f'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=my_tool&email=my_email@example.com&ids={json_dict["pmid"]}')
    pmcids = ET.fromstring(response.content)
    for records in pmcids.iter("record"):
         json_dict["doi"] = records.get('doi', "")


    return {"json":json_dict, "reference_path": d["reference_path"]}

def save_json(d):
    json_file = os.path.join(d["reference_path"],"reference.json")
    ensure_dir(json_file)
    with open(json_file, 'w') as fp:
        json.dump(d['json'],fp, indent=4)

def add_resources(d):
    """
    inputs the result of "add_reference_path()" from add reference path
    :param d:
    :return:
    """
    for file in os.listdir(LITERATUREPATH):
        if file.startswith(d['name']):
            src = os.path.join(LITERATUREPATH,file)
            dst = os.path.join(d["reference_path"],file)
            ensure_dir(dst)
            shutil.copy(src,dst)



collect_reference = [extract_references(REFERENCESPATH),
        pmid_to_int,
        add_reference_sid,
        add_reference_path,]

def get_graph(**options):
    """ Bonobo execution graph.

    :param options:
    :return:
    """
    graph = bonobo.Graph()

    #adds reference to
    graph.add_chain(*collect_reference)

    graph.add_chain(
        load_from_biopython,
        xml_to_data,
        create_json,
        add_doi,
        save_json,
        _input= add_reference_path)


    graph.add_chain(add_resources, _input= add_reference_path)

    return graph


def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph(**options), services=get_services(**options))