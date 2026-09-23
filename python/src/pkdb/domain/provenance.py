"""Find attribution identities without copying the scientific graph."""

from pkdb.schemas.study import CanonicalStudy


def comment_authors(study: CanonicalStudy) -> set[str]:
    records = [
        study,
        study.metadata,
        *study.section_notes.values(),
        *study.groups,
        *study.individuals,
        *study.interventions,
        *study.measurements,
        *study.scatters,
    ]
    records.extend(
        record
        for subject in [*study.groups, *study.individuals]
        for record in subject.characteristica
    )
    for dataset in study.scatters:
        records.extend(dataset.subsets)
        records.extend(
            dimension for subset in dataset.subsets for dimension in subset.dimensions
        )
    return {
        comment.user
        for record in records
        for comment in record.comments
        if comment.user is not None
    }
