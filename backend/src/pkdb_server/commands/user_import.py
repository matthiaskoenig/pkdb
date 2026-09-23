"""Operator-facing account migration orchestration; invitation sending is separate."""

from pathlib import Path

from pkdb_server.services.profiles import ProfileService
from pkdb_server.services.user_import import import_users, load_roster


def import_roster(
    path,
    session_factory,
    *,
    contacts=None,
    apply=False,
    update_existing=False,
    file_root=None,
    avatar_root=None,
):
    rows, provenance, digest = load_roster(
        Path(path), Path(contacts) if contacts else None
    )
    profiles = (
        ProfileService(session_factory, file_root) if file_root and apply else None
    )
    with session_factory.begin() as session:
        report = import_users(
            session,
            rows,
            provenance,
            digest,
            apply=apply,
            update_existing=update_existing,
            profile_service=profiles,
            avatar_root=Path(avatar_root) if avatar_root else None,
        )
    return report
