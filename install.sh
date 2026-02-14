#!/bin/bash
# Install script for Mirascope CLI
# This script installs Python dependencies and sets up Playwright CLI

set -e  # Exit on error

echo "============================================"
echo "  Mirascope CLI Installation Script"
echo "============================================"

# Function to check if a command exists
command_exists() {
    command -v "$1" &> /dev/null
}

# Check for Python
if ! command_exists python; then
    echo "Error: Python is not installed"
    exit 1
fi

echo "✓ Python found: $(python --version)"

# Check for pip
if ! command_exists pip; then
    echo "Error: pip is not installed"
    exit 1
fi

echo "✓ pip found"

# Check for npm
if ! command_exists npm; then
    echo "Error: npm is not installed"
    exit 1
fi

echo "✓ npm found: $(npm --version)"

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python -m venv venv
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

# Install Playwright CLI via npm
echo ""
echo "Installing Playwright CLI..."
npm install -g @playwright/cli@latest

# Verify Playwright CLI installation
echo "Verifying Playwright CLI installation..."
playwright-cli --help

# Initialize the skill system
echo ""
echo "Initializing skill system..."
python -c "from src.utils.skills.manager import get_skill_manager; get_skill_manager().load_skills()"

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
