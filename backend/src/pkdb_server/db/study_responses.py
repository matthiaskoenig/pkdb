"""Batched study detail assembly inside the caller's visibility-filtered snapshot."""

import json
from collections import defaultdict
from urllib.parse import quote

from sqlalchemy import select, union

from pkdb.schemas.responses import StudyResponse
from pkdb.schemas.security import StudyAccess
from pkdb_server.db.models.files import StoredFile, StudyAttachment
from pkdb_server.db.models.interventions import Intervention
from pkdb_server.db.models.measurements import Measurement, Scatter, Subset
from pkdb_server.db.models.studies import Note, Reference, StudyGrant, StudyUser
from pkdb_server.db.models.subjects import Group, Individual
from pkdb_server.db.models.users import User
from pkdb_server.db.models.vocabulary import (
    VocabularyEdge,
    VocabularyNode,
    VocabularyTerm,
)
from pkdb_server.db.serialize import reference_responses
from pkdb_server.services.authorization import AuthorizationDenied, authorize
from pkdb_server.services.profiles import public_profile


def study_responses(session, rows, principal):
    if not rows:
        return []
    study_ids = [row.id for row in rows]
    members = defaultdict(list)
    for row in session.scalars(
        select(StudyUser)
        .where(StudyUser.study_id.in_(study_ids))
        .order_by(StudyUser.user_id)
    ):
        members[row.study_id].append(row)
    note_keys = [
        "study",
        "metadata",
        "section:groupset",
        "section:individualset",
        "section:interventionset",
        "section:outputset",
        "section:dataset",
    ]
    notes = list(
        session.scalars(
            select(Note)
            .where(Note.study_id.in_(study_ids), Note.record_key.in_(note_keys))
            .order_by(Note.position, Note.id)
        )
    )
    user_ids = (
        {row.creator_id for row in rows}
        | {member.user_id for group in members.values() for member in group}
        | {note.user_id for note in notes}
    )
    users = {
        row.id: {
            **public_profile(row),
            "first_name": row.first_name,
            "last_name": row.last_name,
        }
        for row in session.scalars(select(User).where(User.id.in_(user_ids)))
    }
    descriptions, comments = defaultdict(list), defaultdict(list)
    for row in notes:
        data = {"pk": row.id, "text": row.text}
        if row.kind == "comment":
            data["username"] = users.get(row.user_id, {}).get("username")
            comments[row.study_id, row.record_key].append(data)
        else:
            descriptions[row.study_id, row.record_key].append(data)

    def note_data(study_id, *keys):
        return {
            "descriptions": [
                note for key in keys for note in descriptions[study_id, key]
            ],
            "comments": [note for key in keys for note in comments[study_id, key]],
        }

    references = {
        row["pk"]: row
        for row in reference_responses(
            session,
            list(
                session.scalars(
                    select(Reference).where(
                        Reference.id.in_({row.reference_id for row in rows})
                    )
                )
            ),
        )
    }
    ids = {
        key: defaultdict(list)
        for key in ("groups", "individuals", "interventions", "outputs", "subsets")
    }
    for key, model in (
        ("groups", Group),
        ("individuals", Individual),
        ("interventions", Intervention),
        ("outputs", Measurement),
    ):
        query = (
            select(model.study_id, model.id)
            .where(model.study_id.in_(study_ids))
            .order_by(model.id)
        )
        if model is Intervention or model is Measurement:
            query = query.where(model.origin == "normalized")
        for study_id, identifier in session.execute(query):
            ids[key][study_id].append(identifier)
    calculated = defaultdict(int)
    for study_id in session.scalars(
        select(Measurement.study_id).where(
            Measurement.study_id.in_(study_ids),
            Measurement.origin == "normalized",
            Measurement.calculated.is_(True),
        )
    ):
        calculated[study_id] += 1
    subset_types = defaultdict(lambda: defaultdict(int))
    for study_id, identifier, data_type in session.execute(
        select(Subset.study_id, Subset.id, Scatter.data_type)
        .join(Scatter, Subset.scatter_id == Scatter.id)
        .where(Subset.study_id.in_(study_ids))
        .order_by(Subset.id)
    ):
        ids["subsets"][study_id].append(identifier)
        subset_types[study_id][data_type] += 1
    # Legacy studies summarize immediate parent substances for derivatives.
    substance_rows = list(
        session.execute(
            union(
                select(Measurement.study_id, Measurement.substance).where(
                    Measurement.study_id.in_(study_ids),
                    Measurement.substance.is_not(None),
                ),
                select(Intervention.study_id, Intervention.substance).where(
                    Intervention.study_id.in_(study_ids),
                    Intervention.substance.is_not(None),
                ),
            )
        )
    )
    parents = defaultdict(set)
    for edge in session.scalars(
        select(VocabularyEdge).where(
            VocabularyEdge.child.in_({sid for _, sid in substance_rows})
        )
    ):
        parents[edge.child].add(edge.parent)
    study_substances = defaultdict(set)
    for study_id, sid in substance_rows:
        study_substances[study_id].update(parents.get(sid) or {sid})
    substance_ids = {sid for sids in study_substances.values() for sid in sids}
    labels = {
        row.node_sid: json.loads(row.value)
        for row in session.scalars(
            select(VocabularyTerm).where(
                VocabularyTerm.node_sid.in_(substance_ids),
                VocabularyTerm.kind == "label",
            )
        )
    }
    substances = {
        row.sid: {
            "sid": row.sid,
            "name": row.name,
            "label": labels.get(row.sid) or row.name,
        }
        for row in session.scalars(
            select(VocabularyNode).where(VocabularyNode.sid.in_(substance_ids))
        )
    }
    grants = defaultdict(list)
    for grant in session.scalars(
        select(StudyGrant).where(StudyGrant.study_id.in_(study_ids))
    ):
        grants[grant.study_id].append(grant)
    allowed_files = []
    for row in rows:
        if row.creator_id is None:
            continue
        access = StudyAccess(
            sid=row.sid,
            access=row.access,
            licence=row.licence,
            creator_id=row.creator_id,
            curator_ids=frozenset(
                member.user_id for member in grants[row.id] if member.role == "curator"
            ),
            collaborator_ids=frozenset(
                member.user_id
                for member in grants[row.id]
                if member.role == "collaborator"
            ),
        )
        try:
            authorize(principal, "read_file", access)
            allowed_files.append(row.id)
        except AuthorizationDenied:
            pass
    attachments = defaultdict(list)
    if allowed_files:
        for association, file in session.execute(
            select(StudyAttachment, StoredFile)
            .join(StoredFile)
            .where(StudyAttachment.study_id.in_(allowed_files))
            .order_by(StudyAttachment.name.collate("C"))
        ):
            attachments[association.study_id].append(
                {
                    "pk": str(file.id),
                    "name": f"data/{association.name}",
                    "file": f"/media/{file.id}/{quote(file.original_name, safe='')}",
                }
            )
    results = []
    for row in rows:
        reference = references.get(row.reference_id)
        member_rows = members[row.id]
        data = {
            "pk": str(row.id),
            "sid": row.sid,
            "name": row.name,
            "licence": row.licence,
            "access": row.access,
            "date": row.date.isoformat() if row.date else None,
            "creator": users.get(row.creator_id),
            "curators": [
                {**users[member.user_id], "rating": member.rating or 0}
                for member in member_rows
                if member.role == "curator"
            ],
            "collaborators": [
                users[member.user_id]
                for member in member_rows
                if member.role == "collaborator"
            ],
            "reference": {**reference, "study": {"sid": row.sid, "name": row.name}}
            if reference
            else None,
            "reference_date": reference["date"] if reference else None,
            "files": attachments[row.id],
            "substances": [substances[sid] for sid in sorted(study_substances[row.id])],
            **note_data(row.id, "study", "metadata"),
        }
        for section, key, count in (
            ("groupset", "groups", "group_count"),
            ("individualset", "individuals", "individual_count"),
            ("interventionset", "interventions", "intervention_count"),
            ("outputset", "outputs", "output_count"),
            ("dataset", "subsets", "subset_count"),
        ):
            data[section] = {
                **note_data(row.id, f"section:{section}"),
                key: ids[key][row.id],
            }
            data[count] = len(ids[key][row.id])
        data.update(
            output_calculated_count=calculated[row.id],
            timecourse_count=subset_types[row.id]["timecourse"],
            scatter_count=subset_types[row.id]["scatter"],
        )
        results.append(StudyResponse.model_validate(data).model_dump())
    return results
