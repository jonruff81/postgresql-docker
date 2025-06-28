#!/bin/bash

# Start the Web UI for PostgreSQL Takeoff Database
# Make sure PostgreSQL database is running first

echo "🚀 Starting PostgreSQL Takeoff Database Web UI..."
echo ""

# Check if PostgreSQL is running
if ! docker ps | grep -q takeoff_postgres; then
    echo "❌ PostgreSQL database container not found!"
    echo "   Please start the database first:"
    echo "   cd /root/postgresql-docker && ./start.sh"
    exit 1
fi

echo "✅ PostgreSQL database is running"

# Change to the script's directory to ensure correct paths
cd "$(dirname "$0")"

# Install Python dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt

echo ""
echo "🌐 Starting Web UI on http://localhost:5000"
echo "   Press Ctrl+C to stop"
echo ""

# Start Flask app
python3 app.py
