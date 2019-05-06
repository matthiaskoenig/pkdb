# Curation of pharmacokinetics studies for PK-DB
This document provides resources and information on how to curate data and information
from pharmacokinetics studies for the PK-DB database.

Available choices for important fields are available from the PK-DB frontend  
https://develop.pk-db.com/#/curation

If things are unclear during curation or you find incorrect or missing information in 
this document please open an issue at  
https://github.com/matthiaskoenig/pkdb/issues  
with the label `data curation`.



## Interactive curation
All information of a single study is stored in one folder. The complete information can be uploaded 
and iteratively curated using the provided `watch_study` script. The script uploads 
the latest data on file changes therefore allowing rapid iteration of curation and 
validation. Information on how to setup the `watch_study` script is provided
in https://github.com/matthiaskoenig/pkdb_data

```
# activate virtualenv with watch_study script
workon pkdb_data

# export environment variables for backend
(pkdb_data) set -a && source .env.local

# run the watch script
(pkdb_data) watch_study -s $STUDYFOLDER
```

## 1. PDF, Reference, Figures & Tables
For upload a certain folder structure and organisation is expected of the `$STUDYFOLDER`:
- folder name is `STUDYNAME`, e.g., Albert1974
- folder contains the pdf as `STUDYNAME.pdf`, e.g., Albert1974.pdf
- folder contains study information as `study.json`
- folder contains additional files associated with study, i.e.,
    - tables, named `STUDYNAME_Tab[1-9]*.png`, e.g., Albert1974_Tab1.png
    - figures, named `STUDYNAME_Fig[1-9]*.png`, e.g., Albert1974_Fig2.png
    - excel file, named `STUDYNAME.xlsx`, e.g., Albert1974.xlsx
    - data files, named `STUDYNAME_Tab[1-9]*.csv` or `STUDYNAME_Fig[1-9]*.csv`


## 2. Initial study information (`study.json`)
For modifying the json best use Atom with pretty-json and settings `Notify on Parse Error` and `Prettify on Save JSON`.

Fill in basic information for study, use the `PMID` for `sid` and `reference` field, use StudyName for `name` field and `creator` and `curator` fields.
 
```json
{
    "sid": 123456789,
    "pkdb_version": 1.0,
    "creator": "mkoenig",
    "name": "Author2007",
    "reference": 123456789,
    "curators": [
        "mkoenig",
        "janekg"
    ],
    "substances": [],
    "keywords": [],
    "descriptions": [],
    "comments": [],
    "groupset": {
        "descriptions": [],
        "comments": [],
        "groups": []
    },
    "individualset": {
        "descriptions": [],
        "comments": [],
        "individuals": []
    },
    "interventionset": {
      "descriptions": [],
      "comments": [],
      "interventions": []
    },
    "outputset": {
      "descriptions": [],
      "comments": [],
      "outputs": [],
      "timecourses": []
    }
}
```
* The `creator` and `curators` should map to existing data base users.
* The `reference` field is optional. If no pubmed entry exist for publication a `reference.json` should be build manually.
* Substances which are used in the study and are of interest should be mentioned in the `substances` list.
* `keywords` and `substances` relevant for the study should be mentioned in the `keywords` list. `keywords` are documented in `pkdb_app/categorials`, `substances` are documented in `pkdb_app/substances/substances.py`


## 3. Curation of groups/groupset and individuals/individualset
The next step is curating the groups used in the study. The information is stored in the `groupset` of the following form.
Retrieve group information from the publication. The top group containing all subjects must be called `all`.
```json
{
  "groupset": {
    "description": [
      "This is a first description.",
      "This is a second description."
    ],
    "comments": [],
    "groups": [
      {
        "count": 20,
        "name": "all",
        "characteristica": [
          {
            "category": "species",
            "choice": "homo sapiens"
          },
          {
            "category": "healthy",
            "choice": "Y"
          },
          {
            "category": "overnight fast",
            "choice": "Y"
          },
          {
            "category": "fasted",
            "min": "10",
            "max": "14",
            "unit": "hr"
          }
        ]
      }
    ]
  }
}
```
* The groups are defined via `characteristica`, shared characteristica of groups can be defined via parent groups.
* The possible values of categorial are accessible via `pkdb_app/categorials.py`.
* The group names have to be unique within the groupset and should be descriptive, e.g., smoker, nonsmoker, contraceptive.
* All groups require a `name`, all groups with exception of `all` require `parent` field.
    "parent": "string",

All available fields for characteristica on group are:
```json
{
    "category": "categorial",
    "choice": "categorial|string",
    "count": "int",
    "mean": "double",
    "median": "double",
    "min": "double",
    "max": "double",
    "sd": "double",
    "se": "double",
    "cv": "double",
    "unit": "categorial"
}
```

Individuals are curated like groups with the exception that individuals must belong
to a given group, i.e., the `group` attribute must be set. Individuals are most often defined via excel spreadsheets.

## 4. Curation of interventions/interventionset
```json
{
    "interventionset": {
        "description": "All patients and volunteers fasted overnight and, at 0800 hours, were given orally 300 mg caffeine dissolved in 150 ml water; food intake was allowed 3 h after administration of caffeine.",
        "interventions": [
          {
            "name": "glciv",
            "substance": "glucose",
            "route": "iv",
            "form": "solution",
            "application": "single dose",
            "category": "dosing",
            "value": "0.5",
            "unit": "g/kg",
            "time": "0",
            "time_unit": "hr"
          }
        ]
    }
}
```
All available fields for intervention and interventionset are:
```json
{
 
    "name": "string",
    "category": "categorial",
    
    "substance": "categorial (substance)",
    "route": "categorial {oral, iv}",
    "application": "categorial {'single dose', 'multiple doses', 'continuous injection'}",
    "form": "categorial {'tablete', 'capsule', ...}",
    "time": "double||double||double ...",
    "time_unit": "categorial",
     
    "choice": "categorial|string",
    "value": "double",
    "mean": "double",
    "median": "double",
    "min": "double",
    "max": "double",
    "sd": "double",
    "se": "double",
    "cv": "double",
    "unit": "categorial"
}
```
* TODO: document after next iteration

## 5. Curation of output/outputset
Data from Figures should be digized using plot digitizer. See guidelines in

- Use Excel (LibreOffice/OpenOffice) spreadsheets to store data, with all digitized data is stored in excel spreadsheets
- change language settings to use US numbers and formats, i.e. ‘.’ separator). Always use points (‘.’) as number separator, never comma (‘,’), i.e. 1.234 instead of 1,234.
- PlotDigitizer to digitize figures (https://sourceforge.net/projects/plotdigitizer/)

```json

{
        "source": "Akinyinka2000_Tab3.csv",
        "format": "TSV",
        "subset": "substance==paraxanthine",
        "figure": "Akinyinka2000_Tab3.png",
        "group": "healthy subjects",
        "interventions": [
            "Dcaf"
        ],
        "substance": "paraxanthine",
        "tissue": "col==tissue",
        "pktype": "cmax || tmax || auc_inf || thalf",
        "mean": "col==cmax || col==tmax || col==aucinf || col==thalf",
        "sd": "col==cmax_sd || col==tmax_sd || col==aucinf_sd || col==thalf_sd",
        "unit": "\u00b5g/ml || hr || \u00b5g*hr/ml || hr"
    }
```


## Units for curation
Pint units:
https://github.com/hgrecco/pint/blob/master/pint/default_en_0.6.txt


## Open issues
- individual set
- time course data
- column data

## Frequently asked questions (FAQ)
# How to encode multiple substances which are given (e.g., caffeine and acetaminophen are given)?
- encode as individual interventions of caffeine and acetaminophen, i.e., single interventions 
with the respective doses. In the outputs a list of intervention is provided, i.e., in this example the interventions for caffeine and acetaminophen


