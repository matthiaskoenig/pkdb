# PKDB - Pharmacokinetics database

<b><a href="https://orcid.org/0000-0003-1725-179X" title="https://orcid.org/0000-0003-1725-179X"><img src="./docs/images/orcid.png" height="15" width="15"/></a> Matthias König</b>

Database for storing pharmacokinetics information.
This includes
- study data (publication data)
- trial design
- subjects information
- interventions
- dosing schemas
- pharmacokinetics parameters (
- timecourse data


<img src="./docs/images/data_extraction.png" />

## pharmacokinetics
Pharmacokinetics data is hereby a subclass of experimental data. 
These are the numerical values which are normally reported in publications.
The form can vary (mean, median) and also the error terms associated with the values (SD, SE, CV, Range). 
In addition the number of subjects is important as well (n), to be able to convert between different error
measurments.

# Setup & Installation
```
mkvirtualenv pkdb --python=python3
(pkdb) pip install -r requirements.txt
```

----
&copy; 2018 Matthias König.