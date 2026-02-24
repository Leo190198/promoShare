from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


def _validate_hhmm(value: str) -> str:
    parts = value.split(":")
    if len(parts) != 2 or not parts[0].isdigit() or not parts[1].isdigit():
        raise ValueError("must be HH:MM")
    h, m = int(parts[0]), int(parts[1])
    if h < 0 or h > 23 or m < 0 or m > 59:
        raise ValueError("must be HH:MM")
    return f"{h:02d}:{m:02d}"


class ThemeCreateRequest(BaseModel):
    keyword: str = Field(..., min_length=1, max_length=255)
    isActive: bool = True

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str) -> str:
        return value.strip()


class ThemeUpdateRequest(BaseModel):
    keyword: str | None = Field(default=None, min_length=1, max_length=255)
    isActive: bool | None = None

    @field_validator("keyword")
    @classmethod
    def normalize_keyword(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return value.strip()


class ThemeData(BaseModel):
    id: int
    keyword: str
    isActive: bool
    createdAt: datetime
    updatedAt: datetime | None = None


class ThemeListData(BaseModel):
    themes: list[ThemeData]
    total: int


class PostingWindowUpdateRequest(BaseModel):
    startTime: str
    endTime: str
    isActive: bool = True

    @field_validator("startTime", "endTime")
    @classmethod
    def validate_hhmm(cls, value: str) -> str:
        return _validate_hhmm(value)


class PostingWindowData(BaseModel):
    id: int
    startTime: str
    endTime: str
    isActive: bool


class AutomationSettingsData(BaseModel):
    automationEnabled: bool
    timezone: str
    targetGroupId: str | None = None
    targetGroupName: str | None = None
    dailyPostTarget: int
    dailyPostLimit: int
    pricePrefix: str
    messageTemplate: str
    nextSuggestedGenerationAt: datetime | None = None


class AutomationStatusData(BaseModel):
    settings: AutomationSettingsData
    postingWindow: PostingWindowData | None = None
    queue: dict
    suggestions: dict
    whatsapp: dict | None = None
    scheduler: dict


class SuggestionGenerateRequest(BaseModel):
    limitPerTheme: int | None = Field(default=None, ge=1, le=50)
    maxNewSuggestions: int | None = Field(default=None, ge=1, le=200)
    onlyActiveThemes: bool = True


class SuggestionData(BaseModel):
    id: int
    sourceKeyword: str
    itemId: int
    shopId: int | None = None
    productName: str
    imageUrl: str | None = None
    priceMin: str | None = None
    priceMax: str | None = None
    formattedPrice: str | None = None
    productLink: str | None = None
    offerLink: str | None = None
    shortLink: str | None = None
    score: float
    status: str
    approvedAction: str | None = None
    queueScheduledFor: datetime | None = None
    createdAt: datetime
    approvedAt: datetime | None = None
    sentAt: datetime | None = None
    lastError: str | None = None


class SuggestionListData(BaseModel):
    suggestions: list[SuggestionData]
    total: int


class GenerateSuggestionsResult(BaseModel):
    inserted: int
    skippedDuplicates: int
    inspected: int
    suggestions: list[SuggestionData]


class SuggestionRejectRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=500)


class SuggestionApproveResponse(BaseModel):
    suggestion: SuggestionData
    queueItemId: int | None = None
    queueStatus: str | None = None
    messagePreview: str | None = None
    waResult: dict | None = None


class QueueItemData(BaseModel):
    id: int
    suggestionId: int
    chatId: str
    scheduledAt: datetime
    status: str
    attempts: int
    createdAt: datetime
    sentAt: datetime | None = None
    waMessageId: str | None = None
    lastError: str | None = None
    productName: str | None = None


class QueueListData(BaseModel):
    items: list[QueueItemData]
    total: int


class HistoryItemData(BaseModel):
    id: int
    suggestionId: int | None = None
    itemId: int
    chatId: str
    productName: str
    shortLink: str | None = None
    status: str
    waMessageId: str | None = None
    sentAt: datetime


class HistoryListData(BaseModel):
    items: list[HistoryItemData]
    total: int


class SuggestionListQuery(BaseModel):
    status: Literal["pending", "approved", "rejected", "queued", "sent", "failed"] | None = None
    limit: int = Field(default=50, ge=1, le=200)


class QueueListQuery(BaseModel):
    status: Literal["queued", "sending", "sent", "failed"] | None = None
    limit: int = Field(default=50, ge=1, le=200)


class HistoryListQuery(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)

