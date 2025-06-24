#!/bin/bash
# This script rebuilds the PostgreSQL database from scratch.

# Stop the services
docker compose down

# Remove the data volume to ensure a clean slate
docker volume rm postgresql-docker_pgdata

# Restart the services to re-initialize the database
docker compose up -d

echo "Database has been rebuilt."