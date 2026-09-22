[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979)
[![MIT License](https://img.shields.io/pypi/l/pymetadata.svg)](https://opensource.org/licenses/MIT)

# PK-DB - The Pharmacokinetics Database

<img src="./docs/pkdb_logo.png" width="200">

[PK-DB](https://pk-db.com) is a database and web interface for pharmacokinetics data and information from clinical trials as well as pre-clinical research.  
PK-DB allows the curation of pharmacokinetics data integrated with the corresponding meta-information, including:

- characteristics of studied patient collectives and individuals (e.g., age, body weight, smoking status, …)  
- applied interventions (e.g., dosing, substance, route of administration)  
- measured pharmacokinetics time courses and pharmacokinetics parameters (e.g., clearance, half-life, …)  

Important features include:

- representation of experimental errors and variation  
- normalization and consistent representation of units  
- annotation of information with biological ontologies  
- calculation of pharmacokinetics information from time courses (e.g., apparent clearance, half-life, …)  
- workflows for collaborative data curation  
- strong validation rules on data and simple access via a REST API  

PK-DB is available at [https://pk-db.com](https://pk-db.com) and [https://alpha.pk-db.com](https://alpha.pk-db.com).  
The terms of use are listed in the [`TERMS_OF_USE.md`](./TERMS_OF_USE.md).

![PK-DB overview](./docs/images/data_extraction.png)

## How to cite
If you use PK-DB data or the web interface cite

> Grzegorzewski J, Brandhorst J, Green K, Eleftheriadou D, Duport Y, Barthorscht F, Köller A, Ke DYJ, De Angelis S, König M. 
> *PK-DB: pharmacokinetics database for individualized and stratified computational modeling*. 
> Nucleic Acids Res. 2020 Nov 5:gkaa990. doi: [10.1093/nar/gkaa990](https://doi.org/10.1093/nar/gkaa990). Epub ahead of print. PMID: [33151297](https://pubmed.ncbi.nlm.nih.gov/33151297/).

If you use PK-DB code cite in addition 

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979)

## License
PK-DB code and documentation is licensed as
- Source Code: [MIT](https://opensource.org/license/MIT)
- Documentation: [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/)

## Funding
Matthias König (MK) was supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research network Systems Medicine of the Liver (LiSyM, grant number 031L0054). MK is supported by the Federal Ministry of Education and Research (BMBF, Germany) within ATLAS by grant number 031L0304B and by the German Research Foundation (DFG) within the Research Unit Program FOR 5151 QuaLiPerF (Quantifying Liver Perfusion-Function Relationship in Complex Resection - A Systems Medicine Approach) by grant number 436883643 and by grant number 465194077 (Priority Programme SPP 2311, Subproject SimLivA).
Jan Grzegorzewski and Matthias König were supported by the Federal Ministry of Education and Research (BMBF, Germany) within the research network Systems Medicine of the Liver ([LiSyM](http://www.lisym.org/), grant number 031L0054).

&copy; 2017-2025 Jan Grzegorzewski & Matthias König; https://livermetabolism.com.
