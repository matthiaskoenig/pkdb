"""Small transport contracts for legacy staged uploads."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FinalizeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    sid: str = Field(min_length=1, max_length=255)
    action: Literal["index"] = "index"
