<img src="pkdb_logo.png" alt="PK-DB logo" width="200">

# PK-DB – The Pharmacokinetics Database

[PK-DB](https://pk-db.com) is an open database and web platform for the **curation, integration, validation, and analysis of pharmacokinetic (PK) data** from clinical studies and preclinical research.

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

PK-DB is available from [https://pk-db.com](https://pk-db.com). The terms of use are listed in the [`TERMS_OF_USE.md`](https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md).

The source code is at [https://github.com/matthiaskoenig/pkdb](https://github.com/matthiaskoenig/pkdb).

## How to cite
If you use PK-DB data or the web interface cite

> Grzegorzewski J, Brandhorst J, Green K, Eleftheriadou D, Duport Y, Barthorscht F, Köller A, Ke DYJ, De Angelis S, König M. *PK-DB: pharmacokinetics database for individualized and stratified computational modeling*. Nucleic Acids Res. 2021 Jan 8;49(D1):D1358-D1364. doi: [10.1093/nar/gkaa990](https://doi.org/10.1093/nar/gkaa990). PMID: [33151297](https://pubmed.ncbi.nlm.nih.gov/33151297/).

If you use PK-DB code cite in addition

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979)

## Contents

- **[Installation](installation.md)** - run a local development stack with docker compose.
- **[Deployment](deployment.md)** - runtime configuration, persistent storage, and backup requirements.
- **[Development](development.md)** - branch model, repository policies, tooling and release.
- **[Local upload testing](local-upload-testing.md)** - validate and upload your own study with Docker.
- **[Contributing](contributing.md)** - step by step guide for a first contribution.

## Data

Due to copyright, licensing and privacy issues the `pkdb` repository does not contain any data. The curated study data, the curation scripts and the curation workflows are managed in the separate repository [pkdb_data](https://github.com/matthiaskoenig/pkdb_data). If you are interested in curating data or contributing data, contact us at [https://livermetabolism.com](https://livermetabolism.com).

If you have any questions or issues please [open an issue](https://github.com/matthiaskoenig/pkdb/issues).

## License

PK-DB code and documentation is licensed as

- Source Code: [MIT](https://opensource.org/license/MIT)
- Documentation: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

The terms of use of the PK-DB website and API are listed in [TERMS_OF_USE.md](https://github.com/matthiaskoenig/pkdb/blob/develop/TERMS_OF_USE.md).

## Funding
Matthias König (MK) and Jan Grzegorzewski were supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research network Systems Medicine of the Liver (LiSyM, grant number 031L0054). MK is supported by the Federal Ministry of Education and Research (BMBF, Germany) within ATLAS by grant number 031L0304B and by the German Research Foundation (DFG) within the Research Unit Program FOR 5151 QuaLiPerF (Quantifying Liver Perfusion-Function Relationship in Complex Resection - A Systems Medicine Approach) by grant number 436883643 and by grant number 465194077 (Priority Programme SPP 2311, Subproject SimLivA).

&copy; 2017-2026 Matthias König; https://livermetabolism.com.
