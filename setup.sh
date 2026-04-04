#!/bin/bash

# Setup script for Agent Builder Platform

set -e

echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║              Agent Builder Platform - Setup Script                    ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""

# Check Python version
echo "[1/6] Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "  Python version: $PYTHON_VERSION"

# Check Node.js
echo ""
echo "[2/6] Checking Node.js..."
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed"
    exit 1
fi

NODE_VERSION=$(node --version)
echo "  Node.js version: $NODE_VERSION"

# Check if Ollama is running
echo ""
echo "[3/6] Checking Ollama..."
if curl -s http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "  Ollama is running at http://localhost:11434"
else
    echo "  Warning: Ollama does not appear to be running at http://localhost:11434"
    echo "  Please start Ollama: ollama serve"
    echo "  Do you want to continue anyway? (y/n)"
    read -r response
    if [ "$response" != "y" ]; then
        echo "Setup aborted."
        exit 1
    fi
fi

# Install Python dependencies
echo ""
echo "[4/6] Installing Python dependencies..."
pip3 install -r requirements.txt

echo "  Python dependencies installed"

# Create necessary directories
echo ""
echo "[5/6] Creating directories..."
mkdir -p storage/agents storage/runs
echo "  Storage directories created"

# Install frontend dependencies
echo ""
echo "[6/6] Installing frontend dependencies..."
cd frontend && npm install && cd ..
echo "  Frontend dependencies installed"

# Final summary
echo ""
echo "╔═══════════════════════════════════════════════════════════════════════╗"
echo "║                    Setup Complete!                                    ║"
echo "╚═══════════════════════════════════════════════════════════════════════╝"
echo ""
echo "To start the backend:"
echo "  cd backend && uvicorn main:app --reload --port 8000"
echo ""
echo "To start the frontend (in another terminal):"
echo "  cd frontend && npm run dev"
echo ""
echo "Then open http://localhost:3000"
echo ""
