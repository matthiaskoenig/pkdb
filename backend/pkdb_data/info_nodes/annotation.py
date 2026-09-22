"""Annotations for InfoNodes."""

import logging
import urllib.parse
from typing import Any

from pymetadata.core.annotation import ProviderType, RDFAnnotation
from pymetadata.core.miriam import BQB, BQM
from pymetadata.core.xref import CrossReference, is_url
from pymetadata.webservices.ols import ONTOLOGIES, OLSQuery
from pymetadata.webservices.registry import Registry, Resource

from pkdb_data import CACHE_PATH, CACHE_USE

logger = logging.getLogger(__name__)

REGISTRY = Registry()
OLS_QUERY = OLSQuery(ontologies=ONTOLOGIES, cache_path=CACHE_PATH, cache=CACHE_USE)


class NodeAnnotation:
    """Annotation information for info node."""

    def __init__(
        self,
        relation: BQB | BQM,
        resource: str,
    ):
        """Initialize NodeAnnotation."""
        self.relation: BQB | BQM = relation
        self.description: str | None = None
        self.label: str | None = None
        self.url: str | None = None
        self.synonyms: list[str] = []
        self.xrefs: list = []

        self.rdf_annotation = RDFAnnotation(qualifier=relation, resource=resource)

        # basic checks
        RDFAnnotation.check_qualifier(self.rdf_annotation.qualifier)

        if self.rdf_annotation.provider == ProviderType.IDENTIFIERS_ORG:
            self.rdf_annotation.check_miriam_term()

            # register MIRIAM xrefs
            collection = self.rdf_annotation.collection
            miriam_term = self.rdf_annotation.term
            namespace = REGISTRY.ns_dict.get(collection) if collection else None
            if namespace and collection and miriam_term:
                namespace_embedded = namespace.namespaceEmbeddedInLui
                ns_resource: Resource
                for ns_resource in namespace.resources or []:
                    # create url
                    url: str = ns_resource.urlPattern
                    if not self.url:
                        # set url to first resource url
                        self.url = url

                    # remove prefix
                    term = miriam_term
                    if namespace_embedded and namespace.prefix:
                        term = term[len(namespace.prefix) + 1 :]

                    # urlencode term
                    term = urllib.parse.quote(term)

                    # create url
                    url = url.replace("{$Id}", term)
                    url = url.replace("{$id}", term)
                    url = url.replace(
                        f"{collection.upper}:",
                        urllib.parse.quote(f"{collection.upper}:"),
                    )

                    _xref = CrossReference(
                        name=ns_resource.name, accession=term, url=url
                    )
                    valid = _xref.validate() and is_url(self.url)
                    if valid:
                        self.xrefs.append(_xref)

    def query_ols(self) -> None:
        """Query information from ontology lookup services.

        Sets the information on the object.
        """
        d = OLS_QUERY.query_ols(
            ontology=self.rdf_annotation.collection, term=self.rdf_annotation.term
        )
        info: dict[str, Any] = OLS_QUERY.process_response(d)
        if info:
            if self.label is None:
                self.label = info.get("label")

            if self.description is None:
                description = info.get("description")
                if isinstance(description, str):
                    self.description = description

            self.synonyms = info["synonyms"]
            self.xrefs = info["xrefs"]

    def __repr__(self) -> str:
        """Get string representation."""
        return f"Annotation({self.rdf_annotation}|{self.description}|{self.synonyms}|{self.xrefs})"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "term": self.rdf_annotation.term,
            "relation": self.relation.value,
            "collection": self.rdf_annotation.collection,
            "description": self.description,
            "label": self.label,
            "url": self.url,
            # synonyms and xrefs are not serialized
        }
