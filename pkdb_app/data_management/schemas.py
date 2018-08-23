"""
Definition of JSON schema for validation.

FIXME: this should be created programmatically and be exported
In the optimal case directly generated from the serializers.
"""
reference_schema = {
    "properties": {
        "pmid": {"type": "number"},
        "name": {"type": "string"},
        "sid": {"type": ["number", "string"]},
        "date": {"type": "string"},
        "journal": {"type": "string"},
        "title": {"type": "string"},
        "abstract": {"type": "string"},
        "authors": {"type": "array"},
        "doi": {"type": "string"}

    }

}
