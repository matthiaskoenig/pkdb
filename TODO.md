# Small Tasks
- change how to write characteristicy ("choice": "Y(3)||N(1)")

- move reused information on groupset and interventionset, e.g., 
  characteristica which are for all groups ✅
- remove description from group & intervention ✅

- add comments on group and intervention, groupset and intervention (serializer and data model)
- use usernames for name (shorter and faster) ✅
- remove NA from errors ✅
- add substances on study (from categorials list of substances) ✅
- update names changed in categorials ✅
- add value field on valuable ✅, make sure means are stored as mean (i.e. values from a group with more than 1 subject)

- remove choice from valuable ✅

- add design to studies ✅

- API endpoints
    - reference
    - study (complete JSON)
    - groupset ()
    - group
    - characteristica
    - individualset
    - interventionset
    - intervention
    - outputset
    - output
- Documentation API (Swagger DRF/Open API)
   (- show required fields & choices of choice fields if possible, test description for fields)
   
- Group Timecourse with column selection based on Akinyinka2000_Fig1 & Akinyinka2000_Fig2

- individualset similar to groupset (with characteristica on individualset for all individuals)
    - first step list individual individually (no column mapping for now)

- LATER: create list of allowed keywords and choices (for now looked up in categorials)

#Questions Janek: 
- do we need description on study? For now it is in.

# Main Tasks

* web interface for display
* export to excel files and CSVs
* web interface for curation

## Genetic variants
Have a look at genetic variants

https://www.pharmvar.org/
https://www.pharmvar.org/gene/CYP1A1

## timescource example
```json
{ 
"timecourse": [
    {
    "group": "col==subjects",
    "intervention": "D1",
    "source": "Akinyinka2000_Fig1.csv",
    "format": "TSV",
    "figure": "Akinyinka2000_Fig1.png",
    "substance": "caffeine",
    "tissue": "plasma",
    "pktype": "concentration",
    "times": "col==time",
    "values": "col==caf",
    "sd": "col==caf_sd",
    "unit": "µg/ml"
    }, 
    {
    "group": "col==subjects",
    "intervention": "D1",
    "source": "Akinyinka2000_Fig1.csv",
    "format": "TSV",
    "figure": "Akinyinka2000_Fig2.png",
    "substance": "paraxanthine",
    "tissue": "plasma",
    "pktype": "concentration",
    "times": "col==time",
    "values": "col==px",
    "sd": "col==px_sd",
    "unit": "µg/ml"
    }, 
    {
    "group": "col==subjects",
    "intervention": "D1",
    "source": "Akinyinka2000_Fig1.csv",
    "format": "TSV",
    "figure": "Akinyinka2000_Fig1.png && Akinyinka2000_Fig2.png",
    "substance": "paraxanthine && caffeine",
    "tissue": "plasma",
    "pktype": "ratio",
    "times": "col==time",
    "values": "col==px_caf",
    "sd": "col==px_caf_sd",
    "unit": "-"
    }
    ]
}
```
 