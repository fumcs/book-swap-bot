"""Seed the database with example data for demos."""
from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.config import get_settings
from db.models import Book, BookCondition, User
from db.session import session_scope

settings = get_settings()


async def seed() -> None:
    async with session_scope() as session:
        existing = await session.execute(select(User).where(User.telegram_id == 123456789))
        user = existing.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=123456789,
                username="demo_student",
                display_name="Demo Student",
            )
            session.add(user)
            await session.flush()

        demo_books = [
            {
                "title": "Calculus, 8th Edition",
                "author": "James Stewart",
                "price": Decimal("25.00"),
                "condition": BookCondition.GOOD,
                "description": "Light highlighting in chapters 3-5.",
            },
            {
                "title": "Introduction to Algorithms",
                "author": "Cormen, Leiserson, Rivest, Stein",
                "price": Decimal("40.00"),
                "condition": BookCondition.LIKE_NEW,
                "description": "Pristine condition, bought last semester.",
            },
            {
                "title": "Organic Chemistry",
                "author": "Paula Y. Bruice",
                "price": Decimal("30.00"),
                "condition": BookCondition.ACCEPTABLE,
                "description": "Cover wear, all pages intact.",
            },
        ]

        for payload in demo_books:
            exists = await session.execute(
                select(Book).where(Book.title == payload["title"], Book.seller_id == user.id)
            )
            if exists.scalar_one_or_none() is not None:
                continue
            book = Book(seller_id=user.id, **payload)
            session.add(book)

    print("Seeded demo user and books.")


if __name__ == "__main__":
    asyncio.run(seed())
