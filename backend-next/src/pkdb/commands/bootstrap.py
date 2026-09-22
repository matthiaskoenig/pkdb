"""One transactional local bootstrap from a reviewed offline directory."""

from pkdb.db.bootstrap import bootstrap as load_bootstrap


def bootstrap(directory, session_factory):
    with session_factory.begin() as session:
        report = load_bootstrap(directory, session)
        if report.errors:
            session.rollback()
        return report
