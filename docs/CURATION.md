# Curation information
Collection of resources and information on how experimental data
should be curated from manuscripts for upload/inclusion in PKDB.

In the curation JSON files for the study and reference are created which are parsed
 by the model serializers
```
serializers.py
studies/serializers.py
interventions/serializers.py
subjects/serializers.py
```

## 1. PDF, Reference, Figures & Tables
For upload a certain folder structure is expected
- folder name is STUDYNAME, e.g., Albert1974
- folder contains pdf as STUDYNAME.pdf, e.g., Albert1974.pdf
- folder contains reference information as `reference.json`
- folder contains study information as `study.json`
- folder contains additional files associated with study, i.e.,
    - tables, named STUDYNAME_Tab[0-9]*.png, e.g., Albert1974_Tab1.png
    - figures, named STUDYNAME_Fig[0-9]*.png, e.g., Albert1974_Fig2.png
    - excel file, named STUDYNAME.xlsx, e.g., Albert1974.xlsx
    - data files, named STUDYNAME_Tab[0-9]*.csv or STUDYNAME_Fig[0-9]*.csv
* Start watchdog `watch_study.py` via pycharm with `-s PATH_TO_DIRECTORY` argument


## 2. Initial study information (`study.json`)
Fill in basic information for study, use the `PMID` for `sid` and `reference` field, use StudyName for `name` field.
 
```json
{
    "sid": 10877011,
    "pkdb_version": 1.0,
    "creator": "mkoenig",
    "name": "Akinyinka2000",
    "design": "parallel group",
    "reference": 10877011,
    "curators": [
        "mkoenig",
        "janekg"
    ],
    "substances": [
        "caffeine",
        "acetaminophen"
    ],
    "comments": [
      ["mkoenig", "Comment on the study"]
    ]
}
```
* The `creator` and `curators` should map to existing data base users (but is no requirement for now).
* The `reference` field is optional. If no pubmed entry exist for publication a `reference.json` should be build manually. This will be documented later on.
* Substances define which substances are mentioned/studied in the study.


## 3. Curation of groups/groupset
The next step is curating the groups used in the study. The information is stored in the `groupset` of the following form.
```json
{
  "groupset": {
        "description": "This is first part of description.||This is second part of description",
	"characteristica": [
	    {
                "category": "species",
                "choice": "homo sapiens"
            },
            {
                "category": "ethnicity",
                "choice": "Black"
            },
            {
                "category": "sex",
                "choice": null
            },
            {
                "category": "smoking",
                "choice": "N"
            }
	]
  }
}
```
* Descriptions are separated `||`. The identical separator is used for other parts of the JSON.
* The groups are defined via `characteristica`, shared characteristica of all groups are defined on the groupset.
* The allowed values for category and choice can be looked up in `categorials.py` for now.
* Values which are not defined in a characteristica have to be left empty. If the value is set to `null` this represents `NA` values. I.e., it was explicitly checked that the information was not available. This is especially important for the lifestyle characteristica and things like `ethnicity`. A list of characteristicas which should be checked will be provided (smoking, ethnicity, alcohol, contraceptives, ...) 
* Characteristica which are specific to a group are defined in the group
```json
{
"groups": [
            {
                "count": 10,
                "name": "S1",
                "comments": [
			      ["mkoenig", "This is a comment for the group."]
		        ], 
                "characteristica": [
                    {
                        "category": "weight",
                        "mean": "59.8",
                        "min": "38",
                        "max": "82",
                        "sd": "12.3",
                        "se": null,
                        "unit": "kg"
                    },
                    {
                        "category": "age",
                        "mean": "32.1",
                        "min": "18",
                        "max": "40",
                        "sd": "7.6",
                        "se": null,
                        "unit": "yr"
                    },
                    {
                        "category": "healthy",
                        "choice": "Y"
                    }
                ]
            }
         ]
}
```
* names have to be unique within groupset and should be descriptive, e.g., smoker, nonsmoker, contraceptive.

All available fields for characteristica on group and groupset are:
```json
{
    "count": "int",
    "name": "string",  // not on groupset, only on group
    "category": "categorial",
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
* The `choice` field is used for categorials, the numerical values `mean`, `median`, ... for numerical values.
* If only a single value is provided this is stored in the `value` field.

* Inclusion and exclusion criteria for study can be defined via the `ctype` on groupset or group with values in {`exclusion`, `inclusion`}

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