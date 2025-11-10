# Linode Deployment Quick Reference

## 🚀 Quick Start (5 Minutes)

### On Your Local Machine:

```bash
# 1. Push your code to GitHub
git add .
git commit -m "Ready for deployment"
git push origin python3
```

### On Your Linode Server:

```bash
# 2. SSH to server
ssh user@your-linode-ip

# 3. Run the automated setup (copy-paste this entire block)
curl -fsSL https://deb.nodesource.com/setup_20.x | bash - && \
sudo apt update && sudo apt install -y python3.12 python3-pip git nodejs && \
npm install -g pm2

# 4. Install Poetry
curl -sSL https://install.python-poetry.org | python3 - && \
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc && \
source ~/.bashrc

# 5. Clone and deploy
git clone https://github.com/dustin-lennon/NightScoutMongoBackup.git && \
cd NightScoutMongoBackup && \
git checkout python3 && \
npx dotenv-vault@latest pull production

# 6. Edit .env with Discord/MongoDB credentials (if necessary)
nano .env

# 7. Run deployment script
./deploy_linode.sh
# Choose: 1 (PM2)

# 8. Done! Check status
pm2 status
pm2 logs
```

---

## 📋 Essential Commands

### PM2 Management

```bash
# Status
pm2 status

# Logs (live)
pm2 logs

# Restart
pm2 restart nightscout-backup-bot-prod

# Stop
pm2 stop nightscout-backup-bot-prod

# Monitoring dashboard
pm2 monit
```

### Updates

```bash
cd ~/NightScoutMongoBackup
git pull origin python3
poetry install --only main
pm2 restart nightscout-backup-bot-prod
```

### Troubleshooting

```bash
# Check logs
pm2 logs --lines 100

# Check disk space
df -h

# Test config
poetry run python test_startup.py

# Check bot process
pm2 status
ps aux | grep python
```

---

## 🔑 Required Environment Variables

**Minimum .env configuration:**

```bash
# Discord Bot Configuration
DISCORD_TOKEN=your_bot_token_from_discord_developer_portal
DISCORD_CLIENT_ID=your_application_id
DISCORD_PUBLIC_KEY=
BACKUP_CHANNEL_ID=your_channel_id_right_click_copy_id
BOT_REPORT_CHANNEL_ID=
BOT_OWNER_IDS=

# Environment & Monitoring
APP_ENV=production
SENTRY_DSN=
SENTRY_AUTH_TOKEN=

# MongoDB Atlas Configuration
MONGO_HOST=your-cluster.mongodb.net
MONGO_USERNAME=your_mongodb_username
MONGO_PASSWORD=your_mongodb_password
MONGO_DB=nightscout
MONGO_API_KEY=
MONGO_DB_MAX_SIZE=

# AWS S3 Configuration
AWS_ACCESS_KEY_ID=[REDACTED]
AWS_SECRET_ACCESS_KEY=[REDACTED]
AWS_REGION=us-east-2
S3_BACKUP_BUCKET=[REDACTED]

# Backup Settings
ENABLE_NIGHTLY_BACKUP=true
BACKUP_HOUR=2
BACKUP_MINUTE=0
COMPRESSION_METHOD=gzip

# PM2 Process Management (optional)
NIGHTSCOUT_PM2_APP_NAME=dexcom
NIGHTSCOUT_PM2_SSH_USER=
NIGHTSCOUT_PM2_SSH_HOST=
NIGHTSCOUT_PM2_SSH_KEY_PATH=
NIGHTSCOUT_PM2_CMD=npx pm2
BOT_PM2_APP_NAME=nightscout-backup-bot-prod
BOT_PM2_MODE=local
BOT_PM2_CMD=npx pm2
BOT_PM2_SSH_USER=
BOT_PM2_SSH_HOST=
BOT_PM2_SSH_KEY_PATH=
```

---

## 🔐 Get Discord Bot Token

1. Go to https://discord.com/developers/applications
2. Click your application (or create new)
3. Go to "Bot" section
4. Click "Reset Token" → Copy token
5. Get Client ID from "General Information" → Application ID
6. Get Channel ID: Right-click channel in Discord → Copy ID
7. Enable "Developer Mode" in Discord User Settings → Advanced

---

## 📊 Monitoring

### Check Bot Health

```bash
# PM2 dashboard
pm2 monit

# System resources
htop
df -h

# Last 50 log lines
pm2 logs --lines 50

# Check Discord connection in logs
pm2 logs | grep "Bot is ready"
```

### Monitor Backups

```bash
# Check S3 bucket
aws s3 ls s3://dexcom-mongo-backup/backups/

# Check local backups directory
ls -lh ~/NightScoutMongoBackup/backups/

# View backup logs
pm2 logs | grep -i backup
```

---

## ⚡ Performance Tips

### For Large Databases (>500MB)

```bash
# Increase memory limit in ecosystem.config.js
max_memory_restart: '1000M'

# Use Brotli compression (better compression)
# In .env:
COMPRESSION_METHOD=brotli
```

### Optimize Linode

```bash
# Enable swap (for 1GB Linode)
sudo fallocate -l 2G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

---

## 🆘 Common Issues & Fixes

### Bot Won't Start

```bash
# Verify .env exists
ls -la .env

# Check Poetry environment
poetry env info
```

### Discord Connection Fails

```bash
# Invalid token error
# → Get new token from Discord Developer Portal

# Missing intents error
# → Enable "Message Content Intent" in Discord Developer Portal → Bot

# Check logs
pm2 logs | grep -i discord
```

### MongoDB Connection Fails

```bash
# Add Linode IP to MongoDB Atlas whitelist
# Atlas → Network Access → Add IP Address → Add 0.0.0.0/0 (or your Linode IP)

# Test connection
poetry run python -c "from nightscout_backup_bot.services import MongoService; import asyncio; asyncio.run(MongoService().connect())"
```

### S3 Upload Fails

```bash
# Check AWS credentials
aws configure list

# Test S3 access
aws s3 ls s3://dexcom-mongo-backup/

# Check bucket permissions (must allow public-read on uploads)
```

---

## 📱 Discord Commands

Once deployed:

- `/ping` - Check if bot is online
- `/backup` - Trigger manual backup (creates thread with progress)
- `/querydb` - Database statistics (owner only)

---

## 🔄 Update Workflow

```bash
# Local: Make changes and push
git add .
git commit -m "Update feature"
git push origin python3

# Linode: Pull and restart
ssh nightscout-bot@your-linode-ip
cd ~/NightScoutMongoBackup
git pull origin python3
poetry install --only main
pm2 restart nightscout-backup-bot-prod
pm2 logs
```

---

## 💾 Backup & Recovery

```bash
# Backup configuration
tar -czf ~/bot-config-$(date +%Y%m%d).tar.gz .env logs/

# Download to local
scp nightscout-bot@your-linode-ip:~/bot-config-*.tar.gz .

# Restore on new server
scp bot-config-*.tar.gz nightscout-bot@new-linode-ip:~
ssh nightscout-bot@new-linode-ip
tar -xzf bot-config-*.tar.gz
# Re-run deployment
```

---

## 📞 Support

- Full Guide: `DEPLOYMENT.md`
- Development: `DEVELOPMENT.md`
- User Guide: `README_PYTHON.md`
- GitHub Issues: https://github.com/dustin-lennon/NightScoutMongoBackup/issues
