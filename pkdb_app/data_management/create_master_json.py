import os
import sys
import bonobo
import csv
from Bio import Entrez
import xml.etree.ElementTree as ET
import pandas as pd

BASEPATH = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), '../'))
Master = os.path.join(BASEPATH,"Master")
if BASEPATH not in sys.path:
    sys.path.append(BASEPATH)

DATABASEPATH = os.path.join(BASEPATH, "data")
path_studies = os.path.join(DATABASEPATH, "caffeine", "Studies.tsv")
path_subjects = os.path.join(DATABASEPATH, "caffeine", "Subjects.tsv")
path_pharmacokinetics = os.path.join(DATABASEPATH,"caffeine", "Pharmacokinetics.tsv")
path_interventions = os.path.join(DATABASEPATH,"caffeine", "Interventions.tsv")
path_dosing = os.path.join(DATABASEPATH,"caffeine", "Dosing.tsv")
path_master =     os.path.join(DATABASEPATH,"Master")
path_master_studies = os.path.join(path_master,"Studies")


def ensure_dir(file_path):
    directory = os.path.dirname(file_path)
    if not os.path.exists(directory):
        os.makedirs(directory)


def extract_studies(path):
    reader = csv.DictReader(open(path),delimiter='\t')
    for line in reader:
        yield dict(line)


def create_data(data_pd, file_name):
    for n, d in data_pd.groupby("study"):
        data_path = os.path.join(path_master_studies, n, file_name)
        ensure_dir(data_path)
        d.to_csv(data_path, sep="\t")

def split_into_study_folder(path,file_name):
    data_pd = pd.read_csv(path,delimiter='\t')
    create_data(data_pd, file_name)
    for row in data_pd.iterrows():
        yield row




def pmid_to_int(d):
    d['pmid'] = int(d['pmid'])
    yield d

def add_study_sid(d):
    sid = str(d["study"])
    yield {**d ,'sid':sid}

def create_study_folder(d):
    study_path = os.path.join(path_master_studies,d['sid'])
    ensure_dir(study_path)
    yield {**d, "study_path":study_path}


def load_from_biopython(d):
    Entrez.email = 'janekg89@hotmail.de'
    handle = Entrez.efetch(db='pubmed', id=d['pmid'], retmode='xml')
    all_info = handle.read()
    handle.close()
    yield {**d, 'xml': all_info}


def write_biopython_xml_to_file(d):
    file_path = os.path.join(d["study_path"],f'{d["sid"]}.xml')
    text_file = open(file_path, "w")
    text_file.write(d["xml"])
    text_file.close()
    yield {**d, 'data': ET.fromstring(d['xml'])}


def create_authors_file(d):
    file_path = os.path.join(d["study_path"],"authors.csv")

    with open(file_path, 'w+') as f:
        writer = csv.DictWriter(f, fieldnames=["first_name","last_name"])
        writer.writeheader()
    yield {**d, "file_path":file_path}


def get_authors_from_study(d):
    for author in d["data"].iter("Author"):
        d1 = {}
        d1["first_name"] = author.find("ForeName").text
        d1["last_name"] = author.find("LastName").text
        yield {"author": d1, "file_path": os.path.join(d["study_path"],"authors.csv")}


def write_authors(d):
    with open(d["file_path"], 'a') as f:
        writer = csv.DictWriter(f,fieldnames=["first_name","last_name"])
        writer.writerow(d["author"])


def get_graph(**options):
    graph = bonobo.Graph()
    #add studies
    graph.add_chain(
        extract_studies(path_studies),
        pmid_to_int,
        add_study_sid,
        create_study_folder,
        load_from_biopython,
        write_biopython_xml_to_file,
        create_authors_file,
        get_authors_from_study,
        write_authors
    )
    #add dosing
    graph.add_chain(
        split_into_study_folder(path_dosing,"Dosing.tsv"),
    )
    #add subjects
    graph.add_chain(
        split_into_study_folder(path_subjects,"Subjects.tsv"),
    )
    #add Pharmacokinetics
    graph.add_chain(
        split_into_study_folder(path_pharmacokinetics, "Pharmacokinetics.tsv"),
    )
    return graph


def get_services(**options):
    return {}


if __name__ == '__main__':
    parser = bonobo.get_argument_parser()
    with bonobo.parse_args(parser) as options:
        bonobo.run(get_graph(**options), services=get_services(**options))