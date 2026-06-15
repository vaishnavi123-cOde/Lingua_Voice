#!/usr/bin/env bash
set -euo pipefail

# ========================================
# SQL Lecture Assistant - Server Setup
# ========================================

echo "Starting server setup..."

# Detect OS
OS="$(uname -s)"
case "$OS" in
    Linux*)     MACHINE=Linux;;
    Darwin*)    MACHINE=Mac;;
    *)          echo "Unsupported OS: $OS"; exit 1;;
esac
echo "Detected OS: $MACHINE"

# Install Docker if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    if [ "$MACHINE" = "Linux" ]; then
        curl -fsSL https://get.docker.com | sh
        sudo usermod -aG docker "$USER"
        echo "Docker installed. You may need to log out and back in."
    else
        echo "Please install Docker Desktop from https://docker.com"
        exit 1
    fi
else
    echo "Docker already installed: $(docker --version)"
fi

# Install Docker Compose if not present
if ! command -v docker-compose &> /dev/null; then
    echo "Installing Docker Compose..."
    if [ "$MACHINE" = "Linux" ]; then
        sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
        sudo chmod +x /usr/local/bin/docker-compose
    fi
else
    echo "Docker Compose already installed: $(docker-compose --version)"
fi

# Create directory structure
mkdir -p logs audio_cache qdrant_db

# Copy environment file if not exists
if [ ! -f .env ]; then
    if [ -f deploy/.env.production ]; then
        cp deploy/.env.production .env
        echo "Created .env from production template"
    fi
fi

echo ""
echo "========================================="
echo "Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Pull Ollama model:"
echo "     docker exec sql-qa-ollama ollama pull qwen2.5:7b"
echo ""
echo "  2. Start services:"
echo "     docker-compose up -d"
echo ""
echo "  3. Check logs:"
echo "     docker-compose logs -f"
echo ""
echo "  4. Access application:"
echo "     Frontend: http://localhost:3000"
echo "     Backend:  http://localhost:8000"
echo "     API Docs: http://localhost:8000/docs"
echo "========================================="
