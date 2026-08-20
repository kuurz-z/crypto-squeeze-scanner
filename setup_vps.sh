#!/bin/bash
# ==========================================================
# 24/7 Automated Crypto Bot VPS Quick-Deploy Script
# ==========================================================

set -e

echo "🚀 Updating system packages..."
sudo apt update && sudo apt upgrade -y

echo "📦 Installing Docker & Docker Compose..."
sudo apt install -y docker.io docker-compose curl git ufw

sudo systemctl enable --now docker
sudo usermod -aG docker $USER

echo "🛡️ Configuring Firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 8000/tcp
sudo ufw --force enable

echo "🐳 Building and starting Crypto Trading Bot container..."
docker-compose up -d --build

echo "✅ Deployment Successful!"
echo "🌐 Your bot is now running 24/7 at: http://$(curl -s ifconfig.me):8000"
