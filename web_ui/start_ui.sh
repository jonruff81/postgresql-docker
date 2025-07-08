#!/bin/bash

# Start the Web UI for PostgreSQL Takeoff Database
# Connects to Hostinger PostgreSQL database at 31.97.137.221

echo "🚀 Starting PostgreSQL Takeoff Database Web UI..."
echo ""
echo "🌐 Database: 31.97.137.221:5432/takeoff_pricing_db"
echo ""

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
