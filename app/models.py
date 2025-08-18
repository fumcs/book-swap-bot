from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, DateTime, func

class User(SQLModel, table=True):
    """User model for storing Telegram user data"""
    __tablename__: str = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True, index=True)
    display_name: str = Field(max_length=255)
    username: Optional[str] = Field(default=None, max_length=255)
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
    
    # Relationship to books
    books: list["Book"] = Relationship(back_populates="owner")

class Book(SQLModel, table=True):
    """Book model for storing book listings"""
    __tablename__: str = "books"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=500)
    author: str = Field(max_length=255)
    condition: str = Field(max_length=100)  # e.g., "like new", "good", "fair", "poor"
    description: Optional[str] = Field(default=None, max_length=1000)
    is_available: bool = Field(default=True)
    
    # Foreign key to user
    owner_id: int = Field(foreign_key="users.id")
    owner: User = Relationship(back_populates="books")
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )

class BookRequest(SQLModel, table=True):
    """Model for tracking book requests/interest"""
    __tablename__: str = "book_requests"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    book_id: int = Field(foreign_key="books.id")
    requester_id: int = Field(foreign_key="users.id")
    message: Optional[str] = Field(default=None, max_length=500)
    status: str = Field(default="pending", max_length=50)  # pending, accepted, declined
    
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
