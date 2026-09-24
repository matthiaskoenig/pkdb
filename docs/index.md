<img src="pkdb_logo.png" alt="PK-DB logo" width="200">

[![PyPI](https://img.shields.io/pypi/v/pkdb.svg)](https://pypi.org/project/pkdb/) [![Python versions](https://img.shields.io/pypi/pyversions/pkdb.svg)](https://pypi.org/project/pkdb/)

# PK-DB – The Pharmacokinetics Database

[PK-DB](https://alpha.pk-db.com) is an open database and web platform for the **curation, integration, validation, and analysis of pharmacokinetic (PK) data** from clinical studies and preclinical research.

!!! important "PK-DB update in progress"

    PK-DB and its API are currently being updated. A new release with an improved data model, validation, documentation, and API will be available shortly.

PK-DB connects pharmacokinetic measurements with their complete experimental and study context. It supports the structured representation of:

- **Study populations and individuals**, including characteristics such as age, sex, body weight, health status, and smoking status
- **Interventions**, including administered substances, doses, dosing schedules, and routes of administration
- **Pharmacokinetic measurements**, including concentration–time courses and derived PK parameters such as clearance, half-life, area under the curve (AUC), and maximum concentration (Cmax)
- **Study and experimental metadata**, linking measurements to the conditions under which they were obtained

Key features of PK-DB include:

- Representation of **measurement uncertainty, variability, and experimental error**
- **Normalization and harmonization of units** for consistent comparison and analysis
- Semantic annotation using **biological and biomedical ontologies**
- Automated calculation of pharmacokinetic parameters from concentration–time courses
- Workflows for **collaborative and reproducible data curation**
- Extensive **data validation and quality-control rules**
- Programmatic access through a **REST API** for integration into analysis, modeling, and automated workflows

By combining pharmacokinetic data with structured metadata, semantic annotations, validation, and programmatic access, PK-DB provides a foundation for **reproducible pharmacokinetic analyses, meta-analyses, PBPK modeling, and the development of pharmacological digital twins**.

![PK-DB overview](images/pkdb_overview.png)

PK-DB is available from [https://alpha.pk-db.com](https://alpha.pk-db.com). The terms of use are listed in the [Terms of use](terms-of-use.md).

PK-DB is developed by the [Systems Medicine of the Liver Group](https://livermetabolism.com) at Humboldt University Berlin.

The source code is at [https://github.com/matthiaskoenig/pkdb](https://github.com/matthiaskoenig/pkdb).

## Webinterface

Open [alpha.pk-db.com](https://alpha.pk-db.com) and choose **Explore data** to explore studies, subjects, interventions, and measurements. Public browsing needs no account; sign in for dataset and attachment downloads. Start with the illustrated [Web interface guide](web-interface.md).

## Example study

Follow the [example study](example-study.md) to see how a publication connects to structured subjects, interventions, and measurements.

## API

Install [pkdb from PyPI](https://pypi.org/project/pkdb/) with Python 3.14 or 3.15:

```bash
python -m pip install pkdb
```

```python
from pkdb import Client

with Client(endpoint="https://alpha.pk-db.com") as client:
    page = client.studies.list(page=1, page_size=20)
    for study in page.items:
        print(study.sid)
```

Start with [Accounts and API keys](authentication.md) for authenticated access, then see [REST API](api.md) for HTTP examples and [Python client](python-client.md) for queries, downloads, and data curation. All curation examples use `https://alpha.pk-db.com`.

## Development

!!! important "For developers and operators only"

    General users should use the website or install the PyPI package. Source installation and local hosting are development workflows.

See [Development](development.md) for installing the package from source, working against a local development instance, running tests, and deployment.

## Documentation

Read the [documentation](https://matthiaskoenig.github.io/pkdb/) in order: **Introduction**, **Webinterface**, then **API**, starting with **Accounts and API keys** before **REST API** and **Python client**. **Development** is for work on the codebase.

## How to cite

See [Citing PK-DB](citation.md) for the database publication and software citation.

## Data

Due to copyright, licensing and privacy issues the `pkdb` repository does not contain any data. The curated study data, the curation scripts and the curation workflows are managed in the separate repository [pkdb_data](https://github.com/matthiaskoenig/pkdb_data).

## License

PK-DB code and documentation is licensed as

- Source Code: [MIT](https://opensource.org/license/MIT)
- Documentation: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

The terms of use of the PK-DB website and API are listed in [Terms of use](terms-of-use.md).

## Funding

Matthias König (MK) and Jan Grzegorzewski were supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research network Systems Medicine of the Liver (LiSyM, grant number 031L0054). MK is supported by the Federal Ministry of Education and Research (BMBF, Germany) within ATLAS by grant number 031L0304B and by the German Research Foundation (DFG) within the Research Unit Program FOR 5151 QuaLiPerF (Quantifying Liver Perfusion-Function Relationship in Complex Resection - A Systems Medicine Approach) by grant number 436883643 and by grant number 465194077 (Priority Programme SPP 2311, Subproject SimLivA).

The infrastructure is provided by the BMBF-funded de.NBI Cloud within the German Network for Bioinformatics Infrastructure (de.NBI), grants 031A537B, 031A533A, 031A538A, 031A533B, 031A535A, 031A537C, 031A534A, and 031A532B.

&copy; 2017-2026 Matthias König; https://livermetabolism.com.
