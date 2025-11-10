#!/bin/bash
# Automated deployment script for Linode
# Run this on your Linode server as the nightscout-bot user
# Usage: ./scripts/deploy_linode.sh

set -e

echo "=========================================="
echo "NightScout Backup Bot - Linode Deployment"
echo "=========================================="
echo ""

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo -e "${RED}❌ Please do not run as root${NC}"
    echo "Run as: ./scripts/deploy_linode.sh (from project root)"
    exit 1
fi

# Check if Poetry is installed
if ! command -v poetry &> /dev/null; then
    echo -e "${RED}❌ Poetry not found${NC}"
    echo "Install with: curl -sSL https://install.python-poetry.org | python3 -"
    exit 1
fi

# Check if PM2 is installed (optional, warn only)
if ! command -v pm2 &> /dev/null; then
    echo -e "${YELLOW}⚠️  PM2 not found (optional)${NC}"
    echo "For PM2 deployment: sudo npm install -g pm2"
fi

echo -e "${GREEN}✅ Prerequisites check passed${NC}"
echo ""

echo "Using PM2 deployment"

# Get repository path
REPO_PATH=$(cd "$(dirname "$0")/.." && pwd)
echo ""
echo "Repository path: $REPO_PATH"

# Check if .env exists
if [ ! -f "$REPO_PATH/.env" ]; then
    echo -e "${YELLOW}⚠️  .env file not found${NC}"
    if [ -f "$REPO_PATH/.env.example" ]; then
        read -p "Copy .env.example to .env? (y/n): " CREATE_ENV
        if [ "$CREATE_ENV" = "y" ]; then
            cp "$REPO_PATH/.env.example" "$REPO_PATH/.env"
            echo -e "${GREEN}✅ Created .env${NC}"
            echo -e "${YELLOW}⚠️  Please edit .env with your credentials${NC}"
            exit 0
        fi
    fi
    echo -e "${RED}❌ .env file required${NC}"
    exit 1
fi

# Install dependencies
echo ""
echo "Installing dependencies..."
cd "$REPO_PATH"
poetry install --only main
echo -e "${GREEN}✅ Dependencies installed${NC}"

# Create logs and backups directories
mkdir -p "$REPO_PATH/logs" "$REPO_PATH/backups"
echo -e "${GREEN}✅ Created logs and backups directories${NC}"

# Test configuration
echo ""
echo "Testing configuration..."
if poetry run python -c "from nightscout_backup_bot.config import get_settings; get_settings()" 2>/dev/null; then
    echo -e "${GREEN}✅ Configuration valid${NC}"
else
    echo -e "${RED}❌ Configuration error${NC}"
    echo "Please check your .env file"
    exit 1
fi

    # PM2 Deployment
    echo ""
    echo "=========================================="
    echo "PM2 Deployment"
    echo "=========================================="

    if ! command -v pm2 &> /dev/null; then
        echo -e "${RED}❌ PM2 not installed${NC}"
        echo "Install with: sudo npm install -g pm2"
        exit 1
    fi

    # Update ecosystem.prod.config.js with current path
    if [ -f "$REPO_PATH/ecosystem.prod.config.js" ]; then
        # Create backup
        cp "$REPO_PATH/ecosystem.prod.config.js" "$REPO_PATH/ecosystem.prod.config.js.bak"

        # Update path
        sed -i.tmp "s|cwd: '.*'|cwd: '$REPO_PATH'|g" "$REPO_PATH/ecosystem.prod.config.js"
        rm -f "$REPO_PATH/ecosystem.prod.config.js.tmp"

        echo -e "${GREEN}✅ Updated ecosystem.prod.config.js${NC}"
    else
        echo -e "${RED}❌ ecosystem.prod.config.js not found${NC}"
        exit 1
    fi

    # Start with PM2
    echo ""
    echo "Starting bot with PM2..."
    pm2 delete nightscout-backup-bot 2>/dev/null || true
    pm2 start "$REPO_PATH/ecosystem.prod.config.js"

    echo ""
    echo -e "${GREEN}✅ Bot started with PM2${NC}"
    echo ""
    echo "Useful commands:"
    echo "  pm2 status                        - Check status"
    echo "  pm2 logs                          - View logs"
    echo "  pm2 restart nightscout-backup-bot - Restart"
    echo "  pm2 stop nightscout-backup-bot    - Stop"
    echo ""
    echo "To enable auto-start on boot:"
    echo "  pm2 startup systemd -u $USER --hp $HOME"
    echo "  (run the command it outputs as root)"
    echo "  pm2 save"


echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo ""
echo "Check logs to verify bot is running correctly."
echo "Test backup with Discord command: /backup"
echo ""
