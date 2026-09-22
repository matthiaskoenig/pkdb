"""Seed and serve the isolated browser fixture; never point at deployment data."""

import hashlib
import os
import subprocess
from pathlib import Path

import uvicorn
from sqlalchemy import select
from sqlalchemy.engine import make_url

from pkdb.config import Settings
from pkdb.db.models.users import EmailAddress, User
from pkdb.db.session import make_session_factory
from pkdb.files.store import FileStore
from pkdb.schemas.security import Principal
from pkdb.services.authentication import password_hash
from pkdb.services.ingestion import IngestionService


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
        add_frontend_plot_context,
        add_frontend_vocabulary,
        frontend_search_bundle,
        publish_frontend_fixture,
    )

    from pkdb.app import create_app

    subprocess.run(["alembic", "upgrade", "head"], check=True)
    subprocess.run(["pkdb", "bootstrap", "/app/bootstrap"], check=True)
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
                from pkdb.db.models.security import SecurityConfiguration

                config = session.get(SecurityConfiguration, 1)
                if config is None:
                    config = SecurityConfiguration(id=1)
                    session.add(config)
                config.designated_administrator_id = session.scalar(
                    select(User.id).where(User.username == "administrator")
                )
                from cryptography.fernet import Fernet

                from pkdb.db.models.mfa import MfaCredential

                credential = session.get(
                    MfaCredential, config.designated_administrator_id
                )
                if credential is None:
                    credential = MfaCredential(
                        user_id=config.designated_administrator_id, encrypted_secret=""
                    )
                    session.add(credential)
                credential.encrypted_secret = (
                    Fernet(settings.mfa_encryption_key.get_secret_value().encode())
                    .encrypt(b"JBSWY3DPEHPK3PXP")
                    .decode()
                )
                credential.confirmed = True
                credential.last_step = -1
                credential.recovery_digests = [
                    hashlib.sha256(f"frontend-{browser}-{attempt}".encode()).hexdigest()
                    for browser in ("chromium", "firefox", "webkit")
                    for attempt in range(3)
                ]
                creator = session.scalar(select(User).where(User.username == "curator"))
                principal = Principal(
                    user_id=creator.id, username=creator.username, role=creator.role
                )
                add_frontend_vocabulary(session)
                from pkdb.db.models.vocabulary import VocabularyNode

                species = session.get(VocabularyNode, "species")
                species.definition = {**species.definition, "choices": ["Homo sapiens"]}
            ingestion = IngestionService(
                factory,
                FileStore(Path(settings.file_root), factory, settings.upload_max_bytes),
                settings,
            )
            from sqlalchemy import update

            from pkdb.db.models.studies import Study

            with factory.begin() as session:
                session.execute(
                    update(Study)
                    .where(Study.sid == "FRONTEND_SCOPE")
                    .values(access="private")
                )
            ingestion.replace(frontend_search_bundle(), principal)
            with factory.begin() as session:
                publish_frontend_fixture(session)
                add_frontend_plot_context(session)
            factory.kw["bind"].dispose()

    asyncio.run(seed())
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    main()
