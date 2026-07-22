from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from .config import settings
from .db import get_db
from .models import SessionToken, User, RoleCode, UserRole, Role
from .security import new_token

def _utcnow() -> datetime:
    return datetime.now(timezone.utc)

def create_session(db: Session, user: User) -> SessionToken:
    now = _utcnow()
    token = new_token(32)
    expires_at = now + timedelta(minutes=settings.session_absolute_minutes)
    st = SessionToken(
        token=token,
        user_id=user.id,
        created_at=now,
        last_seen_at=now,
        expires_at=expires_at,
        revoked=False,
    )
    db.add(st)
    db.commit()
    db.refresh(st)
    return st

def revoke_session(db: Session, token: str) -> None:
    st = db.execute(select(SessionToken).where(SessionToken.token == token)).scalar_one_or_none()
    if not st:
        return
    st.revoked = True
    db.commit()

def set_session_cookie(resp: Response, token: str) -> None:
    resp.set_cookie(
        key=settings.session_cookie,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,
        max_age=settings.session_absolute_minutes * 60,
        path="/",
    )

def clear_session_cookie(resp: Response) -> None:
    resp.delete_cookie(key=settings.session_cookie, path="/")

def _idle_expired(st: SessionToken) -> bool:
    now = _utcnow()
    idle = timedelta(minutes=settings.session_idle_minutes)
    return (now - st.last_seen_at.replace(tzinfo=timezone.utc)) > idle

def _absolute_expired(st: SessionToken) -> bool:
    now = _utcnow()
    return now > st.expires_at.replace(tzinfo=timezone.utc)

def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    st = db.execute(
        select(SessionToken).where(SessionToken.token == token)
    ).scalar_one_or_none()

    if not st or st.revoked:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    if _absolute_expired(st) or _idle_expired(st):
        st.revoked = True
        db.commit()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    user = db.execute(select(User).where(User.id == st.user_id)).scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)

    st.last_seen_at = _utcnow()
    db.commit()
    return user

def get_user_role_codes(db: Session, user_id: int) -> set[RoleCode]:
    rows = db.execute(
        select(Role.code).join(UserRole, Role.id == UserRole.role_id).where(UserRole.user_id == user_id)
    ).scalars().all()
    return set(rows)

def require_roles(*allowed: RoleCode):
    def _dep(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> User:
        codes = get_user_role_codes(db, user.id)
        if not codes.intersection(set(allowed)):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
        return user
    return _dep
