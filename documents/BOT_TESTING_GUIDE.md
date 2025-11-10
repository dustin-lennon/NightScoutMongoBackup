# Bot Testing Guide - NightScout MongoDB Backup Bot

## ✅ Setup Complete

Poetry is now installed and configured with `python-dotenv-vault` for deployment support.

### What's Been Set Up

1. **Poetry Configuration**
   - Poetry installed at `~/.local/bin/poetry`
   - Added to PATH in `.zshrc`
   - Project dependencies installed including `python-dotenv-vault` for encrypted `.env.vault` support

2. **Dependencies Added**
   - `python-dotenv-vault ^0.7` - For secure environment variable deployment
   - `brotli ^1.1` - For compression support
   - `disnake ^2.9` - Discord bot framework
   - `motor ^3.4` - Async MongoDB driver
   - `boto3 ^1.35` - AWS S3 integration
   - `pydantic ^2.9` and `pydantic-settings ^2.6` - Typed config management
   - `python-dotenv ^1.0` - .env file support
   - `pytest ^8.0`, `pytest-asyncio ^0.24` - Testing
   - `moto[s3] ^5.0` - S3 mocking for tests
   - `ruff ^0.6`, `black ^24.0`, `mypy ^1.11` - Linting, formatting, type checking

3. **Test Files Created**
   - `tests/unit/test_bot.py` - Unit tests for bot initialization (7 tests)
   - `tests/integration/test_bot_connection.py` - Integration tests for Discord connection
   - `test_bot_simple.sh` - Helper script for running tests

## 🚀 Quick Start - Testing Bot Connection

### Option 1: Run Unit Tests (No Discord Connection)
```bash
poetry run pytest tests/unit/test_bot.py -v
```

These tests verify:
- Bot initialization
- Intents configuration
- Cog loading
- Event handlers
- Nightly backup task setup

### Option 2: Run Integration Tests (Quick Check)
```bash
poetry run pytest tests/integration/test_bot_connection.py::test_bot_creation -v
```

Verifies bot can be created with valid Discord credentials.

### Option 3: Full Discord Connection Test
```bash
poetry run pytest tests/integration/test_bot_connection.py::test_bot_discord_connection -v -m slow
```

⚠️ **Warning**: This will actually connect the bot to Discord, verify guild access, check channels, and then disconnect.

### Option 4: Start Bot Interactively
```bash
poetry run python -m nightscout_backup_bot
```

Press `Ctrl+C` to stop. The bot will:
- Connect to Discord
- Load all cogs (commands)
- Start listening for slash commands
- Run nightly backup task if enabled

## 🔧 Poetry Commands Reference

### Dependency Management
```bash
# Install all dependencies
poetry install

# Add a new dependency
poetry add package-name

# Add a dev dependency
poetry add --group dev package-name

# Update dependencies
poetry update

# Show installed packages
poetry show
```

### Running Commands
```bash
# Run Python in Poetry environment
poetry run python script.py

# Run tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src/nightscout_backup_bot

# Run specific test file
poetry run pytest tests/unit/test_bot.py -v

# Run bot
poetry run python -m nightscout_backup_bot
```

### Environment Management
```bash
# Show virtualenv info
poetry env info

# List all virtualenvs
poetry env list

# Remove virtualenv
poetry env remove <env-name>
```

## 🔐 Environment Configuration

Your `.env` file contains:
- Discord bot token and credentials
- MongoDB Atlas connection details
- AWS S3 bucket configuration
- Sentry DSN for error tracking

For deployments, you can use `dotenv-vault`:
```bash
# Build encrypted .env.vault file
npx dotenv-vault local build

# This creates .env.vault and .env.keys
# Deploy with DOTENV_KEY environment variable set on server
```

## 📦 Deployment with python-dotenv-vault

The bot now uses `python-dotenv-vault` which:
1. **Development**: Loads from `.env` file (if `DOTENV_KEY` not set)
2. **Production**: Loads from encrypted `.env.vault` (if `DOTENV_KEY` is set)

This allows you to safely commit `.env.vault` to git while keeping secrets encrypted.

## 🧪 Next Steps for Testing

1. **Test Bot Connection to Discord**:
   ```bash
   poetry run pytest tests/integration/test_bot_connection.py::test_bot_discord_connection -v -m slow
   ```

2. **Start Bot and Test Slash Commands**:
   ```bash
   poetry run python -m nightscout_backup_bot
   ```
   Then in Discord, try:
   - `/ping` - Test bot responsiveness
   - `/backup` - Run a manual backup (admin only)
   - `/queryDb` - Diagnostic: query MongoDB stats

3. **Run Full Test Suite**:
   ```bash
   poetry run pytest -v
   ```

## 🎯 Current Test Coverage by Module

## 🐛 Known Issues

- The `test_bot_on_ready_event` test initially failed due to Discord.py's read-only `user` property - now fixed with proper mocking
- Integration tests require valid Discord credentials in `.env`
- Set `SKIP_DISCORD_TESTS=1` to skip integration tests

## 📚 Additional Resources

- [Discord.py (disnake) Documentation](https://docs.disnake.dev/)
- [Poetry Documentation](https://python-poetry.org/docs/)
- [python-dotenv-vault Documentation](https://pypi.org/project/python-dotenv-vault/)
- [pytest Documentation](https://docs.pytest.org/)

---

**Ready to test!** Run any of the commands above to verify your bot works correctly.
