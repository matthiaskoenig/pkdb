"""One transactional local bootstrap from a reviewed offline directory."""

from pkdb_server.db.bootstrap import bootstrap as load_bootstrap


def bootstrap(directory, session_factory):
    with session_factory.begin() as session:
        report = load_bootstrap(directory, session)
        if report.errors:
            session.rollback()
        return report


def bootstrap_study(path, session_factory):
    """Create disabled attribution identities without changing existing accounts."""
    from pkdb.domain.provenance import comment_authors
    from pkdb.importers.folder import load_folder, parse_bundle
    from sqlalchemy.dialects.postgresql import insert

    from pkdb_server.commands.upload import study_folders
    from pkdb_server.db.bootstrap import BootstrapReport, UserInput
    from pkdb_server.db.models.users import User

    names = set()
    for folder in study_folders(path):
        study = parse_bundle(load_folder(folder))
        names.update(
            {
                study.metadata.creator,
                *study.metadata.collaborators,
                *(curator.user for curator in study.metadata.curators),
                *comment_authors(study),
            }
        )
    users = [UserInput(username=name, role="user") for name in sorted(names)]
    with session_factory.begin() as session:
        inserted = list(
            session.scalars(
                insert(User)
                .values(
                    [
                        {"username": user.username, "role": user.role, "active": False}
                        for user in users
                    ]
                )
                .on_conflict_do_nothing(index_elements=[User.username])
                .returning(User.username)
            )
        )
    return BootstrapReport(inserted=len(inserted), unchanged=len(users) - len(inserted))
