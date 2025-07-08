# PostgreSQL Construction Takeoff System

A comprehensive PostgreSQL-based system for managing construction takeoff pricing data with vendor management, historical price tracking, file attachments, and a full-featured web interface. **Connected to live Hostinger PostgreSQL database.**

## 📑 Table of Contents
- [Current Status](#-current-status---production-ready)
- [Web Interface Features](#-web-interface-features)
- [Project Structure](#-project-structure)
- [Database Architecture](#-database-architecture)
- [Quick Start](#-quick-start)
- [Web Interface Guide](#-web-interface-guide)
- [Current Data Status](#-current-data-status-live-from-hostinger)
- [System Operations](#-system-operations)
- [Business Intelligence Views](#-business-intelligence-views)
- [API Endpoints](#-api-endpoints)
- [Development Workflow](#-development-workflow)
- [Recent Enhancements](#-recent-enhancements)
- [Next Steps](#-next-steps)
- [Documentation](#-documentation)
- [Security Considerations](#-security-considerations)
- [Core Tech Stack](#-core-tech-stack)

## 🚀 Current Status - PRODUCTION READY

✅ **Database Schema Complete** - Full PostgreSQL schema with 26 tables and views
✅ **Hostinger Integration** - Live connection to PostgreSQL database at 31.97.137.221:5432
✅ **Vendor Pricing System** - Historical tracking with 229 pricing records from 62 vendors
✅ **Data Loader Working** - Enhanced loader handles all 61 Excel columns
✅ **Web UI Complete** - Full CRUD interface with dashboard, smart editing, and API
✅ **File Organization Complete** - Clean, organized project structure

## 🌐 Web Interface Features

- **📊 Dashboard**: Overview of all database tables with record counts
- **📋 Table Management**: Browse, search, edit, delete records in any table
- **🎯 Smart Takeoffs**: Advanced takeoff editing with inline updates and meaningful names
- **📈 Enhanced Views**: Filtered takeoff analysis with cost summaries
- **📝 Duplicate & Delete Rows**: Easily duplicate or delete takeoff records directly from the Comprehensive Takeoff Analysis grid
- **📝 Product Duplication**: Duplicating a product creates a new item with a unique name (appends " (Copy)", " (Copy 2)", etc. if needed) and links the product to the correct cost code. Cost code assignment is always respected and saved.
- **📥 Bulk Import/Export/Template**: Every AG-Grid view supports import (Excel/CSV), export (Excel/CSV), and "Download Template" (Excel/CSV with correct headers for that grid).
- **🔑 AG-Grid License**: AG-Grid Enterprise license key is injected from Flask config/environment and never hardcoded; always referenced securely in JS.
- **🔍 Search & Filter**: Powerful search across all data fields
- **📱 Responsive Design**: Works on desktop, tablet, and mobile

## 📁 Project Structure

```
postgresql-docker/
├── 🗄️ Database Configuration
│   ├── config.py                   # Hostinger database configuration
│   ├── init/complete_schema.sql    # Complete database schema
│   └── migrations/                 # SQL migration scripts
├──
├── 🌐 Web Interface
│   ├── web_ui/
│   │   ├── app.py                  # Main Flask application
│   │   ├── start_ui.sh             # Web UI startup script
│   │   ├── requirements.txt        # Python dependencies
│   │   ├── templates/              # HTML templates
│   │   │   ├── dashboard.html      # Main dashboard
│   │   │   ├── *_grid.html         # AG-Grid interfaces
│   │   │   └── base.html           # Common template
│   │   └── static/                 # CSS, JS, images
├──
├── 🔧 Core Scripts
│   ├── scripts/
│   │   ├── new_data_loader.py      # Main Excel data loader
│   │   ├── backup.sh              # Database backup utility
│   │   └── bulk_product_vendor_import.py # Bulk import tools
├──
├── 🌐 Connection Testing
│   ├── [archived/cleanup_2025/test-diagnose/](archived/cleanup_2025/test-diagnose/) (archived)
│   │   ├── test_connection.py      # Database connection test (archived)
│   │   ├── run_hostinger.bat       # Quick start script (archived)
│   │   ├── HOSTINGER_SETUP.md      # Complete setup guide (archived)
│   │   ├── HOSTINGER_DATABASE_CHECKLIST.md # Diagnostic checklist (archived)
│   │   └── HOSTINGER_FIREWALL_SETUP.md # Firewall configuration (archived)
├── 
├── 📊 Source Data
│   ├── [archived/cleanup_2025/PlanElevOptions/](archived/cleanup_2025/PlanElevOptions/) (archived Excel files)
├── 
├── 🛠️ Utilities
│   ├── utils/
│   │   ├── examine_excel.py        # Excel file inspection
│   │   ├── examine_excel_simple.py # Simple Excel analysis
│   │   └── file optimization tools
├── 
├── 📚 Documentation
│   ├── README.md                   # This file (technical overview)
│   ├── USER_README.md              # User-friendly guide
│   └── DATABASE_README.md          # Detailed database docs
├── 
├── 🗂️ Archive & Logs
│   ├── archived/                   # Historical files and all deprecated/test/backup files
│   ├── [archived/cleanup_2025/logs/](archived/cleanup_2025/logs/) (archived application logs)
│   ├── [archived/cleanup_2025/backups/](archived/cleanup_2025/backups/) (archived backups)
```

## 🏗️ Database Architecture

### Database Connection
- **🌐 Hostinger PostgreSQL**: 31.97.137.221:5432/takeoff_pricing_db
- **🔐 Authentication**: User 'Jon' with environment-based password
- **📡 Connection**: Direct TCP connection to live database

### Core Tables (26 total)
- **plans** (6) → **plan_elevations** (7) → **plan_options** (22) → **jobs** (21) → **takeoffs** (2,321)
- **vendors** (62) → **vendor_pricing** (229) → **vendor_quotes** → **quote_line_items**
- **cost_groups** → **cost_codes** (90) → **items** → **products**
- **divisions** → **communities**
- **pricing_attachments** (file management)

### Key Features
- ✅ **Vendor Pricing Catalog**: 229 active pricing records with history tracking
- ✅ **Quote Management**: Formal quote workflow with file attachments
- ✅ **Cost Analysis**: Plan/elevation/option level cost breakdowns
- ✅ **SF Data**: Heated/unheated/total square footage by option
- ✅ **Audit Trail**: Complete change tracking and user attribution

## 🚀 Quick Start

### 1. Start the Application
```bash
# Quick start with batch file
# (Old quick start scripts are now archived. Use the web interface directly.)
cd web_ui
python app.py
```

### 2. Access the System
- **Web Interface**: http://localhost:5000
- **Database Direct**: `psql -h 31.97.137.221 -p 5432 -U Jon -d takeoff_pricing_db`

### 3. Test Connection
```bash
# Test database connection
# (Old test scripts are now archived. Use the web interface for connection status.)
```

## 🌐 Web Interface Guide

### Main Dashboard
Navigate to http://localhost:5000 to see:
- **Table Overview**: All database tables with record counts
- **AG-Grid Interfaces**: Modern data grids for each table
- **System Status**: Database connection and health

### Key Interfaces
- **Plans Grid**: Plan management with elevation/option counts
- **Products Grid**: Product catalog with vendor pricing
- **Vendor Pricing Grid**: Price management with history
- **Comprehensive Takeoff Grid**: Complete takeoff analysis
- **Cost Codes Grid**: Cost code management with groups
- **Items Grid**: Item management with enterprise features
- **Quotes Grid**: Quote management system
- **Plan Options Grid**: Plan option management

### Key Features
1. **AG-Grid Integration**: Professional data grids with sorting, filtering, editing, and Excel-like features
2. **Inline Editing**: Click any field to edit directly; changes are saved to the live Hostinger PostgreSQL database
3. **Smart Dropdowns**: Meaningful names instead of IDs
4. **Real-time Updates**: All changes are saved directly to production (no local/dev DB)
5. **Master-Detail Views**: Related data shown in detail panels (e.g., vendor pricing for products)
6. **Bulk Operations**: Import, export, and template download for every grid (Excel/CSV)
7. **AG-Grid License**: License key is always injected from backend config, never hardcoded
8. **Product Duplication**: Duplicating a product creates a new item with a unique name and links to the correct cost code; cost code is always saved

## 📊 Current Data Status (Live from Hostinger)

### Loaded Data Summary:
- **6 Plans**: Barringer, Calderwood, Croydonette, Oxford, Sandbrook, Winchester
- **7 Elevations**: Various A/B/C elevations with Basement/Crawl foundations
- **22 Options**: BaseHome, Design Options, Structural, Finished Basement, etc.
- **21 Jobs**: Template jobs for each plan/elevation/option combination
- **2,321+ Takeoff Records**: Detailed cost breakdowns (live data)
- **62 Vendors**: From A-Sani-Can Service to Wright Bros Concrete
- **90 Cost Codes**: Complete cost code structure
- **26 Database Tables**: Full schema with views and relationships

### Database Connection Status:
- **✅ Hostinger**: Connected to 31.97.137.221:5432/takeoff_pricing_db
- **✅ Connection Testing**: Automated via test_connection.py
- **✅ Live Data**: Real-time access to production database

## 🔧 System Operations

### Product Duplication & Cost Code Assignment

- When duplicating a product, the system:
  - Creates a new item in the items table with the same name as the original, but ensures uniqueness by appending " (Copy)", " (Copy 2)", etc. if needed.
  - Links the new product to this new item.
  - Assigns the selected cost code to the new item (creating the cost code if it does not exist).
  - All changes are saved directly to the live Hostinger PostgreSQL database.

### AG-Grid Import/Export/Template

- Every AG-Grid view (products, items, cost codes, etc.) supports:
  - **Export**: Download current grid data as Excel or CSV.
  - **Import**: Upload Excel/CSV to update/add rows.
  - **Download Template**: Download an Excel/CSV template with the correct headers for that grid.
- All import/export/template endpoints are implemented in Flask and connected to the live database.

### AG-Grid License Key

- The AG-Grid Enterprise license key is always injected from Flask config/environment and referenced in the JS block.
- The license key is never hardcoded in the frontend.

### Excel Data Loading
```bash
# Main data loader with vendor pricing integration
python scripts/new_data_loader.py [directory] [file_patterns...]

# Bulk vendor pricing import
python scripts/bulk_product_vendor_import.py products.csv vendor_pricing.csv

# Examine Excel file structure
python utils/examine_excel_simple.py "path/to/file.xlsx"
```

### Database Management
```bash
# Backup database to local file
# (Backup scripts are now archived. Use your preferred backup method or restore from archived/cleanup_2025/backups/ if needed.)
```

### Web UI Management
```bash
# Start development server
cd web_ui && python app.py

# Install/update dependencies
pip install -r web_ui/requirements.txt

# Start with shell script
web_ui/start_ui.sh
```

## 📈 Business Intelligence Views

### Cost Analysis Queries
```sql
-- Plan cost analysis
SELECT * FROM takeoff.v_comprehensive_takeoff_analysis WHERE plan_name = 'Winchester';

-- Vendor pricing catalog
SELECT * FROM takeoff.v_current_vendor_pricing ORDER BY vendor_name;

-- Cost codes with groups
SELECT * FROM takeoff.v_cost_codes_with_groups ORDER BY cost_code;
```

### Web Interface Analysis
- **Dashboard**: Real-time table statistics
- **AG-Grid Views**: Advanced filtering and analysis
- **Master-Detail**: Related data exploration

## 🔌 API Endpoints

The web interface includes comprehensive REST API endpoints:

### Table Data APIs
```bash
# Get all tables
GET /api/tables

# Get table structure
GET /api/table/{table_name}/structure

# Get specific table data
GET /api/plans
GET /api/plan-options
GET /api/products
GET /api/vendor-pricing
GET /api/cost-codes-with-groups
GET /api/qty-takeoffs
GET /api/quotes
GET /api/items
```

### CRUD Operations
```bash
# Create records
POST /api/plans
POST /api/plan-options
POST /api/products
POST /api/vendor-pricing
POST /api/qty-takeoffs
POST /api/quotes
POST /api/items

# Update records
PUT /api/plans/{plan_id}
PUT /api/plan-options/{option_id}
PUT /api/products/{product_id}
PUT /api/vendor-pricing/{pricing_id}
PUT /api/qty-takeoffs/{takeoff_id}
PUT /api/quotes/{quote_id}
PUT /api/items/{item_id}

# Delete records
DELETE /api/plans/{plan_id}
DELETE /api/plan-options/{option_id}
DELETE /api/products/{product_id}
DELETE /api/vendor-pricing/{pricing_id}
DELETE /api/qty-takeoffs/{takeoff_id}
DELETE /api/quotes/{quote_id}
DELETE /api/items/{item_id}
```

### Bulk Operations
```bash
# Bulk updates
POST /api/cost-codes-with-groups/bulk-update
POST /api/quotes/bulk-update
POST /api/items/bulk-update
POST /api/qty-takeoffs/bulk-update

# Import operations
POST /api/products/import
POST /api/items/import
POST /api/qty-takeoffs/import
POST /api/quotes/import
```

## 🔄 Development Workflow

### Git Repository
- **main**: Current production-ready state with web UI
- **Sync Status**: Fully synchronized with GitHub
- **Backups**: Timestamped backups before major changes

### Environment Setup
```bash
# Install Python dependencies
pip install -r web_ui/requirements.txt

# Set up database connection (environment variable)
# Database password should be set in environment or config
```

## 🆕 Recent Enhancements

- **AG-Grid Integration**: Professional data grids with enterprise features
- **Master-Detail Views**: Product vendor pricing shown in detail panels
- **Bulk Operations**: Import/export and bulk editing capabilities
- **Responsive Design**: Mobile-friendly interface
- **API Expansion**: Comprehensive REST API for all operations
- **Real-time Updates**: Live data synchronization with database
- **Enhanced Takeoffs View**: Advanced filtering and analysis capabilities
- **UI Performance Improvements**: Reduced page flashing and optimized caching
- **Plan Options Management**: New dedicated interface for plan options

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

## 📚 Documentation

- **README.md**: Technical overview (this file)
- **USER_README.md**: User-friendly guide for end users
- **DATABASE_README.md**: Detailed database schema documentation
- **ENHANCED_TAKEOFFS_README.md**: Guide for the enhanced takeoffs view
- **UI_PERFORMANCE_README.md**: Documentation on UI performance improvements
- **migrations/**: Chronological database evolution
- **archived/**: Historical files, deprecated/test/backup files, and verification queries

---

## 🗃️ Archived and Deprecated Files

The following files and folders have been archived for historical reference and are no longer part of the active system:

- **archived/cleanup_2025/test-diagnose/**: All connection testing and setup scripts
- **archived/cleanup_2025/backups/**: All backup scripts and timestamped backups
- **archived/cleanup_2025/logs/**: Application logs
- **archived/cleanup_2025/archived_old_views/**: Deprecated HTML views
- **archived/cleanup_2025/PlanElevOptions/**: All Excel source data files
- **archived/cleanup_2025/bulk_product_vendor_import.py**: Old bulk import tools
- **archived/cleanup_2025/consolidated-commands.sh**: Batch operation scripts
- **archived/cleanup_2025/new_data_loader.py**: Old data loader scripts
- **archived/old_loaders/**: Previous data loader scripts
- **archived/setup-optimizer.sh**: Old optimizer setup script

To restore any file or folder, simply copy it from the appropriate path under `archived/cleanup_2025/` back to your working directory.


- Database credentials managed through environment variables
- SQL injection protection via parameterized queries
- Input validation and sanitization
- Secure connection to Hostinger database

## 🛠️ Core Tech Stack

- **Backend**: Python 3.x with Flask web framework
- **Database**: PostgreSQL 13+ (hosted on Hostinger)
- **Frontend**: HTML5, CSS3, JavaScript with AG-Grid Enterprise
- **Data Processing**: Pandas for Excel/CSV handling
- **API**: RESTful API with JSON responses
- **Deployment**: Local development with remote database connection
- **Containerization**: Docker support for local development
- **Version Control**: Git with GitHub integration
- **Testing**: Python unittest and manual verification
- **Documentation**: Markdown-based documentation

---

**🎯 Production-Ready Construction Takeoff System**  
*Database ✓ | Web Interface ✓ | API ✓ | Documentation ✓*

**Quick Access**: Visit http://localhost:5000 after starting the web interface.
