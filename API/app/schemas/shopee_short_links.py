from __future__ import annotations

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class ShortLinkCreateRequest(BaseModel):
    originUrl: AnyHttpUrl
    subIds: list[str] | None = None

    @field_validator("subIds")
    @classmethod
    def validate_sub_ids(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            return None
        if len(value) > 5:
            raise ValueError("subIds supports at most 5 items")
        normalized: list[str] = []
        for item in value:
            stripped = item.strip()
            if not stripped:
                raise ValueError("subIds items must be non-empty strings")
            normalized.append(stripped)
        return normalized


class ShortLinkData(BaseModel):
    shortLink: str = Field(..., min_length=1)

