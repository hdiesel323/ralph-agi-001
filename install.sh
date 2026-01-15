#!/bin/bash
#
# RALPH-AGI Installer
# One command to set everything up
#

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

echo "
╔═══════════════════════════════════════════════════════════════╗
║                    RALPH-AGI Installer                        ║
╚═══════════════════════════════════════════════════════════════╝
"

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required but not installed."
    echo "Install Python 3.11+ from https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

echo "Found Python $PYTHON_VERSION"

# Require Python 3.11+
if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 11 ]); then
    echo ""
    echo "ERROR: Python 3.11 or higher is required."
    echo "       You have Python $PYTHON_VERSION"
    echo ""
    echo "To install Python 3.11+:"
    echo "  macOS:   brew install python@3.12"
    echo "  Ubuntu:  sudo apt install python3.12"
    echo "  Windows: Download from https://python.org/downloads/"
    echo ""
    echo "If you have Python 3.11+ installed elsewhere, use it directly:"
    echo "  python3.12 -m venv venv"
    echo "  source venv/bin/activate"
    echo "  pip install -e ."
    exit 1
fi

echo "Python version OK"

# Create virtual environment
echo ""
echo "Creating virtual environment..."
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo "Virtual environment created."
else
    echo "Virtual environment already exists."
fi

# Activate venv
source venv/bin/activate

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip -q
pip install -e ".[dev]" -q
pip install anthropic openai python-dotenv -q
echo "Dependencies installed."

# Setup .env file
echo ""
if [ ! -f ".env" ]; then
    echo "Setting up API keys..."
    echo ""
    read -p "Enter your Anthropic API key (or press Enter to skip): " API_KEY
    if [ -n "$API_KEY" ]; then
        echo "ANTHROPIC_API_KEY=$API_KEY" > .env
        echo "API key saved to .env"
    else
        echo "# Add your API key here" > .env
        echo "ANTHROPIC_API_KEY=" >> .env
        echo "Skipped. Edit .env later to add your API key."
    fi
else
    echo ".env file already exists."
    if ! grep -q "ANTHROPIC_API_KEY=sk-" .env 2>/dev/null; then
        echo "WARNING: ANTHROPIC_API_KEY may not be set in .env"
    fi
fi

# Make scripts executable
chmod +x run-ralph.sh 2>/dev/null || true

# Verify installation
echo ""
echo "Verifying installation..."
python3 -c "import anthropic; import ralph_agi; print('All packages loaded successfully!')"

echo "
╔═══════════════════════════════════════════════════════════════╗
║                    Installation Complete!                      ║
╚═══════════════════════════════════════════════════════════════╝

To run RALPH-AGI:

  ./run-ralph.sh --help           # See all options
  ./run-ralph.sh run              # Start basic loop
  ./run-ralph.sh run --prd FILE   # Run with PRD file

Or activate manually:

  source venv/bin/activate
  ralph-agi --help

"
