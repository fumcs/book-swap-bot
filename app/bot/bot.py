"""Bot factory and dispatcher wiring."""
from __future__ import annotations

import logging
from typing import Any

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent

from app.config import get_settings
from app.db.session import dispose_engine
from app.i18n import T
from app.logger import logger

from .handlers import router

settings = get_settings()

def create_bot() -> Bot:
    return Bot(
        token=settings.TELEGRAM_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def error_handler(event: ErrorEvent) -> Any:
    """Global error handler for aiogram."""
    logger.error(
        "Critical error caused by update %s: %s",
        event.update.update_id if event.update else "unknown",
        event.exception,
        exc_info=event.exception,
    )


def create_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher(storage=MemoryStorage())
    dispatcher.include_router(router)
    
    # Register global error handler
    dispatcher.errors.register(error_handler)
    
    return dispatcher


async def setup_bot_commands(bot: Bot) -> None:
    commands = [
        BotCommand(command="start", description=T("Show welcome menu")),
        BotCommand(command="post", description=T("List a new book")),
        BotCommand(command="browse", description=T("Browse available books")),
        BotCommand(command="mybooks", description=T("Manage your listings")),
    ]
    await bot.set_my_commands(commands)


async def on_startup(bot: Bot) -> None:
    logging.getLogger(__name__).info("Bot startup complete")
    await setup_bot_commands(bot)


async def on_shutdown(bot: Bot) -> None:
    logging.getLogger(__name__).info("Shutting down bot and disposing engine")
    await bot.session.close()
    await dispose_engine()
