# Curation information
Collection of resources and information on how to curate data and information
from manuscripts for the PKDB.

A single study is hereby stored in one folder which can be uploaded and iteratively curated using the `watch_study` script
```
cd pkdb
(pkdb) python pkdb_app/data_management/watch_study.py -s $STUDYFOLDER
```

## 1. PDF, Reference, Figures & Tables
For upload a certain folder structure and organisation is expected of the `$STUDYFOLDER`:
- folder name is `STUDYNAME`, e.g., Albert1974
- folder contains the pdf as `STUDYNAME.pdf`, e.g., Albert1974.pdf
- folder contains study information as `study.json`
- folder contains reference information as `reference.json`
- folder contains additional files associated with study, i.e.,
    - tables, named `STUDYNAME_Tab[0-9]*.png`, e.g., Albert1974_Tab1.png
    - figures, named `STUDYNAME_Fig[0-9]*.png`, e.g., Albert1974_Fig2.png
    - excel file, named `STUDYNAME.xlsx`, e.g., Albert1974.xlsx
    - data files, named `STUDYNAME_Tab[0-9]*.csv` or `STUDYNAME_Fig[0-9]*.csv`

## 2. Initial study information (`study.json`)
Fill in basic information for study, use the `PMID` for `sid` and `reference` field, use StudyName for `name` field.
 
```json
{
    "sid": 123456789,
    "pkdb_version": 1.0,
    "creator": "mkoenig",
    "name": "Author2007",
    "design": "",
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
* The `creator` and `curators` should map to existing data base users (but is no requirement for now).
* The `reference` field is optional. If no pubmed entry exist for publication a `reference.json` should be build manually. This will be documented later on.
* Substances which are used in the study and are of interest should be mentioned in the `substances` list.
* Keywords relevant for the study should be mentioned in the `keywords` list. 


## 3. Curation of groups/groupset and individuals/individualset
The next step is curating the groups used in the study. The information is stored in the `groupset` of the following form.
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
            "unit": "h"
          }
        ]
      },
      {
        "count": 10,
        "name": "nonobese",
        "parent": "all",
        "characteristica": [
          {
            "category": "sex",
            "count": "5 || 5",
            "choice": "M || F"
          },
          {
            "category": "age",
            "mean": "31",
            "min": "17",
            "max": "45",
            "unit": "yr"
          },
          {
            "category": "weight",
            "mean": "78.5",
            "min": "67",
            "max": "112",
            "unit": "kg"
          },
          {
            "category": "obesity index",
            "mean": "104",
            "min": "92",
            "max": "114",
            "unit": "%"
          }
        ]
      }
    ]
  }
}
```
* The groups are defined via `characteristica`, shared characteristica of groups can be defined via parent groups.
* The possible values of categorial are accessible via the curation web interface and in `categorials.py`.
* The group names have to be unique within the groupset and should be descriptive, e.g., smoker, nonsmoker, contraceptive.

All available fields for characteristica on group are:
```json
{
    "count": "int",
    "name": "string",
    "parent": "string",
    "category": "categorial",
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
* Inclusion and exclusion criteria for study can be defined via the `ctype` on groupset or group with values in {`exclusion`, `inclusion`}

Individuals are curated like groups with the exception that individuals must belong
to a given group, i.e., the `group` attribute must be set.

## 4. Curation of interventions/interventionset
```json
{
    "interventionset": {
        "description": "All patients and volunteers fasted overnight and, at 0800 hours, were given orally 300 mg caffeine dissolved in 150 ml water; food intake was allowed 3 h after administration of caffeine.",
        "interventions": [
            {
                "name": "D1",
                "substance": "caffeine",
                "time": "0",
                "time_unit": "h",
                "route": "oral",
                "value": 300.0,
                "unit": "mg"
            }
        ]
    }
}
```
All available fields for intervention and interventionset are:
```json
{
 
    "name": "string",  // not on groupset, only on group
    "category": "categorial",
    
    "substance": "categorial (substance)",
    "route": "categorial {oral, iv}",
    "application": "categorial {'single dose', 'multiple doses', 'continuous injection'}",
    "form": "categorial {'tablete', 'capsule', ...}",
    "time": "double||double||double ...",
    "time_unit": "categorial",
     
    // valueable field
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


## Open issues
- individual set
- time course data
- column data