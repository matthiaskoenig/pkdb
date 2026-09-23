<img src="./docs/pkdb_logo.png" width="200">

[![PyPI](https://img.shields.io/pypi/v/pkdb.svg)](https://pypi.org/project/pkdb/) [![Python versions](https://img.shields.io/pypi/pyversions/pkdb.svg)](https://pypi.org/project/pkdb/) [![CI-CD](https://github.com/matthiaskoenig/pkdb/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/matthiaskoenig/pkdb/actions/workflows/ci-cd.yml) [![ruff](https://github.com/matthiaskoenig/pkdb/actions/workflows/ruff.yml/badge.svg)](https://github.com/matthiaskoenig/pkdb/actions/workflows/ruff.yml) [![ty](https://github.com/matthiaskoenig/pkdb/actions/workflows/ty.yml/badge.svg)](https://github.com/matthiaskoenig/pkdb/actions/workflows/ty.yml) [![documentation](https://github.com/matthiaskoenig/pkdb/actions/workflows/docs.yml/badge.svg)](https://github.com/matthiaskoenig/pkdb/actions/workflows/docs.yml) [![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979) [![MIT License](https://img.shields.io/pypi/l/pkdb.svg)](https://opensource.org/licenses/MIT)

# PK-DB – The Pharmacokinetics Database

[PK-DB](https://alpha.pk-db.com) is an open database and web platform for the **curation, integration, validation, and analysis of pharmacokinetic (PK) data** from clinical studies and preclinical research.

> [!IMPORTANT]
> **PK-DB update in progress**
>
> PK-DB and its API are currently being updated. A new release with an improved data model, validation, documentation, and API will be available shortly.

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

![PK-DB overview](./docs/images/pkdb_overview.png)


PK-DB is available from [https://alpha.pk-db.com](https://alpha.pk-db.com). The terms of use are listed in the [`TERMS_OF_USE.md`](./TERMS_OF_USE.md).


## Browse and access data

Open [alpha.pk-db.com](https://alpha.pk-db.com) and choose **Explore data** to explore studies, subjects, interventions, and measurements. Public browsing needs no account; sign in for dataset and attachment downloads. Start with the illustrated [Web interface guide](docs/web-interface.md).

## Python client and API

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

See [Python client and API](docs/python-client.md) for queries, downloads, and data curation, [REST API](docs/api.md) for HTTP examples, and [Accounts and API keys](docs/authentication.md) for authenticated access. All curation examples use `https://alpha.pk-db.com`.

## Development

> [!IMPORTANT]
> This section is for developers and operators. General users should use the website or install the PyPI package; no local server or source checkout is needed.

See [Development](docs/development.md) for installing the package from source, working against a local development instance, running tests, and deployment.

## Documentation

Read the [documentation](https://matthiaskoenig.github.io/pkdb/) in order: **Browse and access data**, **Python client and API**, then **Development** when you work on the codebase.

## How to cite
If you use PK-DB data or the web interface cite

> Grzegorzewski J, Brandhorst J, Green K, Eleftheriadou D, Duport Y, Barthorscht F, Köller A, Ke DYJ, De Angelis S, König M. *PK-DB: pharmacokinetics database for individualized and stratified computational modeling*. Nucleic Acids Res. 2021 Jan 8;49(D1):D1358-D1364. doi: [10.1093/nar/gkaa990](https://doi.org/10.1093/nar/gkaa990). PMID: [33151297](https://pubmed.ncbi.nlm.nih.gov/33151297/).

If you use PK-DB code cite in addition 

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979)

## License
PK-DB code and documentation is licensed as
- Source Code: [MIT](https://opensource.org/license/MIT)
- Documentation: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

## Funding
Matthias König (MK) and Jan Grzegorzewski were supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research network Systems Medicine of the Liver (LiSyM, grant number 031L0054). MK is supported by the Federal Ministry of Education and Research (BMBF, Germany) within ATLAS by grant number 031L0304B and by the German Research Foundation (DFG) within the Research Unit Program FOR 5151 QuaLiPerF (Quantifying Liver Perfusion-Function Relationship in Complex Resection - A Systems Medicine Approach) by grant number 436883643 and by grant number 465194077 (Priority Programme SPP 2311, Subproject SimLivA).

&copy; 2017-2026 Matthias König; https://livermetabolism.com.
