"""Typed acquisition provenance, independent of scientific calculation origin."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field


class SourceAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: str
    sha256: Annotated[str, Field(pattern=r"^[a-f0-9]{64}$")]


class Acquisition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source_key: Annotated[str, Field(min_length=1, max_length=255)]


class ManualCuration(Acquisition):
    kind: Literal["manual_curation"] = "manual_curation"
    source_key: Annotated[str, Field(min_length=1, max_length=255)] = "pkdb.manual"


class DataImport(Acquisition):
    kind: Literal["data_import"] = "data_import"
    release: str
    revision: str
    importer: str
    importer_version: str
    assets: list[SourceAsset] = Field(min_length=1)
    dataset_ids: list[str] = Field(default_factory=list)
    report_file: str | None = None


class AutomaticCuration(Acquisition):
    kind: Literal["automatic_curation"] = "automatic_curation"
    method: str
    version: str
    assets: list[SourceAsset] = Field(min_length=1)
    run_id: str


StudyProvenance = Annotated[
    ManualCuration | DataImport | AutomaticCuration, Field(discriminator="kind")
]
