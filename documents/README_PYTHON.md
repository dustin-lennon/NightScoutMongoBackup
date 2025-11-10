# NightScout MongoDB Backup Bot - Python Edition

[![Python 3.12+](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Ruff](https://img.shields.io/badge/linter-ruff-red.svg)](https://github.com/astral-sh/ruff)

A production-ready Discord bot that provides automated and manual backup functionality for NightScout MongoDB databases with AWS S3 storage.

## Features

- 🤖 **Discord Bot Integration**: Slash commands for easy backup management
- 🔄 **Automated Nightly Backups**: Configurable scheduled backups
- 📦 **Efficient Compression**: Gzip (default) or Brotli compression with 70-95% size reduction
- ☁️ **S3 Storage**: Automatic upload to AWS S3 with 7-day retention
- 🧵 **Real-time Progress**: Discord threads with live progress updates
- 🔒 **Secure**: Environment-based configuration, rate limiting, permission checks
- ✅ **Tested**: >85% code coverage with unit and integration tests

## Architecture

Built with a service-oriented architecture:

- **MongoService**: MongoDB Atlas connection and data export
- **CompressionService**: Gzip/Brotli compression with native Python libraries
- **S3Service**: AWS S3 upload with public URL generation
- **DiscordThreadService**: Discord thread creation and progress updates
- **FileService**: Local backup file management
- **BackupService**: Orchestrates the complete backup workflow

## Prerequisites

- Python 3.12 or higher
- Poetry (recommended) or pip
- MongoDB Atlas database
- AWS S3 bucket
- Discord Bot with appropriate permissions

## Installation

### Option 1: Using Poetry (Recommended)

```bash
# Install Poetry if not already installed
curl -sSL https://install.python-poetry.org | python3 -

# Clone repository
git clone https://github.com/dustin-lennon/NightScoutMongoBackup.git
cd NightScoutMongoBackup

# Checkout Python branch
git checkout python3

# Install dependencies
poetry install

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

### Option 2: Using pip

```bash
# Clone repository
git clone https://github.com/dustin-lennon/NightScoutMongoBackup.git
cd NightScoutMongoBackup

# Checkout Python branch
git checkout python3

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment template
cp .env.example .env
# Edit .env with your credentials
```

## Configuration

### Option 1: Using .env file (Traditional)

Edit `.env` file with your credentials:

```bash
# =================================================================
# Discord Bot Configuration
# =================================================================
DISCORD_TOKEN=your_discord_bot_token
DISCORD_CLIENT_ID=your_client_id
DISCORD_PUBLIC_KEY=
BACKUP_CHANNEL_ID=channel_id_for_backups
BOT_REPORT_CHANNEL_ID=
BOT_OWNER_IDS=comma,separated,user,ids

# =================================================================
# Environment & Monitoring
# =================================================================
# Environment: "development" or "production"
APP_ENV=development
SENTRY_DSN=your_sentry_dsn
SENTRY_AUTH_TOKEN=your_sentry_auth_token

# =================================================================
# MongoDB Atlas Configuration
# =================================================================
MONGO_HOST=your-cluster.mongodb.net
MONGO_USERNAME=your_username
MONGO_PASSWORD=your_password
MONGO_DB=your_database
MONGO_API_KEY=your_api_key
# Maximum database size in MB (optional, used for capacity warnings)
MONGO_DB_MAX_SIZE=

# =================================================================
# AWS S3 Configuration for Backups
# =================================================================
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
AWS_REGION=us-east-1
S3_BACKUP_BUCKET=your-backup-bucket

# =================================================================
# Backup Job Configuration
# =================================================================
# Enable or disable nightly backups (default: true)
ENABLE_NIGHTLY_BACKUP=true
# Backup schedule (24-hour format, UTC)
BACKUP_HOUR=2
BACKUP_MINUTE=0
# Compression method: 'gzip' (recommended) or 'brotli' (better compression, slightly slower)
COMPRESSION_METHOD=gzip

# =================================================================
# PM2 Process Management Configuration
# =================================================================

# -----------------------------------------------------------------
# NightScout Website (Dexcom) - Managed via SSH
# -----------------------------------------------------------------
# PM2 app name for the NightScout site on the remote server
NIGHTSCOUT_PM2_APP_NAME=dexcom
# SSH connection details for the server hosting the NightScout site
NIGHTSCOUT_PM2_SSH_USER=
NIGHTSCOUT_PM2_SSH_HOST=
# Optional: Path to the specific SSH private key for this connection
NIGHTSCOUT_PM2_SSH_KEY_PATH=
# PM2 command to use on the remote server (e.g., 'pm2', 'npx pm2', or a wrapper script)
NIGHTSCOUT_PM2_CMD=npx pm2

# -----------------------------------------------------------------
# Discord Bot - Managed locally in dev, can be SSH in prod
# -----------------------------------------------------------------
# PM2 app name for the bot itself.
BOT_PM2_APP_NAME=nightscout-backup-bot
# Execution mode for bot commands: "local" or "ssh"
# - "local": Commands run on the machine where the bot is running (for dev)
# - "ssh": Commands are sent to a remote server (for managing prod bot from dev)
BOT_PM2_MODE=local
# PM2 command to use for the bot (e.g., 'pm2', 'npx pm2')
BOT_PM2_CMD=npx pm2

# --- SSH settings for when BOT_PM2_MODE is "ssh" ---
# SSH connection details for the server hosting the production bot
BOT_PM2_SSH_USER=
BOT_PM2_SSH_HOST=
# Optional: Path to the specific SSH private key for this connection
BOT_PM2_SSH_KEY_PATH=
```

### Option 2: Using dotenv-vault (Secure Encrypted Credentials)

The bot supports [dotenv.org](https://dotenv.org) encrypted vaults. If you have a `.env.me` file:

Run `npx --yes dotenv-vault@1.24.0 pull --yes` to pull a stored .env file (default is development env)

```bash
# Then run normally
poetry run python -m nightscout_backup_bot
```

**Benefits of dotenv-vault:**
- ✅ Encrypted credentials (safe to commit `.env.me`)
- ✅ Team sharing with different access levels
- ✅ Environment-specific credentials (dev/staging/prod)
- ✅ Audit logs of credential access

## Deployment

### Production Deployment (Recommended)

**🚀 GitHub Actions - Automated CI/CD**

Deployment is triggered when merging to `main` branch:

1. **Quick Start**: [GITHUB_ACTIONS_QUICKSTART.md](GITHUB_ACTIONS_QUICKSTART.md) - 5-minute setup
2. **Full Guide**: [GITHUB_ACTIONS_DEPLOYMENT.md](GITHUB_ACTIONS_DEPLOYMENT.md) - Complete documentation

**Workflow:**
- Develop on `python3` branch → CI tests run
- Merge `python3` → `main` → Automatic deployment
- Zero-downtime updates with PM2

**Features:**
- ✅ Automated testing before deployment
- ✅ One-click rollback
- ✅ Deployment history
- ✅ Production-only deployments

### Alternative Deployment Methods

**Manual Deployment to Linode**

For manual deployment or troubleshooting, see:
- [DEPLOYMENT.md](DEPLOYMENT.md) - PM2 and systemd setup guides
- [LINODE_QUICKSTART.md](LINODE_QUICKSTART.md) - Quick reference

## Usage

### Running the Bot Locally

```bash
# Using Poetry
poetry run python -m nightscout_backup_bot
```

### Discord Commands

- `/ping` - Check if bot is responsive (all users)
- `/backup` - Create manual backup (backup channel only, rate limited)
- `/querydb` - Query database statistics (bot owners only)

### Development

```bash
# Run tests
poetry run pytest

# Run tests with coverage
poetry run pytest --cov=src --cov-report=html

# Format code
poetry run black src tests

# Lint code
poetry run ruff check src tests

# Type check
poetry run mypy src
```

## Backup Workflow

1. Command triggered (slash command or scheduled)
2. Create Discord thread for progress tracking
3. Connect to MongoDB Atlas and export data to JSON
4. Compress JSON using configured method (gzip/brotli)
5. Upload compressed file to S3 bucket
6. Generate public download link (valid for 7 days)
7. Post completion message to Discord thread
8. Clean up local files

## Compression Methods

### Gzip (Default - Recommended)
- **Compression**: 70-80% size reduction
- **Speed**: Fast compression/decompression
- **Compatibility**: Universal cross-platform support
- **Use case**: Balanced performance and compression

### Brotli (Alternative)
- **Compression**: 85-95% size reduction
- **Speed**: Slightly slower but better compression
- **Compatibility**: Modern cross-platform support
- **Use case**: Maximum compression for slower networks

Set via `COMPRESSION_METHOD` environment variable.

## Production Deployment

### Using PM2 (Linode/VPS)

```bash
# Install PM2 globally
npm install -g pm2

# Update ecosystem.config.js with your path
# Start bot
pm2 start ecosystem.config.js --env production

# Save PM2 configuration
pm2 save

# Setup PM2 to start on boot
pm2 startup
```

## Testing

The project includes comprehensive test coverage:

```bash
# Run all tests
poetry run pytest

# Run specific test file
poetry run pytest tests/unit/test_mongo_service.py

# Run with coverage report
poetry run pytest --cov=src --cov-report=term-missing

# Run integration tests (requires AWS credentials)
export AWS_ACCESS_KEY_ID=your_key
export AWS_SECRET_ACCESS_KEY=your_secret
poetry run pytest tests/integration/
```

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

## Troubleshooting

### Import Errors
```bash
# Ensure you're in the virtual environment
poetry shell
# Or
source venv/bin/activate
```

### MongoDB Connection Issues
- Verify MongoDB Atlas IP whitelist includes your server
- Check username/password are correct
- Ensure connection string format is correct

### S3 Upload Failures
- Verify AWS credentials have S3 write permissions
- Check bucket name and region are correct
- Ensure bucket has appropriate CORS/public access settings

### Discord Bot Not Responding
- Verify bot token is correct
- Check bot has appropriate permissions in Discord server
- Ensure bot is invited to the correct guild/channel

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or contributions, please open an issue on GitHub.
