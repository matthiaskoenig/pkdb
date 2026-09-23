"""Reviewed, transactional account imports that never issue credentials or activate users."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

from pkdb.schemas.profiles import ProfileUpdate
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from pkdb_server.db.models.security import SecurityConfiguration, UserImportRun
from pkdb_server.db.models.studies import Study, StudyGrant
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.profiles import sanitize_avatar


class ImportRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=150, pattern=r"^\S+$")
    role: Literal["user", "curator", "reviewer", "admin"] = "user"
    user_id: int | None = Field(default=None, gt=0)
    email: str | None = Field(
        default=None, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    assigned_study_ids: list[int] = Field(default_factory=list)
    display_name: str | None = Field(default=None, max_length=200)
    affiliation: str | None = Field(default=None, max_length=250)
    title: str | None = Field(default=None, max_length=100)
    github: str | None = None
    orcid: str | None = None
    avatar: dict | None = None
    profile_references: dict = Field(default_factory=dict)
    import_policy: Literal[
        "reviewed_invitation", "administrator_bootstrap", "exclude_test_account"
    ] = "reviewed_invitation"
    # Public manifest annotations are provenance only and never authentication evidence.
    identity_match: str | None = None
    avatar_note: str | None = None
    migration_note: str | None = None
    exclusion_reason: str | None = None


class ContactOverlay(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str
    email: str | None = Field(
        default=None, max_length=320, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$"
    )
    user_id: int | None = Field(default=None, gt=0)
    assigned_study_ids: list[int] = Field(default_factory=list)


def _read(path: Path):
    if path.suffix.lower() == ".csv":
        with path.open(newline="") as stream:
            values = list(csv.DictReader(stream))
        for row in values:
            for field in ("user_id", "email"):
                if row.get(field) == "":
                    row.pop(field)
            if "assigned_study_ids" in row:
                row["assigned_study_ids"] = [
                    int(value)
                    for value in row["assigned_study_ids"].split(";")
                    if value
                ]
        return values
    return json.loads(path.read_text())


def load_roster(path: Path, contacts: Path | None = None):
    document = _read(path)
    if isinstance(document, dict):
        values = document["users"]
        provenance = {
            key: document[key]
            for key in ("roster_source", "avatar_source")
            if key in document
        }
    else:
        values = document
        provenance = {}
    rows = [ImportRow.model_validate(value) for value in values]
    names = [row.username for row in rows]
    if len(names) != len({name.casefold() for name in names}):
        raise ValueError("Duplicate usernames in roster")
    if contacts:
        overlay = _read(contacts)
        if isinstance(overlay, dict):
            overlay = overlay["users"]
        updates = [ContactOverlay.model_validate(value) for value in overlay]
        overlay_names = [update.username for update in updates]
        if len(overlay_names) != len(set(overlay_names)) or set(overlay_names) - set(
            names
        ):
            raise ValueError("Contact overlay contains duplicate or unknown usernames")
        by_name = {update.username: update for update in updates}
        rows = [
            ImportRow.model_validate(
                row.model_dump() | by_name[row.username].model_dump(exclude_unset=True)
            )
            if row.username in by_name
            else row
            for row in rows
        ]
    for row in rows:
        if row.email:
            row.email = row.email.casefold()
        if len(row.assigned_study_ids) != len(set(row.assigned_study_ids)) or any(
            value <= 0 for value in row.assigned_study_ids
        ):
            raise ValueError("Study assignments must be unique positive IDs")
        if row.import_policy == "administrator_bootstrap" and (
            row.username != "mkoenig" or row.role != "admin"
        ):
            raise ValueError(
                "Administrator profile mapping must target mkoenig with admin role"
            )
        if row.role == "admin" and (
            row.username != "mkoenig" or row.import_policy != "administrator_bootstrap"
        ):
            raise ValueError("Administrators must use the dedicated mkoenig bootstrap")
        if row.username == "mkoenig" and row.import_policy != "administrator_bootstrap":
            raise ValueError("mkoenig is reserved for administrator bootstrap")
        if row.username == "reviewer" and row.import_policy != "exclude_test_account":
            raise ValueError("Historical reviewer test account must remain excluded")
    # Digest is never authentication evidence. No contact addresses enter the run report.
    canonical = json.dumps(
        {"users": [row.model_dump() for row in rows], "provenance": provenance},
        sort_keys=True,
    )
    return rows, provenance, hashlib.sha256(canonical.encode()).hexdigest()


def import_users(
    session,
    rows,
    provenance,
    digest,
    *,
    apply=False,
    update_existing=False,
    profile_service=None,
    avatar_root: Path | None = None,
):
    """Caller owns transaction. Validate the complete batch before making any changes."""
    if apply:
        # Lock the singleton to serialize operator imports and administrator designation.
        session.scalar(
            select(SecurityConfiguration)
            .where(SecurityConfiguration.id == 1)
            .with_for_update()
        )
    previous = session.scalar(
        select(UserImportRun).where(UserImportRun.digest == digest)
    )
    if previous:
        return {
            "ok": True,
            "applied": False,
            "already_applied": True,
            "digest": digest,
            "operations": [],
            "conflicts": [],
        }
    report = {
        "ok": True,
        "applied": False,
        "already_applied": False,
        "digest": digest,
        "provenance": provenance,
        "operations": [],
        "conflicts": [],
    }
    planned = []
    contacts = {}
    for row in rows:
        if row.import_policy == "exclude_test_account":
            report["operations"].append(
                {"username": row.username, "action": row.import_policy}
            )
            continue
        query = select(User).where(User.username == row.username)
        user = session.scalar(query.with_for_update() if apply else query)
        administrator_profile = row.import_policy == "administrator_bootstrap"
        if administrator_profile:
            configuration = session.get(SecurityConfiguration, 1)
            if (
                user is None
                or user.role != "admin"
                or configuration is None
                or configuration.designated_administrator_id != user.id
            ):
                report["operations"].append(
                    {"username": row.username, "action": "administrator_bootstrap"}
                )
                continue
        conflicts = []
        if (
            user is None
            and session.scalar(
                select(User.id).where(
                    func.lower(User.username) == func.lower(row.username)
                )
            )
            is not None
        ):
            conflicts.append("case_insensitive_username_collision")
        if administrator_profile and row.assigned_study_ids:
            conflicts.append("administrator_profile_import_cannot_change_grants")
        if row.user_id is not None and (user is None or user.id != row.user_id):
            conflicts.append("explicit_user_id_mismatch")
        if user is not None and user.role == "admin" and not administrator_profile:
            conflicts.append("administrator_requires_dedicated_bootstrap")
        if user is not None and user.role != row.role and not update_existing:
            conflicts.append("role_change_requires_update_existing")
        if row.email:
            if row.email in contacts:
                conflicts.append("duplicate_contact_in_roster")
            contacts[row.email] = row.username
            owner = session.scalar(
                select(User.id).where(
                    User.email == row.email, User.id != (user.id if user else -1)
                )
            )
            email_owner = session.scalar(
                select(EmailAddress.user_id).where(EmailAddress.email == row.email)
            )
            if owner is not None or (
                email_owner is not None and (user is None or email_owner != user.id)
            ):
                conflicts.append("contact_belongs_to_another_account")
            primary_email = (
                session.scalar(
                    select(EmailAddress).where(
                        EmailAddress.user_id == user.id,
                        EmailAddress.is_primary.is_(True),
                    )
                )
                if user
                else None
            )
            if (
                primary_email is not None
                and primary_email.email.casefold() != row.email
            ):
                conflicts.append("primary_contact_differs_preserve_existing")
            if user and user.email and user.email.casefold() != row.email:
                conflicts.append("primary_contact_differs_preserve_existing")
        assignments = []
        for study_id in row.assigned_study_ids:
            if session.get(Study, study_id) is None:
                conflicts.append(f"missing_study:{study_id}")
            elif (
                user is None
                or session.get(StudyGrant, (study_id, user.id, "curator")) is None
            ):
                assignments.append(study_id)
        if assignments and user is not None and not update_existing:
            conflicts.append("assignment_change_requires_update_existing")
        if row.assigned_study_ids and row.role == "user":
            conflicts.append("study_write_assignment_requires_privileged_role")
        avatar_bytes = None
        if avatar_root is not None and row.avatar:
            try:
                avatar_bytes = _avatar_content(row.avatar, avatar_root)
                sanitize_avatar(avatar_bytes)
            except ValueError, OSError:
                conflicts.append("invalid_avatar_asset")
        try:
            profile_values = _profile_values(row)
        except ValueError:
            conflicts.append("invalid_profile_values")
            profile_values = {}
        operation = {
            "username": row.username,
            "user_id": user.id if user else None,
            "action": "administrator_profile_only"
            if administrator_profile
            else "match"
            if user
            else "create_disabled",
            "current_role": user.role if user else None,
            "proposed_role": row.role,
            "add_study_ids": assignments,
            "contact_available": bool(row.email or (user and user.email)),
            "active_unchanged": user.active if user else False,
            "suspended_unchanged": bool(user and user.suspended_at),
        }
        report["operations"].append(operation)
        report["conflicts"].extend(
            {"username": row.username, "reason": reason} for reason in conflicts
        )
        planned.append(
            (row, user, assignments, avatar_bytes, profile_values, operation)
        )
    report["ok"] = not report["conflicts"]
    if not apply or not report["ok"]:
        return report
    for row, user, assignments, avatar_bytes, profile_values, operation in planned:
        if user is None:
            user = User(
                username=row.username, role=row.role, active=False, email=row.email
            )
            session.add(user)
            session.flush()
            operation["user_id"] = user.id
        elif update_existing and row.import_policy != "administrator_bootstrap":
            user.role = row.role
        if row.email and not user.email:
            user.email = row.email
        if (
            row.email
            and session.scalar(
                select(EmailAddress.id).where(EmailAddress.email == row.email)
            )
            is None
        ):
            session.add(
                EmailAddress(
                    user_id=user.id, email=row.email, is_primary=True, is_verified=False
                )
            )
        for study_id in assignments:
            session.add(StudyGrant(study_id=study_id, user_id=user.id, role="curator"))
        if profile_service:
            profile_service.import_profile(
                session,
                user,
                profile_values,
                avatar_content=avatar_bytes,
                provenance=provenance | {"avatar": row.avatar},
            )
    report["applied"] = True
    session.add(UserImportRun(digest=digest, provenance=provenance, report=report))
    session.flush()
    return report


def _avatar_content(avatar, root):
    if root is None:
        raise ValueError("Avatar root is required")
    url = avatar["url"]
    if not url.startswith("/assets/images/avatars/"):
        raise ValueError("Avatar must be a managed local asset")
    root = root.resolve()
    path = (root / url.lstrip("/")).resolve()
    if not path.is_relative_to(root / "assets/images/avatars"):
        raise ValueError("Avatar path escapes managed directory")
    content = path.read_bytes()
    if hashlib.sha256(content).hexdigest() != avatar["sha256"]:
        raise ValueError("Avatar checksum mismatch")
    return content


def _profile_values(row):
    values = {
        key: getattr(row, key)
        for key in ("display_name", "affiliation", "title", "github", "orcid")
        if getattr(row, key)
    }
    repository = row.profile_references.get("repository")
    if repository and not values.get("github"):
        parsed = urlparse(repository)
        if parsed.scheme == "https" and parsed.netloc == "github.com":
            values["github"] = parsed.path.strip("/")
    if row.profile_references.get("orcid") and not values.get("orcid"):
        values["orcid"] = row.profile_references["orcid"]
    return ProfileUpdate.model_validate(values).model_dump(exclude_unset=True)
