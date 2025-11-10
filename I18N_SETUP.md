# Internationalization (i18n) Setup Complete ✅

## Summary

The Book Swap Bot now has full internationalization support using GNU gettext. Here's what's been set up:

### Languages Configured
- ✅ **English (en)** - Default language
- ✅ **Persian/Farsi (fa)** - فارسی

### File Structure
```
locale/
├── messages.pot                    # Translation template (all strings)
├── en/LC_MESSAGES/
│   ├── messages.po                # English translations (base language)
│   └── messages.mo                # Compiled English (binary)
└── fa/LC_MESSAGES/
    ├── messages.po                # Persian translations
    └── messages.mo                # Compiled Persian (binary)
```

### How It Works

1. **Extraction**: All user-facing strings in the bot use the `T()` function
   ```python
   from app.i18n import T
   message = T("Hello, world!")
   ```

2. **Translation**: Translators edit the `.po` files to provide translations
   ```po
   msgid "Hello, world!"
   msgstr "سلام جهان!"  # Persian translation
   ```

3. **Compilation**: `.po` files are compiled to `.mo` files for runtime use
   ```bash
   msgfmt locale/fa/LC_MESSAGES/messages.po -o locale/fa/LC_MESSAGES/messages.mo
   ```

4. **Runtime**: The bot loads translations based on the language setting

### Key Files Added

- **`app/i18n.py`** - i18n module with language support and translator functions
- **`I18N_README.md`** - Detailed documentation about the i18n system
- **`translate.sh`** - Helper script for managing translations
- **`locale/messages.pot`** - Master template with all translatable strings

### Using the Helper Script

```bash
# Extract strings from code (run after adding new T() calls)
./translate.sh extract

# Add a new language (e.g., German)
./translate.sh add de

# Update existing language with new strings
./translate.sh update fa

# Compile all translations
./translate.sh compile

# Extract and compile in one go
./translate.sh all
```

### Modified Files

- **`main.py`** - Added `init_translations()` call at startup
- **`app/bot/handlers.py`** - All user messages now use `T()` function
- **`app/bot/keyboards.py`** - All button labels now use `T()` function
- **`app/bot/utils.py`** - All utility messages now use `T()` function
- **`README.md`** - Added i18n section with quick reference

### Adding Translations

To add Persian translations (as an example):

1. Edit `locale/fa/LC_MESSAGES/messages.po`
2. Find empty `msgstr ""` entries
3. Add translations, e.g.:
   ```po
   msgid "Browse books"
   msgstr "مرور کتاب ها"
   ```
4. Compile: `./translate.sh compile`

### Complete Extraction List

The POT file contains 68 translatable strings including:

- Menu options (Post, Browse, Search, My listings)
- Input prompts (title, author, price, description)
- Status messages (book listed, contact sent, marked as sold)
- Error messages (invalid input, missing data)
- Book condition labels (New, Like new, Good, Acceptable, Poor)
- UI elements (buttons, pagination, confirmations)

### Next Steps

1. **Share with translators**: Give them `locale/fa/LC_MESSAGES/messages.po` to fill in Persian translations
2. **Update code**: If you add new user-facing text, wrap it with `T()` function
3. **Extract**: Run `./translate.sh extract` to update the template
4. **Merge**: Run `./translate.sh update fa` to add new strings to existing translations
5. **Compile**: Run `./translate.sh compile` to generate `.mo` files
6. **Test**: Run the bot with different languages

### Language Selection Implementation

Currently the bot defaults to English. To add per-user language selection:

```python
# In user model/state, store preferred_language
# In handlers, use:
from app.i18n import get_translator

user_language = user.preferred_language or "en"
T = get_translator(user_language)

message = T("Hello")
```

### Troubleshooting

- **Strings not translating**: Ensure `.mo` file is compiled from latest `.po`
- **New strings missing**: Run `./translate.sh extract` to update the template
- **Import errors**: Ensure `app/i18n.py` is in the correct location
- **Encoding issues**: All files use UTF-8; ensure your editor uses UTF-8

### Resources

- [GNU gettext documentation](https://www.gnu.org/software/gettext/)
- [Python gettext module](https://docs.python.org/3/library/gettext.html)
- [Poedit](https://poedit.net/) - GUI tool for editing .po files
- [Persian language code](https://en.wikipedia.org/wiki/Persian_language#Classification): `fa`

---

**Status**: ✅ Ready for translation! The infrastructure is in place and sample Persian translations have been started.
