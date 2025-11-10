"""Entrypoint running both the Telegram bot and Starlette web app."""
from __future__ import annotations

import asyncio
import logging
import signal
from contextlib import suppress

import uvicorn
from aiogram import Dispatcher

from app.bot.bot import create_bot, create_dispatcher, on_shutdown, on_startup
from app.config import get_settings
from app.db.migration import run_migrations
from app.i18n import init_translations
from app.logger import logger

settings = get_settings()


async def run_bot(dispatcher: Dispatcher) -> None:
    bot = create_bot()
    await on_startup(bot)
    try:
        if settings.POLLING:
            await dispatcher.start_polling(
                bot,
                polling_timeout=settings.BOT_POLLING_INTERVAL,
            )
        else:
            config = uvicorn.Config(
                "web.app:app",
                host=settings.UVICORN_HOST,
                port=settings.UVICORN_PORT,
                log_level=settings.LOG_LEVEL.lower(),
                reload=settings.UVICORN_RELOAD,
                access_log=True,
            )
            server = uvicorn.Server(config)
            web_task = asyncio.create_task(server.serve(), name="uvicorn-server")
            await web_task
    finally:
        await on_shutdown(bot)


async def main() -> None:
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    
    # Enable aiogram logging
    logging.getLogger("aiogram").setLevel(logging.INFO)
    logging.getLogger("aiogram.dispatcher").setLevel(logging.DEBUG if settings.LOG_LEVEL == "DEBUG" else logging.INFO)

    # Initialize translations
    init_translations()

    logger.info('running migrations')
    await run_migrations()

    dispatcher = create_dispatcher()
    bot_task = asyncio.create_task(run_bot(dispatcher), name="bot-polling")


    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    def _request_shutdown() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, _request_shutdown)

    stop_future = asyncio.create_task(stop_event.wait(), name="shutdown-waiter")
    done, pending = await asyncio.wait(
        {bot_task, stop_future},
        return_when=asyncio.FIRST_COMPLETED,
    )

    if stop_future not in done:
        stop_event.set()
    else:
        logger.info("Shutdown requested via signal.")

    for task in done:
        if task is stop_future:
            continue
        if exception := task.exception():
            logger.error("Task %s exited with error: %s", task.get_name(), exception)


    wait_for = [task for task in pending if task is not stop_future]
    if wait_for:
        await asyncio.gather(*wait_for, return_exceptions=True)

    stop_future.cancel()
    with suppress(asyncio.CancelledError):
        await stop_future

    for sig in (signal.SIGINT, signal.SIGTERM):
        with suppress(NotImplementedError):
            loop.remove_signal_handler(sig)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
