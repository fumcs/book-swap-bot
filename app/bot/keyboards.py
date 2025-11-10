"""Reusable keyboard factories for the bot."""
from __future__ import annotations

import gettext
from typing import Iterable, List, Tuple

T = gettext.gettext

from aiogram.filters.callback_data import CallbackData
from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.db.models import BookCondition
from .utils import condition_label


class ConfirmCallback(CallbackData, prefix="confirm"):
    action: str


class BrowseCallback(CallbackData, prefix="browse"):
    action: str
    page: int = 1
    book_id: int | None = None


class ManageBookCallback(CallbackData, prefix="manage"):
    action: str
    book_id: int


class MainMenuCallback(CallbackData, prefix="menu"):
    action: str


class SearchCallback(CallbackData, prefix="search"):
    action: str
    page: int = 1
    book_id: int | None = None


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    buttons = [
        [KeyboardButton(text=T("Post a book")), KeyboardButton(text=T("Browse books"))],
        [KeyboardButton(text=T("My listings"))],
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)


def inline_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Create an inline keyboard for the main menu."""
    builder = InlineKeyboardBuilder()
    builder.button(text=T("📚 Post a book"), callback_data=MainMenuCallback(action="post"))
    builder.button(text=T("🔍 Browse books"), callback_data=MainMenuCallback(action="browse"))
    builder.button(text=T("🔎 Search books"), callback_data=MainMenuCallback(action="search"))
    builder.button(text=T("📋 My listings"), callback_data=MainMenuCallback(action="mybooks"))
    builder.adjust(2, 2)  # 2 buttons in first row, 2 in second
    return builder.as_markup()


def condition_keyboard() -> ReplyKeyboardMarkup:
    rows = []
    current_row: list[KeyboardButton] = []
    for index, condition in enumerate(BookCondition):
        current_row.append(KeyboardButton(text=condition_label(condition)))
        if (index + 1) % 2 == 0:
            rows.append(current_row)
            current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([KeyboardButton(text=T("Cancel"))])
    return ReplyKeyboardMarkup(keyboard=rows, resize_keyboard=True, one_time_keyboard=True)


def confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text=T("✅ Confirm"), callback_data=ConfirmCallback(action="confirm"))
    builder.button(text=T("✖️ Cancel"), callback_data=ConfirmCallback(action="cancel"))
    builder.adjust(2)
    return builder.as_markup()


def browse_keyboard(
    *,
    books: Iterable[tuple[int, str]],
    page: int,
    total_pages: int,
) -> InlineKeyboardMarkup:
    items: List[Tuple[int, str]] = list(books)
    builder = InlineKeyboardBuilder()
    for book_id, title in items:
        builder.button(
            text=T("Contact: {title}").format(title=title[:32]),
            callback_data=BrowseCallback(action="contact", book_id=book_id, page=page),
        )
    if total_pages > 1:
        if page > 1:
            builder.button(
                text=T("⬅️ Prev"),
                callback_data=BrowseCallback(action="page", page=page - 1),
            )
        if page < total_pages:
            builder.button(
                text=T("Next ➡️"),
                callback_data=BrowseCallback(action="page", page=page + 1),
            )
    builder.adjust(*(1 for _ in range(len(items) or 1)))
    return builder.as_markup()


def manage_books_keyboard(book_ids: Iterable[int]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for book_id in book_ids:
        builder.button(
            text=T("Mark #{book_id} sold").format(book_id=book_id),
            callback_data=ManageBookCallback(action="mark_sold", book_id=book_id),
        )
    builder.adjust(1)
    return builder.as_markup()


def search_results_keyboard(
    *,
    books: Iterable[tuple[int, str]],
    page: int,
    total_pages: int,
    query: str = "",
) -> InlineKeyboardMarkup:
    """Create keyboard for search results with pagination."""
    items: List[Tuple[int, str]] = list(books)
    builder = InlineKeyboardBuilder()
    
    # Contact buttons for each book
    for book_id, title in items:
        builder.button(
            text=T("Contact: {title}").format(title=title[:32]),
            callback_data=SearchCallback(action="contact", book_id=book_id, page=page),
        )
    
    # Pagination buttons
    if total_pages > 1:
        if page > 1:
            builder.button(
                text=T("⬅️ Prev"),
                callback_data=SearchCallback(action="page", page=page - 1),
            )
        if page < total_pages:
            builder.button(
                text=T("Next ➡️"),
                callback_data=SearchCallback(action="page", page=page + 1),
            )
    
    # New search button
    builder.button(
        text=T("🔎 New Search"),
        callback_data=MainMenuCallback(action="search"),
    )
    
    builder.adjust(*(1 for _ in range(len(items) or 1)))
    return builder.as_markup()
