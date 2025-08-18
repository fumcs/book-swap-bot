import asyncio
import logging
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from database import init_db
from handlers import setup_handlers

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Main function to start the bot"""
    # Get bot token from environment
    bot_token = os.getenv("BOT_TOKEN")
    if not bot_token:
        logger.error("BOT_TOKEN environment variable is required")
        return
    
    # Initialize database
    await init_db()
    logger.info("Database initialized successfully")
    
    # Initialize bot and dispatcher
    bot = Bot(
        token=bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Setup handlers
    setup_handlers(dp)
    
    # Start polling
    logger.info("Starting bot polling...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Error during polling: {e}")
    finally:
        await bot.session.close()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
