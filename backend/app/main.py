from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import select
from apscheduler.schedulers.background import BackgroundScheduler

from .config import settings
from .db import engine, SessionLocal
from .models import Base
from .routers import auth_routes, dashboard_routes, tables_routes, orders_routes, kitchen_routes, cash_routes, products_routes, delivery_routes, public_routes
from .scripts_internal import ensure_data_dirs, backup_sqlite

def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)

    app.mount("/static", StaticFiles(directory=str(Path(__file__).parent / "static")), name="static")

    app.include_router(public_routes.router)
    app.include_router(auth_routes.router)
    app.include_router(dashboard_routes.router)
    app.include_router(tables_routes.router)
    app.include_router(orders_routes.router)
    app.include_router(kitchen_routes.router)
    app.include_router(cash_routes.router)
    app.include_router(products_routes.router)
    app.include_router(delivery_routes.router)

    @app.on_event("startup")
    def _startup():
        ensure_data_dirs()
        Base.metadata.create_all(bind=engine)

        scheduler = BackgroundScheduler()
        # Daily backup at 02:00 local server time
        scheduler.add_job(backup_sqlite, "cron", hour=2, minute=0)
        scheduler.start()
        app.state.scheduler = scheduler

    @app.on_event("shutdown")
    def _shutdown():
        sch = getattr(app.state, "scheduler", None)
        if sch:
            sch.shutdown(wait=False)

    @app.exception_handler(401)
    async def _unauth(request: Request, exc):
        return RedirectResponse(url="/login", status_code=303)

    return app

app = create_app()
