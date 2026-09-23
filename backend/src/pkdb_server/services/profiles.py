"""Owner-only profile editing and locally managed, sanitized avatars."""

from datetime import UTC, datetime, timedelta
from hashlib import sha256
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from PIL import Image, ImageOps, UnidentifiedImageError
from sqlalchemy import select

from pkdb.schemas.profiles import ProfileUpdate
from pkdb_server.db.models.users import AccountThrottle, AvatarAsset, EmailAddress, User
from pkdb_server.services.accounts import AccountThrottled
from pkdb_server.services.authentication import AuthenticationFailed

MAX_AVATAR_BYTES = 5 * 1024 * 1024
MAX_AVATAR_PIXELS = 16_000_000
FALLBACK_URL = "/api/v1/avatars/default.svg"


def public_profile(user: User) -> dict:
    """Explicit allowlist, safe for attribution on already-visible content."""
    return {
        "username": user.username,
        "display_name": user.display_name or user.username,
        "affiliation": user.affiliation,
        "title": user.title,
        "github": user.github if user.github_visible is not False else None,
        "github_provenance": user.github_provenance
        if user.github_visible is not False
        else None,
        "orcid": user.orcid if user.orcid_visible is not False else None,
        "orcid_provenance": user.orcid_provenance
        if user.orcid_visible is not False
        else None,
        "avatar_url": f"/api/v1/avatars/{user.avatar_key}"
        if user.avatar_key
        else FALLBACK_URL,
    }


def sanitize_avatar(content: bytes) -> tuple[bytes, int]:
    if not content or len(content) > MAX_AVATAR_BYTES:
        raise ValueError("Avatar must contain at most 5 MiB")
    try:
        with Image.open(BytesIO(content)) as source:
            if source.format not in {"JPEG", "PNG", "WEBP"}:
                raise ValueError("Avatar must be JPEG, PNG, or WebP")
            if getattr(source, "n_frames", 1) != 1:
                raise ValueError("Animated avatars are not supported")
            if source.width * source.height > MAX_AVATAR_PIXELS:
                raise ValueError("Avatar exceeds 16 megapixels")
            source.load()
            oriented = ImageOps.exif_transpose(source)
            size = min(256, oriented.width, oriented.height)
            thumb = ImageOps.fit(oriented.convert("RGB"), (size, size))
            # A fresh image strips EXIF, ICC profiles, comments and other metadata.
            clean = Image.new("RGB", thumb.size)
            clean.paste(thumb)
            buffer = BytesIO()
            clean.save(buffer, "WEBP", quality=85)
            return buffer.getvalue(), size
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
        raise ValueError("Invalid avatar image") from exc


class ProfileService:
    def __init__(self, session_factory, file_root):
        self.session_factory = session_factory
        self.root = Path(file_root) / "avatars"
        self.root.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _owner(session, principal):
        from pkdb_server.services.credentials import require_session

        user = session.scalar(
            select(User).where(User.id == principal.user_id).with_for_update()
        )
        require_session(principal, session)
        if user is None or not user.active:
            raise AuthenticationFailed()
        return user

    @staticmethod
    def _private(session, user):
        result = public_profile(user)
        addresses = session.scalars(
            select(EmailAddress)
            .where(EmailAddress.user_id == user.id)
            .order_by(EmailAddress.id)
        ).all()
        primary = next((item for item in addresses if item.is_primary), None)
        secondary = next((item for item in addresses if not item.is_primary), None)
        result.update(
            github=user.github,
            orcid=user.orcid,
            github_provenance=user.github_provenance,
            orcid_provenance=user.orcid_provenance,
            github_visible=user.github_visible,
            orcid_visible=user.orcid_visible,
            id=user.id,
            role=user.role,
            email=primary.email if primary else None,
            email_verified=primary.is_verified if primary else False,
            second_email=secondary.email if secondary else None,
            second_email_verified=secondary.is_verified if secondary else False,
            emails=[
                {
                    "id": item.id,
                    "email": item.email,
                    "is_primary": item.is_primary,
                    "is_verified": item.is_verified,
                }
                for item in addresses
            ],
        )
        return result

    def read(self, principal):
        with self.session_factory.begin() as session:
            return self._private(session, self._owner(session, principal))

    def update(self, principal, values):
        values = ProfileUpdate.model_validate(values).model_dump(exclude_unset=True)
        with self.session_factory.begin() as session:
            user = self._owner(session, principal)
            for field, value in values.items():
                setattr(user, field, value)
                if field in {"github", "orcid"}:
                    setattr(
                        user, f"{field}_provenance", "self_asserted" if value else None
                    )
            user.profile_edited_fields = sorted(
                set(user.profile_edited_fields or []) | values.keys()
            )
            session.flush()
            return self._private(session, user)

    def import_profile(
        self, session, user, values, avatar_content=None, provenance=None
    ):
        """Fill untouched fields from a reviewed roster in the caller's transaction.

        A failed caller transaction can leave an unreferenced file; cleanup_orphans
        removes these after a grace period. No database reference is committed early.
        """
        values = ProfileUpdate.model_validate(values).model_dump(exclude_unset=True)
        edited = set(user.profile_edited_fields or [])
        changed = []
        for field, value in values.items():
            if value and field not in edited and not getattr(user, field):
                setattr(user, field, value)
                if field in {"github", "orcid"}:
                    setattr(user, f"{field}_provenance", "imported")
                changed.append(field)
        if avatar_content and not user.avatar_initialized and not user.avatar_key:
            # Preserve site WebP thumbnails exactly, including nonsquare originals.
            normalized, size = sanitize_avatar(avatar_content)
            provenance = dict(provenance or {})
            provenance["source_checksum"] = sha256(avatar_content).hexdigest()
            with Image.open(BytesIO(avatar_content)) as source:
                if source.format == "WEBP" and max(source.size) <= 256:
                    width, height = source.size
                else:
                    avatar_content = normalized
                    width = height = size
            key = uuid4().hex
            (self.root / f"{key}.webp").write_bytes(avatar_content)
            session.add(
                AvatarAsset(
                    key=key,
                    user_id=user.id,
                    media_type="image/webp",
                    width=width,
                    height=height,
                    checksum=sha256(avatar_content).hexdigest(),
                    source_kind="import",
                    provenance=provenance,
                )
            )
            user.avatar_key = key
            user.avatar_initialized = True
            changed.append("avatar")
        session.flush()
        return {"imported_fields": changed}

    def cleanup_orphans(self, grace=timedelta(days=1)):
        """Remove files left by interrupted/rolled-back imports after a grace period."""
        cutoff = datetime.now(UTC).timestamp() - grace.total_seconds()
        removed = 0
        with self.session_factory() as session:
            referenced = set(session.scalars(select(AvatarAsset.key)))
            for path in self.root.glob("*.webp"):
                if path.stem not in referenced and path.stat().st_mtime < cutoff:
                    path.unlink(missing_ok=True)
                    removed += 1
        return removed

    def avatar(self, key):
        # Only current assets are served; random identifiers prevent account enumeration.
        with self.session_factory() as session:
            asset = session.get(AvatarAsset, key)
            if (
                asset is None
                or session.scalar(select(User.id).where(User.avatar_key == key)) is None
            ):
                raise LookupError("Avatar not found")
            path = self.root / f"{asset.key}.webp"
            if not path.is_file():
                raise LookupError("Avatar not found")
            return path

    def set_avatar(self, principal, content=None):
        normalized = sanitize_avatar(content) if content is not None else None
        key = uuid4().hex if normalized else None
        path = self.root / f"{key}.webp" if key else None
        try:
            with self.session_factory.begin() as session:
                user = self._owner(session, principal)
                now = datetime.now(UTC)
                throttle_key = sha256(f"avatar:{user.id}".encode()).hexdigest()
                throttle = session.get(AccountThrottle, throttle_key)
                if throttle is None:
                    throttle = AccountThrottle(
                        key=throttle_key,
                        attempts=0,
                        expires_at=now + timedelta(hours=1),
                    )
                    session.add(throttle)
                elif throttle.expires_at <= now:
                    throttle.attempts = 0
                    throttle.expires_at = now + timedelta(hours=1)
                if throttle.attempts >= 20:
                    raise AccountThrottled()
                throttle.attempts += 1
                old_key = user.avatar_key
                if normalized:
                    data, size = normalized
                    assert path is not None
                    path.write_bytes(data)
                    session.add(
                        AvatarAsset(
                            key=key,
                            user_id=user.id,
                            media_type="image/webp",
                            width=size,
                            height=size,
                            checksum=sha256(data).hexdigest(),
                            source_kind="upload",
                        )
                    )
                user.avatar_key = key
                user.avatar_initialized = True
                if old_key:
                    old = session.get(AvatarAsset, old_key)
                    if old:
                        session.delete(old)
                session.flush()
                result = self._private(session, user)
        except BaseException:
            if path:
                path.unlink(missing_ok=True)
            raise
        if old_key:
            (self.root / f"{old_key}.webp").unlink(missing_ok=True)
        return result
