from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_api_key
from app.schemas.automation import (
    AutomationStatusData,
    GenerateSuggestionsResult,
    HistoryListData,
    PostingWindowData,
    PostingWindowUpdateRequest,
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
from app.schemas.common import SuccessEnvelope, success_response
from app.services.automation_service import AutomationService


def create_automation_router(service: AutomationService) -> APIRouter:
    router = APIRouter(prefix="/automation", tags=["automation"], dependencies=[Depends(require_api_key)])

    @router.get("/status", response_model=SuccessEnvelope[AutomationStatusData])
    def status(db: Session = Depends(get_db)) -> dict:
        return success_response(service.get_status(db))

    @router.get("/themes", response_model=SuccessEnvelope[ThemeListData])
    def list_themes(db: Session = Depends(get_db)) -> dict:
        return success_response(service.list_themes(db))

    @router.post("/themes", response_model=SuccessEnvelope[ThemeData])
    def create_theme(payload: ThemeCreateRequest, db: Session = Depends(get_db)) -> dict:
        return success_response(service.create_theme(db, payload))

    @router.put("/themes/{theme_id}", response_model=SuccessEnvelope[ThemeData])
    def update_theme(theme_id: int, payload: ThemeUpdateRequest, db: Session = Depends(get_db)) -> dict:
        return success_response(service.update_theme(db, theme_id, payload))

    @router.get("/posting-windows", response_model=SuccessEnvelope[PostingWindowData | None])
    def get_posting_window(db: Session = Depends(get_db)) -> dict:
        return success_response(service.get_posting_window(db))

    @router.put("/posting-windows", response_model=SuccessEnvelope[PostingWindowData])
    def put_posting_window(payload: PostingWindowUpdateRequest, db: Session = Depends(get_db)) -> dict:
        return success_response(service.update_posting_window(db, payload))

    @router.post("/suggestions/generate", response_model=SuccessEnvelope[GenerateSuggestionsResult])
    def generate_suggestions(payload: SuggestionGenerateRequest, db: Session = Depends(get_db)) -> dict:
        return success_response(service.generate_suggestions(db, payload))

    @router.get("/suggestions", response_model=SuccessEnvelope[SuggestionListData])
    def list_suggestions(
        status: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        db: Session = Depends(get_db),
    ) -> dict:
        return success_response(service.list_suggestions(db, status=status, limit=limit))

    @router.post("/suggestions/{suggestion_id}/approve-schedule", response_model=SuccessEnvelope[SuggestionApproveResponse])
    def approve_schedule(suggestion_id: int, db: Session = Depends(get_db)) -> dict:
        return success_response(service.approve_suggestion_schedule(db, suggestion_id))

    @router.post("/suggestions/{suggestion_id}/approve-send-now", response_model=SuccessEnvelope[SuggestionApproveResponse])
    def approve_send_now(suggestion_id: int, db: Session = Depends(get_db)) -> dict:
        return success_response(service.approve_suggestion_send_now(db, suggestion_id))

    @router.post("/suggestions/{suggestion_id}/reject", response_model=SuccessEnvelope[SuggestionData])
    def reject_suggestion(suggestion_id: int, payload: SuggestionRejectRequest, db: Session = Depends(get_db)) -> dict:
        return success_response(service.reject_suggestion(db, suggestion_id, payload))

    @router.get("/queue", response_model=SuccessEnvelope[QueueListData])
    def list_queue(
        status: str | None = Query(default=None),
        limit: int = Query(default=50, ge=1, le=200),
        db: Session = Depends(get_db),
    ) -> dict:
        return success_response(service.list_queue(db, status=status, limit=limit))

    @router.get("/history", response_model=SuccessEnvelope[HistoryListData])
    def list_history(limit: int = Query(default=50, ge=1, le=200), db: Session = Depends(get_db)) -> dict:
        return success_response(service.list_history(db, limit=limit))

    return router

