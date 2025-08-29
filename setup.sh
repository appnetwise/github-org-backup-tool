#!/bin/bash

# GitHub Organization Backup Tool Setup Script

echo "🚀 Setting up GitHub Organization Backup Tool..."

# Check if Python 3.8+ is installed
python_version=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
required_version="3.8"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then
    echo "✅ Python $python_version detected"
else
    echo "❌ Python 3.8+ is required. Found: $python_version"
    exit 1
fi

# Check if Git is installed
if command -v git &> /dev/null; then
    echo "✅ Git is installed"
else
    echo "❌ Git is required but not installed"
    exit 1
fi

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip3 install -r requirements.txt

if [ $? -eq 0 ]; then
    echo "✅ Dependencies installed successfully"
else
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Create config file from example if it doesn't exist
if [ ! -f "config.json" ]; then
    cp config.example.json config.json
    echo "📝 Created config.json from example"
    echo "⚠️  Please edit config.json with your organization details and tokens"
else
    echo "ℹ️  config.json already exists"
fi

# Make the script executable
chmod +x backup_org.py

echo ""
echo "🎉 Setup complete!"
echo ""
echo "Next steps:"
echo "1. Edit config.json with your GitHub tokens and organization names"
echo "2. Run a dry-run to test: python3 backup_org.py --source-org SOURCE --dest-org DEST --dry-run"
echo "3. Run the full backup: python3 backup_org.py --source-org SOURCE --dest-org DEST"
echo ""
echo "For more options, run: python3 backup_org.py --help"
