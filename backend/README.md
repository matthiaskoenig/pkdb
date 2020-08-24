# PKDB Backend (`django`)

- [ ] documentation page with queries and searches

## PKData Query
The event cycle of PKData is:
1. Query studies, interventions, groups, individuals, and outputs by adding
 the respective word as a prefix following two underscores to the url filter 
 (e.g. ...api/v1/pkdata/?studies__sid=PKDB00008 is equivalent to ...api/v1/studies/?sid=PKDB00008).
 The search/filter is performed on the indexed database. For more details on how to construct the query by patterns in the 
 url check "https://django-elasticsearch-dsl-drf.readthedocs.io/en/latest/".
 
2. All tables are updated to get rid of redundant entries. This results in a concise set of entries
in all tables (e.g. a filter on the study table for a specific sid reduces the entries of the other tables 
only to interventions, groups, individuals, and outputs which are part of the study).

3. paginated studies, interventions, groups, individuals, and outputs are returned. Getting the next page for one of the tables 
works equivalently to the filters (e.g. getting the second studies page while searching for the interventions containing caffeine.  ...api/v1/pkdata/?interventions__substance=caffeine&studies__page=2).


## PKDData
documentation

### Queries

Query for single study:
``` 
http://localhost:8000/api/v1/pkdata/?studies__sid=PKDB00008 
```
Query for multiple studies based on sids:
```
http://localhost:8000/api/v1/pkdata/?studies__sid__in=PKDB00008__PKDB00001
```
Query for interventions substance:
```
http://localhost:8000/api/v1/pkdata/?interventions__substance=codeine
```
Query for interventions and outputs simultaneously:
```
http://localhost:8000/api/v1/pkdata/?interventions__substance=codeine&outputs__measurement_type=clearance
```

&copy; 2017-2020 Jan Grzegorzewski & Matthias König.
