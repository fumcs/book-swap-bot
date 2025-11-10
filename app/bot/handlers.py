"""Aiogram router with command and callback handlers."""
from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation
from functools import wraps
from typing import Iterable, Callable, Any
from app.i18n import T

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, Message, ReplyKeyboardRemove

from app.config import get_settings
from app.db.session import session_scope
from app.db.models import Book, BookCondition
from app.logger import logger


from .keyboards import (
    BrowseCallback,
    ConfirmCallback,
    MainMenuCallback,
    ManageBookCallback,
    SearchCallback,
    browse_keyboard,
    condition_keyboard,
    confirm_keyboard,
    inline_main_menu_keyboard,
    main_menu_keyboard,
    manage_books_keyboard,
    search_results_keyboard,
)
from .utils import (
    buyer_contact_repr,
    condition_label,
    ensure_user,
    format_book_summary,
    get_book_by_id,
    get_user_books,
    notify_seller_of_interest,
    paginate_books,
    search_books,
)

router = Router()
settings = get_settings()

POST_COMMANDS = {"/post", "post a book", "list a book"}
BROWSE_COMMANDS = {"/browse", "browse", "browse books"}
SEARCH_COMMANDS = {"/search", "search", "search books"}
MY_LISTINGS_COMMANDS = {"/mybooks", "my books", "my listings"}


def log_errors(func: Callable) -> Callable:
    """Decorator to log errors in handler functions."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in handler {func.__name__}: {e}", exc_info=True)
            # Re-raise so aiogram's error handler can also process it
            raise
    return wrapper


class PostBookStates(StatesGroup):
    title = State()
    author = State()
    condition = State()
    price = State()
    description = State()
    confirm = State()


class SearchStates(StatesGroup):
    query = State()


CONDITION_MAP = {condition_label(c).casefold(): c for c in BookCondition}


@router.message(CommandStart())
async def handle_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with session_scope() as session:
        await ensure_user(session, message.from_user)
    welcome = T(
        "👋 Welcome to the Book Swap Marketplace!\n\n"
        "• Post textbooks you want to sell\n"
        "• Browse available books from other students\n"
        "• Manage your active listings\n\n"
        "Choose an option from the menu below:"
    )
    await message.answer(welcome, reply_markup=inline_main_menu_keyboard())


@router.message(Command("help"))
async def handle_help(message: Message) -> None:
    help_text = T(
        "Here are the main commands:\n"
        "/start – show welcome menu\n"
        "/post – start listing flow\n"
        "/browse – browse available books\n"
        "/search – search for specific books\n"
        "/mybooks – manage your listings"
    )
    await message.answer(help_text)


@router.message(Command("cancel"))
async def handle_cancel(message: Message, state: FSMContext) -> None:
    current_state = await state.get_state()
    if current_state is None:
        await message.answer(T("❌ You're not in any process to cancel."))
    else:
        await state.clear()
        await message.answer(T("✅ Canceled! Back to the main menu."), reply_markup=inline_main_menu_keyboard())


@router.message(Command("post"))
@router.message(F.text.casefold().in_(POST_COMMANDS))
async def start_post_flow(message: Message, state: FSMContext) -> None:
    await state.clear()
    async with session_scope() as session:
        await ensure_user(session, message.from_user)
    await state.set_state(PostBookStates.title)
    await message.answer(
        T("Let's list a book! What is the title?"),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(PostBookStates.title)
async def collect_title(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    if not text:
        await message.answer(T("Please provide a title."))
        return
    await state.update_data(title=text)
    await state.set_state(PostBookStates.author)
    await message.answer(T("Who's the author? Send 'skip' if unknown."))


@router.message(PostBookStates.author)
async def collect_author(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    author = None if text.lower() == "skip" else text
    await state.update_data(author=author)
    await state.set_state(PostBookStates.condition)
    await message.answer(T("Select the condition:"), reply_markup=condition_keyboard())


@router.message(PostBookStates.condition)
async def collect_condition(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip().casefold()
    if text not in CONDITION_MAP:
        await message.answer(T("Please choose a condition from the keyboard options."))
        return
    await state.update_data(condition=CONDITION_MAP[text].value)
    await state.set_state(PostBookStates.price)
    await message.answer(
        T("What price are you asking? Use numbers only (e.g., 12.50)."),
        reply_markup=ReplyKeyboardRemove(),
    )


@router.message(PostBookStates.price)
async def collect_price(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    try:
        price = Decimal(text)
        if price < 0:
            raise InvalidOperation
    except (InvalidOperation, ValueError):
        await message.answer(T("Please send a valid non-negative price (e.g., 15.00)."))
        return
    await state.update_data(price=str(price))
    await state.set_state(PostBookStates.description)
    await message.answer(T("Add an optional description or send 'skip'."))


@router.message(PostBookStates.description)
async def collect_description(message: Message, state: FSMContext) -> None:
    text = (message.text or "").strip()
    description = None if text.lower() == "skip" else text
    await state.update_data(description=description)
    await state.set_state(PostBookStates.confirm)
    data = await state.get_data()
    summary = build_summary_preview(data)
    await message.answer(summary, reply_markup=confirm_keyboard())


def build_summary_preview(data: dict) -> str:
    condition = condition_label(BookCondition(data["condition"]))
    template = T("Please confirm your listing:\n\nTitle: {title}\nAuthor: {author}\nCondition: {condition}\nPrice: {price}\nDescription: {description}")
    return template.format(
        title=data['title'],
        author=data.get('author') or T('Unknown'),
        condition=condition,
        price=data['price'],
        description=data.get('description') or '—'
    )


@router.callback_query(ConfirmCallback.filter())
async def finish_post_flow(query: CallbackQuery, callback_data: ConfirmCallback, state: FSMContext) -> None:
    if callback_data.action == "cancel":
        await state.clear()
        await query.message.edit_text(T("Listing cancelled."))
        await query.answer()
        return

    data = await state.get_data()
    try:
        price = Decimal(data["price"])
    except (KeyError, InvalidOperation):
        await query.answer(T("Invalid price data."), show_alert=True)
        return

    async with session_scope() as session:
        seller = await ensure_user(session, query.from_user)
        book = Book(
            title=data["title"],
            author=data.get("author"),
            price=price,
            condition=BookCondition(data["condition"]),
            description=data.get("description"),
            seller_id=seller.id,
        )
        session.add(book)
        await session.flush()
        book_id = book.id

    await state.clear()
    await query.message.edit_text(
        T("✅ Book listed! (ID #{book_id})").format(book_id=book_id), reply_markup=None
    )
    await query.answer(T("Listing published!"))
    
    # Send main menu after successful book posting
    menu_text = T(
        "🎉 Your book has been successfully listed!\n\n"
        "What would you like to do next?"
    )
    await query.message.answer(menu_text, reply_markup=inline_main_menu_keyboard())


@router.callback_query(MainMenuCallback.filter())
async def handle_main_menu(query: CallbackQuery, callback_data: MainMenuCallback, state: FSMContext) -> None:
    """Handle inline main menu button presses."""
    await query.answer()
    
    if callback_data.action == "post":
        await state.clear()
        async with session_scope() as session:
            await ensure_user(session, query.from_user)
        await state.set_state(PostBookStates.title)
        await query.message.answer(
            T("Let's list a book! What is the title?"),
            reply_markup=ReplyKeyboardRemove(),
        )
        
    elif callback_data.action == "browse":
        text, buttons, _, total_pages = await render_browse_page(page=1)
        markup = browse_keyboard(books=buttons, page=1, total_pages=total_pages) if buttons else None
        await query.message.answer(text, reply_markup=markup, disable_web_page_preview=True)
        
    elif callback_data.action == "search":
        await state.clear()
        await state.set_state(SearchStates.query)
        await query.message.answer(
            T("🔎 <b>Search Books</b>\n\n"
            "Enter keywords to search for books by:\n"
            "• Title\n"
            "• Author\n"
            "• Description\n\n"
            "Type your search term:"),
            parse_mode="HTML",
            reply_markup=ReplyKeyboardRemove(),
        )
        
    elif callback_data.action == "mybooks":
        async with session_scope() as session:
            user = await ensure_user(session, query.from_user)
            books = await get_user_books(session, seller_id=user.id, include_sold=False)

        if not books:
            await query.message.answer(
                T("You have no active listings right now.\n\n"
                "Use the menu below to post your first book!"),
                reply_markup=inline_main_menu_keyboard()
            )
            return

        text, markup = build_my_listings_view(books)
        await query.message.answer(text, reply_markup=markup, disable_web_page_preview=True)


async def render_browse_page(page: int) -> tuple[str, list[tuple[int, str]], int, int]:
    async with session_scope() as session:
        books, total, total_pages = await paginate_books(
            session, page=page, per_page=settings.PAGE_SIZE
        )
    if total == 0:
        return (T("No books are available yet. Try again soon!"), [], page, 1)

    lines = [T("📚 Page {page}/{total_pages}").format(page=page, total_pages=total_pages)]
    for idx, book in enumerate(books, start=1):
        lines.append(f"\n#{idx}\n{format_book_summary(book)}")
    text = "\n".join(lines)
    buttons = [(book.id, book.title) for book in books]
    return text, buttons, total, total_pages


@router.message(Command("browse"))
@router.message(F.text.casefold().in_(BROWSE_COMMANDS))
async def browse_books(message: Message) -> None:
    text, buttons, _, total_pages = await render_browse_page(page=1)
    markup = browse_keyboard(books=buttons, page=1, total_pages=total_pages) if buttons else None
    await message.answer(text, reply_markup=markup, disable_web_page_preview=True)


@router.message(Command("search"))
@router.message(F.text.casefold().in_(SEARCH_COMMANDS))
async def start_search(message: Message, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SearchStates.query)
    await message.answer(
        T("🔎 <b>Search Books</b>\n\n"
        "Enter keywords to search for books by:\n"
        "• Title\n"
        "• Author\n"
        "• Description\n\n"
        "Type your search term:"),
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove(),
    )


@router.callback_query(BrowseCallback.filter(F.action == "page"))
async def paginate_browse(query: CallbackQuery, callback_data: BrowseCallback) -> None:
    page = max(1, callback_data.page)
    text, buttons, _, total_pages = await render_browse_page(page=page)
    markup = browse_keyboard(books=buttons, page=page, total_pages=total_pages) if buttons else None
    try:
        await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
    except TelegramBadRequest:
        await query.message.answer(text, reply_markup=markup, disable_web_page_preview=True)
    await query.answer()


@router.callback_query(BrowseCallback.filter(F.action == "contact"))
async def contact_seller(query: CallbackQuery, callback_data: BrowseCallback) -> None:
    book_id = callback_data.book_id
    if not book_id:
        await query.answer(T("Missing book information."), show_alert=True)
        return

    async with session_scope() as session:
        book = await get_book_by_id(session, book_id)
        buyer = await ensure_user(session, query.from_user)

    if book is None or book.is_sold:
        await query.answer(T("This listing is no longer available."), show_alert=True)
        return

    seller_contact = book.seller.public_display() if book.seller else T("Unavailable")
    buyer_contact = buyer_contact_repr(query.from_user)

    message = T(
        "Seller contact for '{title}': {contact}\n"
        "Mention that you're from the Book Swap Marketplace."
    ).format(title=book.title, contact=seller_contact)
    await query.message.answer(message)

    await notify_seller_of_interest(
        query.bot,
        book=book,
        buyer=buyer,
        buyer_contact=buyer_contact,
    )
    await query.answer(T("Contact sent! 👌"))


@router.message(Command("mybooks"))
@router.message(F.text.casefold().in_(MY_LISTINGS_COMMANDS))
async def my_listings(message: Message) -> None:
    async with session_scope() as session:
        user = await ensure_user(session, message.from_user)
        books = await get_user_books(session, seller_id=user.id, include_sold=False)

    if not books:
        await message.answer(T("You have no active listings right now."))
        return

    text, markup = build_my_listings_view(books)
    await message.answer(text, reply_markup=markup, disable_web_page_preview=True)


def build_my_listings_view(books: Iterable[Book]) -> tuple[str, InlineKeyboardMarkup]:
    lines = [T("📚 Your active listings:")]
    ids = []
    for book in books:
        ids.append(book.id)
        lines.append(f"\nID #{book.id}\n{format_book_summary(book)}")
    markup = manage_books_keyboard(ids)
    return "\n".join(lines), markup


@router.message(SearchStates.query)
async def handle_search_query(message: Message, state: FSMContext) -> None:
    """Handle search query input and display results."""
    query = (message.text or "").strip()
    if not query:
        await message.answer(T("Please enter a search term."))
        return
    
    await state.clear()
    await state.update_data(search_query=query)
    
    text, buttons, _, total_pages = await render_search_page(query=query, page=1)
    markup = search_results_keyboard(books=buttons, page=1, total_pages=total_pages, query=query) if buttons else None
    
    if not buttons:
        await message.answer(
            T("🔍 No books found for '<b>{query}</b>'\n\n"
            "Try different keywords or browse all books instead.").format(query=query),
            parse_mode="HTML",
            reply_markup=inline_main_menu_keyboard()
        )
    else:
        await message.answer(text, reply_markup=markup, disable_web_page_preview=True, parse_mode="HTML")


async def render_search_page(query: str, page: int) -> tuple[str, list[tuple[int, str]], int, int]:
    """Render a page of search results."""
    async with session_scope() as session:
        books, total, total_pages = await search_books(
            session, query=query, page=page, per_page=settings.PAGE_SIZE
        )
    
    if total == 0:
        return (T("No books found for '{query}'").format(query=query), [], page, 1)

    lines = [T("🔍 Search results for '<b>{query}</b>' - Page {page}/{total_pages}").format(query=query, page=page, total_pages=total_pages)]
    for idx, book in enumerate(books, start=1):
        lines.append(f"\n#{idx}\n{format_book_summary(book)}")
    
    text = "\n".join(lines)
    buttons = [(book.id, book.title) for book in books]
    return text, buttons, total, total_pages


@router.callback_query(SearchCallback.filter(F.action == "page"))
async def paginate_search_results(query: CallbackQuery, callback_data: SearchCallback, state: FSMContext) -> None:
    """Handle search results pagination."""
    data = await state.get_data()
    search_query = data.get("search_query", "")
    
    if not search_query:
        await query.answer(T("Search query not found. Please start a new search."), show_alert=True)
        return
    
    page = max(1, callback_data.page)
    text, buttons, _, total_pages = await render_search_page(query=search_query, page=page)
    markup = search_results_keyboard(books=buttons, page=page, total_pages=total_pages, query=search_query) if buttons else None
    
    try:
        await query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True, parse_mode="HTML")
    except TelegramBadRequest:
        await query.message.answer(text, reply_markup=markup, disable_web_page_preview=True, parse_mode="HTML")
    await query.answer()


@router.callback_query(SearchCallback.filter(F.action == "contact"))
async def contact_seller_from_search(query: CallbackQuery, callback_data: SearchCallback) -> None:
    """Handle contacting seller from search results."""
    book_id = callback_data.book_id
    if not book_id:
        await query.answer(T("Missing book information."), show_alert=True)
        return

    async with session_scope() as session:
        book = await get_book_by_id(session, book_id)
        buyer = await ensure_user(session, query.from_user)

    if book is None or book.is_sold:
        await query.answer(T("This listing is no longer available."), show_alert=True)
        return

    seller_contact = book.seller.public_display() if book.seller else T("Unavailable")
    buyer_contact = buyer_contact_repr(query.from_user)

    message = T(
        "Seller contact for '<b>{title}</b>': {contact}\n"
        "Mention that you're from the Book Swap Marketplace."
    ).format(title=book.title, contact=seller_contact)
    await query.message.answer(message, parse_mode="HTML")

    await notify_seller_of_interest(
        query.bot,
        book=book,
        buyer=buyer,
        buyer_contact=buyer_contact,
    )
    await query.answer(T("Contact sent! 👌"))


@router.callback_query(ManageBookCallback.filter(F.action == "mark_sold"))
async def mark_book_sold(query: CallbackQuery, callback_data: ManageBookCallback) -> None:
    async with session_scope() as session:
        seller = await ensure_user(session, query.from_user)
        book = await get_book_by_id(session, callback_data.book_id)
        if book is None or book.seller_id != seller.id:
            await query.answer(T("You cannot modify this listing."), show_alert=True)
            return
        if book.is_sold:
            await query.answer(T("Already marked as sold."))
            return
        book.mark_sold()
        await session.flush()

    await query.answer(T("Marked as sold."))
    await query.message.edit_text(
        T("Listing marked as sold. Refresh /mybooks to see remaining items.")
    )