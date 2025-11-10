# Development Guide

## Quick Start

```bash
# Run setup script
./scripts/setup.sh

# Edit environment variables
nano .env

# Run the bot (Poetry)
poetry run python -m nightscout_backup_bot
```

## Development Commands

### Testing

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test file
poetry run pytest tests/unit/test_mongo_service.py

# Run integration tests (requires AWS credentials)
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
poetry run pytest tests/integration/ -v
```

### Code Quality

```bash
# Format code with Black
poetry run black src tests

# Lint with Ruff
poetry run ruff check src tests

# Fix auto-fixable issues
poetry run ruff check --fix src tests

# Type check with mypy
poetry run mypy src
```

### Running Locally

```bash
# With Poetry
poetry run python -m nightscout_backup_bot
```

### Debugging

```bash
# Enable debug logging
export NODE_ENV=development
```

Use VSCode Debugger to step through the code.

## Project Structure

```
.
├── pyproject.toml                # Poetry configuration & dependencies
├── ecosystem.config.js           # PM2 configuration
├── .env.example                  # Environment template
├── documents/                    # Project documentation
│   ├── BOT_TESTING_GUIDE.md
│   └── README_PYTHON.md
├── backups/                      # Local backup files
├── logs/                         # Log files
├── htmlcov/                      # Coverage reports
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── __mocks__/                # Test mocks
│   ├── unit/                     # Unit tests
│   └── integration/              # Integration tests
├── src/
│   └── nightscout_backup_bot/
│       ├── __init__.py
│       ├── __main__.py           # Entrypoint (python -m nightscout_backup_bot)
│       ├── main.py               # Entrypoint logic
│       ├── bot.py                # Bot creation & startup
│       ├── config.py             # Pydantic settings/config management
│       ├── logging_config.py     # Logging setup
│       ├── cogs/
│       │   ├── __init__.py
│       │   ├── admin/            # Admin commands
│       │   └── general/          # General commands
│       ├── services/
│       │   ├── __init__.py
│       │   ├── backup_service.py
│       │   ├── compression_service.py
│       │   ├── discord_thread_service.py
│       │   ├── file_service.py
│       │   ├── mongo_service.py
│       │   └── s3_service.py
│       └── utils/                # Helper functions/utilities
```

## Adding New Features

### Adding a New Discord Command

1. Decide which cog your command belongs in:
   - For admin-only commands (e.g., backup, system, thread management), add to `src/nightscout_backup_bot/cogs/admin/`
   - For general/user commands (e.g., ping, querydb, listbackups), add to `src/nightscout_backup_bot/cogs/general/`
2. Create a new file for the command (recommended for complex commands) or add to an existing cog file.
3. Define your command using the `@commands.slash_command` decorator. Use type hints and docstrings.
4. Add any required permission checks (e.g., `@is_owner`, channel checks, cooldowns).
5. Implement the command logic, including Discord embed responses if needed.
6. Register the cog in `bot.py` if it's a new cog.
7. Add unit tests in `tests/unit/` for your command logic and permission checks.

Example (general command):
```python
@commands.slash_command(name="ping", description="Check if the bot is responsive")
async def ping(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
    """
    Ping command to check bot responsiveness.
    """
    latency_ms = round(self.bot.latency * 1000)
    embed = disnake.Embed(
        title="🏓 Pong!",
        description="Bot is online and responsive.",
        color=disnake.Color.green(),
    )
    embed.add_field(name="Latency", value=f"{latency_ms}ms", inline=True)
    embed.add_field(name="Status", value="✅ Operational", inline=True)
    await inter.response.send_message(embed=embed)
```

Example (admin command with checks):
```python
@commands.slash_command(name="backup", description="Creates a backup of the Nightscout database.")
@commands.cooldown(1, 300, type=commands.BucketType.user)
async def backup(self, inter: disnake.ApplicationCommandInteraction[NightScoutBackupBot]) -> None:
    """
    Create a backup of the Nightscout database.
    """
    await inter.response.defer(ephemeral=False)
    # ...command logic...
```

### Adding a New Service


1. Create a new service file in `src/nightscout_backup_bot/services/` (e.g., `my_service.py`).
2. Define your service class with type hints, docstrings, and appropriate async methods if needed.
3. If your service should be available for import, add it to `services/__init__.py`.
4. Integrate your service into the relevant workflow (e.g., `BackupService`, a cog, or another service).
5. Add unit tests for your service in `tests/unit/` (mock external dependencies).
6. Document any new environment variables in `config.py`, `.env.example`, and `README_PYTHON.md` if your service requires them.

Example:
```python
# src/nightscout_backup_bot/services/my_service.py
class MyService:
    """Service for handling custom logic."""
    def __init__(self):
        pass
    async def do_something(self, arg: str) -> str:
        """Perform an async operation."""
        return f"Processed {arg}"
```

Then in `services/__init__.py`:
```python
from .my_service import MyService
```

Add tests in `tests/unit/test_my_service.py`:
```python
import pytest
from nightscout_backup_bot.services.my_service import MyService

@pytest.mark.asyncio
async def test_do_something():
    service = MyService()
    result = await service.do_something("test")
    assert result == "Processed test"
```

### Environment Variables

Add new variables in:
1. `config.py` - Add field to `Settings` class
2. `.env.example` - Add with description
3. `README_PYTHON.md` - Document in configuration section

## Testing Guidelines

### Unit Tests
- Mock all external dependencies
- Test each service in isolation
- Aim for >85% coverage

### Integration Tests
- Only for critical external integrations (S3)
- Skip if credentials not available
- Mark with `@pytest.mark.integration`

### Test Structure
```python
class TestServiceName:
    @pytest.fixture
    def service(self):
        return ServiceName()
    
    @pytest.mark.asyncio
    async def test_method_name(self, service):
        result = await service.method()
        assert result == expected
```

## Common Tasks

### Update Dependencies

```bash
# With Poetry
poetry update
```

### Database Backup Test

```bash
# Set test credentials
export MONGO_HOST=test-cluster.mongodb.net
export MONGO_USERNAME=testuser
export MONGO_PASSWORD=testpass

# Run the bot
poetry run  python -m nightscout_backup_bot

# In Discord issue /backup slash command
/backup
```

## Troubleshooting

### Type Checking Errors
```bash
# Check specific file
mypy src/nightscout_backup_bot/services/mongo_service.py
```

### Test Failures
```bash
# Run with verbose output
pytest -vv tests/unit/test_mongo_service.py
```

## Git Workflow

1. Create feature branch from `python3`
2. Make changes and test locally
3. Run code quality checks
4. Commit with descriptive message
5. Push and create PR to `python3` branch

```bash
git checkout -b feature/my-feature
# Make changes
poetry run black src tests
poetry run ruff check src tests
poetry run pytest
git add .
git commit -m "feat: Add new feature"
git push origin feature/my-feature
```

## Performance Tips

- Use `async`/`await` for I/O operations
- Minimize MongoDB queries
- Stream large files instead of loading into memory
- Use connection pooling for external services

## Security Best Practices

- Never commit `.env` file
- Rotate credentials regularly
- Use read-only MongoDB credentials when possible
- Validate all user inputs
- Rate limit commands
- Check permissions before destructive operations
