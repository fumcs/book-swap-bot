# Internationalization (i18n) Setup

This bot supports multiple languages using GNU gettext. Currently configured for:
- **English (en)** - Default language
- **Persian/Farsi (fa)** - فارسی

## Directory Structure

```
locale/
├── messages.pot           # Template file with all translatable strings
├── en/
│   └── LC_MESSAGES/
│       └── messages.po    # English translations
└── fa/
    └── LC_MESSAGES/
        ├── messages.po    # Persian translations
        └── messages.mo    # Compiled Persian translations (generated)
```

## Adding Translations

### Extracting Strings

To extract translatable strings from Python files:

```bash
xgettext --from-code=UTF-8 --language=Python --keyword=T \
  --output=locale/messages.pot --add-comments app/bot/*.py
```

### Creating New Language

To add a new language (e.g., German):

```bash
# Initialize the PO file for the new language
msginit --input=locale/messages.pot --locale=de \
  --output=locale/de/LC_MESSAGES/messages.po --no-translator

# Then edit locale/de/LC_MESSAGES/messages.po and add translations
```

### Compiling Translations

To compile the Persian translations for use by the bot:

```bash
msgfmt locale/fa/LC_MESSAGES/messages.po -o locale/fa/LC_MESSAGES/messages.mo
```

## Using in Code

All user-facing strings in the bot use the `T()` function for translation:

```python
from app.i18n import T

# String will be translated based on the current language
message = T("Hello, world!")
```

### In Handlers

```python
import gettext
from app.i18n import get_translator

# Get translator for a specific language
fa_translator = get_translator("fa")
message = fa_translator("Hello, world!")
```

## Workflow for Translators

1. **Extract strings**: Run xgettext to update `messages.pot`
2. **Update translations**: Edit `.po` files to add/update translations
3. **Compile**: Run msgfmt to generate `.mo` files
4. **Test**: Run the bot with the new language configured

## Supported Language Codes

- `en` - English
- `fa` - Persian (فارسی)

## Notes

- The `.pot` file is the template that should be version controlled
- The `.po` files contain human-readable translations
- The `.mo` files are compiled binary files generated from `.po` files (not version controlled)
- The bot defaults to English if a translation is not found
