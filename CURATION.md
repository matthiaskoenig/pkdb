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

For upload a certain folder structure and organisation is expected of the `$STUDYFOLDER`.
The first step is to create the folder and the basic files in the folder 

- folder name is `STUDYNAME`, e.g., `Albert1974`
- folder contains the pdf as `STUDYNAME.pdf`, e.g., `Albert1974.pdf`
- folder contains additional files associated with study, i.e.,
    - tables, named `STUDYNAME_Tab[1-9]*.png`, e.g., `Albert1974_Tab1.png`
    - figures, named `STUDYNAME_Fig[1-9]*.png`, e.g., `Albert1974_Fig2.png`
    - excel file, named `STUDYNAME.xlsx`, e.g., `Albert1974.xlsx`

In addition the folder can contain data files, 
named `STUDYNAME_Tab[1-9]*.tsv` or `STUDYNAME_Fig[1-9]*.tsv`
    The information is the excel file is the primary data source, i.e., the `*.tsv`
information is redundant and not guaranteed to be maintained.

Information about the study is stored in the `study.json` which we will create 
in the following steps. Information about the reference for the study is stored
in the `reference.json` (this file is created automatically and should not be altered).


## 2. Initial study information (`study.json`)

For modifying JSON files best use the `Atom` editor with the plugin `pretty-json` and activate the following 
settings `Notify on Parse Error` and `Prettify on Save JSON`.

If a `study.json` is already existing we will modify it in the following, if not 
now is the time to create a new `study.json` in the `$STUDYFOLDER`. The following template JSON
contains all the relevant information  
 
```json
{
    "sid": 123456789,
    "pkdb_version": 1.0,
    "creator": "mkoenig",
    "name": "Author2007",
    "reference": 123456789,
    "license": "open || closed",
    "access": "public || private",
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
* Fill in basic information for study, i.e., the `name` field with the `$STUDYNAME`, the `creator` and `curator` fields with existing users 
(creator is a single user, whereas curators is a list of users), 
the `sid` and `reference` field with the `PubmedId` of the study.  
* Substances which are used in the study should be listed in the `substances`. Substances must be existing substances which can be looked up at https://develop.pk-db.com/#/curation
* `keywords` relevant for the study should be mentioned in the `keywords` list. Keywords must be existing keywords which can be looked up at https://develop.pk-db.com/#/curation
* The `reference` field is optional. If no pubmed entry exist for publication a `reference.json` should be build manually (please ask what to do in such a case).

After this initial information is created in the `study_json` we can start running the `watch_study` script.
```
(pkdb_data) watch_study -s $STUDYFOLDER
```

## 3. Curation of groups
The next step is the curation of the `group` information, i.e., which groups where studied. The information is stored in the `groupset` of the following form.
Retrieve group information from the publication and copy it in the description of the groupset. The top group containing all subjects must be called `all`.

The main steps for defining groups is to set the `name` and `count` of the group (with `name` being `all` for the top-level group, or an arbitrary descriptive name
otherwise; the `count` is the number of subjects in the group. In addition to this core information a group is characterized by `characteristica`.
An overview over the available `characteristica` and possible choices is available from https://develop.pk-db.com/#/curation
```json
{
  "groupset": {
    "description": [
      "The subjects were six healthy volunteers, three males and three females, aged 21.0 ± 0.9 years (range 20 to 22 years) and weighing 63 ± 11 kg (range 50 to 76 kg). All were nonsmokers. Subjects abstained from all methylxanthine containing foods and beverages during the entire period of the study. Compliance with this requirement was assessed by questioning at each presentation for blood sampling or urine delivery."
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


