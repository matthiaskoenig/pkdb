"""Seed and serve the isolated browser fixture; never point at deployment data."""

import os
import subprocess
import tempfile
from pathlib import Path

import uvicorn
from sqlalchemy import select
from sqlalchemy.engine import make_url

from pkdb.schemas.security import Principal
from pkdb_server.config import Settings
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.db.session import make_session_factory
from pkdb_server.files.store import FileStore
from pkdb_server.services.authentication import password_hash
from pkdb_server.services.ingestion import IngestionService


def main():
    settings = Settings()
    url = make_url(settings.database_url)
    if (
        os.environ.get("PKDB_FRONTEND_FIXTURE") != "isolated-test-only"
        or url.database != "pkdb_frontend_test"
        or url.username != "pkdb_frontend_test"
        or url.host != "db"
    ):
        raise RuntimeError(
            "Fixture loader only accepts the isolated frontend test database"
        )
    from frontend_search import (
        FORMAT2_LEGACY_ISSUE,
        FORMAT2_LEGACY_PKDB_ID,
        FORMAT2_LEGACY_PMID,
        FORMAT2_LEGACY_SID,
        FORMAT2_PUBLIC_ISSUE,
        FORMAT2_PUBLIC_PKDB_ID,
        FORMAT2_PUBLIC_PMID,
        FORMAT2_PUBLIC_SID,
        add_frontend_plot_context,
        add_frontend_vocabulary,
        forget_views,
        frontend_search_bundle,
        publish_frontend_fixture,
        write_frontend_format2_study,
    )

    from pkdb_server.app import create_app

    subprocess.run(["alembic", "upgrade", "head"], check=True)
    subprocess.run(["pkdb-server", "bootstrap", "/app/bootstrap"], check=True)
    app = create_app(settings)
    # Seed after schema/bootstrap using the same service lifecycle as API tests.
    import asyncio

    async def seed():
        async with app.router.lifespan_context(app):
            factory = make_session_factory(settings.database_url)
            with factory.begin() as session:
                for name, role in [
                    ("curator", "curator"),
                    ("reader", "user"),
                    ("reader-chromium", "user"),
                    ("reader-firefox", "user"),
                    ("reader-webkit", "user"),
                    ("reviewer", "reviewer"),
                    ("administrator", "admin"),
                ]:
                    user = session.scalar(select(User).where(User.username == name))
                    if user is None:
                        user = User(
                            username=name,
                            role=role,
                            active=True,
                            email=f"{name}@example.invalid",
                        )
                        session.add(user)
                    session.flush()
                    if (
                        session.scalar(
                            select(EmailAddress).where(EmailAddress.user_id == user.id)
                        )
                        is None
                    ):
                        session.add(
                            EmailAddress(
                                user_id=user.id,
                                email=f"{name}@example.invalid",
                                is_primary=True,
                                is_verified=True,
                            )
                        )
                    user.password_hash = password_hash.hash(
                        "Frontend-test-password-42!"
                    )
                session.flush()
                from pkdb_server.db.models.security import SecurityConfiguration

                config = session.get(SecurityConfiguration, 1)
                if config is None:
                    config = SecurityConfiguration(id=1)
                    session.add(config)
                config.designated_administrator_id = session.scalar(
                    select(User.id).where(User.username == "administrator")
                )
                creator = session.scalar(select(User).where(User.username == "curator"))
                principal = Principal(
                    user_id=creator.id, username=creator.username, role=creator.role
                )
                add_frontend_vocabulary(session)
            ingestion = IngestionService(
                factory,
                FileStore(Path(settings.file_root), factory, settings.upload_max_bytes),
                settings,
            )
            from sqlalchemy import update

            from pkdb_server.db.models.studies import Study

            with factory.begin() as session:
                session.execute(
                    update(Study)
                    .where(Study.sid == "FRONTEND_SCOPE")
                    .values(access="private")
                )
            ingestion.replace(frontend_search_bundle(), principal)
            # Three study format 2 studies, released and under review, curated by
            # `curator`: Format2Fixture is private, Format2Public public (the anonymous
            # search sees it and FRONTEND_SCOPE), and Format2Legacy, private, loses its
            # stored views, as a study uploaded before the study pages of the website,
            # and shows on the record page. No test changes their access.
            with tempfile.TemporaryDirectory() as sources:
                ingestion.replace(
                    write_frontend_format2_study(Path(sources)), principal
                )
                ingestion.replace(
                    write_frontend_format2_study(
                        Path(sources),
                        FORMAT2_PUBLIC_SID,
                        pkdb_id=FORMAT2_PUBLIC_PKDB_ID,
                        issue=FORMAT2_PUBLIC_ISSUE,
                        pmid=FORMAT2_PUBLIC_PMID,
                        access="public",
                    ),
                    principal,
                )
                ingestion.replace(
                    write_frontend_format2_study(
                        Path(sources),
                        FORMAT2_LEGACY_SID,
                        pkdb_id=FORMAT2_LEGACY_PKDB_ID,
                        issue=FORMAT2_LEGACY_ISSUE,
                        pmid=FORMAT2_LEGACY_PMID,
                    ),
                    principal,
                )
            with factory.begin() as session:
                publish_frontend_fixture(session)
                add_frontend_plot_context(session)
                forget_views(session, FORMAT2_LEGACY_SID)
            factory.kw["bind"].dispose()

    asyncio.run(seed())
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
