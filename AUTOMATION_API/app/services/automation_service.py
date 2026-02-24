from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.exceptions import ApiException
from app.models import AutomationSettings, PostHistory, PostingWindow, QueueItem, Suggestion, Theme
from app.schemas.automation import (
    AutomationSettingsData,
    AutomationStatusData,
    GenerateSuggestionsResult,
    HistoryItemData,
    HistoryListData,
    PostingWindowData,
    PostingWindowUpdateRequest,
    QueueItemData,
    QueueListData,
    SuggestionApproveResponse,
    SuggestionData,
    SuggestionGenerateRequest,
    SuggestionListData,
    SuggestionRejectRequest,
    ThemeCreateRequest,
    ThemeData,
    ThemeListData,
    ThemeUpdateRequest,
)
from app.services.api_clients import ShopeeApiClient, WhatsAppApiClient

logger = logging.getLogger(__name__)

OPEN_SUGGESTION_STATUSES = {"pending", "approved", "queued"}


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_hhmm(value: str) -> time:
    hour, minute = value.split(":")
    return time(hour=int(hour), minute=int(minute))


def format_brl_price(raw: str | None) -> str | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if not text:
        return None
    try:
        if text.isdigit():
            amount = Decimal(text)
        elif "," in text and "." in text:
            amount = Decimal(text.replace(".", "").replace(",", "."))
        else:
            amount = Decimal(text.replace(",", "."))
    except InvalidOperation:
        return text
    amount = amount.quantize(Decimal("0.01"))
    integer_part, decimal_part = f"{amount:.2f}".split(".")
    chunks: list[str] = []
    while integer_part:
        chunks.append(integer_part[-3:])
        integer_part = integer_part[:-3]
    return ".".join(reversed(chunks)) + "," + decimal_part


def _safe_float(value: Any) -> float:
    try:
        return float(str(value).replace(",", "."))
    except Exception:
        return 0.0


def _safe_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _compute_score(node: dict[str, Any]) -> float:
    commission = _safe_float(node.get("commissionRate"))
    rating = _safe_float(node.get("ratingStar"))
    sales = _safe_int(node.get("sales"))
    discount = _safe_int(node.get("priceDiscountRate"))
    return round((commission * 100) + (rating * 2) + min(sales, 5000) / 200 + discount / 10, 4)


@dataclass
class TickResult:
    generated: int = 0
    queued_processed: int = 0
    queued_sent: int = 0
    queued_failed: int = 0
    skipped_not_ready: bool = False

    def model_dump(self) -> dict[str, Any]:
        return {
            "generated": self.generated,
            "queuedProcessed": self.queued_processed,
            "queuedSent": self.queued_sent,
            "queuedFailed": self.queued_failed,
            "skippedNotReady": self.skipped_not_ready,
        }


class AutomationService:
    def __init__(self, settings: Settings, shopee_client: ShopeeApiClient, wa_client: WhatsAppApiClient) -> None:
        self.settings = settings
        self.shopee_client = shopee_client
        self.wa_client = wa_client

    def bootstrap_defaults(self, db: Session) -> None:
        settings_row = db.get(AutomationSettings, 1)
        if settings_row is None:
            db.add(
                AutomationSettings(
                    id=1,
                    automation_enabled=self.settings.automation_enabled,
                    timezone=self.settings.automation_timezone,
                    target_group_id=self.settings.automation_default_group_id or None,
                    target_group_name=self.settings.automation_default_group_name or None,
                    daily_post_target=self.settings.automation_default_daily_target,
                    daily_post_limit=self.settings.automation_default_daily_limit,
                    price_prefix="A partir de R$ ",
                    message_template=self.settings.automation_default_message_template,
                )
            )

        window = db.get(PostingWindow, 1)
        if window is None:
            db.add(
                PostingWindow(
                    id=1,
                    start_time=self.settings.automation_default_start_time,
                    end_time=self.settings.automation_default_end_time,
                    is_active=True,
                )
            )

        if not db.scalars(select(Theme)).first():
            for keyword in self.settings.default_theme_keywords_list:
                db.add(Theme(keyword=keyword, is_active=True))

        db.commit()

    def _settings_row(self, db: Session) -> AutomationSettings:
        row = db.get(AutomationSettings, 1)
        if row is None:
            self.bootstrap_defaults(db)
            row = db.get(AutomationSettings, 1)
        if row is None:
            raise ApiException(status_code=500, code="settings_missing", message="Automation settings not initialized")
        return row

    def _window_row(self, db: Session) -> PostingWindow | None:
        return db.get(PostingWindow, 1)

    def _theme_data(self, row: Theme) -> ThemeData:
        return ThemeData(
            id=row.id,
            keyword=row.keyword,
            isActive=row.is_active,
            createdAt=row.created_at,
            updatedAt=row.updated_at,
        )

    def _window_data(self, row: PostingWindow | None) -> PostingWindowData | None:
        if row is None:
            return None
        return PostingWindowData(id=row.id, startTime=row.start_time, endTime=row.end_time, isActive=row.is_active)

    def _suggestion_data(self, row: Suggestion) -> SuggestionData:
        return SuggestionData(
            id=row.id,
            sourceKeyword=row.source_keyword,
            itemId=row.item_id,
            shopId=row.shop_id,
            productName=row.product_name,
            imageUrl=row.image_url,
            priceMin=row.price_min,
            priceMax=row.price_max,
            formattedPrice=row.formatted_price,
            productLink=row.product_link,
            offerLink=row.offer_link,
            shortLink=row.short_link,
            score=row.score,
            status=row.status,
            approvedAction=row.approved_action,
            queueScheduledFor=row.queue_scheduled_for,
            createdAt=row.created_at,
            approvedAt=row.approved_at,
            sentAt=row.sent_at,
            lastError=row.last_error,
        )

    def _queue_item_data(self, row: QueueItem) -> QueueItemData:
        return QueueItemData(
            id=row.id,
            suggestionId=row.suggestion_id,
            chatId=row.chat_id,
            scheduledAt=row.scheduled_at,
            status=row.status,
            attempts=row.attempts,
            createdAt=row.created_at,
            sentAt=row.sent_at,
            waMessageId=row.wa_message_id,
            lastError=row.last_error,
            productName=row.suggestion.product_name if row.suggestion else None,
        )

    def _history_item_data(self, row: PostHistory) -> HistoryItemData:
        return HistoryItemData(
            id=row.id,
            suggestionId=row.suggestion_id,
            itemId=row.item_id,
            chatId=row.chat_id,
            productName=row.product_name,
            shortLink=row.short_link,
            status=row.status,
            waMessageId=row.wa_message_id,
            sentAt=row.sent_at,
        )

    def list_themes(self, db: Session) -> ThemeListData:
        self.bootstrap_defaults(db)
        rows = db.scalars(select(Theme).order_by(Theme.id.asc())).all()
        items = [self._theme_data(row) for row in rows]
        return ThemeListData(themes=items, total=len(items))

    def create_theme(self, db: Session, payload: ThemeCreateRequest) -> ThemeData:
        self.bootstrap_defaults(db)
        keyword = payload.keyword.strip()
        existing = db.scalar(select(Theme).where(func.lower(Theme.keyword) == keyword.lower()))
        if existing:
            raise ApiException(status_code=409, code="theme_exists", message="Theme keyword already exists", details={"keyword": keyword})
        row = Theme(keyword=keyword, is_active=payload.isActive)
        db.add(row)
        db.commit()
        db.refresh(row)
        return self._theme_data(row)

    def update_theme(self, db: Session, theme_id: int, payload: ThemeUpdateRequest) -> ThemeData:
        row = db.get(Theme, theme_id)
        if row is None:
            raise ApiException(status_code=404, code="theme_not_found", message="Theme not found", details={"themeId": theme_id})
        if payload.keyword is not None:
            keyword = payload.keyword.strip()
            existing = db.scalar(select(Theme).where(func.lower(Theme.keyword) == keyword.lower(), Theme.id != theme_id))
            if existing:
                raise ApiException(status_code=409, code="theme_exists", message="Theme keyword already exists", details={"keyword": keyword})
            row.keyword = keyword
        if payload.isActive is not None:
            row.is_active = payload.isActive
        db.commit()
        db.refresh(row)
        return self._theme_data(row)

    def get_posting_window(self, db: Session) -> PostingWindowData | None:
        self.bootstrap_defaults(db)
        return self._window_data(self._window_row(db))

    def update_posting_window(self, db: Session, payload: PostingWindowUpdateRequest) -> PostingWindowData:
        self.bootstrap_defaults(db)
        row = self._window_row(db)
        if row is None:
            row = PostingWindow(id=1, start_time=payload.startTime, end_time=payload.endTime, is_active=payload.isActive)
            db.add(row)
        else:
            row.start_time = payload.startTime
            row.end_time = payload.endTime
            row.is_active = payload.isActive
        db.commit()
        db.refresh(row)
        return self._window_data(row)  # type: ignore[arg-type]

    def _dedup_item_sets(self, db: Session) -> tuple[set[int], set[int]]:
        cutoff = utc_now() - timedelta(days=self.settings.product_dedup_days)
        recent_history_item_ids = set(
            db.scalars(select(PostHistory.item_id).where(PostHistory.sent_at >= cutoff, PostHistory.status == "sent")).all()
        )
        open_suggestion_item_ids = set(
            db.scalars(
                select(Suggestion.item_id).where(
                    Suggestion.created_at >= cutoff,
                    Suggestion.status.in_(sorted(OPEN_SUGGESTION_STATUSES)),
                )
            ).all()
        )
        return recent_history_item_ids, open_suggestion_item_ids

    def _suggestion_from_product_node(self, keyword: str, node: dict[str, Any]) -> Suggestion | None:
        if not node.get("itemId") or not node.get("productName"):
            return None
        return Suggestion(
            source_keyword=keyword,
            item_id=int(node["itemId"]),
            shop_id=int(node["shopId"]) if node.get("shopId") is not None else None,
            product_name=str(node["productName"]),
            image_url=node.get("imageUrl"),
            price_min=node.get("priceMin"),
            price_max=node.get("priceMax"),
            formatted_price=format_brl_price(node.get("priceMin")),
            product_link=node.get("productLink"),
            offer_link=node.get("offerLink"),
            short_link=None,
            commission_rate=node.get("commissionRate"),
            rating_star=node.get("ratingStar"),
            sales=_safe_int(node.get("sales")) if node.get("sales") is not None else None,
            score=_compute_score(node),
            status="pending",
            raw_payload=node,
        )

    def generate_suggestions(self, db: Session, payload: SuggestionGenerateRequest) -> GenerateSuggestionsResult:
        self.bootstrap_defaults(db)
        max_per_theme = payload.limitPerTheme or self.settings.suggestion_fetch_limit_per_theme
        max_new = payload.maxNewSuggestions or self.settings.suggestion_max_per_run

        query = select(Theme).order_by(Theme.id.asc())
        if payload.onlyActiveThemes:
            query = query.where(Theme.is_active.is_(True))
        themes = db.scalars(query).all()

        recent_history_item_ids, open_suggestion_item_ids = self._dedup_item_sets(db)
        inserted: list[Suggestion] = []
        inspected = 0
        skipped_duplicates = 0

        for theme in themes:
            if len(inserted) >= max_new:
                break
            try:
                nodes = self.shopee_client.search_products(keyword=theme.keyword, page=1, limit=max_per_theme)
            except ApiException as exc:
                logger.warning("Failed to fetch suggestions for theme '%s': %s", theme.keyword, exc.message)
                continue

            for node in nodes:
                inspected += 1
                suggestion = self._suggestion_from_product_node(theme.keyword, node)
                if suggestion is None:
                    continue
                if suggestion.item_id in recent_history_item_ids or suggestion.item_id in open_suggestion_item_ids:
                    skipped_duplicates += 1
                    continue
                db.add(suggestion)
                db.flush()
                inserted.append(suggestion)
                open_suggestion_item_ids.add(suggestion.item_id)
                if len(inserted) >= max_new:
                    break

        settings_row = self._settings_row(db)
        settings_row.last_suggestion_generation_at = utc_now()
        db.commit()

        for row in inserted:
            db.refresh(row)

        return GenerateSuggestionsResult(
            inserted=len(inserted),
            skippedDuplicates=skipped_duplicates,
            inspected=inspected,
            suggestions=[self._suggestion_data(row) for row in inserted],
        )

    def list_suggestions(self, db: Session, *, status: str | None, limit: int) -> SuggestionListData:
        self.bootstrap_defaults(db)
        query = select(Suggestion).order_by(Suggestion.created_at.desc(), Suggestion.id.desc())
        if status:
            query = query.where(Suggestion.status == status)
        rows = db.scalars(query.limit(limit)).all()

        total_query = select(func.count(Suggestion.id))
        if status:
            total_query = total_query.where(Suggestion.status == status)
        total = int(db.scalar(total_query) or 0)
        return SuggestionListData(suggestions=[self._suggestion_data(row) for row in rows], total=total)

    def _timezone(self, db: Session) -> ZoneInfo:
        settings_row = self._settings_row(db)
        try:
            return ZoneInfo(settings_row.timezone or self.settings.automation_timezone)
        except Exception as exc:
            raise ApiException(status_code=500, code="invalid_timezone", message="Invalid automation timezone") from exc

    def _window_bounds_for_local_day(self, db: Session, day_local: date) -> tuple[datetime, datetime]:
        tz = self._timezone(db)
        window = self._window_row(db)
        if window is None or not window.is_active:
            raise ApiException(status_code=400, code="posting_window_missing", message="Posting window is not configured")
        start_local = datetime.combine(day_local, parse_hhmm(window.start_time), tzinfo=tz)
        end_local = datetime.combine(day_local, parse_hhmm(window.end_time), tzinfo=tz)
        if end_local <= start_local:
            end_local = end_local + timedelta(days=1)
        return start_local, end_local

    def _is_within_window(self, db: Session, dt_utc: datetime) -> bool:
        tz = self._timezone(db)
        local_dt = dt_utc.astimezone(tz)
        start_local, end_local = self._window_bounds_for_local_day(db, local_dt.date())
        return start_local <= local_dt <= end_local

    def _next_window_start(self, db: Session, after_utc: datetime) -> datetime:
        tz = self._timezone(db)
        local_dt = after_utc.astimezone(tz)
        start_local, end_local = self._window_bounds_for_local_day(db, local_dt.date())
        if local_dt <= start_local:
            return start_local.astimezone(UTC)
        if local_dt <= end_local:
            return local_dt.astimezone(UTC)
        next_start, _ = self._window_bounds_for_local_day(db, local_dt.date() + timedelta(days=1))
        return next_start.astimezone(UTC)

    def _min_spacing_seconds(self, db: Session) -> int:
        settings_row = self._settings_row(db)
        window = self._window_row(db)
        if window is None:
            return 1800
        start_t = parse_hhmm(window.start_time)
        end_t = parse_hhmm(window.end_time)
        start_minutes = start_t.hour * 60 + start_t.minute
        end_minutes = end_t.hour * 60 + end_t.minute
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60
        duration_seconds = max(300, (end_minutes - start_minutes) * 60)
        return max(180, int(duration_seconds / max(1, settings_row.daily_post_target)))

    def _daily_counts(self, db: Session, chat_id: str, ref_utc: datetime) -> tuple[int, int]:
        tz = self._timezone(db)
        local_day = ref_utc.astimezone(tz).date()
        day_start_local, day_end_local = self._window_bounds_for_local_day(db, local_day)
        day_start_utc = day_start_local.astimezone(UTC)
        day_end_utc = day_end_local.astimezone(UTC)
        sent_count = int(
            db.scalar(
                select(func.count(PostHistory.id)).where(
                    PostHistory.chat_id == chat_id,
                    PostHistory.status == "sent",
                    PostHistory.sent_at >= day_start_utc,
                    PostHistory.sent_at <= day_end_utc,
                )
            )
            or 0
        )
        queued_count = int(
            db.scalar(
                select(func.count(QueueItem.id)).where(
                    QueueItem.chat_id == chat_id,
                    QueueItem.status.in_(["queued", "sending"]),
                    QueueItem.scheduled_at >= day_start_utc,
                    QueueItem.scheduled_at <= day_end_utc,
                )
            )
            or 0
        )
        return sent_count, queued_count

    def _target_group(self, db: Session) -> tuple[str, str | None]:
        settings_row = self._settings_row(db)
        if not settings_row.target_group_id:
            raise ApiException(status_code=400, code="target_group_not_configured", message="Target group is not configured")
        return settings_row.target_group_id, settings_row.target_group_name

    def _ensure_short_link(self, suggestion: Suggestion) -> str:
        if suggestion.short_link:
            return suggestion.short_link
        origin = suggestion.product_link or suggestion.offer_link
        if not origin:
            raise ApiException(
                status_code=400,
                code="suggestion_missing_links",
                message="Suggestion missing product/offer link to generate shortlink",
                details={"suggestionId": suggestion.id},
            )
        suggestion.short_link = self.shopee_client.generate_short_link(origin_url=origin)
        return suggestion.short_link

    def _build_message_text(self, db: Session, suggestion: Suggestion) -> str:
        settings_row = self._settings_row(db)
        short_link = self._ensure_short_link(suggestion)
        formatted_price = suggestion.formatted_price or format_brl_price(suggestion.price_min) or (suggestion.price_min or "-")
        text = settings_row.message_template
        text = text.replace("{productName}", suggestion.product_name)
        text = text.replace("{formattedPrice}", formatted_price)
        text = text.replace("{shortLink}", short_link)
        return text.strip()

    def _pending_suggestion(self, db: Session, suggestion_id: int) -> Suggestion:
        row = db.get(Suggestion, suggestion_id)
        if row is None:
            raise ApiException(status_code=404, code="suggestion_not_found", message="Suggestion not found", details={"suggestionId": suggestion_id})
        if row.status != "pending":
            raise ApiException(
                status_code=409,
                code="suggestion_not_pending",
                message="Suggestion is not pending",
                details={"suggestionId": suggestion_id, "status": row.status},
            )
        return row

    def _compute_next_schedule_at(self, db: Session, chat_id: str) -> datetime:
        now = utc_now()
        candidate = self._next_window_start(db, now)
        spacing = timedelta(seconds=self._min_spacing_seconds(db))

        latest_queue = db.scalar(
            select(QueueItem)
            .where(QueueItem.chat_id == chat_id, QueueItem.status.in_(["queued", "sending", "sent"]))
            .order_by(QueueItem.scheduled_at.desc())
        )
        latest_sent = db.scalar(select(PostHistory).where(PostHistory.chat_id == chat_id).order_by(PostHistory.sent_at.desc()))
        anchors = [candidate]
        if latest_queue and latest_queue.scheduled_at:
            anchors.append(latest_queue.scheduled_at + spacing)
        if latest_sent and latest_sent.sent_at:
            anchors.append(latest_sent.sent_at + spacing)
        candidate = max(anchors)

        if not self._is_within_window(db, candidate):
            candidate = self._next_window_start(db, candidate)

        settings_row = self._settings_row(db)
        sent_count, queued_count = self._daily_counts(db, chat_id, candidate)
        if sent_count + queued_count >= settings_row.daily_post_limit:
            candidate = self._next_window_start(db, candidate + timedelta(days=1))
        return candidate

    def _register_history(self, db: Session, suggestion: Suggestion, chat_id: str, message_text: str, wa_result: dict[str, Any]) -> None:
        db.add(
            PostHistory(
                suggestion_id=suggestion.id,
                item_id=suggestion.item_id,
                shop_id=suggestion.shop_id,
                chat_id=chat_id,
                product_name=suggestion.product_name,
                message_text=message_text,
                short_link=suggestion.short_link,
                wa_message_id=wa_result.get("messageId"),
                status="sent",
                sent_at=utc_now(),
            )
        )

    def _send_suggestion(self, db: Session, suggestion: Suggestion) -> tuple[str, dict[str, Any]]:
        chat_id, _group_name = self._target_group(db)
        message_text = self._build_message_text(db, suggestion)
        wa_result = self.wa_client.send_text_message(chat_id=chat_id, text=message_text)
        self._register_history(db, suggestion, chat_id, message_text, wa_result)
        suggestion.status = "sent"
        suggestion.sent_at = utc_now()
        suggestion.last_error = None
        return message_text, wa_result

    def approve_suggestion_schedule(self, db: Session, suggestion_id: int) -> SuggestionApproveResponse:
        self.bootstrap_defaults(db)
        suggestion = self._pending_suggestion(db, suggestion_id)
        chat_id, _ = self._target_group(db)
        message_text = self._build_message_text(db, suggestion)
        scheduled_at = self._compute_next_schedule_at(db, chat_id)

        queue_item = QueueItem(
            suggestion_id=suggestion.id,
            chat_id=chat_id,
            scheduled_at=scheduled_at,
            status="queued",
            message_text=message_text,
            attempts=0,
        )
        db.add(queue_item)
        suggestion.status = "queued"
        suggestion.approved_action = "schedule"
        suggestion.approved_at = utc_now()
        suggestion.queue_scheduled_for = scheduled_at
        suggestion.last_error = None

        db.commit()
        db.refresh(suggestion)
        db.refresh(queue_item)
        return SuggestionApproveResponse(
            suggestion=self._suggestion_data(suggestion),
            queueItemId=queue_item.id,
            queueStatus=queue_item.status,
            messagePreview=queue_item.message_text,
        )

    def approve_suggestion_send_now(self, db: Session, suggestion_id: int) -> SuggestionApproveResponse:
        self.bootstrap_defaults(db)
        suggestion = self._pending_suggestion(db, suggestion_id)
        suggestion.approved_action = "send_now"
        suggestion.approved_at = utc_now()
        message_text, wa_result = self._send_suggestion(db, suggestion)
        db.commit()
        db.refresh(suggestion)
        return SuggestionApproveResponse(
            suggestion=self._suggestion_data(suggestion),
            messagePreview=message_text,
            waResult=wa_result,
        )

    def reject_suggestion(self, db: Session, suggestion_id: int, payload: SuggestionRejectRequest) -> SuggestionData:
        suggestion = self._pending_suggestion(db, suggestion_id)
        suggestion.status = "rejected"
        suggestion.rejection_reason = payload.reason.strip() if payload.reason else None
        suggestion.last_error = None
        db.commit()
        db.refresh(suggestion)
        return self._suggestion_data(suggestion)

    def list_queue(self, db: Session, *, status: str | None, limit: int) -> QueueListData:
        self.bootstrap_defaults(db)
        query = select(QueueItem).order_by(QueueItem.scheduled_at.asc(), QueueItem.id.asc())
        if status:
            query = query.where(QueueItem.status == status)
        rows = db.scalars(query.limit(limit)).all()

        total_query = select(func.count(QueueItem.id))
        if status:
            total_query = total_query.where(QueueItem.status == status)
        total = int(db.scalar(total_query) or 0)
        return QueueListData(items=[self._queue_item_data(row) for row in rows], total=total)

    def list_history(self, db: Session, *, limit: int) -> HistoryListData:
        self.bootstrap_defaults(db)
        rows = db.scalars(select(PostHistory).order_by(PostHistory.sent_at.desc(), PostHistory.id.desc()).limit(limit)).all()
        total = int(db.scalar(select(func.count(PostHistory.id))) or 0)
        return HistoryListData(items=[self._history_item_data(row) for row in rows], total=total)

    def get_status(self, db: Session) -> AutomationStatusData:
        self.bootstrap_defaults(db)
        settings_row = self._settings_row(db)
        window = self._window_row(db)

        suggestion_counts = {
            "pending": int(db.scalar(select(func.count(Suggestion.id)).where(Suggestion.status == "pending")) or 0),
            "queued": int(db.scalar(select(func.count(Suggestion.id)).where(Suggestion.status == "queued")) or 0),
            "sent": int(db.scalar(select(func.count(Suggestion.id)).where(Suggestion.status == "sent")) or 0),
            "rejected": int(db.scalar(select(func.count(Suggestion.id)).where(Suggestion.status == "rejected")) or 0),
            "failed": int(db.scalar(select(func.count(Suggestion.id)).where(Suggestion.status == "failed")) or 0),
        }
        queue_counts = {
            "queued": int(db.scalar(select(func.count(QueueItem.id)).where(QueueItem.status == "queued")) or 0),
            "sending": int(db.scalar(select(func.count(QueueItem.id)).where(QueueItem.status == "sending")) or 0),
            "failed": int(db.scalar(select(func.count(QueueItem.id)).where(QueueItem.status == "failed")) or 0),
            "sent": int(db.scalar(select(func.count(QueueItem.id)).where(QueueItem.status == "sent")) or 0),
        }

        next_gen = None
        if settings_row.last_suggestion_generation_at:
            next_gen = settings_row.last_suggestion_generation_at + timedelta(
                minutes=self.settings.automation_suggestion_interval_minutes
            )

        wa_status = None
        try:
            wa_status = self.wa_client.get_session_status()
        except ApiException as exc:
            wa_status = {"status": "unavailable", "code": exc.code, "message": exc.message}

        return AutomationStatusData(
            settings=AutomationSettingsData(
                automationEnabled=settings_row.automation_enabled,
                timezone=settings_row.timezone,
                targetGroupId=settings_row.target_group_id,
                targetGroupName=settings_row.target_group_name,
                dailyPostTarget=settings_row.daily_post_target,
                dailyPostLimit=settings_row.daily_post_limit,
                pricePrefix=settings_row.price_prefix,
                messageTemplate=settings_row.message_template,
                nextSuggestedGenerationAt=next_gen,
            ),
            postingWindow=self._window_data(window),
            queue=queue_counts,
            suggestions=suggestion_counts,
            whatsapp=wa_status,
            scheduler={
                "tickSeconds": self.settings.automation_tick_seconds,
                "lastSchedulerRunAt": settings_row.last_scheduler_run_at,
                "lastSuggestionGenerationAt": settings_row.last_suggestion_generation_at,
            },
        )

    def _should_auto_generate(self, settings_row: AutomationSettings) -> bool:
        if settings_row.last_suggestion_generation_at is None:
            return True
        return utc_now() >= settings_row.last_suggestion_generation_at + timedelta(
            minutes=self.settings.automation_suggestion_interval_minutes
        )

    def _process_due_queue(self, db: Session, tick: TickResult) -> None:
        now = utc_now()
        due_rows = db.scalars(
            select(QueueItem)
            .where(QueueItem.status == "queued", QueueItem.scheduled_at <= now)
            .order_by(QueueItem.scheduled_at.asc(), QueueItem.id.asc())
            .limit(10)
        ).all()
        if not due_rows:
            return

        try:
            wa_status = self.wa_client.get_session_status()
        except ApiException as exc:
            logger.warning("Skipping queue processing: WA API status failed: %s", exc.message)
            tick.skipped_not_ready = True
            return

        if not wa_status.get("isReady"):
            tick.skipped_not_ready = True
            return

        settings_row = self._settings_row(db)

        for row in due_rows:
            tick.queued_processed += 1
            suggestion = row.suggestion
            if suggestion is None:
                row.status = "failed"
                row.last_error = "Suggestion not found"
                tick.queued_failed += 1
                continue

            now = utc_now()
            if not self._is_within_window(db, now):
                row.scheduled_at = self._next_window_start(db, now)
                continue

            sent_count, _queued_count = self._daily_counts(db, row.chat_id, now)
            if sent_count >= settings_row.daily_post_limit:
                row.scheduled_at = self._next_window_start(db, now + timedelta(days=1))
                continue

            try:
                row.status = "sending"
                row.attempts += 1
                db.flush()

                _message_text, wa_result = self._send_suggestion(db, suggestion)
                row.status = "sent"
                row.sent_at = utc_now()
                row.wa_message_id = wa_result.get("messageId")
                row.last_error = None
                tick.queued_sent += 1
            except ApiException as exc:
                row.status = "failed"
                row.last_error = exc.message
                suggestion.status = "failed"
                suggestion.last_error = exc.message
                tick.queued_failed += 1
            except Exception as exc:  # pragma: no cover
                row.status = "failed"
                row.last_error = str(exc)
                suggestion.status = "failed"
                suggestion.last_error = str(exc)
                tick.queued_failed += 1

    def run_scheduler_tick(self, db: Session) -> TickResult:
        self.bootstrap_defaults(db)
        tick = TickResult()
        settings_row = self._settings_row(db)

        if settings_row.automation_enabled and self._should_auto_generate(settings_row):
            try:
                generated = self.generate_suggestions(db, SuggestionGenerateRequest())
                tick.generated = generated.inserted
            except ApiException as exc:
                logger.warning("Auto suggestion generation failed: %s", exc.message)

        if settings_row.automation_enabled:
            self._process_due_queue(db, tick)

        settings_row.last_scheduler_run_at = utc_now()
        db.commit()
        return tick
