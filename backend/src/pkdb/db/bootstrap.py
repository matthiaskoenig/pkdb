"""Load explicit, validated offline snapshots within a caller-owned transaction."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from pkdb.db.models.users import User
from pkdb.db.models.vocabulary import (
    VocabularyEdge,
    VocabularyNode,
    VocabularyTerm,
    VocabularyVersion,
)
from pkdb.domain.vocabulary import MeasurementRule, SubstanceDefinition, Vocabulary
from pkdb.schemas.validation import ValidationIssue

# Shared by bootstrap and publication; locks survive until the caller commits.
VOCABULARY_LOCK = 741260818467


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid")


class UserInput(Input):
    username: str = Field(min_length=1, max_length=150)
    role: Literal["admin", "curator", "reviewer", "user"] = "curator"
    email: str | None = None


class NodeInput(Input):
    sid: str = Field(min_length=1, max_length=255)
    name: str = Field(min_length=1)
    kind: Literal[
        "measurement",
        "substance",
        "tissue",
        "method",
        "route",
        "form",
        "application",
        "calculation_type",
        "info_node",
        "choice",
        "substance_set",
    ]
    definition: dict = Field(default_factory=dict)
    parents: list[str] = Field(default_factory=list)
    terms: dict[str, list[str]] = Field(default_factory=dict)


class Snapshot(Input):
    version: str = Field(min_length=1)
    nodes: list[NodeInput]


class BootstrapReport(BaseModel):
    inserted: int = 0
    unchanged: int = 0
    updated: int = 0
    errors: list[ValidationIssue] = Field(default_factory=list)


def validate_snapshot(snapshot: Snapshot) -> dict[str, NodeInput]:
    """Validate node identities, scientific definitions, parents and cycles offline."""
    nodes = {node.sid: node for node in snapshot.nodes}
    if len(nodes) != len(snapshot.nodes):
        raise ValueError("Duplicate vocabulary SID")
    for node in snapshot.nodes:
        if len(node.parents) != len(set(node.parents)):
            raise ValueError(f"Duplicate parent of {node.sid}")
        for parent in node.parents:
            if parent not in nodes:
                raise ValueError(f"Unknown parent {parent}")
        if node.kind == "measurement":
            MeasurementRule.model_validate(
                {**node.definition, "name": node.name, "sid": node.sid}
            )
        if node.kind == "substance":
            SubstanceDefinition.model_validate(
                {**node.definition, "name": node.name, "sid": node.sid}
            )
    done: set[str] = set()
    visiting: set[str] = set()

    def visit(sid: str):
        if sid in visiting:
            raise ValueError(f"Vocabulary cycle at {sid}")
        if sid in done:
            return
        visiting.add(sid)
        for parent in nodes[sid].parents:
            visit(parent)
        visiting.remove(sid)
        done.add(sid)

    for sid in nodes:
        visit(sid)
    return nodes


def bootstrap(directory: Path, session: Session) -> BootstrapReport:
    if not session.in_transaction():
        raise RuntimeError("Bootstrap requires an explicit caller-owned transaction")
    report = BootstrapReport()
    try:
        users = [
            UserInput.model_validate(item)
            for item in json.loads((directory / "users.json").read_text())
        ]
        snapshot = Snapshot.model_validate_json(
            (directory / "vocabulary.json").read_text()
        )
        if len({user.username for user in users}) != len(users):
            raise ValueError("Duplicate username")
        nodes = validate_snapshot(snapshot)
    except (OSError, ValueError, TypeError, ValidationError) as error:
        report.errors.append(
            ValidationIssue(code="invalid_bootstrap", message=str(error))
        )
        return report
    session.execute(
        text("SELECT pg_advisory_xact_lock(:key)"), {"key": VOCABULARY_LOCK}
    )
    existing_users = {
        user.username: user for user in session.scalars(select(User).with_for_update())
    }
    existing_nodes = {
        node.sid: node
        for node in session.scalars(select(VocabularyNode).with_for_update())
    }
    # Existing credentials and roles are managed by account administration, never by corpus reupload.
    for entry in users:
        if entry.username in existing_users:
            report.unchanged += 1
        else:
            session.add(User(**entry.model_dump(), active=False))
            report.inserted += 1
    for entry in snapshot.nodes:
        row = existing_nodes.get(entry.sid)
        definition = entry.definition
        values: dict[str, object] = dict(
            name=entry.name, kind=entry.kind, definition=definition
        )
        if entry.kind == "substance":
            values.update(
                {name: definition.get(name) for name in ("mass", "formula", "charge")}
            )
        if row is None:
            session.add(VocabularyNode(sid=entry.sid, **values))
            report.inserted += 1
        elif all(getattr(row, key) == value for key, value in values.items()):
            report.unchanged += 1
        else:
            for key, value in values.items():
                setattr(row, key, value)
            report.updated += 1
    session.flush()
    supplied = list(nodes)
    session.execute(delete(VocabularyEdge).where(VocabularyEdge.child.in_(supplied)))
    session.execute(delete(VocabularyTerm).where(VocabularyTerm.node_sid.in_(supplied)))
    for node in snapshot.nodes:
        session.add_all(
            VocabularyEdge(child=node.sid, parent=parent) for parent in node.parents
        )
        session.add_all(
            VocabularyTerm(node_sid=node.sid, kind=kind, value=value)
            for kind, values in node.terms.items()
            for value in set(values)
        )
    session.flush()
    # Hash the entire effective vocabulary, including retained nodes from earlier snapshots.
    effective = [
        (node.sid, node.name, node.kind, node.definition)
        for node in session.scalars(select(VocabularyNode).order_by(VocabularyNode.sid))
    ]
    edges = list(
        session.execute(
            select(VocabularyEdge.child, VocabularyEdge.parent).order_by(
                VocabularyEdge.child, VocabularyEdge.parent
            )
        ).tuples()
    )
    terms = list(
        session.execute(
            select(
                VocabularyTerm.node_sid, VocabularyTerm.kind, VocabularyTerm.value
            ).order_by(
                VocabularyTerm.node_sid, VocabularyTerm.kind, VocabularyTerm.value
            )
        ).tuples()
    )
    digest = hashlib.sha256(
        json.dumps(
            [effective, [list(row) for row in edges], [list(row) for row in terms]],
            sort_keys=True,
        ).encode()
    ).hexdigest()
    version = session.get(VocabularyVersion, 1)
    if version is None:
        session.add(VocabularyVersion(id=1, version=digest))
    else:
        version.version = digest
    session.flush()
    return report


def load_vocabulary(session: Session) -> Vocabulary:
    version = session.get(VocabularyVersion, 1)
    if version is None:
        raise RuntimeError("Vocabulary has not been bootstrapped")
    rows = list(session.scalars(select(VocabularyNode).order_by(VocabularyNode.sid)))
    return Vocabulary(
        version=version.version,
        measurements=tuple(
            MeasurementRule.model_validate(
                {**row.definition, "name": row.name, "sid": row.sid}
            )
            for row in rows
            if row.kind == "measurement"
        ),
        substances=tuple(
            SubstanceDefinition.model_validate(
                {**row.definition, "name": row.name, "sid": row.sid}
            )
            for row in rows
            if row.kind == "substance"
        ),
        **{
            field: tuple(row.name for row in rows if row.kind == kind)
            for field, kind in [
                ("tissues", "tissue"),
                ("methods", "method"),
                ("routes", "route"),
                ("forms", "form"),
                ("applications", "application"),
                ("calculation_types", "calculation_type"),
            ]
        },
    )
