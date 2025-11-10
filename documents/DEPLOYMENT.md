# Linode Deployment Guide for NightScout Backup Bot

## Overview

This guide covers deploying the Python NightScout Backup Bot to a Linode server. 

**🚀 RECOMMENDED: Use GitHub Actions for automated deployment** - See [GITHUB_ACTIONS_DEPLOYMENT.md](GITHUB_ACTIONS_DEPLOYMENT.md) for CI/CD setup.

This document covers manual deployment methods for initial setup or troubleshooting.

## Prerequisites

- Linode server (Ubuntu 20.04+ or Debian 11+ recommended)
- SSH access to your Linode
- sudo privileges
- Domain name (optional, for easier access)

## Deployment Methods

### Method 1: GitHub Actions (Recommended)

**✅ Best for production deployments**

Automated CI/CD pipeline that deploys on every push to `python3` branch.

**Features:**
- ✅ Automated testing before deployment
- ✅ One-click rollback
- ✅ Deployment history and logs
- ✅ Zero-downtime deployments
- ✅ Security scanning and code quality checks

**📖 Full Guide**: [GITHUB_ACTIONS_DEPLOYMENT.md](GITHUB_ACTIONS_DEPLOYMENT.md)

### Method 2: Manual PM2 Deployment

PM2 is a production process manager for Node.js applications, but works great with Python too.

**Pros:**
- ✅ Automatic restarts on crashes
- ✅ Startup on system boot
- ✅ Log management
- ✅ Zero-downtime reloads
- ✅ Monitoring dashboard

---

## Method 2: Manual PM2 Deployment

Use this method for initial server setup or when not using GitHub Actions.

### 1. Initial Server Setup

```bash
# SSH into your Linode
ssh root@your-linode-ip

# Update system
apt update && apt upgrade -y

# Install required packages
apt install -y python3.12 python3.12-venv python3-pip git curl

# Install Node.js (for PM2)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt install -y nodejs

# Install PM2 globally
npm install -g pm2

# Create dedicated user (security best practice)
adduser --disabled-password --gecos "" nightscout-bot
usermod -aG sudo nightscout-bot
```

### 2. Install Poetry

```bash
# Switch to bot user
su - nightscout-bot

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Verify
poetry --version
```

### 3. Clone and Setup Repository

```bash
# Clone repository
cd ~
git clone https://github.com/dustin-lennon/NightScoutMongoBackup.git
cd NightScoutMongoBackup

# Checkout Python branch
git checkout python3

# Install dependencies
poetry install --only main  # Skip dev dependencies for production
```

### 4. Configure Environment

```bash
# Copy your .env.me or create .env
nano .env

# Add all required credentials:
# - Discord token & IDs
# - MongoDB credentials
# - AWS S3 credentials
# - Backup settings
```

### 5. Update PM2 Configuration

```bash
# Edit ecosystem.config.js
nano ecosystem.prod.config.js
```

Example `ecosystem.prod.config.js` for production:

```javascript
const path = require('path');

module.exports = {
  apps: [
    {
      name: 'nightscout-backup-bot',
      script: 'poetry',
      args: 'run nightscout-backup-bot',
      cwd: path.resolve(__dirname),
      exec_mode: 'fork',
      interpreter: 'none',
      instances: 1,
      autorestart: true,
	  watch: false,
      max_memory_restart: '500M',
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      env: {
        NODE_ENV: 'production',
        // Add other development environment variables here
      }
    }
  ]
};
```

__Interpreter is set to none on Linux machines and how poetry is installed__

Example `ecosystem.dev.config.js` for development:

```
const path = require('path');

module.exports = {
  apps: [
    {
      name: 'nightscout-backup-bot',
      script: 'poetry',
      args: 'run nightscout-backup-bot',
      cwd: path.resolve(__dirname),
      exec_mode: 'fork',
      interpreter: '/bin/sh',
      watch: ['src/'],
      instances: 1,
      autorestart: true,
      max_memory_restart: '500M',
      error_file: './logs/error.log',
      out_file: './logs/output.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
      merge_logs: true,
      env: {
        NODE_ENV: 'development',
        // Add other development environment variables here
      }
    }
  ]
};
```

__Interpreter is set to `/bin/sh` due to how Poetry is installed on macOS__

### 6. Create Logs Directory

```bash
mkdir -p ~/NightScoutMongoBackup/logs
```

### 7. Start the Bot

```bash
# Start with PM2
pm2 start ecosystem.prod.config.js

# Check status
pm2 status

# View logs
pm2 logs nightscout-backup-bot

# Monitor in real-time
pm2 monit
```

### 8. Configure Auto-Start on Boot

```bash
# Generate startup script
pm2 startup systemd -u user --hp /path/to/nightscout-bot

# Run the command it outputs (as root)
exit  # Exit to root
# Run the command PM2 gave you

# Switch back to bot user
su - nightscout-bot
cd ~/NightScoutMongoBackup

# Save PM2 configuration
pm2 save
```

### 9. Verify Deployment

```bash
# Check bot is running
pm2 status

# Check logs for errors
pm2 logs --lines 50

# Test restart
pm2 restart nightscout-backup-bot

# Reboot server and verify auto-start
sudo reboot
# After reboot, SSH back in and check:
pm2 status
```

---

## Deployment Workflow (Updates)

### For PM2:

```bash
# SSH to server
ssh nightscout-bot@your-linode-ip

cd ~/NightScoutMongoBackup

# Pull latest changes
git pull origin python3

# Install any new dependencies
poetry install --only main

# Restart bot (zero downtime)
pm2 reload nightscout-backup-bot

# Or full restart
pm2 restart nightscout-backup-bot

# Check logs
pm2 logs --lines 50
```

---

## Monitoring & Maintenance

### PM2 Monitoring

```bash
# Real-time monitoring
pm2 monit

# Memory/CPU usage
pm2 list

# Detailed info
pm2 show nightscout-backup-bot

# Logs
pm2 logs
pm2 logs --lines 200
pm2 flush  # Clear logs
```

### Log Rotation

For PM2 (install PM2 log rotate):
```bash
pm2 install pm2-logrotate
pm2 set pm2-logrotate:max_size 10M
pm2 set pm2-logrotate:retain 7
```

---

## Security Considerations

### Firewall Setup

```bash
# Install UFW if not present
sudo apt install ufw

# Allow SSH
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

### Secure Credentials

```bash
# Restrict .env file permissions
chmod 600 ~/.env

# Never commit .env to git
# (already in .gitignore)

# Use dotenv-vault for team sharing
# (credentials encrypted, safe to commit .env.me)
```

### Regular Updates

```bash
# Update system packages weekly
sudo apt update && sudo apt upgrade -y

# Update Python dependencies monthly
poetry update

# Monitor security advisories
poetry show --outdated
```

---

## Troubleshooting

### Bot Won't Start

```bash
# Check logs
pm2 logs  # or sudo journalctl -u nightscout-backup-bot

# Common issues:
# 1. Missing environment variables
#    - Check .env file exists and has all required values
# 2. Wrong Python version
#    - poetry env info
# 3. Port conflicts
#    - Bot shouldn't need ports, but check if Discord connects
# 4. Permission issues
#    - ls -la logs/ backups/
```

### High Memory Usage

```bash
# Check current usage
pm2 list

# Adjust max_memory_restart in ecosystem.config.js
# Default: 500M (adjust based on your backup size)
```

### Bot Crashes on Backup

```bash
# Check disk space
df -h

# Check logs for errors
pm2 logs --err --lines 100

# Common causes:
# - Out of disk space (backups/ directory)
# - MongoDB connection timeout
# - S3 upload failures
```

### Can't Connect to MongoDB

```bash
# Test connection manually
poetry run python -c "from nightscout_backup_bot.services import MongoService; import asyncio; asyncio.run(MongoService().connect())"

# Check MongoDB Atlas IP whitelist
# Add Linode IP: 0.0.0.0/0 (or specific IP)
```

---

## Backup & Recovery

### Backup Bot Configuration

```bash
# Backup .env and logs
tar -czf ~/nightscout-bot-backup-$(date +%Y%m%d).tar.gz \
  ~/.env \
  ~/NightScoutMongoBackup/logs/ \
  ~/NightScoutMongoBackup/.git/config

# Copy to local machine
scp nightscout-bot@your-linode-ip:~/nightscout-bot-backup-*.tar.gz .
```

### Disaster Recovery

```bash
# On new server:
# 1. Setup server (step 1)
# 2. Install Poetry (step 2)
# 3. Clone repository (step 3)
# 4. Restore .env from backup
# 5. Setup PM2/systemd (steps 5-8)
```

---

## Performance Tuning

### For Large Databases (>1GB)

```bash
# Increase memory limit in ecosystem.config.js
max_memory_restart: '1000M'  # or '2G'

# Enable compression to reduce S3 upload time
# In .env:
COMPRESSION_METHOD=brotli  # Better compression for large files
```

---

## Recommended Linode Plan

**Minimum:** Nanode 1GB ($5/month)
- 1 CPU Core
- 1 GB RAM
- 25 GB Storage
- Good for: Small databases (<100MB)

**Recommended:** Linode 2GB ($12/month)
- 1 CPU Core
- 2 GB RAM
- 50 GB Storage
- Good for: Medium databases (100MB-500MB)

**For Large Databases:** Linode 4GB ($24/month)
- 2 CPU Cores
- 4 GB RAM
- 80 GB Storage
- Good for: Large databases (>500MB)

---

## Next Steps

1. ✅ Choose deployment method (PM2 or systemd)
2. ✅ Setup Linode server
3. ✅ Install dependencies
4. ✅ Configure credentials
5. ✅ Deploy bot
6. ✅ Configure monitoring
7. ✅ Test backup manually with `/backup` command
8. ✅ Verify nightly backups work

For additional help, see:
- `README_PYTHON.md` - General documentation
- `DEVELOPMENT.md` - Development guide
- GitHub Issues - Report problems
