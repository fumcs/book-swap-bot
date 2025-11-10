"""Utility helpers for Telegram bot interactions."""
from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal
from typing import Optional


from aiogram import Bot, types
from aiogram.exceptions import TelegramForbiddenError, TelegramNotFound
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import Book, BookCondition, User
from app.i18n import T

settings = get_settings()


def condition_label(condition: BookCondition | str) -> str:
    """Return a human-friendly label for a book condition."""

    value = condition.value if isinstance(condition, BookCondition) else str(condition)
    mapping = {
        BookCondition.NEW.value: T("New"),
        BookCondition.LIKE_NEW.value: T("Like new"),
        BookCondition.GOOD.value: T("Good"),
        BookCondition.ACCEPTABLE.value: T("Acceptable"),
        BookCondition.POOR.value: T("Poor"),
    }
    return mapping.get(value, value.title())


def format_price(price: Decimal | str | None) -> str:
    if price is None:
        return "—"
    return f"{Decimal(price):.2f}"


def format_book_summary(book: Book) -> str:
    """Generate a concise multi-line summary of a book."""
    template = T("<b>{title}</b>\nAuthor: {author}\nCondition: {condition}\nPrice: {price}\nListed: {listed}\nSeller: {seller}\nBook ID: {book_id}")
    
    return template.format(
        title=book.title,
        author=book.author or T('Unknown'),
        condition=condition_label(book.condition),
        price=format_price(book.price),
        listed=book.created_at.strftime('%Y-%m-%d %H:%M UTC') if book.created_at else '—',
        seller=book.seller.public_display() if book.seller else T('Unknown'),
        book_id=book.id
    )


async def ensure_user(session: AsyncSession, tg_user: types.User) -> User:
    """Ensure a User row exists and is up-to-date."""

    result = await session.execute(select(User).where(User.telegram_id == tg_user.id))
    user = result.scalar_one_or_none()

    display_name = tg_user.full_name or tg_user.first_name or tg_user.username or str(tg_user.id)
    username = tg_user.username

    if user is None:
        user = User(
            telegram_id=tg_user.id,
            username=username,
            display_name=display_name,
        )
        session.add(user)
        await session.flush()
        return user

    updated = False
    if username != user.username:
        user.username = username
        updated = True
    if display_name != user.display_name:
        user.display_name = display_name
        updated = True
    if updated:
        await session.flush()
    return user


async def paginate_books(
    session: AsyncSession,
    *,
    page: int,
    per_page: int,
    include_sold: bool = False,
) -> tuple[list[Book], int, int]:
    """Return books for the given page.

    Returns a tuple of (books, total_count, total_pages).
    """

    filters = []
    if not include_sold:
        filters.append(Book.is_sold.is_(False))

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

    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1
    return books, total, total_pages


async def notify_seller_of_interest(
    bot: Bot,
    *,
    book: Book,
    buyer: User,
    buyer_contact: str,
) -> None:
    """Send a notification to the seller about buyer interest."""

    template = T("📚 Someone is interested in your book!\n\nBook: {book_title}\nBuyer: {buyer_contact}\nReply directly in Telegram to arrange the exchange.")
    message = template.format(
        book_title=book.title,
        buyer_contact=buyer_contact
    )
    try:
        await bot.send_message(chat_id=book.seller.telegram_id, text=message)
    except (TelegramForbiddenError, TelegramNotFound):
        # The seller cannot be contacted directly by the bot.
        pass


async def get_user_books(
    session: AsyncSession,
    *,
    seller_id: int,
    include_sold: bool = False,
) -> list[Book]:
    stmt = (
        select(Book)
        .options(selectinload(Book.seller))
        .where(Book.seller_id == seller_id)
        .order_by(Book.created_at.desc())
    )
    if not include_sold:
        stmt = stmt.where(Book.is_sold.is_(False))
    result = await session.execute(stmt)
    return list(result.scalars())


async def get_book_by_id(session: AsyncSession, book_id: int) -> Optional[Book]:
    result = await session.execute(
        select(Book).options(selectinload(Book.seller)).where(Book.id == book_id)
    )
    return result.scalar_one_or_none()


def buyer_contact_repr(tg_user: types.User) -> str:
    if tg_user.username:
        return f"@{tg_user.username}"
    if tg_user.full_name:
        return tg_user.full_name
    return f"tg:{tg_user.id}"


async def search_books(
    session: AsyncSession,
    *,
    query: str,
    page: int,
    per_page: int,
    include_sold: bool = False,
) -> tuple[list[Book], int, int]:
    """Search books by title, author, or description.
    
    Returns a tuple of (books, total_count, total_pages).
    """
    if not query.strip():
        return [], 0, 1
    
    search_term = f"%{query.strip().lower()}%"
    
    filters = [
        func.lower(Book.title).like(search_term) |  
        func.lower(Book.author).like(search_term) |
        func.lower(Book.description).like(search_term)
    ]
    
    if not include_sold:
        filters.append(Book.is_sold.is_(False))

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

    total_pages = max(1, (total + per_page - 1) // per_page) if total else 1
    return books, total, total_pages
