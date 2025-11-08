# Copilot Instructions for NightScout MongoDB Backup (Python)

## Project Overview

This is a **Python rewrite** of a Discord bot that provides automated and manual backup functionality for NightScout MongoDB databases. Here are the responsibilities:

-   Runs 24/7 on a **Linode** server, supervised by **PM2**.
-   Connects to a **MongoDB Atlas** database.
-   The bot creates **nightly scheduled backups** of specific Mongo collections, supports **slash commands** for on-demand backups, uploads compressed backups to **AWS S3 bucket** with a 7-day retention policy (retention is handled by S3 lifecycle rules; the bot only uploads).
-   Provides real-time progress updates via Discord threads.
-   Is fully managed as a **Poetry** project with testing, CI, and automated deployment from GitHub to Linode.

Copilot should generate code that is **production-ready**, **typed**, and structured for long-term maintainability.

**Current Status**: `python3` branch - fresh Python implementation replacing the TypeScript version on `main`.

## Architecture & Core Components

### Service Layer Architecture

The original TypeScript project uses a service-oriented architecture with clear separation of concerns:

1. **MongoService** - MongoDB Atlas connection and data export
2. **CompressionService** - Handles gzip/Brotli compression (see Compression Strategy below)
3. **S3Service** - AWS S3 upload with public URL generation
4. **DiscordThreadService** - Discord thread creation and progress updates
5. **FileService** - Local backup file management (`backups/` directory)
6. **BackupService** - Orchestrates the full backup workflow

### Discord Bot Structure

-   **Commands**: `/backup` (admin), `/ping` (general), `/queryDb` (diagnostic)
-   **Preconditions**: BackupChannelOnly, BackupRateLimit, GuildOnly
-   **Events**: Command execution tracking, client ready, connection errors
-   **Scheduled Tasks**: Nightly backup using cron-like scheduling

### Backup Workflow (Expected in Python)

1. Command triggered (slash command or scheduled)
2. Create Discord thread for progress tracking
3. Connect to MongoDB Atlas and export data to JSON
4. Compress JSON using gzip (default) or Brotli
5. Upload compressed file to S3 bucket
6. Generate public download link
7. Post completion message to Discord thread with download link
8. Clean up local files

## Environment Configuration

Required environment variables (from `.env.example`):

```bash
# Discord Bot
DISCORD_TOKEN=              # Bot token from Discord Developer Portal
DISCORD_CLIENT_ID=          # Application ID
BACKUP_CHANNEL_ID=          # Channel where backup threads are created

# MongoDB Atlas
MONGO_HOST=                 # Atlas cluster hostname
MONGO_USERNAME=             # Database username
MONGO_PASSWORD=             # Database password
MONGO_DB=                   # Database name
MONGO_API_KEY=              # Atlas API key (if needed)

# AWS S3
AWS_ACCESS_KEY_ID=          # AWS credentials
AWS_SECRET_ACCESS_KEY=      # AWS secret
AWS_REGION=us-east-1        # Default: us-east-1
S3_BACKUP_BUCKET=           # Bucket for backup storage

# Backup Config
ENABLE_NIGHTLY_BACKUP=true  # Enable/disable scheduled backups
BACKUP_HOUR=2               # Hour for nightly backup (24-hour format)
BACKUP_MINUTE=0             # Minute for nightly backup
COMPRESSION_METHOD=gzip     # 'gzip' (default) or 'brotli'

# Monitoring (Optional)
SENTRY_DSN=                 # Error tracking
BOT_REPORT_CHANNEL_ID=      # Bot status reports
BOT_OWNER_IDS=              # Comma-separated Discord user IDs
```

Copilot must assume and use:

-   **Python**: Latest stable 3.x (>=3.10)
-   **Discord SDK**: dissnake (https://dissnake.dev/)
-   **Package / env management**: Poetry (https://python-poetry.org/).
-   **MongoDB**: `motor` (async driver) for MongoDB Atlas.
-   **AWS S3**: `boto3` (and `botocore`) for interacting with S3.
-   **Config management**: `pydantic-settings` or `pydantic` v2 settings, reading from environment variables and optionally a `.env` file.
-   **Logging**: Standard library `logging` with structured, configurable loggers.
-   **Testing**: `pytest` + `pytest-asyncio` for async tests, with mocks for external services.
-   **Lint/format**: `ruff` and `black` (config in `pyproject.toml`).
-   **Type checking**: `mypy` or `pyright`-friendly type hints throughout the codebase.

## Poetry

-   All dependencies and dev-dependencies must be added in **`pyproject.toml`**.
-   Copilot should not create `requirements.txt` unless explicitly asked; if it must, it should derive it from Poetry.

Example dependencies Copilot should prefer:

```toml
[tool.poetry.dependencies]
python = "^3.12"
dissnake = "^2.9"
motor = "^3.4"
boto3 = "^1.35"
pydantic = "^2.9"
pydantic-settings = "^2.6"
python-dotenv = "^1.0"

[tool.poetry.group.dev.dependencies]
pytest = "^8.0"
pytest-asyncio = "^0.24"
moto = { extras = ["s3"], version = "^5.0" }
ruff = "^0.6"
black = "^24.0"
mypy = "^1.11"
```

## Project Structure

This project structure is the minimum Copilot should follow:

```
.
├─ pyproject.toml
├─ .env.example
├─ .vscode/
│  └─ launch.json
├─ .github/
│  └─ workflows/
│     └─ deploy.yml
|  └─ copilot-instructions.md
├─ ecosystem.config.js          # PM2 config
└─ src/
   └─ nightscout_backup_bot/
      ├─ __init__.py
      ├─ main.py                # Entrypoint (python -m nightscout_backup_bot)
      ├─ config.py              # Settings via pydantic-settings
      ├─ logging_config.py
      ├─ bot.py                 # Bot creation & startup
      ├─ cogs/
      │  ├─ __init__.py
      │  ├─ admin.py
      │  └─ general.py
      └─ services/
         ├─ __init__.py
         ├─ mongo_service.py
         ├─ s3_service.py
         └─ backup_service.py
```

## Compression Strategy

**Critical Design Decision**: Use native Python compression libraries only.

### Gzip (Default - Recommended)

-   70-80% size reduction for JSON data
-   Fast compression/decompression
-   Universal cross-platform support
-   Use: `gzip` module

### Brotli (Alternative)

-   85-95% size reduction for JSON data
-   Slightly slower but better compression
-   Modern cross-platform support
-   Use: `brotli` module
-   Enable with: `COMPRESSION_METHOD=brotli`

**Why not 7z/zip?** Avoid external binaries. Native Python libraries provide excellent compression with zero platform dependencies.

## Testing Requirements

The original project has **87.09% test coverage** with 161 unit tests and 3 S3 integration tests.

### Testing Standards

-   **Unit tests**: Mock all external dependencies (MongoDB, AWS S3, Discord API)
-   **Integration tests**: S3 connectivity tests (require real AWS credentials, run conditionally)
-   **Coverage target**: Maintain >85% coverage
-   **Framework**: Use `pytest` with `pytest-asyncio` for async tests

### Test Structure (Expected)

```
tests/
├── __mocks__/          # Mock objects for external services
├── unit/
│   ├── test_mongo.py
│   ├── test_s3.py
│   ├── test_compression.py
│   ├── test_discord_thread.py
│   └── test_backup_workflow.py
├── integration/
│   └── test_s3_integration.py
└── conftest.py         # Pytest fixtures
```

### S3 Integration Testing

-   Only run when AWS credentials are present
-   Test: authentication, bucket access, upload/download, error handling
-   Skip gracefully if credentials missing

## Code Quality & CI/CD

### GitHub Actions Workflows

-   **`testing.yml`**: Runs on PRs to `develop`, requires all tests passing
-   **`linting-checks.yml`**: Code quality checks (adapt for Python: Black, Flake8, mypy)
-   **`sonarcloud.yml`**: Code quality metrics, coverage tracking
-   **`semgrep.yml`**: Security scanning
-   **`codeql-analysis.yml`**: Security vulnerability detection
-   **`sync-main-to-develop.yml`**: Git Flow automation
-   **`delete-merged-branches.yml`**: Cleanup feature branches

### Python Code Quality Tools (To Configure)

-   **Formatter**: `black` (120 char line length)
-   **Linter**: `flake8` or `ruff`
-   **Type Checking**: `mypy` (use type hints throughout)
-   **Security**: Semgrep + CodeQL (already configured)
-   **Pre-commit**: `.husky/pre-commit` runs lint + tests before commit

## Git Workflow (Git Flow)

-   **`main`**: Production-ready code (TypeScript version until Python is ready)
-   **`develop`**: Development branch
-   **`python3`**: Python rewrite branch (CURRENT)
-   **Feature branches**: `feature/*`, `bugfix/*`, `hotfix/*`

PRs should target `python3` branch until Python version is production-ready.

## Development Workflow

### Setup Commands (Python)

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Dev dependencies

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Run tests
pytest
pytest --cov=src --cov-report=html  # With coverage

# Run bot
python src/main.py  # or bot.py, index.py - TBD
```

### Discord Bot Development

-   Use `discord.py` library (latest stable version)
-   Implement slash commands using `discord.app_commands`
-   Use `@tasks.loop()` decorator for scheduled tasks
-   Handle errors gracefully with Sentry integration

### MongoDB Connection

-   Use `motor` (async MongoDB driver) with MongoDB Atlas connection string
-   Export collections to JSON using `bson.json_util`
-   Handle authentication and connection errors
-   Support read-only backup operations

## Key Differences from TypeScript Version

### Async/Await

-   Python: Use `asyncio` with `async`/`await`
-   Discord.py is fully async
-   Use `aiofiles` for async file I/O
-   Use `aioboto3` for async S3 operations

### Project Structure

```
src/
├── main.py              # Bot entry point
├── commands/
│   ├── admin/           # /backup command
│   └── general/         # /ping, /queryDb
├── services/
│   ├── mongo.py
│   ├── s3.py
│   ├── compression.py
│   ├── discord_thread.py
│   ├── file.py
│   └── backup.py
├── listeners/           # Event handlers
├── preconditions/       # Command checks
├── scheduled/
│   └── nightly_backup.py
└── utils/               # Helper functions
```

## Common Patterns

### Error Handling

-   Use Sentry for error tracking
-   Log errors to Discord bot report channel
-   Provide user-friendly error messages in Discord threads
-   Never expose credentials in error messages

### Discord Thread Updates

```python
# Update thread with progress
await thread.send("🔄 Connecting to MongoDB...")
await thread.send("✅ Data exported (1.2MB)")
await thread.send("📦 Compressed (240KB - 80% reduction)")
await thread.send("☁️ Uploaded to S3")
await thread.send("✅ Backup complete! [Download](url)")
```

### File Management

-   Write backups to `backups/` directory
-   Naming: `nightscout-backup-YYYY-MM-DD-HHMMSS.json.gz`
-   Clean up local files after S3 upload
-   Keep `backups/.gitkeep` (directory is in `.gitignore`)

## Security Considerations

-   Never commit `.env` file (in `.gitignore`)
-   Use environment variables for all secrets
-   S3 URLs should be public but unguessable (UUID in filename)
-   Validate Discord user permissions before backup operations
-   Rate limit backup commands (max 1 per 5 minutes per user)
-   MongoDB connection should be read-only when possible

## Performance Expectations

-   Backup of 100MB MongoDB should complete in <2 minutes
-   Compression should reduce JSON by 70-80% (gzip) or 85-95% (Brotli)
-   S3 upload progress updates every 10%
-   Discord thread updates should be responsive (<1s delay)

## Additional Notes

-   Original TypeScript codebase is on `main` branch (reference for architecture)
-   SonarCloud is configured for code quality tracking
-   Dependabot manages dependency updates targeting `develop`
-   All PRs require passing tests and lint checks
-   Code owners: @dustin-lennon (see `.github/CODEOWNERS`)
