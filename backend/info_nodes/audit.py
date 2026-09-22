"""Deterministic metadata diagnostics that require curator review."""

from pymetadata.core.annotation import RDFAnnotationData
from pymetadata.core.miriam import BQB

from info_nodes.graph import NodeIndex

# Preserve stable identifiers and scientific policies until curated data is reviewed.
CURATION_REVIEW = {
    "sex": "The sex measurement is annotated with NCIT:C16576 (Female); review whether this identifies the quantity or one of its choices.",
    "mixed-race": "The Caucasian annotation and synonym 'white' conflict with mixed race.",
    "angiotensinogen": "The description identifies angiotensin I; review the description and annotations.",
    "clearance-intrinsic": "The description equates intrinsic clearance with total minus renal clearance; verify the intended quantity.",
    "auc-ratio": "A ratio of AUC values declares AUC units; verify units against curated usage.",
    "svr": "Review the existing unit TODO and the dimensionality of systemic vascular resistance.",
    "pcwp": "Review the existing unit TODO for pulmonary capillary wedge pressure.",
    "pap": "Review the existing unit TODO for pulmonary artery pressure.",
    "got": "Review overlap with AST before merging or retiring stable identifiers.",
    "bile": "Review whether this fluid belongs in substances, tissues, or both.",
    "phenobarbitone": "Review overlap with phenobarbital before merging stable identifiers.",
    "1s-2r-alpha-hydroxymetoprolol": "The source flags the stereoisomer annotation as incorrect; verify a stereospecific identifier.",
    "1s-2s-alpha-hydroxymetoprolol": "The source flags the stereoisomer annotation as incorrect; verify a stereospecific identifier.",
    "1r-2r-alpha-hydroxymetoprolol": "The source flags the stereoisomer annotation as incorrect; verify a stereospecific identifier.",
    "1r-2s-alpha-hydroxymetoprolol": "The source flags the stereoisomer annotation as incorrect; verify a stereospecific identifier.",
}


def audit_nodes(nodes: NodeIndex, *, policies: dict[str, list[str]]) -> list[dict]:
    """Flag questionable metadata without guessing scientific corrections."""
    issues = []

    def report(sid: str, code: str, message: str) -> None:
        issues.append({"sid": sid, "code": code, "message": message})

    names = {node.name for node in nodes if node.ntype == "measurement_type"}
    for policy, values in policies.items():
        for name in sorted(set(values) - names):
            report(
                name,
                "unknown_policy_measurement",
                f"{policy} references an unknown measurement name.",
            )

    for node in nodes:
        if not node.description or not node.description.strip():
            report(node.sid, "missing_description", "Provide a scientific description.")
        seen = set()
        chebi = set()
        for annotation in node.annotations or []:
            key = (annotation.qualifier, annotation.collection, annotation.term)
            if key in seen:
                report(
                    node.sid,
                    "duplicate_annotation",
                    f"Repeated annotation: {annotation.resource}.",
                )
            seen.add(key)
            if annotation.qualifier == BQB.IS and annotation.collection == "chebi":
                chebi.add(annotation.term)
            if not annotation.validate():
                report(
                    node.sid,
                    "invalid_annotation",
                    f"Invalid annotation: {annotation.resource}.",
                )
            if not isinstance(annotation, RDFAnnotationData):
                report(
                    node.sid,
                    "unresolved_annotation",
                    f"No registry namespace for {annotation.resource}; annotation retained without enrichment.",
                )
            else:
                for message in annotation.errors + annotation.warnings:
                    if str(message) == f"'{annotation.collection}' is not on OLS.":
                        continue
                    report(
                        node.sid,
                        "annotation_metadata",
                        f"{annotation.resource}: {message}",
                    )
        if node.ntype == "substance" and len(chebi) > 1:
            report(
                node.sid,
                "ambiguous_chemical_identity",
                "Multiple BQB.IS ChEBI terms; chemical enrichment currently uses the first.",
            )
        if node.sid in CURATION_REVIEW:
            report(node.sid, "curation_review", CURATION_REVIEW[node.sid])
    return sorted(
        issues, key=lambda issue: (issue["sid"], issue["code"], issue["message"])
    )
