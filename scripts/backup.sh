#!/bin/bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m'

# Configuration
BACKUP_DIR="./backups"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="takeoff_pricing_db_backup_${DATE}.sql"
CONTAINER_NAME="takeoff_postgres"
DB_NAME="takeoff_pricing_db"
DB_USER="Jon"

echo -e "${BLUE}🗄️  Creating PostgreSQL backup...${NC}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo -e "${RED}❌ Container '$CONTAINER_NAME' is not running${NC}"
    exit 1
fi

# Create backup
echo -e "${BLUE}📦 Backing up database '$DB_NAME'...${NC}"
docker exec $CONTAINER_NAME pg_dump -U $DB_USER -d $DB_NAME > "$BACKUP_DIR/$BACKUP_FILE"

# Compress backup
echo -e "${BLUE}🗜️  Compressing backup...${NC}"
gzip "$BACKUP_DIR/$BACKUP_FILE"

echo -e "${GREEN}✅ Backup completed: $BACKUP_DIR/${BACKUP_FILE}.gz${NC}"

# Cleanup old backups (keep last 30 days)
echo -e "${BLUE}🧹 Cleaning up old backups...${NC}"
find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete

echo -e "${GREEN}🎉 Backup process completed successfully!${NC}" 