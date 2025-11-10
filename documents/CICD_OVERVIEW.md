# CI/CD Pipeline Overview

## GitHub Actions Workflows

This project uses GitHub Actions for continuous integration and deployment. Here's what happens automatically:

### On Every Pull Request to `python3` or `develop`:

1. **Python Testing** (`.github/workflows/python-testing.yml`)
   - Runs full test suite with pytest
   - Generates coverage report
   - Uploads coverage to Codecov
   - Must pass before PR can be merged

2. **Python Linting** (`.github/workflows/python-linting.yml`)
   - Black format checking
   - Ruff linting
   - mypy type checking
   - Must pass before PR can be merged

3. **Security Scanning**
   - Semgrep (`.github/workflows/semgrep.yml`)
   - CodeQL analysis (`.github/workflows/codeql-analysis.yml`)
   - Identifies security vulnerabilities

### On Push to `main` Branch (Production):

1. **Automated Deployment** (`.github/workflows/deploy-linode.yml`)
   - SSH into Linode server
   - Pull latest code from `main`
   - Install/update dependencies
   - Reload bot with PM2
   - Verify deployment success

**Note**: Deployments only happen when `develop` is merged to `main` via PR.

### Manual Triggers:

- **Deploy to Linode**: Can be triggered manually via GitHub Actions UI
- **Choose Environment**: Select production or staging

## Workflow Files

### 1. Python Testing (`python-testing.yml`)

```yaml
Triggers:
  - Pull requests to develop, main
  - Push to develop, feature/*, bugfix/*, hotfix/*, release/*
  - Manual dispatch

Steps:
  1. Checkout code
  2. Setup Python 3.12
  3. Install Poetry
  4. Cache dependencies
  5. Install project
  6. Run tests with coverage
  7. Upload coverage to Codecov
```

**Mock Credentials**: Uses test credentials if secrets not available, allowing CI to run without real tokens.

### 2. Python Linting (`python-linting.yml`)

```yaml
Triggers:
  - Pull requests to develop, main
  - Push to develop, feature/*, bugfix/*, hotfix/*, release/*
  - Manual dispatch

Steps:
  1. Checkout code
  2. Setup Python 3.12
  3. Install Poetry
  4. Cache dependencies
  5. Run Black (format check)
  6. Run Ruff (lint)
  7. Run mypy (type check)
```

**Note**: mypy errors don't fail the build initially (continue-on-error: true) to allow gradual type coverage improvement.

### 3. Deploy to Linode (`deploy-linode.yml`)

```yaml
Triggers:
  - Push to main (automatic) - Production only
  - Manual dispatch with environment choice
  - Excludes: markdown and docs changes

Steps:
  1. Checkout code
  2. Setup SSH with private key
  3. Connect to Linode via SSH
  4. Pull latest changes from main
  5. Install dependencies with Poetry
  6. Reload bot with PM2
  7. Verify bot is running
  8. Post logs for verification
```

**Required Secrets**:
- `LINODE_SSH_KEY`: Private SSH key for deployment
- `LINODE_HOST`: Server IP or hostname
- `LINODE_USER`: SSH username
- `DEPLOY_PATH`: Installation directory

## Branch Strategy

```
main (Production - Deploys to Linode)
  ↑
development (Python development - CI/Testing only)
  ↑
feature/* (Feature development branches)
```

### Workflow:

1. Create feature branch from `development`
   ```bash
   git checkout develop
   git pull
   git checkout -b feature/my-new-feature
   ```

2. Make changes and commit
   ```bash
   git add .
   git commit -m "feat: add new feature"
   git push origin feature/my-new-feature
   ```

3. Open PR to `develop`
   - CI checks run automatically
   - Tests must pass
   - Linting must pass
   - Security scans must pass
   - Review and approval

4. Merge PR to `develop`
   - Changes are integrated
   - No automatic deployment yet

5. When ready for production, create PR from `develop` to `main`
   - Final review
   - Merge to `main`
   - **Automatic deployment to Linode** 🚀
   - Bot reloads with zero downtime
   - Logs available in GitHub Actions

## Required GitHub Secrets

### For Testing (Optional but Recommended):

| Secret | Description |
|--------|-------------|
| `DISCORD_TOKEN` | Discord bot token for integration tests |
| `DISCORD_CLIENT_ID` | Discord application client ID |
| `BACKUP_CHANNEL_ID` | Channel ID for backup operations |

### For Deployment (Required):

| Secret | Description |
|--------|-------------|
| `LINODE_SSH_KEY` | Private SSH key (Ed25519 recommended) |
| `LINODE_HOST` | Linode server IP (e.g., `123.45.67.89`) |
| `LINODE_USER` | SSH username (e.g., `root` or `ubuntu`) |
| `DEPLOY_PATH` | Bot install path (default: `/opt/nightscout-backup-bot`) |

## Setting Up Secrets

1. Go to repository settings:
   ```
   https://github.com/dustin-lennon/NightScoutMongoBackup/settings/secrets/actions
   ```

2. Click "New repository secret"

3. Add each secret with its value

4. Secrets are encrypted and never exposed in logs

## Deployment Process

### Automatic (Recommended):

```bash
# Develop on develop branch
git checkout develop
git add .
git commit -m "fix: improve error handling"
git push origin develop

# CI runs tests and linting ✅

# When ready for production, merge to main
git checkout main
git pull origin main
git merge develop
git push origin main

# GitHub Actions automatically:
# 1. Deploys to Linode 🚀
# 2. Verifies deployment ✅
```

**Or via Pull Request** (recommended):
```bash
# Push changes to develop
git push origin develop

# Create PR: develop → main
# Review and merge PR
# Deployment triggers automatically on merge
```

### Manual:

1. Go to Actions tab: https://github.com/dustin-lennon/NightScoutMongoBackup/actions
2. Select "Deploy to Linode"
3. Click "Run workflow"
4. Choose environment (production/staging)
5. Click "Run workflow"

## Monitoring Deployments

### GitHub Actions UI:

View real-time deployment progress:
```
https://github.com/dustin-lennon/NightScoutMongoBackup/actions
```

Features:
- ✅ Live log streaming
- ✅ Step-by-step progress
- ✅ Deployment history
- ✅ Success/failure status
- ✅ Re-run failed deployments

### Server Logs:

SSH into Linode and check PM2:
```bash
pm2 logs nightscout-backup-bot --lines 100
pm2 status
```

## Rollback Procedures

### Quick Rollback:

1. Find previous successful deployment in GitHub Actions
2. Get the commit hash
3. Manually trigger deployment with that commit:

```bash
# On Linode server
cd /opt/nightscout-backup-bot
git checkout <previous-commit-hash>
pm2 reload ecosystem.prod.config.js
```

### Automated Rollback:

1. Revert the commit locally:
   ```bash
   git revert HEAD
   git push origin develop
   ```

2. GitHub Actions automatically deploys the reverted version

## Best Practices

### Development:

1. **Always work in feature branches**
   ```bash
   git checkout -b feature/descriptive-name
   ```

2. **Write tests for new features**
   ```bash
   poetry run pytest tests/unit/test_my_feature.py
   ```

3. **Check linting before pushing**
   ```bash
   poetry run black src tests
   poetry run ruff check src tests
   ```

4. **Test locally before pushing**
   ```bash
   poetry run pytest
   poetry run python -m nightscout_backup_bot
   ```

### Deployment:

1. **Review CI checks before merging**
   - All tests passing ✅
   - No linting errors ✅
   - Security scans clean ✅

2. **Monitor deployment logs**
   - Watch GitHub Actions for errors
   - Check PM2 logs after deployment

3. **Verify bot functionality**
   - Test `/ping` command in Discord
   - Check for error messages

4. **Keep deployment small**
   - Deploy frequently with small changes
   - Easier to identify and fix issues

## Troubleshooting

### Deployment Fails: "Permission denied (publickey)"

**Cause**: SSH key not properly configured

**Fix**:
1. Generate new SSH key pair
2. Add public key to Linode `~/.ssh/authorized_keys`
3. Add private key to GitHub Secrets as `LINODE_SSH_KEY`

### Tests Pass Locally But Fail in CI

**Cause**: Environment differences or missing dependencies

**Fix**:
1. Check `poetry.lock` is committed
2. Verify Python version matches (3.12)
3. Check for environment-specific code

### Bot Doesn't Restart After Deployment

**Cause**: PM2 not configured or environment variables missing

**Fix**:
```bash
# SSH into Linode
cd /opt/nightscout-backup-bot

# Check PM2 status
pm2 status

# View errors
pm2 logs nightscout-backup-bot --err --lines 50

# Manually restart
pm2 restart nightscout-backup-bot
```

### Deployment Succeeds But Bot Has Errors

**Cause**: Configuration issue or missing credentials

**Fix**:
```bash
# Check .env file on server
ssh user@linode "cat /opt/nightscout-backup-bot/.env"

# Verify all required variables are set
# Update .env if needed
ssh user@linode "nano /opt/nightscout-backup-bot/.env"

# Restart bot
ssh user@linode "cd /opt/nightscout-backup-bot && pm2 restart nightscout-backup-bot"
```

## Additional Resources

- **Quick Start**: [GITHUB_ACTIONS_QUICKSTART.md](GITHUB_ACTIONS_QUICKSTART.md)
- **Full Deployment Guide**: [GITHUB_ACTIONS_DEPLOYMENT.md](GITHUB_ACTIONS_DEPLOYMENT.md)
- **Manual Deployment**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **Development Guide**: [DEVELOPMENT.md](DEVELOPMENT.md)

## CI/CD Metrics

Current workflow configuration provides:

- **Automated Testing**: ~2-3 minutes per run
- **Deployment Time**: ~1-2 minutes
- **Zero Downtime**: PM2 reload strategy
- **Rollback Time**: <5 minutes

**Total time from push to production**: ~5 minutes ⚡
