"""Stable publication identity shared across independently authorized source studies."""

import hashlib
import json

from sqlalchemy import select, text

from pkdb.references import normalize_doi, normalize_pmid
from pkdb_server.db.models.studies import Publication, PublicationIdentifier, Study


def lock_identity(session, identity):
    key = int.from_bytes(
        hashlib.sha256(json.dumps(identity).encode()).digest()[:8], "big", signed=True
    )
    session.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": key})


def identifiers(reference):
    result = []
    if reference.pmid:
        result.append(("pmid", normalize_pmid(reference.pmid)))
    if reference.doi:
        result.append(("doi", normalize_doi(reference.doi)))
    if not result:
        if reference.url:
            result.append(("url", reference.url.strip()))
        else:
            result.append(("reference", reference.sid))
    return sorted(result)


def assign_publication(session, root, study):
    from pkdb_server.services.ingestion import PublicationConflict

    keys = identifiers(study.reference)
    # Serialize overlapping aliases, while allowing unrelated papers to publish concurrently.
    for namespace, value in keys:
        lock_identity(session, ("publication-alias", namespace, value))
    publications = {
        identifier.publication_id
        for namespace, value in keys
        if (identifier := session.get(PublicationIdentifier, (namespace, value)))
        is not None
    }
    if len(publications) > 1:
        raise PublicationConflict(
            "Conflicting publication aliases require explicit reconciliation"
        )
    source = study.metadata.provenance.source_key
    if root.publication_id is not None and (
        root.source_key != source
        or root.acquisition.get("kind") != study.metadata.provenance.kind
    ):
        raise PublicationConflict(
            "An existing study cannot change its acquisition source"
        )
    publication_id = next(iter(publications), root.publication_id)
    if root.publication_id is not None and publication_id != root.publication_id:
        raise PublicationConflict(
            "An existing study cannot change its publication identity"
        )
    if publication_id is None:
        publication = Publication()
        session.add(publication)
        session.flush()
        publication_id = publication.id
    # Different incoming aliases can already resolve to the same publication.
    lock_identity(session, ("publication", publication_id))
    duplicate = session.scalar(
        select(Study.sid).where(
            Study.publication_id == publication_id,
            Study.source_key == source,
            Study.sid != study.sid,
        )
    )
    if duplicate:
        raise PublicationConflict(
            "A study already exists for this publication and source"
        )
    # Enrichment can add aliases, but may not replace an established namespace with a different identifier.
    prior = {
        alias.namespace: alias.value
        for alias in session.scalars(
            select(PublicationIdentifier).where(
                PublicationIdentifier.publication_id == publication_id
            )
        )
    }
    for namespace, value in keys:
        if namespace in prior and prior[namespace] != value:
            raise PublicationConflict(
                "Publication identifier conflicts with the stored identity"
            )
        if session.get(PublicationIdentifier, (namespace, value)) is None:
            session.add(
                PublicationIdentifier(
                    namespace=namespace, value=value, publication_id=publication_id
                )
            )
    root.publication_id = publication_id
    root.source_key = source
    root.acquisition = study.metadata.provenance.model_dump(mode="json")
