from datetime import UTC, datetime, timedelta
from io import BytesIO

import pytest
from PIL import Image
from pkdb.schemas.profiles import ProfileUpdate
from pkdb.schemas.responses import UserResponse
from pkdb.schemas.security import Principal
from pydantic import ValidationError

from pkdb_server.db.models.credentials import BrowserSession
from pkdb_server.db.models.users import EmailAddress, User
from pkdb_server.services.authentication import AuthenticationFailed
from pkdb_server.services.authorization import AuthorizationDenied
from pkdb_server.services.credentials import session_principal
from pkdb_server.services.profiles import (
    ProfileService,
    public_profile,
    sanitize_avatar,
)


def picture(size=(128, 128), format="WEBP"):
    buffer = BytesIO()
    Image.new("RGB", size, "red").save(buffer, format)
    return buffer.getvalue()


def test_validation_and_public_allowlist():
    for field in (
        "role",
        "username",
        "email",
        "second_email",
        "avatar_url",
        "github_provenance",
    ):
        with pytest.raises(ValidationError):
            ProfileUpdate.model_validate({field: "admin"})
    assert (
        ProfileUpdate(orcid="https://orcid.org/0000-0002-1825-0097").orcid
        == "0000-0002-1825-0097"
    )
    with pytest.raises(ValidationError):
        ProfileUpdate(orcid="0000-0002-1825-0098")
    with pytest.raises(ValidationError):
        ProfileUpdate(github="https://github.com/mkoenig")
    user = User(
        username="scientist",
        email="private@example.org",
        password_hash="secret",
        role="admin",
    )
    result = public_profile(user)
    assert result["display_name"] == "scientist"
    assert not {"email", "password_hash", "role", "id", "active"} & result.keys()
    UserResponse.model_validate({**result, "first_name": "", "last_name": ""})
    with pytest.raises(ValidationError):
        UserResponse.model_validate(
            {
                **result,
                "first_name": "",
                "last_name": "",
                "email": "private@example.org",
            }
        )


def test_sanitization_bounds_and_formats():
    data, size = sanitize_avatar(picture((1000, 700), "PNG"))
    with Image.open(BytesIO(data)) as image:
        assert image.format == "WEBP" and image.size == (256, 256)
        assert not image.getexif()
    assert size == 256
    assert sanitize_avatar(picture())[1] == 128
    for value in (b"<svg/>", b"x" * (5 * 1024 * 1024 + 1), picture(format="GIF")):
        with pytest.raises(ValueError):
            sanitize_avatar(value)
    output = BytesIO()
    Image.new("RGB", (10, 10), "red").save(
        output, "PNG", save_all=True, append_images=[Image.new("RGB", (10, 10), "blue")]
    )
    with pytest.raises(ValueError, match="Animated"):
        sanitize_avatar(output.getvalue())


@pytest.fixture
def profile_context(session_factory, tmp_path):
    with session_factory.begin() as session:
        user = User(username="profile-owner", active=True)
        session.add(user)
        session.flush()
        now = datetime.now(UTC)
        credential = BrowserSession(
            user_id=user.id,
            digest="a" * 64,
            last_seen_at=now,
            expires_at=now + timedelta(days=1),
            authenticated_at=now,
        )
        session.add_all(
            [
                credential,
                EmailAddress(
                    user_id=user.id,
                    email="primary@example.org",
                    is_primary=True,
                    is_verified=True,
                ),
                EmailAddress(
                    user_id=user.id, email="second@example.org", is_verified=False
                ),
            ]
        )
        session.flush()
        actor = session_principal(user, credential)
    return ProfileService(session_factory, tmp_path), actor


def test_owner_update_contact_privacy_and_session_requirement(
    profile_context, session_factory
):
    service, actor = profile_context
    result = service.update(
        actor, {"display_name": "研究者", "github": "scientist", "affiliation": "Lab"}
    )
    assert result["display_name"] == "研究者"
    assert result["email"] == "primary@example.org"
    assert result["second_email_verified"] is False
    assert result["github_provenance"] == "self_asserted"
    with pytest.raises(AuthorizationDenied):
        service.read(Principal(user_id=actor.user_id, credential_kind="api_key"))
    with session_factory.begin() as session:
        user = session.get(User, actor.user_id)
        user.github_provenance = "authenticated"
    result = service.update(actor, {"github": "someone-else"})
    assert result["github"] == "someone-else"
    assert result["github_provenance"] == "self_asserted"
    with session_factory.begin() as session:
        session.get(BrowserSession, actor.credential_id).revoked_at = datetime.now(UTC)
    with pytest.raises(AuthenticationFailed):
        service.read(actor)


def test_avatar_lifecycle_and_import_preserves_edits(profile_context, session_factory):
    service, actor = profile_context
    content = picture()
    result = service.set_avatar(actor, content)
    key = result["avatar_url"].rsplit("/", 1)[-1]
    assert service.avatar(key).exists()
    service.update(actor, {"display_name": None, "affiliation": "My lab"})
    service.set_avatar(actor)
    with pytest.raises(LookupError):
        service.avatar(key)
    with session_factory.begin() as session:
        user = session.get(User, actor.user_id)
        imported = service.import_profile(
            session,
            user,
            {
                "display_name": "Imported",
                "affiliation": "Other lab",
                "github": "imported",
            },
            content,
        )
    assert imported["imported_fields"] == ["github"]
    result = service.read(actor)
    assert result["display_name"] == "profile-owner"
    assert result["affiliation"] == "My lab"
    assert result["avatar_url"].endswith("default.svg")
    assert result["github_provenance"] == "imported"
