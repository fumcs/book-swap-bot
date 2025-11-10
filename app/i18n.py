"""Internationalization support for the bot."""
import gettext
import os
from pathlib import Path
from typing import Optional

# Get the locale directory path
LOCALE_DIR = Path(__file__).parent.parent / "locale"


def get_translator(language: str = "en") -> callable:
    """
    Get a translator function for the specified language.
    
    Args:
        language: Language code (e.g., 'en', 'fa')
    
    Returns:
        Translation function T()
    """
    try:
        lang_translation = gettext.translation(
            "messages",
            localedir=str(LOCALE_DIR),
            languages=[language],
            fallback=True
        )
        return lang_translation.gettext
    except Exception:
        # Fallback to default gettext if there's any issue
        return gettext.gettext


def init_translations() -> None:
    """Initialize gettext for the bot. Should be called once at startup."""
    try:
        translation = gettext.translation(
            "messages",
            localedir=str(LOCALE_DIR),
            languages=["en"],
            fallback=True
        )
        translation.install()
    except Exception as e:
        print(f"Warning: Could not initialize translations: {e}")
        # Install null translation as fallback
        gettext.install("messages")


# Default translator (English)
T = get_translator("en")

# Available languages
AVAILABLE_LANGUAGES = {
    "en": "English 🇺🇸",
    "fa": "فارسی 🇮🇷",
}


__all__ = ["get_translator", "init_translations", "T", "AVAILABLE_LANGUAGES", "LOCALE_DIR"]
