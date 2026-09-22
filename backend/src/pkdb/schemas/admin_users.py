from typing import Literal

from pydantic import Field

from pkdb.schemas.accounts import AccountInput, Registration

LegacyRole = Literal["basic", "curator", "reviewer"]


class AdminUserCreate(Registration):
    username: str = Field(min_length=1, max_length=150, pattern=r"^[\w.@+-]+$")
    password: str = Field(min_length=8, max_length=1024)
    first_name: str = Field(default="", max_length=150)
    last_name: str = Field(default="", max_length=150)
    groups: list[LegacyRole] = Field(min_length=1, max_length=1)


class AdminUserPatch(AccountInput):
    # The legacy update serializer accepts but ignores this read-only field.
    username: str | None = None
    first_name: str = Field(default="", max_length=150)
    last_name: str = Field(default="", max_length=150)
    groups: list[LegacyRole] = Field(default_factory=list, min_length=1, max_length=1)


class AdminUserPut(AdminUserPatch):
    groups: list[LegacyRole] = Field(min_length=1, max_length=1)
