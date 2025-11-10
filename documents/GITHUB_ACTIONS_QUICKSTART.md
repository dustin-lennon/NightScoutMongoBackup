# GitHub Actions Deployment Quick Start

## 🚀 5-Minute Setup for Automated Deployment

### Step 1: Prepare Your Linode Server (One Time)

```bash
# SSH into your Linode
ssh user@YOUR_LINODE_IP

# Run the automated setup script
curl -sSL https://raw.githubusercontent.com/dustin-lennon/NightScoutMongoBackup/python3/setup.sh | bash

# Configure environment variables
cd /opt/nightscout-backup-bot
nano .env
# Add your Discord, MongoDB, and AWS credentials

# Start the bot
pm2 start ecosystem.config.js --only nightscout-backup-bot --env production
pm2 save
pm2 startup  # Run the command it outputs
```

### Step 2: Generate SSH Key for GitHub Actions

```bash
# On your LOCAL machine (not the server)
ssh-keygen -t ed25519 -f ~/.ssh/linode_deploy -N ""

# Copy the public key to your Linode
ssh-copy-id -i ~/.ssh/linode_deploy.pub root@YOUR_LINODE_IP

# View the private key (you'll add this to GitHub)
cat ~/.ssh/linode_deploy
```

### Step 3: Add GitHub Secrets

1. Go to: `https://github.com/dustin-lennon/NightScoutMongoBackup/settings/secrets/actions`
2. Click **"New repository secret"**
3. Add these secrets:

| Name | Value | Example |
|------|-------|---------|
| `LINODE_SSH_KEY` | Private key from `~/.ssh/linode_deploy` | (full key content) |
| `LINODE_HOST` | Your Linode IP address | `123.45.67.89` |
| `LINODE_USER` | SSH username (usually `root`) | `root` |
| `DEPLOY_PATH` | Bot installation path | `/opt/nightscout-backup-bot` |

### Step 4: Test Deployment

```bash
# Make a small change on develop branch
echo "# Test change" >> README_PYTHON.md
git add README_PYTHON.md
git commit -m "test: verify CI pipeline"
git push origin develop

# This runs CI checks but does NOT deploy

# When ready to deploy, merge to main
git checkout main
git merge develop
git push origin main

# Now deployment triggers:
# https://github.com/dustin-lennon/NightScoutMongoBackup/actions
```

---

## How It Works

### Automatic Deployment

**Deployments only happen on push to `main` branch**

When you merge `develop` → `main`:
1. ✅ Code checkout
2. ✅ SSH into Linode
3. ✅ Pull latest changes from `main`
4. ✅ Install dependencies
5. ✅ Reload bot with PM2
6. ✅ Verify it's running

**Development on `develop` branch**:
- ✅ Runs tests
- ✅ Runs linting
- ❌ Does NOT deploy

### Manual Deployment

Need to deploy without pushing code?

1. Go to: https://github.com/dustin-lennon/NightScoutMongoBackup/actions
2. Click **"Deploy to Linode"**
3. Click **"Run workflow"**
4. Select environment
5. Click **"Run workflow"**

---

## Common Commands

### View GitHub Actions Logs

```bash
# In your browser:
https://github.com/dustin-lennon/NightScoutMongoBackup/actions
```

### View Server Logs

```bash
# SSH into Linode
ssh root@YOUR_LINODE_IP

# Live logs
pm2 logs nightscout-backup-bot

# Last 100 lines
pm2 logs nightscout-backup-bot --lines 100

# Status
pm2 status
```

### Rollback a Deployment

```bash
# SSH into Linode
ssh root@YOUR_LINODE_IP
cd /opt/nightscout-backup-bot

# View recent commits
git log --oneline -10

# Rollback to previous commit
git checkout HEAD~1

# Restart bot
pm2 reload ecosystem.config.js --only nightscout-backup-bot --env production
```

---

## Troubleshooting

### ❌ Deployment Failed: "Permission denied"

**Fix**: Check your SSH key in GitHub Secrets

```bash
# Test SSH connection
ssh -i ~/.ssh/linode_deploy root@YOUR_LINODE_IP "echo 'Connected!'"

# If fails, re-copy the public key
ssh-copy-id -i ~/.ssh/linode_deploy.pub root@YOUR_LINODE_IP
```

### ❌ Deployment Failed: "pm2 command not found"

**Fix**: Install PM2 on the server

```bash
# SSH into Linode
ssh root@YOUR_LINODE_IP

# Install PM2
npm install -g pm2

# Verify
pm2 --version
```

### ❌ Bot Not Starting After Deployment

**Fix**: Check environment variables

```bash
# SSH into Linode
ssh root@YOUR_LINODE_IP
cd /opt/nightscout-backup-bot

# Check .env file exists
ls -la .env

# View errors
pm2 logs nightscout-backup-bot --err --lines 50
```

### ❌ Deployment Succeeds But Bot Crashes

**Fix**: Missing Python dependencies

```bash
# SSH into Linode
ssh root@YOUR_LINODE_IP
cd /opt/nightscout-backup-bot

# Reinstall dependencies
poetry install --no-interaction --only main

# Restart
pm2 restart nightscout-backup-bot --only nightscout-backup-bot --env production
```

---

## Security Checklist

- [ ] SSH key is Ed25519 (more secure than RSA)
- [ ] Private key is only in GitHub Secrets (not committed)
- [ ] Public key is in Linode `~/.ssh/authorized_keys`
- [ ] `.env` file contains real credentials (not `.env.example`)
- [ ] GitHub branch protection is enabled on `python3`
- [ ] Only trusted users can approve deployments

---

## Next Steps

1. ✅ Set up GitHub Actions deployment (this guide)
2. 📊 Configure monitoring: [DEPLOYMENT.md#monitoring](DEPLOYMENT.md#monitoring)
3. 🔐 Harden security: [DEPLOYMENT.md#security](DEPLOYMENT.md#security)
4. 🚨 Set up alerts: Configure Sentry DSN in `.env`

---

## Full Documentation

- **Complete Setup**: [GITHUB_ACTIONS_DEPLOYMENT.md](GITHUB_ACTIONS_DEPLOYMENT.md)
- **Manual Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Development Guide**: [DEVELOPMENT.md](DEVELOPMENT.md)
- **Python README**: [README_PYTHON.md](README_PYTHON.md)
