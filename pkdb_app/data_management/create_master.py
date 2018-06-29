import os
import csv
import sys
import bonobo
import xml.etree.ElementTree as ET
from Bio import Entrez
import json

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
Master = os.path.join(BASEPATH,"Master")
if BASEPATH not in sys.path:
    sys.path.append(BASEPATH)

DATABASEPATH = os.path.join(BASEPATH, "data")
STUDIESPATH = os.path.join(DATABASEPATH, "caffeine", "Studies.tsv")
SUBJECTSPATH = os.path.join(DATABASEPATH, "caffeine", "Subjects.tsv")
PHARMACOKINETICSPATH = os.path.join(DATABASEPATH, "caffeine", "Pharmacokinetics.tsv")
INTERVENTIONSPATH = os.path.join(DATABASEPATH, "caffeine", "Interventions.tsv")
DOSINGPATH = os.path.join(DATABASEPATH, "caffeine", "Dosing.tsv")
MASTERPATH =     os.path.join(DATABASEPATH, "Master")
STUDIESMASTERPATH = os.path.join(MASTERPATH, "Studies")


def extract_studies(path):
    reader = csv.DictReader(open(path),delimiter='\t')
    for line in reader:
        yield dict(line)


def pmid_to_int(d):
    d['pmid'] = int(d['pmid'])
    yield d


def add_study_sid(d):
    sid = str(d["study"])
    yield {**d ,'sid':sid}


def add_study_path(d):
    study_path = os.path.join(STUDIESMASTERPATH, d['sid'])
    yield {**d, "study_path":study_path}


def load_from_biopython(d):
    Entrez.email = 'janekg89@hotmail.de'
    handle = Entrez.efetch(db='pubmed', id=d['pmid'], retmode='xml')
    all_info = handle.read()
    handle.close()
    yield {**d, 'xml': all_info}


def xml_to_data(d):
    yield {**d, 'data': ET.fromstring(d['xml'])}


def create_json(d):
    json_dict = {}
    for title in d["data"].iter("ArticleTitle"):
        json_dict["title"] = title.text
        continue
    for abstract in d["data"].iter("AbstractText"):
        json_dict["abstract"] = abstract.text
        continue
    json_dict["pmid"] = d["pmid"]
    authors = []
    for author in d["data"].iter("Author"):
        author_dict = {}
        author_dict["first_name"] = author.find("ForeName").text
        author_dict["last_name"] = author.find("LastName").text
        authors.append(author_dict)
    json_dict["authors"] = authors
    return {'json': json_dict, 'study_path' : d["study_path"]}


#save
def save_json(d):
    json_file = os.path.join(d["study_path"],"data.json")
    with open(json_file, 'w') as fp:
        json.dump(d['json'],fp, indent=4)


def get_graph(**options):
    graph = bonobo.Graph()
    graph.add_chain(
        extract_studies(STUDIESPATH),
        pmid_to_int,
        add_study_sid,
        add_study_path,
        load_from_biopython,
        xml_to_data,
        create_json,
        save_json,
    )
    return graph


def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph(**options), services=get_services(**options))