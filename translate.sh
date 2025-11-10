#!/bin/bash
# Helper script to manage translations

set -e

LOCALE_DIR="locale"
POT_FILE="$LOCALE_DIR/messages.pot"

function extract() {
    echo "📋 Extracting translatable strings..."
    xgettext --from-code=UTF-8 --language=Python --keyword=T \
      --output="$POT_FILE" --add-comments app/bot/*.py
    echo "✅ POT file updated: $POT_FILE"
}

function compile() {
    echo "🔨 Compiling translations..."
    for lang_dir in $LOCALE_DIR/*/; do
        if [ -d "$lang_dir/LC_MESSAGES" ]; then
            lang=$(basename "$lang_dir")
            po_file="$lang_dir/LC_MESSAGES/messages.po"
            mo_file="$lang_dir/LC_MESSAGES/messages.mo"
            
            if [ -f "$po_file" ]; then
                msgfmt "$po_file" -o "$mo_file"
                echo "✅ Compiled: $mo_file"
            fi
        fi
    done
}

function update_language() {
    lang=$1
    if [ -z "$lang" ]; then
        echo "❌ Usage: $0 update <language_code>"
        echo "   Example: $0 update fa"
        exit 1
    fi
    
    echo "📝 Updating translations for language: $lang"
    msgmerge -U "$LOCALE_DIR/$lang/LC_MESSAGES/messages.po" "$POT_FILE"
    echo "✅ Updated: $LOCALE_DIR/$lang/LC_MESSAGES/messages.po"
}

function add_language() {
    lang=$1
    if [ -z "$lang" ]; then
        echo "❌ Usage: $0 add <language_code>"
        echo "   Example: $0 add de"
        exit 1
    fi
    
    lang_dir="$LOCALE_DIR/$lang/LC_MESSAGES"
    mkdir -p "$lang_dir"
    
    echo "🌍 Creating new language: $lang"
    msginit --input="$POT_FILE" --locale="$lang" \
      --output="$lang_dir/messages.po" --no-translator
    echo "✅ Created: $lang_dir/messages.po"
    echo "📝 Now edit the file and add translations!"
}

case "${1:-}" in
    extract)
        extract
        ;;
    compile)
        compile
        ;;
    update)
        update_language "$2"
        ;;
    add)
        add_language "$2"
        ;;
    all)
        extract
        compile
        ;;
    *)
        echo "📚 Translation Management Script"
        echo ""
        echo "Usage: $0 <command> [args]"
        echo ""
        echo "Commands:"
        echo "  extract              Extract translatable strings from Python files"
        echo "  compile              Compile .po files to .mo files"
        echo "  update <lang>        Update existing language translations (msgmerge)"
        echo "  add <lang>           Create new language (e.g., 'de' for German)"
        echo "  all                  Extract and compile in one command"
        echo ""
        echo "Examples:"
        echo "  $0 extract           # Update the POT template"
        echo "  $0 add de            # Add German translations"
        echo "  $0 update fa         # Update Persian translations"
        echo "  $0 compile           # Compile all .po to .mo"
        echo "  $0 all               # Extract and compile"
        exit 0
        ;;
esac
