import logging
from typing import Optional
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlmodel import select
from sqlalchemy.orm import selectinload

from database import get_session_context
from models import User, Book

logger = logging.getLogger(__name__)

# FSM States for multi-step flows
class AddBookStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_author = State()
    waiting_for_condition = State()
    waiting_for_description = State()

# Create router
router = Router()

async def get_or_create_user(telegram_id: int, display_name: str, username: Optional[str] = None) -> User:
    """Get existing user or create new one"""
    async with get_session_context() as session:
        # Try to find existing user
        stmt = select(User).where(User.telegram_id == telegram_id)
        result = await session.exec(stmt)
        user = result.first()
        
        if user:
            # Update user info if changed
            if user.display_name != display_name or user.username != username:
                user.display_name = display_name
                user.username = username
                user.updated_at = datetime.utcnow()
                session.add(user)
                await session.commit()
                await session.refresh(user)
        else:
            # Create new user
            user = User(
                telegram_id=telegram_id,
                display_name=display_name,
                username=username
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
        
        return user

@router.message(CommandStart())
async def start_handler(message: Message):
    """Handle /start command"""
    try:
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            display_name=message.from_user.full_name,
            username=message.from_user.username
        )
        
        welcome_text = f"""
👋 <b>Welcome to BookSwap Bot, {user.display_name}!</b>

📚 This bot helps you exchange books with other users locally.

<b>Available Commands:</b>
/start - Show this welcome message
/addbook - Add a book to your collection
/browse - Browse available books
/mybooks - View your book listings

<b>Quick Start:</b>
Try adding a book: <code>/addbook The Hobbit|J.R.R. Tolkien|like new</code>

Happy book swapping! 📖✨
        """
        
        await message.reply(welcome_text)
        logger.info(f"User {user.telegram_id} started the bot")
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await message.reply("❌ Sorry, something went wrong. Please try again later.")

@router.message(Command("addbook"))
async def addbook_handler(message: Message, state: FSMContext):
    """Handle /addbook command - supports both quick format and step-by-step"""
    try:
        # Get or create user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            display_name=message.from_user.full_name,
            username=message.from_user.username
        )
        
        # Check if quick format is used: /addbook Title|Author|Condition
        command_text = message.text.replace("/addbook", "", 1).strip()
        
        if command_text and "|" in command_text:
            # Quick format
            parts = [part.strip() for part in command_text.split("|")]
            if len(parts) >= 3:
                title, author, condition = parts[0], parts[1], parts[2]
                description = parts[3] if len(parts) > 3 else None
                
                # Create book
                async with get_session_context() as session:
                    book = Book(
                        title=title,
                        author=author,
                        condition=condition,
                        description=description,
                        owner_id=user.id
                    )
                    session.add(book)
                    await session.commit()
                    await session.refresh(book)
                
                await message.reply(
                    f"✅ <b>Book added successfully!</b>\n\n"
                    f"📖 <b>Title:</b> {book.title}\n"
                    f"✍️ <b>Author:</b> {book.author}\n"
                    f"🏷️ <b>Condition:</b> {book.condition}\n"
                    f"{f'📝 <b>Description:</b> {book.description}' if book.description else ''}"
                )
                logger.info(f"User {user.telegram_id} added book: {book.title}")
                return
            else:
                await message.reply("❌ Invalid format. Use: <code>/addbook Title|Author|Condition</code>")
                return
        
        # Step-by-step flow
        await state.set_state(AddBookStates.waiting_for_title)
        await message.reply(
            "📚 <b>Let's add a new book!</b>\n\n"
            "📖 Please enter the book title:"
        )
        
    except Exception as e:
        logger.error(f"Error in addbook handler: {e}")
        await message.reply("❌ Sorry, something went wrong. Please try again later.")

@router.message(AddBookStates.waiting_for_title)
async def process_title(message: Message, state: FSMContext):
    """Process book title input"""
    await state.update_data(title=message.text.strip())
    await state.set_state(AddBookStates.waiting_for_author)
    await message.reply("✍️ Please enter the author's name:")

@router.message(AddBookStates.waiting_for_author)
async def process_author(message: Message, state: FSMContext):
    """Process book author input"""
    await state.update_data(author=message.text.strip())
    await state.set_state(AddBookStates.waiting_for_condition)
    await message.reply(
        "🏷️ Please enter the book condition:\n\n"
        "Examples: <i>like new</i>, <i>good</i>, <i>fair</i>, <i>poor</i>"
    )

@router.message(AddBookStates.waiting_for_condition)
async def process_condition(message: Message, state: FSMContext):
    """Process book condition input"""
    await state.update_data(condition=message.text.strip())
    await state.set_state(AddBookStates.waiting_for_description)
    await message.reply(
        "📝 (Optional) Please enter a description or additional notes:\n\n"
        "Send /skip to skip this step."
    )

@router.message(AddBookStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Process book description and save the book"""
    try:
        # Get user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            display_name=message.from_user.full_name,
            username=message.from_user.username
        )
        
        # Get data from state
        data = await state.get_data()
        description = None if message.text.strip() == "/skip" else message.text.strip()
        
        # Create book
        async with get_session_context() as session:
            book = Book(
                title=data["title"],
                author=data["author"],
                condition=data["condition"],
                description=description,
                owner_id=user.id
            )
            session.add(book)
            await session.commit()
            await session.refresh(book)
        
        await message.reply(
            f"✅ <b>Book added successfully!</b>\n\n"
            f"📖 <b>Title:</b> {book.title}\n"
            f"✍️ <b>Author:</b> {book.author}\n"
            f"🏷️ <b>Condition:</b> {book.condition}\n"
            f"{f'📝 <b>Description:</b> {book.description}' if book.description else ''}"
        )
        
        await state.clear()
        logger.info(f"User {user.telegram_id} added book via stepper: {book.title}")
        
    except Exception as e:
        logger.error(f"Error saving book: {e}")
        await message.reply("❌ Sorry, something went wrong. Please try again later.")
        await state.clear()

@router.message(Command("browse"))
async def browse_handler(message: Message):
    """Handle /browse command - show recent books"""
    try:
        async with get_session_context() as session:
            # Get recent available books
            stmt = (
                select(Book)
                .options(selectinload(Book.owner))
                .where(Book.is_available == True)
                .order_by(Book.created_at.desc())
                .limit(10)
            )
            result = await session.exec(stmt)
            books = result.all()
        
        if not books:
            await message.reply(
                "📚 <b>No books available yet!</b>\n\n"
                "Be the first to add a book with /addbook"
            )
            return
        
        response = "📚 <b>Available Books:</b>\n\n"
        
        for i, book in enumerate(books, 1):
            # Don't show user's own books
            if book.owner.telegram_id == message.from_user.id:
                continue
                
            response += f"<b>{i}.</b> 📖 <b>{book.title}</b>\n"
            response += f"   ✍️ by {book.author}\n"
            response += f"   🏷️ Condition: {book.condition}\n"
            response += f"   👤 Owner: {book.owner.display_name}\n"
            if book.description:
                response += f"   📝 {book.description[:100]}{'...' if len(book.description) > 100 else ''}\n"
            response += f"   📅 Added: {book.created_at.strftime('%Y-%m-%d')}\n\n"
        
        if len(response.split('\n\n')) <= 2:  # Only header
            await message.reply("📚 <b>No books from other users available yet!</b>")
        else:
            await message.reply(response)
        
        logger.info(f"User {message.from_user.id} browsed books")
        
    except Exception as e:
        logger.error(f"Error in browse handler: {e}")
        await message.reply("❌ Sorry, something went wrong. Please try again later.")

@router.message(Command("mybooks"))
async def mybooks_handler(message: Message):
    """Handle /mybooks command - show user's books"""
    try:
        # Get user
        user = await get_or_create_user(
            telegram_id=message.from_user.id,
            display_name=message.from_user.full_name,
            username=message.from_user.username
        )
        
        async with get_session_context() as session:
            # Get user's books
            stmt = (
                select(Book)
                .where(Book.owner_id == user.id)
                .order_by(Book.created_at.desc())
            )
            result = await session.exec(stmt)
            books = result.all()
        
        if not books:
            await message.reply(
                "📚 <b>You haven't added any books yet!</b>\n\n"
                "Add your first book with /addbook"
            )
            return
        
        response = f"📚 <b>Your Books ({len(books)}):</b>\n\n"
        
        for i, book in enumerate(books, 1):
            status_emoji = "✅" if book.is_available else "❌"
            response += f"<b>{i}.</b> {status_emoji} 📖 <b>{book.title}</b>\n"
            response += f"   ✍️ by {book.author}\n"
            response += f"   🏷️ Condition: {book.condition}\n"
            if book.description:
                response += f"   📝 {book.description[:100]}{'...' if len(book.description) > 100 else ''}\n"
            response += f"   📅 Added: {book.created_at.strftime('%Y-%m-%d')}\n\n"
        
        await message.reply(response)
        logger.info(f"User {user.telegram_id} viewed their books")
        
    except Exception as e:
        logger.error(f"Error in mybooks handler: {e}")
        await message.reply("❌ Sorry, something went wrong. Please try again later.")

def setup_handlers(dp):
    """Setup all handlers"""
    dp.include_router(router)
    logger.info("Handlers setup completed")
