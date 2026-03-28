#!/usr/bin/env bash
# setup.sh — birdnet-signage server environment setup
# Run once after cloning the repo, or again to update dependencies.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_DIR="$SCRIPT_DIR/server"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS="$SERVER_DIR/requirements.txt"
CONFIG="$SERVER_DIR/config.env"
CONFIG_EXAMPLE="$SERVER_DIR/config.env.example"
MIN_PYTHON_MINOR=9

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

green()  { echo -e "\033[0;32m$*\033[0m"; }
yellow() { echo -e "\033[0;33m$*\033[0m"; }
red()    { echo -e "\033[0;31m$*\033[0m"; }
bold()   { echo -e "\033[1m$*\033[0m"; }

# ---------------------------------------------------------------------------
# 1. Check Python version
# ---------------------------------------------------------------------------

bold "Checking Python..."

PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        version=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        major=$(echo "$version" | cut -d. -f1)
        minor=$(echo "$version" | cut -d. -f2)
        if [ "$major" -eq 3 ] && [ "$minor" -ge "$MIN_PYTHON_MINOR" ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    red "Python 3.$MIN_PYTHON_MINOR or higher is required but was not found."
    red "On Raspberry Pi OS: sudo apt install python3"
    exit 1
fi

green "  Found $($PYTHON --version)"

# ---------------------------------------------------------------------------
# 2. Handle existing venv
# ---------------------------------------------------------------------------

bold "Checking virtual environment..."

if [ -d "$VENV_DIR" ]; then
    yellow "  Existing venv found at $VENV_DIR"
    read -rp "  Delete and recreate? [y/N] " response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf "$VENV_DIR"
        green "  Removed existing venv."
    else
        echo "  Keeping existing venv."
    fi
fi

if [ ! -d "$VENV_DIR" ]; then
    echo "  Creating virtual environment..."
    "$PYTHON" -m venv "$VENV_DIR"
    green "  Created venv at $VENV_DIR"
fi

# ---------------------------------------------------------------------------
# 3. Install dependencies
# ---------------------------------------------------------------------------

bold "Installing dependencies..."

"$VENV_DIR/bin/pip" install --quiet --upgrade pip
"$VENV_DIR/bin/pip" install --quiet -r "$REQUIREMENTS"

green "  Dependencies installed."

# ---------------------------------------------------------------------------
# 4. Create config.env if missing
# ---------------------------------------------------------------------------

bold "Checking configuration..."

if [ ! -f "$CONFIG" ]; then
    cp "$CONFIG_EXAMPLE" "$CONFIG"
    green "  Created $CONFIG from example."
    yellow "  ACTION REQUIRED: edit server/config.env and set BIRDNETPI_DB to your database path."
else
    echo "  config.env already exists, skipping."
fi

# ---------------------------------------------------------------------------
# 5. Warn if DB path does not exist
# ---------------------------------------------------------------------------

if [ -f "$CONFIG" ]; then
    DB_PATH=$(grep -E '^BIRDNETPI_DB=' "$CONFIG" | cut -d= -f2- | tr -d '"' | tr -d "'")
    # Expand ~ manually since it won't expand inside a variable
    DB_PATH="${DB_PATH/#\~/$HOME}"

    if [ -n "$DB_PATH" ] && [ ! -f "$DB_PATH" ]; then
        yellow "  WARNING: BIRDNETPI_DB is set to:"
        yellow "    $DB_PATH"
        yellow "  That file does not exist. The server will start but cannot serve detections."
        yellow "  Update BIRDNETPI_DB in server/config.env once BirdNET-Pi is installed."
    elif [ -n "$DB_PATH" ]; then
        green "  Database found at $DB_PATH"
    fi
fi

# ---------------------------------------------------------------------------
# 6. Check for placeholder image
# ---------------------------------------------------------------------------

bold "Checking static assets..."

STATIC_DIR="$SERVER_DIR/static"
PLACEHOLDER="$STATIC_DIR/placeholder.png"

if [ ! -f "$PLACEHOLDER" ]; then
    mkdir -p "$STATIC_DIR"
    yellow "  WARNING: server/static/placeholder.png is missing."
    yellow "  The server will start, but missing-image fallback will return a 404."
    yellow "  Add placeholder.png to server/static/ before running."
else
    green "  placeholder.png found."
fi

# ---------------------------------------------------------------------------
# Done
# ---------------------------------------------------------------------------

echo ""
green "Setup complete."
echo ""
bold "To start the server:"
echo "  source .venv/bin/activate"
echo "  cd server && python server.py"
echo ""
bold "Or without activating the venv:"
echo "  .venv/bin/python server/server.py"
echo ""
