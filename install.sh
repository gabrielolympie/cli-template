#!/bin/bash
# Install script for Mirascope CLI
# This script installs Python dependencies and sets up Playwright

set -e  # Exit on error

echo "============================================"
echo "  Mirascope CLI Installation Script"
echo "============================================"

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check for Python
if ! command_exists python3; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

echo "✓ Python 3 found: $(python3 --version)"

# Check for pip
if ! command_exists pip3; then
    echo "Error: pip3 is not installed"
    exit 1
fi

echo "✓ pip3 found"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo ""
echo "Installing Python dependencies from requirements.txt..."
pip install -r requirements.txt

# Install Playwright browsers
echo ""
echo "Installing Playwright browsers..."
python -m playwright install --with-deps

# Initialize the skill system
echo ""
echo "Initializing skill system..."
python -c "from src.skills.manager import get_skill_manager; get_skill_manager().load_skills()"

echo ""
echo "============================================"
echo "  Installation Complete!"
echo "============================================"
echo ""
echo "Next steps:"
echo "  1. Edit mirascope_cli.py to set your LLM endpoint"
echo "  2. Run 'python mirascope_cli.py' to start the CLI"
echo "  3. Add skills to .claude/skills/ to extend capabilities"
echo ""
