#!/bin/bash

# Setup script for Construction Takeoff Database
# This script initializes the PostgreSQL database with the complete schema

set -e

echo "=== Construction Takeoff Database Setup ==="
echo

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker first."
    exit 1
fi

# Stop and remove existing containers
echo "Stopping existing containers..."
docker-compose down -v

# Start PostgreSQL container
echo "Starting PostgreSQL container..."
docker-compose up -d

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until docker exec takeoff_postgres pg_isready -U Jon -d takeoff_pricing_db; do
    echo "PostgreSQL is unavailable - sleeping..."
    sleep 2
done

echo "PostgreSQL is ready!"
sleep 5

# Apply the complete schema
echo "Applying complete database schema..."
docker exec -i takeoff_postgres psql -U Jon -d takeoff_pricing_db < init/complete_schema.sql

echo
echo "=== Database Setup Complete! ==="
echo
echo "Your PostgreSQL database is now ready with:"
echo "  - Complete table structure"
echo "  - All relationships and constraints"
echo "  - Performance indexes"
echo "  - Proper data types and validations"
echo
echo "Next steps:"
echo "  1. Install Python dependencies: pip install pandas openpyxl psycopg2-binary"
echo "  2. Run data loader: python3 data_loader.py"
echo "  3. Connect to database: docker exec -it takeoff_postgres psql -U Jon -d takeoff_pricing_db"
echo
echo "Database connection details:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: takeoff_pricing_db" 
echo "  Username: Jon"
echo "  Password: Transplant4real"
echo 