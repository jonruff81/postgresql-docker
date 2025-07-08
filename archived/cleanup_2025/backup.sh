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
DB_HOST="31.97.137.221"
DB_PORT="5432"
DB_NAME="takeoff_pricing_db"
DB_USER="Jon"

echo -e "${BLUE}🗄️  Creating PostgreSQL backup from Hostinger...${NC}"

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Check if pg_dump is available
if ! command -v pg_dump &> /dev/null; then
    echo -e "${RED}❌ pg_dump not found. Please install PostgreSQL client tools.${NC}"
    echo -e "${BLUE}💡 On Ubuntu/Debian: sudo apt install postgresql-client${NC}"
    echo -e "${BLUE}💡 On Windows: Install PostgreSQL or use pgAdmin${NC}"
    exit 1
fi

# Create backup
echo -e "${BLUE}📦 Backing up database '$DB_NAME' from Hostinger...${NC}"
echo -e "${BLUE}🌐 Host: $DB_HOST:$DB_PORT${NC}"

# Set PGPASSWORD environment variable to avoid password prompt
# Note: In production, consider using .pgpass file for security
export PGPASSWORD="Transplant4real"

pg_dump -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME > "$BACKUP_DIR/$BACKUP_FILE"

# Check if backup was successful
if [ $? -eq 0 ]; then
    # Compress backup
    echo -e "${BLUE}🗜️  Compressing backup...${NC}"
    gzip "$BACKUP_DIR/$BACKUP_FILE"
    
    echo -e "${GREEN}✅ Backup completed: $BACKUP_DIR/${BACKUP_FILE}.gz${NC}"
    
    # Display backup size
    BACKUP_SIZE=$(du -h "$BACKUP_DIR/${BACKUP_FILE}.gz" | cut -f1)
    echo -e "${GREEN}📊 Backup size: $BACKUP_SIZE${NC}"
else
    echo -e "${RED}❌ Backup failed${NC}"
    exit 1
fi

# Cleanup old backups (keep last 30 days)
echo -e "${BLUE}🧹 Cleaning up old backups...${NC}"
DELETED=$(find "$BACKUP_DIR" -name "*.gz" -mtime +30 -delete -print | wc -l)
if [ $DELETED -gt 0 ]; then
    echo -e "${GREEN}🗑️  Deleted $DELETED old backup(s)${NC}"
else
    echo -e "${GREEN}📁 No old backups to delete${NC}"
fi

# List recent backups
echo -e "${BLUE}📋 Recent backups:${NC}"
ls -lht "$BACKUP_DIR"/*.gz 2>/dev/null | head -5 || echo "No backups found"

echo -e "${GREEN}🎉 Backup process completed successfully!${NC}"

# Clear password from environment
unset PGPASSWORD
