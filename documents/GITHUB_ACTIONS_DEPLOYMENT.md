# GitHub Actions Deployment Setup

This guide explains how to set up automated deployment to your Linode server using GitHub Actions.

## Overview

The deployment workflow automatically deploys to Linode when:
- Code is pushed to the `main` branch (production)
- Manual deployment is triggered via GitHub Actions UI
- Pull requests are merged from `develop` to `main`

**Important**: Pushes to `develop` branch run CI tests but do NOT deploy. Only merges to `main` trigger deployment.

## Prerequisites

1. **Linode Server**: Running Ubuntu/Debian with SSH access
2. **GitHub Repository**: This repo with Actions enabled
3. **Server Setup**: Bot installed at `/opt/nightscout-backup-bot` (or your custom path)

## One-Time Setup

### 1. Server Preparation

SSH into your Linode server and set up the deployment directory:

```bash
# Create deployment directory
sudo mkdir -p /opt/nightscout-backup-bot
sudo chown $USER:$USER /opt/nightscout-backup-bot

# Clone the repository
cd /opt/nightscout-backup-bot
git clone https://github.com/dustin-lennon/NightScoutMongoBackup.git .
git checkout main  # Checkout main branch for production

# Install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add Poetry to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc

# Install dependencies
poetry install --no-dev

# Install PM2
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash
source ~/.bashrc
nvm install --lts
npm install -g pm2

# Set up environment variables
cp .env.example .env
nano .env  # Edit with your credentials

# Start the bot
pm2 start ecosystem.config.js --only nightscout-backup-bot --env production
pm2 save
pm2 startup  # Follow the instructions to set up autostart
```

### 2. Generate SSH Key for GitHub Actions

On your **local machine** (not the server):

```bash
# Generate a new SSH key pair
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ~/.ssh/linode_deploy_key -N ""

# Display the private key (you'll add this to GitHub Secrets)
cat ~/.ssh/linode_deploy_key

# Display the public key (you'll add this to your Linode server)
cat ~/.ssh/linode_deploy_key.pub
```

### 3. Add SSH Public Key to Linode Server

SSH into your Linode server and add the public key:

```bash
# On your Linode server
nano ~/.ssh/authorized_keys
# Paste the public key (from linode_deploy_key.pub)
# Save and exit

# Set proper permissions
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 4. Configure GitHub Secrets

Go to your GitHub repository:
- Navigate to **Settings** → **Secrets and variables** → **Actions**
- Click **New repository secret** and add the following:

| Secret Name | Value | Description |
|-------------|-------|-------------|
| `LINODE_SSH_KEY` | Content of `~/.ssh/linode_deploy_key` | Private SSH key for deployment |
| `LINODE_HOST` | Your Linode IP or hostname | e.g., `123.45.67.89` |
| `LINODE_USER` | SSH username | e.g., `ubuntu` or `root` |
| `DEPLOY_PATH` | Deployment directory path | e.g., `/opt/nightscout-backup-bot` |

**Optional Discord/Bot secrets** (for testing workflow):
| Secret Name | Value | Description |
|-------------|-------|-------------|
| `DISCORD_TOKEN` | Your Discord bot token | For running tests in CI |
| `DISCORD_CLIENT_ID` | Your Discord client ID | For running tests in CI |
| `BACKUP_CHANNEL_ID` | Your backup channel ID | For running tests in CI |

### 5. Test SSH Connection

Verify GitHub Actions can connect to your server:

```bash
# On your local machine, test with the deployment key
ssh -i ~/.ssh/linode_deploy_key $LINODE_USER@$LINODE_HOST "echo 'Connection successful!'"
```

## Deployment Workflows

### Automatic Deployment

**Triggered by**: Push to `main` branch (production only)

```bash
# Develop on python3 branch (does NOT deploy)
git checkout python3
git add .
git commit -m "feat: add new feature"
git push origin python3
# → Runs CI tests only

# When ready for production, merge to main
git checkout main
git pull origin main
git merge python3
git push origin main
# → Triggers automatic deployment to Linode
```

**Or use Pull Request** (recommended):
```bash
# Push to python3
git push origin develop

# Create PR on GitHub: python3 → main
# Review and merge
# → Deployment triggers on merge
```

### Manual Deployment

**Triggered by**: GitHub Actions UI

1. Go to your repository on GitHub
2. Click **Actions** tab
3. Select **Deploy to Linode** workflow
4. Click **Run workflow**
5. Choose environment (production/staging)
6. Click **Run workflow**

## Deployment Process

The deployment workflow performs these steps:

1. **Checkout Code**: Pulls latest code from `main` branch
2. **Setup SSH**: Configures SSH connection to Linode
3. **Deploy**:
   - SSH into Linode server
   - Navigate to deployment directory
   - Pull latest changes from `main` branch
   - Install/update dependencies with Poetry
   - Reload application with PM2
4. **Verify**: Checks that the bot is running
5. **Notify**: Reports success/failure

## Monitoring Deployment

### View Logs in GitHub

- Go to **Actions** tab in your repository
- Click on the latest workflow run
- Expand the job steps to see detailed logs

### View Logs on Server

SSH into your Linode and check PM2 logs:

```bash
# View live logs
pm2 logs nightscout-backup-bot

# View last 100 lines
pm2 logs nightscout-backup-bot --lines 100

# View only errors
pm2 logs nightscout-backup-bot --err
```

## Rollback

If a deployment fails, you can quickly rollback:

```bash
# SSH into your Linode server
cd /opt/nightscout-backup-bot

# View commit history
git log --oneline -10

# Rollback to previous commit
git checkout <previous-commit-hash>

# Reinstall dependencies (if needed)
poetry install --no-dev

# Restart the bot
pm2 reload ecosystem.config.js --only nightscout-backup-bot --env production
```

## Troubleshooting

### Deployment Fails: "Permission denied"

**Problem**: SSH key authentication failed

**Solution**:
```bash
# Verify SSH key is correct in GitHub Secrets
# Verify public key is in ~/.ssh/authorized_keys on server
# Check permissions on server
ssh $LINODE_USER@$LINODE_HOST "ls -la ~/.ssh"
```

### Deployment Fails: "pm2 command not found"

**Problem**: PM2 not installed or not in PATH

**Solution**:
```bash
# SSH into server and install PM2
npm install -g pm2

# Or add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Deployment Fails: "poetry command not found"

**Problem**: Poetry not installed or not in PATH

**Solution**:
```bash
# SSH into server and install Poetry
curl -sSL https://install.python-poetry.org | python3 -

# Add to PATH
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### Bot Doesn't Start After Deployment

**Problem**: Missing environment variables or configuration

**Solution**:
```bash
# SSH into server
cd /opt/nightscout-backup-bot

# Check environment file exists
ls -la .env

# View PM2 logs for errors
pm2 logs nightscout-backup-bot --err --lines 50

# Manually test startup
poetry run python -m nightscout_backup_bot
```

## Security Best Practices

1. **Use Dedicated Deploy Key**: Don't use your personal SSH key
2. **Least Privilege**: Deploy user should only have access to deployment directory
3. **Rotate Keys**: Periodically generate new SSH keys
4. **Monitor Logs**: Check GitHub Actions logs for unauthorized deployments
5. **Protected Branch**: Enable branch protection on `python3` branch
6. **Review PRs**: Require reviews before merging to deployment branch

## Environment-Specific Deployments

To deploy to different environments (staging/production):

1. Create environment-specific directories:
   ```bash
   /opt/nightscout-backup-bot-staging
   /opt/nightscout-backup-bot-production
   ```

2. Add environment-specific secrets in GitHub:
   - `STAGING_LINODE_HOST`
   - `STAGING_DEPLOY_PATH`
   - `PRODUCTION_LINODE_HOST`
   - `PRODUCTION_DEPLOY_PATH`

3. Update the workflow to use environment-specific secrets

## Additional Resources

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [SSH Key Authentication](https://docs.github.com/en/authentication/connecting-to-github-with-ssh)
- [PM2 Documentation](https://pm2.keymetrics.io/docs/usage/quick-start/)
- [Poetry Documentation](https://python-poetry.org/docs/)
