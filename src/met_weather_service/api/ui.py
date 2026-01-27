from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["ui"])

_BASE_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=str(_BASE_DIR / "templates"))


@router.get("/", response_class=HTMLResponse, include_in_schema=False)
def ui_index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "title": "MET Weather Service",
        },
    )


@router.get("/ui", response_class=HTMLResponse, include_in_schema=False)
def ui_alias(request: Request) -> HTMLResponse:
    return ui_index(request)
