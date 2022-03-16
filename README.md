[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.1406979.svg)](https://doi.org/10.5281/zenodo.1406979)
[![License (LGPL version 3)](https://img.shields.io/badge/license-LGPLv3.0-blue.svg?style=flat-square)](http://opensource.org/licenses/LGPL-3.0)

<b><a href="https://orcid.org/0000-0002-4588-4925" title="0000-0002-4588-4925"><img src="./docs/images/orcid.png" height="15"/></a> Jan Grzegorzewski</b>
and
<b><a href="https://orcid.org/0000-0003-1725-179X" title="https://orcid.org/0000-0003-1725-179X"><img src="./docs/images/orcid.png" height="15" width="15"/></a> Matthias König</b>

# PK-DB - a pharmacokinetics database

* [Overview](https://github.com/matthiaskoenig/pkdb#overview)
* [How to cite](https://github.com/matthiaskoenig/pkdb#how-to-cite)
* [License](https://github.com/matthiaskoenig/pkdb#license)
* [Funding](https://github.com/matthiaskoenig/pkdb#funding)

## Overview
[PK-DB](https://pk-db.com) is a database and web interface for pharmacokinetics data and information from clinical trials 
as well as pre-clinical research. PK-DB allows to curate pharmacokinetics data integrated with the 
corresponding meta-information 
- characteristics of studied patient collectives and individuals (age, bodyweight, smoking status, ...) 
- applied interventions (e.g., dosing, substance, route of application)
- measured pharmacokinetics time courses and pharmacokinetics parameters (e.g., clearance, half-life, ...). 

Important features are 
- the representation of experimental errors and variation
- the representation and normalisation of units
- annotation of information to biological ontologies
- calculation of pharmacokinetics information from time courses (apparent clearance, half-life, ...)
- a workflow for collaborative data curation
- strong validation rules on data, and simple access via a REST API

PK-DB is available at https://pk-db.com and https://alpha.pk-db.com. The terms of use are listed in the [`TERMS_OF_USE.md`](./TERMS_OF_USE.md).

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
* Source Code: [LGPLv3](http://opensource.org/licenses/LGPL-3.0)
* Documentation: [CC BY-SA 4.0](http://creativecommons.org/licenses/by-sa/4.0/)

## Funding
Jan Grzegorzewski and Matthias König are supported by the Federal Ministry of Education and Research (BMBF, Germany)
within the research network Systems Medicine of the Liver ([LiSyM](http://www.lisym.org/), grant number 031L0054).
Matthias König is supported by the German Research Foundation (DFG) within the Research Unit Programme FOR 5151 
[QuaLiPerF](https://qualiperf.de) (Quantifying Liver Perfusion-Function Relationship in Complex Resection - 
A Systems Medicine Approach) by grant number 436883643 and by grant number 
465194077 (Priority Programme SPP 2311, Subproject SimLivA).

&copy; 2017-2022 Jan Grzegorzewski & Matthias König; https://livermetabolism.com.
