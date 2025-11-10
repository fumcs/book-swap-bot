"""Starlette application exposing health and book listing endpoints."""
from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.config import get_settings
from db.models import Book, BookCondition
from db.session import session_scope

settings = get_settings()


async def healthz(_: Request) -> JSONResponse:
    """Simple health probe."""

    return JSONResponse({"status": "ok"})


async def list_books(request: Request) -> JSONResponse:
    """Return a paginated list of available books."""

    params = request.query_params
    page = max(1, int(params.get("page", 1)))
    per_page_raw = int(params.get("per_page", settings.PAGE_SIZE))
    per_page = max(1, min(per_page_raw, 100))

    filters = [Book.is_sold.is_(False)]

    if author := params.get("author"):
        filters.append(Book.author.ilike(f"%{author.strip()}%"))
    if title := params.get("title"):
        filters.append(Book.title.ilike(f"%{title.strip()}%"))
    if condition := params.get("condition"):
        try:
            condition_enum = BookCondition(condition)
            filters.append(Book.condition == condition_enum)
        except ValueError:
            return JSONResponse(
                {"detail": "Invalid condition parameter."}, status_code=400
            )

    async with session_scope() as session:
        stmt = (
            select(Book)
            .options(selectinload(Book.seller))
            .where(*filters)
            .order_by(Book.created_at.desc())
            .offset((page - 1) * per_page)
            .limit(per_page)
        )
        result = await session.execute(stmt)
        books = list(result.scalars())

        count_stmt = select(func.count()).select_from(select(Book.id).where(*filters).subquery())
        total = await session.scalar(count_stmt) or 0

    data = {
        "items": [book.serialize() for book in books],
        "page": page,
        "per_page": per_page,
        "total": total,
    }
    return JSONResponse(data)


routes = [
    Route("/healthz", healthz, methods=["GET"]),
    Route("/books", list_books, methods=["GET"]),
]

app = Starlette(debug=settings.LOG_LEVEL == "DEBUG", routes=routes)
