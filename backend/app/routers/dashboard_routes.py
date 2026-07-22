from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..auth import get_current_user, get_user_role_codes
from ..db import get_db
from ..config import settings
from ..templating import templates

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db), user=Depends(get_current_user)):
    roles = sorted([r.value for r in get_user_role_codes(db, user.id)])
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "user": user,
            "roles": roles,
        },
    )
