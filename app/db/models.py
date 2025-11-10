# db/models.py
# from __future__ import annotations
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional
from enum import Enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    Enum as SAEnum,
    Integer,
    String,
    Numeric,
    Boolean,
    func,
    Index,
    CheckConstraint,
    ForeignKey,
)
from sqlalchemy.orm import Mapped
from sqlmodel import SQLModel, Field, Column as SQLColumn, JSON, Relationship
from pydantic import field_validator


def _utc_now() -> datetime:
    """Return a timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


# --- Domain enums ---
class BookCondition(str, Enum):
    NEW = "new"
    LIKE_NEW = "like_new"
    GOOD = "good"
    ACCEPTABLE = "acceptable"
    POOR = "poor"


class User(SQLModel, table=True):
    __tablename__ = "users"

    id: Optional[int] = Field(
        default=None, sa_column=Column(Integer, primary_key=True)
    )

    telegram_id: int = Field(..., index=True, description="Telegram user id")
    username: Optional[str] = Field(
        None, max_length=64, description="Telegram username (without @)"
    )
    display_name: Optional[str] = Field(None, max_length=128)
    contact_phone: Optional[str] = Field(None, max_length=32, description="Optional phone")

    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
        description="Record creation timestamp (UTC)",
    )

    # Relationships
    books: Mapped[List["Book"]] = Relationship(
        back_populates="seller"
    )

    def public_display(self) -> str:
        """Return a human friendly contact string for showing to buyers."""
        if self.username:
            return f"@{self.username}"
        if self.display_name:
            return self.display_name
        return f"tg:{self.telegram_id}"


class Book(SQLModel, table=True):
    __tablename__ = "books"
    # table args: indexes and constraints
    __table_args__ = (
        CheckConstraint("price >= 0", name="ck_books_price_nonnegative"),
        Index("ix_books_title", "title"),
        Index("ix_books_author", "author"),
        Index("ix_books_is_sold_created_at", "is_sold", "created_at"),
    )

    id: Optional[int] = Field(sa_column=Column(Integer, primary_key=True, default=None, nullable=True))
    created_at: datetime = Field(
        default_factory=_utc_now,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), nullable=False),
    )

    title: str = Field(..., min_length=1, max_length=256, sa_column=Column(String(256), nullable=False), description="Book title")
    author: Optional[str] = Field(None, max_length=256, sa_column=Column(String(256), nullable=True), description="Book author")
    # Use Decimal for price; validation handled in field_validator below
    price: Decimal = Field(..., sa_column=Column(Numeric(10, 2), nullable=False), description="Price in your currency")
    condition: BookCondition = Field(..., sa_column=Column(SAEnum(BookCondition, name="book_condition")), description="Book physical condition")
    description: Optional[str] = Field(None, max_length=2000, sa_column=Column(String(2000), nullable=True), description="Optional book description")
    # Flags & meta
    is_sold: bool = Field(default=False, description="Whether this book is already sold")

    seller_id: int = Field(
        nullable=False, foreign_key='users.id',
        description="FK to users.id",
    )
    seller: Mapped[Optional["User"]] = Relationship(back_populates="books")

    # Example: store extra metadata if needed (e.g., tags) using JSON column (optional)
    extra_metadata: Optional[dict] = Field(default=None, sa_column=Column(JSON), description="Optional free-form metadata")

    # --- Domain / convenience methods ---
    def mark_sold(self) -> None:
        """Mark the book as sold (in-memory). Commit handled by caller via session."""
        self.is_sold = True

    def serialize(self) -> dict:
        """Return a JSON-serializable dict suitable for APIs."""
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "price": str(self.price) if self.price is not None else None,
            "condition": self.condition.value if isinstance(self.condition, BookCondition) else str(self.condition),
            "is_sold": self.is_sold,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "seller": {
                "id": self.seller.id,
                "telegram_id": self.seller.telegram_id,
                "display": self.seller.public_display(),
            } if self.seller else {"id": self.seller_id},
            "metadata": self.extra_metadata,
        }

    # Pydantic validators: ensure price uses Decimal quantization (2 decimal places)
    @field_validator("price", mode="before")
    @classmethod
    def quantize_price(cls, v):
        if v is None:
            return v
        if not isinstance(v, Decimal):
            v = Decimal(str(v))
        # quantize to 2 decimal places
        quantized = v.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if quantized < Decimal("0"):
            raise ValueError("price must be non-negative")
        return quantized

    @field_validator("title", "author", "description", mode="before")
    @classmethod
    def strip_and_validate_strings(cls, v):
        if v is None:
            return None
        if isinstance(v, str):
            s = v.strip()
            return s if s != "" else None
        return v
