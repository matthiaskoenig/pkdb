from typing import Literal

from pydantic import BaseModel, ConfigDict

Action = Literal["read", "write", "delete", "read_file", "administer"]


class Principal(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    user_id: int | None = None
    username: str | None = None
    role: str = "anonymous"


class StudyAccess(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    sid: str
    access: Literal["public", "private"]
    licence: Literal["open", "closed"]
    creator_id: int
    curator_ids: frozenset[int] = frozenset()
    collaborator_ids: frozenset[int] = frozenset()
