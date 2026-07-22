from __future__ import annotations

from fastapi import APIRouter, Depends, Form, Request, Response, status
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from sqlalchemy import select

from ..db import get_db
from ..models import User
from ..security import verify_password
from ..auth import create_session, set_session_cookie, clear_session_cookie, revoke_session
from ..config import settings
from ..templating import templates

router = APIRouter(tags=["auth"])

@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "app_name": settings.app_name, "error": None})

@router.post("/login")
def login_action(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.execute(select(User).where(User.username == username)).scalar_one_or_none()
    if not user or not user.is_active or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "app_name": settings.app_name, "error": "Credenciales inválidas."},
            status_code=400,
        )

    st = create_session(db, user)
    resp = RedirectResponse(url="/dashboard", status_code=status.HTTP_303_SEE_OTHER)
    set_session_cookie(resp, st.token)
    return resp

@router.post("/logout")
def logout_action(request: Request, response: Response, db: Session = Depends(get_db)):
    token = request.cookies.get(settings.session_cookie)
    if token:
        revoke_session(db, token)
    resp = RedirectResponse(url="/login", status_code=status.HTTP_303_SEE_OTHER)
    clear_session_cookie(resp)
    return resp
