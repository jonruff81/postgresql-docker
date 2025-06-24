# PostgreSQL Takeoff Pricing Database

A comprehensive PostgreSQL-based system for managing construction takeoff pricing data with vendor management, historical price tracking, and file attachments.

## 🚀 Current Status - PRODUCTION READY

✅ **Database Schema Complete** - Full PostgreSQL schema with 20 tables and views  
✅ **Data Migration Complete** - SF fields properly moved to plan_options table  
✅ **Vendor Pricing System** - Historical tracking with 229 pricing records from 62 vendors  
✅ **Data Loader Working** - Enhanced loader handles all 61 Excel columns  
✅ **File Organization Complete** - Clean, organized project structure  

## 📁 Project Structure

```
postgresql-docker/
├── docker-compose.yml          # Docker PostgreSQL configuration
├── start.sh                    # Quick start script
├── README.md                   # This file
├── DATABASE_README.md          # Detailed database documentation
├── 
├── scripts/                    # Core operational scripts
│   ├── new_data_loader.py      # Main data loader (USE THIS)
│   ├── setup_database.sh       # Database setup script
│   ├── rebuild_database.sh     # Database rebuild script
│   ├── backup.sh              # Database backup utility
│   └── consolidated-commands.sh # Batch operations
├── 
├── migrations/                 # SQL migration scripts (chronological)
│   ├── 001_update_schema.sql   # Initial schema updates
│   ├── 002_migrate_sf_fields.sql # SF field migration
│   ├── 003_vendor_pricing_enhancement.sql # Vendor pricing system
│   └── 004_populate_vendor_pricing.sql # Initial pricing data
├── 
├── utils/                      # Utility tools
│   ├── examine_excel.py        # Excel file inspection
│   ├── examine_excel_simple.py # Simple Excel analysis
│   ├── file-optimizer-agent.py # File optimization
│   └── simple-file-optimizer.py # Basic file optimization
├── 
├── init/                       # Database initialization
│   └── complete_schema.sql     # Complete database schema
├── 
├── PlanElevOptions/           # Excel data files (21 files)
│   ├── Barringer_A_Crawl_*.xlsx
│   ├── Calderwood_A_Basement_*.xlsx
│   ├── Croydonette_*_*.xlsx
│   ├── Oxford_A_Basement_*.xlsx
│   ├── Sandbrook_B_Crawl_*.xlsx
│   └── Winchester_A_Basement_*.xlsx
├── 
├── archived/                   # Archived/historical files
│   ├── old_loaders/           # Previous data loader versions
│   ├── verification_queries.sql
│   ├── Excel_Column_to_Database_Mapping.csv
│   └── other historical files
└── 
└── logs/                      # Application logs
    └── postgresql-*.log
```

## 🏗️ Database Architecture

### Core Tables (20 total)
- **plans** (6) → **plan_elevations** (7) → **plan_options** (22) → **jobs** (21) → **takeoffs** (2,321)
- **vendors** (62) → **vendor_pricing** (229) → **vendor_quotes** → **quote_line_items**
- **cost_groups** → **cost_codes** → **items** → **products**
- **divisions** → **communities**
- **pricing_attachments** (file management)

### Key Features
- ✅ **Vendor Pricing Catalog**: 229 active pricing records with history tracking
- ✅ **Quote Management**: Formal quote workflow with file attachments
- ✅ **Cost Analysis**: Plan/elevation/option level cost breakdowns
- ✅ **SF Data**: Heated/unheated/total square footage by option
- ✅ **Audit Trail**: Complete change tracking and user attribution

## 🚀 Quick Start

### 1. Start Database
```bash
./start.sh
```

### 2. Load Data
```bash
# Load all Excel files
python3 scripts/new_data_loader.py

# Load specific files
python3 scripts/new_data_loader.py PlanElevOptions Winchester
```

### 3. Access Database
```bash
docker exec -it takeoff_postgres psql -U Jon -d takeoff_pricing_db
```

## 📊 Current Data Status

### Loaded Data Summary:
- **6 Plans**: Barringer, Calderwood, Croydonette, Oxford, Sandbrook, Winchester
- **7 Elevations**: Various A/B/C elevations with Basement/Crawl foundations
- **22 Options**: BaseHome, Design Options, Structural, Finished Basement, etc.
- **21 Jobs**: Template jobs for each plan/elevation/option combination
- **2,321 Takeoff Records**: Detailed cost breakdowns
- **62 Vendors**: From A-Sani-Can Service to Wright Bros Concrete
- **229 Pricing Records**: Current vendor pricing with history

### Pricing Analysis:
- **Standard Pricing**: 179 records, avg $1,481.63
- **Quote Pricing**: 50 records, avg $14,924.95
- **Price Range**: $0.15 - $108,252.00

## 🔧 Key Operations

### Data Loading
```bash
# Main data loader with vendor pricing integration
python3 scripts/new_data_loader.py [directory] [file_patterns...]
```

### Database Management
```bash
# Rebuild from scratch
scripts/rebuild_database.sh

# Setup fresh database
scripts/setup_database.sh

# Backup database
scripts/backup.sh
```

### Excel Analysis
```bash
# Examine Excel file structure
python3 utils/examine_excel_simple.py "path/to/file.xlsx"
```

## 📈 Business Intelligence Views

### Cost Analysis
```sql
-- Plan cost analysis
SELECT * FROM takeoff.v_job_cost_analysis WHERE plan_name = 'Winchester';

-- Vendor pricing catalog
SELECT * FROM takeoff.v_current_vendor_pricing ORDER BY vendor_name;

-- Price history analysis
SELECT * FROM takeoff.v_price_history WHERE price_change_percent IS NOT NULL;
```

## 🔄 Git Branches

- **main**: Current production-ready state
- **backup-before-cleanup**: Backup of pre-organization state

## 📝 Next Steps

1. **Web UI Development**: Simple dashboard for table management
2. **Enhanced File Attachments**: Quote PDF storage and management
3. **Advanced Analytics**: Cost trend analysis and reporting
4. **API Development**: REST API for external integrations

## 📚 Documentation

- `DATABASE_README.md`: Detailed database schema documentation
- `migrations/`: Chronological database evolution
- `archived/`: Historical files and verification queries

## 🐳 Docker Configuration

The system runs in Docker with:
- PostgreSQL 13 with persistent storage
- Custom takeoff_pricing_db database
- Volume-mounted data directory
- Automated backups

---

**Database Ready for Production Use** 🎯  
*All Excel data loaded, vendor pricing active, cost analysis operational*
