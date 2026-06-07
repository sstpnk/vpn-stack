#!/bin/bash

# VPN Stack Setup Script
# Usage: chmod +x setup.sh && ./setup.sh

set -e

echo "=== VPN Stack Setup ==="

# Check if .env exists
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please edit .env with your values and run this script again"
    exit 1
fi

# Load environment variables
source .env

# Validate required variables
if [ -z "$WG_HOST" ] || [ "$WG_HOST" = "xxx.xxx.xxx.xxx" ]; then
    echo "ERROR: Please set WG_HOST in .env file"
    exit 1
fi

if [ -z "$WG_EASY_PASSWORD" ] || [ "$WG_EASY_PASSWORD" = "your_secure_password" ]; then
    echo "ERROR: Please set WG_EASY_PASSWORD in .env file"
    exit 1
fi

echo "Configuration OK"

# Create directories
mkdir -p data/wg-easy xray-config

# Generate Xray config if template exists and keys are set
if [ -f xray-config/config.template.json ]; then
    if [ ! -f xray-config/config.json ]; then
        echo "Generating Xray config..."
        cp xray-config/config.template.json xray-config/config.json
        echo "WARNING: Replace YOUR_UUID, YOUR_PRIVATE_KEY, YOUR_PUBLIC_KEY, YOUR_SHORT_ID in xray-config/config.json"
        echo "Run: docker run --rm teddysun/xray:latest xray x25519"
        echo "Run: docker run --rm teddysun/xray:latest xray uuid"
    fi
fi

# Build and start containers
echo "Starting VPN stack..."
docker compose up -d --build

echo "=== Setup complete ==="
echo "Web UI: http://$WG_HOST:51821"
echo "Check status: docker compose ps"
echo "View logs: docker compose logs -f"
