from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AutomationSettings(Base):
    __tablename__ = "automation_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    automation_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="America/Sao_Paulo")
    target_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_group_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    daily_post_target: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    daily_post_limit: Mapped[int] = mapped_column(Integer, nullable=False, default=15)
    price_prefix: Mapped[str] = mapped_column(String(64), nullable=False, default="A partir de R$ ")
    message_template: Mapped[str] = mapped_column(Text, nullable=False, default="🔥 {productName}\n💰 A partir de R$ {formattedPrice}\n🔗 {shortLink}")
    last_suggestion_generation_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_scheduler_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class PostingWindow(Base):
    __tablename__ = "posting_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Theme(Base):
    __tablename__ = "themes"
    __table_args__ = (UniqueConstraint("keyword", name="uq_theme_keyword"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_keyword: Mapped[str] = mapped_column(String(255), nullable=False)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    shop_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    price_min: Mapped[str | None] = mapped_column(String(64), nullable=True)
    price_max: Mapped[str | None] = mapped_column(String(64), nullable=True)
    formatted_price: Mapped[str | None] = mapped_column(String(64), nullable=True)
    product_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    offer_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    short_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    commission_rate: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rating_star: Mapped[str | None] = mapped_column(String(32), nullable=True)
    sales: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[float] = mapped_column(Float, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    approved_action: Mapped[str | None] = mapped_column(String(32), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    queue_scheduled_for: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    queue_items: Mapped[list["QueueItem"]] = relationship(back_populates="suggestion")


class QueueItem(Base):
    __tablename__ = "queue_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    suggestion_id: Mapped[int] = mapped_column(ForeignKey("suggestions.id"), nullable=False, index=True)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    scheduled_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued", index=True)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wa_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    suggestion: Mapped["Suggestion"] = relationship(back_populates="queue_items")


class PostHistory(Base):
    __tablename__ = "post_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    suggestion_id: Mapped[int | None] = mapped_column(ForeignKey("suggestions.id"), nullable=True, index=True)
    item_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    shop_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    chat_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    product_name: Mapped[str] = mapped_column(Text, nullable=False)
    message_text: Mapped[str] = mapped_column(Text, nullable=False)
    short_link: Mapped[str | None] = mapped_column(Text, nullable=True)
    wa_message_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="sent")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())

