# PostgreSQL Construction Takeoff System

A comprehensive PostgreSQL-based system for managing construction takeoff pricing data with vendor management, historical price tracking, file attachments, and a full-featured web interface.

## 🚀 Current Status - PRODUCTION READY

✅ **Database Schema Complete** - Full PostgreSQL schema with 20 tables and views  
✅ **Data Migration Complete** - SF fields properly moved to plan_options table  
✅ **Vendor Pricing System** - Historical tracking with 229 pricing records from 62 vendors  
✅ **Data Loader Working** - Enhanced loader handles all 61 Excel columns  
✅ **Web UI Complete** - Full CRUD interface with dashboard, smart editing, and API  
✅ **File Organization Complete** - Clean, organized project structure  

## 🌐 Web Interface Features

- **📊 Dashboard**: Overview of all database tables with record counts
- **📋 Table Management**: Browse, search, edit, delete records in any table
- **🎯 Smart Takeoffs**: Advanced takeoff editing with inline updates and meaningful names
- **📈 Enhanced Views**: Filtered takeoff analysis with cost summaries
- **📥 Bulk Import**: CSV import functionality for batch data loading
- **🔍 Search & Filter**: Powerful search across all data fields
- **📱 Responsive Design**: Works on desktop, tablet, and mobile

## 📁 Project Structure

```
postgresql-docker/
├── 🐳 Docker & Database
│   ├── docker-compose.yml          # PostgreSQL container configuration
│   ├── start.sh                    # Quick database startup
│   └── init/complete_schema.sql    # Complete database schema
├── 
├── 🌐 Web Interface
│   ├── web_ui/
│   │   ├── app.py                  # Main Flask application
│   │   ├── alt_server.py           # Alternative server config
│   │   ├── start_ui.sh             # Web UI startup script
│   │   ├── requirements.txt        # Python dependencies
│   │   ├── templates/              # HTML templates
│   │   │   ├── dashboard.html      # Main dashboard
│   │   │   ├── table_view.html     # Table browsing
│   │   │   ├── smart_takeoffs.html # Advanced takeoff editing
│   │   │   ├── takeoffs_enhanced.html # Filtered analysis
│   │   │   ├── edit_record.html    # Record editing
│   │   │   ├── create_record.html  # Record creation
│   │   │   ├── bulk_import.html    # CSV import
│   │   │   └── debug.html          # Development tools
│   │   └── static/                 # CSS, JS, images
├── 
├── 🔧 Core Scripts
│   ├── scripts/
│   │   ├── new_data_loader.py      # Main Excel data loader
│   │   ├── setup_database.sh       # Database initialization
│   │   ├── rebuild_database.sh     # Complete rebuild
│   │   ├── backup.sh              # Database backup utility
│   │   └── consolidated-commands.sh # Batch operations
├── 
├── 🗄️ Database Evolution
│   ├── migrations/                 # SQL migration scripts (chronological)
│   │   ├── 001_update_schema.sql   # Initial schema updates
│   │   ├── 002_migrate_sf_fields.sql # SF field migration
│   │   ├── 003_vendor_pricing_enhancement.sql # Vendor pricing
│   │   └── 004_populate_vendor_pricing.sql # Initial pricing data
├── 
├── 📊 Source Data
│   ├── PlanElevOptions/           # Excel files (21 files)
│   │   ├── Barringer_A_Crawl_*.xlsx
│   │   ├── Calderwood_A_Basement_*.xlsx
│   │   ├── Croydonette_*_*.xlsx
│   │   ├── Oxford_A_Basement_*.xlsx
│   │   ├── Sandbrook_B_Crawl_*.xlsx
│   │   └── Winchester_A_Basement_*.xlsx
├── 
├── 🛠️ Utilities
│   ├── utils/
│   │   ├── examine_excel.py        # Excel file inspection
│   │   ├── examine_excel_simple.py # Simple Excel analysis
│   │   ├── file-optimizer-agent.py # File optimization
│   │   └── simple-file-optimizer.py # Basic optimization
├── 
├── 📚 Documentation
│   ├── README.md                   # This file (technical overview)
│   ├── USER_README.md              # User-friendly guide
│   └── DATABASE_README.md          # Detailed database docs
├── 
├── 🗂️ Archive & Logs
│   ├── archived/                   # Historical files
│   │   ├── old_loaders/           # Previous loader versions
│   │   └── verification_queries.sql
│   ├── logs/                      # Application logs
│   └── backups/                   # Timestamped backups
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

### 1. Start the System
```bash
# Start PostgreSQL database
./start.sh

# Start Web UI (in separate terminal)
cd web_ui
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
python3 app.py
```

### 2. Access the System
- **Web Interface**: http://localhost:5000
- **Database Direct**: `docker exec -it takeoff_postgres psql -U Jon -d takeoff_pricing_db`

### 3. Load Data (if needed)
```bash
# Load all Excel files
python3 scripts/new_data_loader.py

# Load specific files
python3 scripts/new_data_loader.py PlanElevOptions Winchester
```

## 🌐 Web Interface Guide

### Main Dashboard
Navigate to http://localhost:5000 to see:
- **Table Overview**: All database tables with record counts
- **Quick Actions**: Direct links to table management
- **System Status**: Database connection and health

### Smart Takeoffs Management
- **Smart Takeoffs** (`/takeoffs/smart`): Advanced editing with dropdowns
- **Enhanced Takeoffs** (`/takeoffs/enhanced`): Filtering and cost analysis
- **Table View** (`/table/takeoffs`): Basic table browsing

### Key Features
1. **Inline Editing**: Click any field to edit directly
2. **Smart Dropdowns**: Meaningful names instead of IDs
3. **Real-time Updates**: Changes saved automatically
4. **Search & Filter**: Find records quickly
5. **Bulk Operations**: Import CSV data

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

## 🔧 System Operations

### Database Management
```bash
# Rebuild from scratch
scripts/rebuild_database.sh

# Setup fresh database
scripts/setup_database.sh

# Backup database
scripts/backup.sh
```

### Excel Data Loading
```bash
# Main data loader with vendor pricing integration
python3 scripts/new_data_loader.py [directory] [file_patterns...]

# Examine Excel file structure
python3 utils/examine_excel_simple.py "path/to/file.xlsx"
```

### Web UI Management
```bash
# Start development server
cd web_ui && python3 app.py

# Start with alternative configuration
cd web_ui && python3 alt_server.py

# Install/update dependencies
pip install -r web_ui/requirements.txt
```

## 📈 Business Intelligence Views

### Cost Analysis Queries
```sql
-- Plan cost analysis
SELECT * FROM takeoff.v_job_cost_analysis WHERE plan_name = 'Winchester';

-- Vendor pricing catalog
SELECT * FROM takeoff.v_current_vendor_pricing ORDER BY vendor_name;

-- Price history analysis
SELECT * FROM takeoff.v_price_history WHERE price_change_percent IS NOT NULL;
```

### Web Interface Analysis
- **Dashboard**: Real-time table statistics
- **Enhanced Takeoffs**: Filtered cost analysis with totals
- **Smart Views**: Meaningful data relationships

## 🔌 API Endpoints

The web interface includes REST API endpoints:

```bash
# Get all tables
GET /api/tables

# Get table structure
GET /api/table/{table_name}/structure

# Update takeoff field
POST /api/takeoffs/{takeoff_id}/update

# Get lookup data
GET /api/lookup-data

# Create takeoff
POST /api/takeoffs/create

# Delete takeoff
DELETE /api/takeoffs/{takeoff_id}/delete
```

## 🔄 Development Workflow

### Git Repository
- **main**: Current production-ready state with web UI
- **Sync Status**: Fully synchronized with GitHub
- **Backups**: Timestamped backups before major changes

### File Organization
- All virtual environment files properly excluded
- Clean repository structure
- Comprehensive documentation

## 📝 Next Steps

1. **Enhanced UI Features**:
   - Advanced filtering and sorting
   - Export functionality (CSV, PDF)
   - User authentication and permissions
   - Mobile app development

2. **Business Intelligence**:
   - Cost trend analysis dashboards
   - Vendor performance metrics
   - Automated reporting

3. **Integration**:
   - REST API expansion
   - Third-party integrations
   - Cloud deployment options

4. **Advanced Features**:
   - File attachment management
   - Automated data validation
   - Advanced search capabilities

## 🐳 Docker Configuration

The system runs in Docker with:
- **PostgreSQL 13** with persistent storage
- **Custom Database**: takeoff_pricing_db
- **Volume Mounting**: Data directory persistence
- **Automated Backups**: Scheduled backup system
- **Network**: Isolated container networking

## 📚 Documentation

- **README.md**: Technical overview (this file)
- **USER_README.md**: User-friendly guide for end users
- **DATABASE_README.md**: Detailed database schema documentation
- **migrations/**: Chronological database evolution
- **archived/**: Historical files and verification queries

## 🔒 Security Considerations

- Database credentials stored in configuration
- Web UI secret key (change for production)
- SQL injection protection via parameterized queries
- Input validation and sanitization

---

**🎯 Production-Ready Construction Takeoff System**  
*Database ✓ | Web Interface ✓ | API ✓ | Documentation ✓*

**Quick Access**: Start with `./start.sh` then visit http://localhost:5000
