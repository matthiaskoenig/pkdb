"""The curator roster of a PK-DB server, read by the GitHub issue sync."""

from pydantic import BaseModel, ConfigDict


class Curator(BaseModel):
    model_config = ConfigDict(extra="ignore")
    username: str
    name: str
    github: str | None = None


class CuratorList(BaseModel):
    model_config = ConfigDict(extra="ignore")
    curators: list[Curator]
