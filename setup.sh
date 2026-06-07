#!/bin/bash

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo "=== VPN Stack Setup ==="

# Check Docker
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Installing...${NC}"
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker $USER
    echo -e "${YELLOW}Please log out and back in, then run this script again${NC}"
    exit 1
fi

if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Installing...${NC}"
    sudo apt update && sudo apt install -y docker-compose-plugin
fi

echo -e "${GREEN}✓ Docker is ready${NC}"

# Interactive .env creation
if [ ! -f .env ]; then
    echo -e "${YELLOW}Creating .env file...${NC}"
    
    read -p "Server IP address: " WG_HOST
    read -sp "Web UI password: " WG_EASY_PASSWORD
    echo
    read -p "WireGuard port [51820]: " WG_PORT
    WG_PORT=${WG_PORT:-51820}
    read -p "Xray port [443]: " XRAY_PORT
    XRAY_PORT=${XRAY_PORT:-443}
    read -p "Telegram bot token (press Enter to skip): " BOT_TOKEN
    read -p "Telegram username (without @): " ALLOWED_USERNAMES
    
    cat > .env << ENV_EOF
# Server configuration
WG_HOST=$WG_HOST
WG_EASY_PASSWORD=$WG_EASY_PASSWORD
WG_PORT=$WG_PORT
XRAY_PORT=$XRAY_PORT

# Telegram bot (optional)
BOT_TOKEN=$BOT_TOKEN
ALLOWED_USERNAMES=$ALLOWED_USERNAMES
ENV_EOF
    echo -e "${GREEN}✓ .env created${NC}"
else
    echo -e "${YELLOW}.env already exists, using existing values${NC}"
    source .env
fi

# Generate Xray keys
echo -e "${YELLOW}Generating Xray keys...${NC}"
PRIVATE_KEY=$(docker run --rm teddysun/xray:latest xray x25519 | grep PrivateKey | awk '{print $2}')
PUBLIC_KEY=$(docker run --rm teddysun/xray:latest xray x25519 | grep "Password (PublicKey)" | awk '{print $3}')
UUID=$(docker run --rm teddysun/xray:latest xray uuid)
SHORT_ID=${UUID:0:8}

# Create Xray config from template
if [ -f xray-config/config.template.json ]; then
    sed "s/YOUR_UUID/$UUID/g; s/YOUR_PRIVATE_KEY/$PRIVATE_KEY/g; s/YOUR_PUBLIC_KEY/$PUBLIC_KEY/g; s/YOUR_SHORT_ID/$SHORT_ID/g" \
        xray-config/config.template.json > xray-config/config.json
    echo -e "${GREEN}✓ Xray config generated${NC}"
fi

# Create data directories
mkdir -p data/wg-easy

# Start the stack
echo -e "${YELLOW}Starting VPN stack...${NC}"
docker compose up -d --build

echo -e "${GREEN}=== Setup complete ===${NC}"
echo "Web UI: http://$WG_HOST:51821"
echo "Check status: docker compose ps"
echo "View logs: docker compose logs -f"
