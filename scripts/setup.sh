#!/bin/bash

# Setup script for NightScout Backup Bot
# Usage: ./scripts/setup.sh

set -e

echo "🚀 Setting up NightScout Backup Bot (Python)"
echo "=============================================="

# Check Python version
echo "📝 Checking Python version..."
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
REQUIRED_VERSION="3.12"

if ! python3 -c "import sys; exit(0 if sys.version_info >= (3, 12) else 1)"; then
    echo "❌ Error: Python 3.12 or higher is required. Found: $PYTHON_VERSION"
    exit 1
fi
echo "✅ Python version: $PYTHON_VERSION"

# Check if Poetry is installed
if command -v poetry &> /dev/null; then
    echo "✅ Poetry found"
    USE_POETRY=true
else
    echo "⚠️  Poetry not found. Using pip instead."
    echo "   Install Poetry for better dependency management: https://python-poetry.org/docs/#installation"
    USE_POETRY=false
fi

# Create virtual environment if using pip
if [ "$USE_POETRY" = false ]; then
    echo "📦 Creating virtual environment..."
    if [ ! -d "venv" ]; then
        python3 -m venv venv
        echo "✅ Virtual environment created"
    else
        echo "✅ Virtual environment already exists"
    fi

    echo "📦 Activating virtual environment..."
    source venv/bin/activate
fi

# Install dependencies
echo "📦 Installing dependencies..."
if [ "$USE_POETRY" = true ]; then
    poetry install
else
    pip install --upgrade pip
    pip install -r requirements.txt
fi
echo "✅ Dependencies installed"

# Setup environment file
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "✅ .env file created"
    echo "⚠️  Please edit .env with your credentials before running the bot"
else
    echo "✅ .env file already exists"
fi

# Create backups directory
if [ ! -d "backups" ]; then
    echo "📁 Creating backups directory..."
    mkdir -p backups
    touch backups/.gitkeep
    echo "✅ Backups directory created"
else
    echo "✅ Backups directory already exists"
fi

# Create logs directory
if [ ! -d "logs" ]; then
    echo "📁 Creating logs directory..."
    mkdir -p logs
    echo "✅ Logs directory created"
else
    echo "✅ Logs directory already exists"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Edit .env file with your credentials:"
echo "   - Discord bot token"
echo "   - MongoDB connection details"
echo "   - AWS S3 credentials"
echo ""
echo "2. Run the bot:"
echo "   poetry run python -m nightscout_backup_bot"
echo ""
echo "3. Run tests:"
echo "   poetry run pytest"
echo ""
echo "📚 See README_PYTHON.md for detailed documentation"
echo ""
