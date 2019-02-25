"""
Improved substance model using data from chebi.
https://github.com/matthiaskoenig/pkdb/issues/114

https://www.ebi.ac.uk/chebi/downloadsForward.do
https://www.ebi.ac.uk/chebi/searchId.do?chebiId=CHEBI:33699
"""

# Query via Chebi database



# TODO: search list of chebi identifiers for substances
# TODO: get information via REST query for chebi substance (for all substances and store locally)
# https://www.ebi.ac.uk/ols/api/ontologies/chebi/terms?iri=http://purl.obolibrary.org/obo/CHEBI_17234
#- Main information:
#  - label
#  - description
#  - mass
#  - charge
#  - formula
#  - database xrefs
#  - synonyms

# TODO: store in flat file & use information when creating substances