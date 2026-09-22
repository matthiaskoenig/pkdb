"""Editable public profile fields; authorization and contact fields are excluded."""

import re

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    display_name: str | None = Field(default=None, max_length=200)
    affiliation: str | None = Field(default=None, max_length=250)
    title: str | None = Field(default=None, max_length=100)
    github: str | None = Field(default=None, max_length=39)
    orcid: str | None = Field(default=None, max_length=37)

    github_visible: bool = Field(default=True, strict=True)
    orcid_visible: bool = Field(default=True, strict=True)

    @field_validator("display_name", "affiliation", "title", "github", "orcid")
    @classmethod
    def empty_to_none(cls, value):
        return value or None

    @field_validator("github")
    @classmethod
    def github_handle(cls, value):
        if value is not None and (
            not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]*[A-Za-z0-9])?", value)
            or "--" in value
        ):
            raise ValueError("Supply a GitHub handle, not a URL")
        return value

    @field_validator("orcid")
    @classmethod
    def orcid_identifier(cls, value):
        if value is None:
            return None
        value = value.removeprefix("https://orcid.org/").upper()
        if not re.fullmatch(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]", value):
            raise ValueError("Supply a hyphenated ORCID iD")
        digits = value.replace("-", "")
        total = 0
        for digit in digits[:-1]:
            total = (total + int(digit)) * 2
        check = (12 - total % 11) % 11
        if digits[-1] != ("X" if check == 10 else str(check)):
            raise ValueError("Invalid ORCID checksum")
        return value
