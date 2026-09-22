"""Module for working with scientific references.

Creates reference.json from given pubmed id.
Pubmed information is retrieved using web services.
"""

import json
import logging
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any, Final

import requests
from Bio import Entrez
from pymetadata.console import console

from pkdb_data.management.utils import recursive_iter, set_keys

logger = logging.getLogger(__name__)
entrez_email: Final = "janekg89@hotmail.de"
reference_filename: Final = "reference.json"


def create_reference_for_pmid(study_name: str, pmid: str, output_path: Path) -> None:
    """Run function."""
    xml = load_pmid_from_biopython(pmid)

    # create json
    json_dict: dict[str, Any] = {"sid": pmid, "name": study_name}
    # an arbitrary reference string creates a template without pmid
    if pmid.isdigit():
        json_dict["pmid"] = int(pmid)

    xml_data = ET.fromstring(xml)

    for date in xml_data.iter("DateCompleted"):
        year = date.find("Year").text  # type: ignore
        month = date.find("Month").text  # type: ignore
        day = date.find("Day").text  # type: ignore
        json_dict["date"] = f"{year}-{str(month).zfill(2)}-{str(day).zfill(2)}"
        break

    for journal in xml_data.iter("Title"):
        json_dict["journal"] = journal.text
        break

    for title in xml_data.iter("ArticleTitle"):
        json_dict["title"] = title.text
        break
    for abstract in xml_data.iter("AbstractText"):
        json_dict["abstract"] = abstract.text
        break

    authors = []
    for author in xml_data.iter("Author"):
        author_dict = {}
        for key, value in {"first_name": "ForeName", "last_name": "LastName"}.items():
            try:
                author_dict[key] = author.find(value).text  # type: ignore
            except AttributeError:
                msg = (
                    f"No information on author <{key}>. Consider adding the {key} "
                    "manually to <reference.json>."
                )
                logger.warning(msg)
        authors.append(author_dict)

    json_dict["authors"] = authors
    json_dict["doi"] = ""  # get_doi_for_pmid(pmid)
    # FIXME: https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=PubMed&tool=Zotero&retmode=xml&rettype=citation&id=19688338

    for keys, item in recursive_iter(json_dict):
        if item == "":
            set_keys(json_dict, None, *keys)

    # serialize data
    with open(Path(output_path) / reference_filename, "w") as f_json:
        json.dump(json_dict, fp=f_json, indent=2)


def load_pmid_from_biopython(pmid: str) -> str:
    """Retrieve pubmed information using biopython."""
    # biopython initializes `Entrez.email` with None and infers that type
    Entrez.email = entrez_email  # ty: ignore[invalid-assignment]

    xml_str: str
    try:
        pmid_int: int = int(pmid)
        handle = Entrez.efetch(db="pubmed", id=pmid_int, retmode="xml")
        xml_str = handle.read()
        handle.close()
    except ValueError:
        logger.warning(
            "Empty `reference.json` created. Fill out required fields "
            "['title', 'date']. "
        )
        xml_str = (
            "<all>"
            "<PMID> 12345 </PMID>"
            "<DateCompleted>"
            "<Year>1000</Year>"
            "<Month>10</Month>"
            "<Day>10</Day>"
            "</DateCompleted>"
            "<Article>"
            "<Journal>"
            "<Title>Add your title</Title>"
            "</Journal>"
            "<ArticleTitle>Add your title</ArticleTitle>"
            "<AuthorList>"
            "<Author>"
            "<LastName>Mustermann</LastName>"
            "<ForeName>Max</ForeName>"
            "<Initials>MM</Initials>"
            "</Author>"
            "</AuthorList>"
            "</Article>"
            "</all>"
        )

    # console.print(xml_str)
    return xml_str


def get_doi_for_pmid(pmid: str) -> str | None:
    """Get DOI for pubmed."""
    url: str = f"https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?tool=pkdb&email=koenigmx@hu-berlin.de&ids={pmid}"
    response = requests.get(url)
    text = response.content
    console.rule()
    console.print(text)
    console.rule()

    response.raise_for_status()

    pmcids = ET.fromstring(text)

    for records in pmcids.iter("record"):
        record_doi = records.get("doi", None)
        if record_doi:
            return record_doi

    return None
