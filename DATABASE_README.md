# Construction Takeoff Database System

This database system is designed to manage construction takeoff data, organize it by Plan/Elevation/Option combinations, and provide normalized storage for efficient reuse and comparison. **Connected to live Hostinger PostgreSQL database at 31.97.137.221:5432.**

## 📑 Table of Contents
- [Database Structure](#database-structure)
- [Database Connection](#database-connection)
- [Excel File Format](#excel-file-format)
- [Database Views for Analysis](#database-views-for-analysis)
- [Useful Queries](#useful-queries)
- [Database Connection Methods](#database-connection-methods)
- [Data Loading](#data-loading)
- [Database Maintenance](#database-maintenance)
- [Data Integrity Features](#data-integrity-features)
- [Current Database Statistics](#current-database-statistics-live-from-hostinger)
- [Troubleshooting](#troubleshooting)
- [API Integration](#api-integration)
- [Next Steps](#next-steps)
- [Support](#support)
- [Core Tech Stack](#core-tech-stack)

## Database Structure

### Core Hierarchy
```
takeoff.plans (Winchester, Oxford, etc.)
  └── takeoff.plan_elevations (A, B, C + Foundation type)
      └── takeoff.plan_options (Base Home, Design Option, Structural)
          └── takeoff.jobs (Individual takeoffs)
              └── takeoff.takeoffs (Line items)
```

### Key Features

1. **Normalized Data**: Items, products, vendors, and cost codes are normalized for reuse
2. **Flexible Options**: Support for Base Home, Design Options, and Structural packages
3. **Square Footage Tracking**: Multiple measurement types (Inside/Outside Studs, Veneer, Heated/Unheated)
4. **Cost Management**: Hierarchical cost groups and codes
5. **Version Control**: Support for plan versions and current version tracking
6. **Audit Trail**: Timestamps and update tracking on all tables
7. **Vendor Pricing**: Historical price tracking with current pricing views
8. **Quote Management**: Formal quote workflow with attachments

## Database Connection

### Live Hostinger PostgreSQL Database
- **Host**: 31.97.137.221
- **Port**: 5432
- **Database**: takeoff_pricing_db
- **User**: Jon
- **Schema**: takeoff (all tables are in the 'takeoff' schema)

### Quick Start
```bash
# Start web interface
cd web_ui
python app.py
```

### Python Dependencies
```bash
# Install required packages
pip install pandas openpyxl psycopg2-binary flask
```

## Excel File Format

Your Excel files should follow this naming convention:
```
PlanName_Elevation_Foundation_OptionType.xlsx
```

Examples:
- `Winchester_A_Basement_Base Home.xlsx`
- `Oxford_A_Basement_Design Option.xlsx` 
- `Barringer_A_Crawl_Structural.xlsx`

### Required Excel Columns
Based on your data structure, ensure your Excel files contain these columns:

| Excel Column | Database Field | Required |
|-------------|----------------|----------|
| Plan | takeoff.plans.plan_name | Yes |
| Elevation | takeoff.plan_elevations.elevation_name | Yes |
| Foundation | takeoff.plan_elevations.foundation | Yes |
| CostGroup | takeoff.cost_groups.cost_group_name | Yes |
| CostCodeNumber | takeoff.cost_codes.cost_code | Yes |
| CostCodeDescription | takeoff.cost_codes.cost_code_description | Yes |
| Item | takeoff.items.item_name | Yes |
| ItemDescription | takeoff.products.item_description | Yes |
| QTY | takeoff.takeoffs.quantity | Yes |
| ExtendedPrice | takeoff.takeoffs.extended_price | Yes |
| Vendor | takeoff.vendors.vendor_name | No |
| Notes | takeoff.takeoffs.notes | No |
| Price | takeoff.takeoffs.unit_price | No |

## Database Views for Analysis

### 1. Cost Codes with Groups View
```sql
-- View combining cost codes with their groups
SELECT * FROM takeoff.v_cost_codes_with_groups;
```

### 2. Current Vendor Pricing View
```sql
-- View showing current vendor pricing for all products
SELECT * FROM takeoff.v_current_vendor_pricing
ORDER BY cost_code, vendor_name;
```

### 3. Comprehensive Takeoff Analysis View
```sql
-- Complete takeoff analysis with all related data
SELECT * FROM takeoff.v_comprehensive_takeoff_analysis
WHERE plan_name = 'Winchester';
```

### 4. Plans, Elevations, and Options View
```sql
-- Hierarchical view of all plans with their options
SELECT * FROM takeoff.v_plans_elevations_options
ORDER BY plan_name, elevation_name, option_name;
```

## Useful Queries

### 1. Compare Costs Between Options
```sql
-- Compare total costs between Base Home, Design Option, and Structural for same plan/elevation
SELECT 
    p.plan_name,
    pe.elevation_name,
    pe.foundation,
    po.option_type,
    SUM(t.extended_price) as total_cost,
    COUNT(t.takeoff_id) as line_items
FROM takeoff.takeoffs t
JOIN takeoff.jobs j ON t.job_id = j.job_id
JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
JOIN takeoff.plans p ON pe.plan_id = p.plan_id
GROUP BY p.plan_name, pe.elevation_name, pe.foundation, po.option_type
ORDER BY p.plan_name, pe.elevation_name, po.option_type;
```

### 2. Cost Breakdown by Cost Group
```sql
-- Get cost breakdown by cost group for a specific plan/elevation/option
SELECT 
    cg.cost_group_name,
    SUM(t.extended_price) as group_total,
    COUNT(t.takeoff_id) as line_items,
    AVG(t.extended_price) as avg_line_item
FROM takeoff.takeoffs t
JOIN takeoff.products pr ON t.product_id = pr.product_id
JOIN takeoff.items i ON pr.item_id = i.item_id
JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
JOIN takeoff.cost_groups cg ON cc.cost_group_id = cg.cost_group_id
JOIN takeoff.jobs j ON t.job_id = j.job_id
JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
JOIN takeoff.plans p ON pe.plan_id = p.plan_id
WHERE p.plan_name = 'Winchester' 
  AND pe.elevation_name = 'A' 
  AND pe.foundation = 'Basement'
GROUP BY cg.cost_group_name
ORDER BY group_total DESC;
```

### 3. Find Most Expensive Items Across All Plans
```sql
-- Top 20 most expensive line items across all takeoffs
SELECT 
    p.plan_name,
    pe.elevation_name || ' - ' || pe.foundation as elevation,
    po.option_type,
    i.item_name,
    pr.item_description,
    t.quantity,
    t.unit_price,
    t.extended_price,
    cg.cost_group_name
FROM takeoff.takeoffs t
JOIN takeoff.products pr ON t.product_id = pr.product_id
JOIN takeoff.items i ON pr.item_id = i.item_id
JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
JOIN takeoff.cost_groups cg ON cc.cost_group_id = cg.cost_group_id
JOIN takeoff.jobs j ON t.job_id = j.job_id
JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
JOIN takeoff.plans p ON pe.plan_id = p.plan_id
ORDER BY t.extended_price DESC
LIMIT 20;
```

### 4. Plan Comparison Summary
```sql
-- Summary of all plans with totals by option type
SELECT 
    p.plan_name,
    pe.elevation_name,
    pe.foundation,
    COUNT(CASE WHEN po.option_type LIKE '%Base%' THEN 1 END) as has_base_home,
    COUNT(CASE WHEN po.option_type LIKE '%Design%' THEN 1 END) as has_design_option,
    COUNT(CASE WHEN po.option_type LIKE '%Structural%' THEN 1 END) as has_structural,
    SUM(CASE WHEN po.option_type LIKE '%Base%' THEN t.extended_price ELSE 0 END) as base_home_cost,
    SUM(CASE WHEN po.option_type LIKE '%Design%' THEN t.extended_price ELSE 0 END) as design_option_cost,
    SUM(CASE WHEN po.option_type LIKE '%Structural%' THEN t.extended_price ELSE 0 END) as structural_cost
FROM takeoff.takeoffs t
JOIN takeoff.jobs j ON t.job_id = j.job_id
JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
JOIN takeoff.plans p ON pe.plan_id = p.plan_id
GROUP BY p.plan_name, pe.elevation_name, pe.foundation
ORDER BY p.plan_name, pe.elevation_name;
```

### 5. Vendor Analysis
```sql
-- Vendor usage and spending analysis
SELECT 
    v.vendor_name,
    COUNT(DISTINCT p.plan_name) as plans_used,
    COUNT(t.takeoff_id) as line_items,
    SUM(t.extended_price) as total_spending,
    AVG(t.extended_price) as avg_line_item,
    COUNT(DISTINCT vp.pricing_id) as pricing_records
FROM takeoff.takeoffs t
JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
LEFT JOIN takeoff.vendor_pricing vp ON v.vendor_id = vp.vendor_id AND vp.is_current = true
JOIN takeoff.jobs j ON t.job_id = j.job_id
JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
JOIN takeoff.plans p ON pe.plan_id = p.plan_id
GROUP BY v.vendor_name
ORDER BY total_spending DESC;
```

### 6. Vendor Pricing Analysis
```sql
-- Current vendor pricing with price ranges
SELECT 
    i.item_name,
    COUNT(DISTINCT v.vendor_name) as vendor_count,
    MIN(vp.price) as min_price,
    MAX(vp.price) as max_price,
    AVG(vp.price) as avg_price,
    (MAX(vp.price) - MIN(vp.price)) as price_range
FROM takeoff.v_current_vendor_pricing vp
JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
JOIN takeoff.items i ON vp.item_name = i.item_name
GROUP BY i.item_name
HAVING COUNT(DISTINCT v.vendor_name) > 1
ORDER BY price_range DESC;
```

## Database Connection Methods

### Direct PostgreSQL Connection
```bash
# Connect using psql (if installed locally)
psql -h 31.97.137.221 -p 5432 -U Jon -d takeoff_pricing_db

# Or using pgAdmin with these settings:
# Host: 31.97.137.221
# Port: 5432
# Database: takeoff_pricing_db
# Username: Jon
# Schema: takeoff
```

### Python Connection
```python
# Using the config system (recommended)
from config import DB_CONFIG
import psycopg2
from psycopg2.extras import RealDictCursor

# Connect to Hostinger database
conn = psycopg2.connect(**DB_CONFIG.to_dict())
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Example query
cursor.execute("SELECT * FROM takeoff.plans ORDER BY plan_name")
plans = cursor.fetchall()

# Manual connection
conn = psycopg2.connect(
    host='31.97.137.221',
    port=5432,
    database='takeoff_pricing_db',
    user='Jon',
    password='Transplant4real'
)
```

### Web Interface API
```bash
# REST API endpoints available at:
# http://localhost:5000/api/plans
# http://localhost:5000/api/plan-options
# http://localhost:5000/api/products
# http://localhost:5000/api/vendor-pricing
# http://localhost:5000/api/cost-codes-with-groups
# http://localhost:5000/api/qty-takeoffs
# http://localhost:5000/api/quotes
# http://localhost:5000/api/items
```

## Data Loading

### Excel Data Loader
```bash
# Load Excel files (old PlanElevOptions directory is now archived)
python scripts/new_data_loader.py /path/to/excel/files
```
> **Note:** If you need to restore archived Excel files, copy them from `archived/cleanup_2025/PlanElevOptions/` to your working directory.

### Bulk Import Tools
```bash
# Import product and vendor data from CSV
python scripts/bulk_product_vendor_import.py products.csv vendor_pricing.csv
```

## Database Maintenance

### Backup Database
> **Note:** Backup scripts are now archived. Use your preferred backup method or restore from `archived/cleanup_2025/backups/` if needed.

### Connection Testing
> **Note:** Old test scripts are now archived. Use the web interface dashboard to verify connection status.

## Data Integrity Features

1. **Foreign Key Constraints**: Ensure referential integrity between all related tables
2. **Automatic Timestamps**: created_date and updated_date fields automatically managed
3. **Default Values**: Sensible defaults for optional fields
4. **Indexes**: Optimized for common query patterns and joins
5. **Data Types**: Proper precision for monetary values (DECIMAL for prices)
6. **Vendor Pricing History**: Complete audit trail of price changes
7. **Current Pricing Views**: Always shows latest active pricing

## Current Database Statistics (Live from Hostinger)

- **Plans**: 6 (Winchester, Oxford, Barringer, Calderwood, Croydonette, Sandbrook)
- **Plan Elevations**: 7 (various A/B/C elevations with foundation types)
- **Plan Options**: 22 (Base Home, Design Options, Structural packages)
- **Jobs**: 21 (template jobs for each plan/elevation/option combination)
- **Takeoffs**: 2,321+ line items with detailed cost breakdowns
- **Vendors**: 62 active vendors and contractors
- **Vendor Pricing**: 229+ current pricing records
- **Cost Codes**: 90 organized cost codes with groups
- **Products**: Thousands of construction products and materials
- **Database Tables**: 26 total tables and views

## Troubleshooting

### Common Issues

1. **Connection timeout**: Check internet connection to Hostinger servers
2. **Authentication failed**: Verify username and password in config
3. **Schema not found**: Ensure you're connecting to 'takeoff_pricing_db' database
4. **Excel file format**: Ensure files are .xlsx format with correct column headers
5. **Python dependencies**: Install all required packages with pip

### Diagnostic Tools

```bash
# Check system status
# Navigate to http://localhost:5000 after starting web interface

# View system logs
# (Archived; contact admin if historical logs are needed)
```

### Performance Optimization

1. **Use Views**: Predefined views are optimized for common queries
2. **Filter Early**: Use WHERE clauses to limit data before JOINs
3. **Index Usage**: The system includes indexes on commonly queried fields
4. **Connection Pooling**: Web interface uses connection pooling for efficiency

## API Integration

### REST Endpoints
The web interface provides comprehensive REST API access:

```bash
# Table data
GET /api/plans
GET /api/plan-options
GET /api/products  
GET /api/vendor-pricing
GET /api/cost-codes-with-groups
GET /api/qty-takeoffs
GET /api/quotes
GET /api/items

# CRUD operations
POST /api/plans
PUT /api/plans/{plan_id}
DELETE /api/plans/{plan_id}

# Bulk operations
POST /api/cost-codes-with-groups/bulk-update
POST /api/products/import
POST /api/qty-takeoffs/bulk-update
```

## Next Steps

1. **Explore the Data**: Use the web interface at http://localhost:5000
2. **Run Queries**: Try the example queries above to understand your data
3. **Load New Data**: Use the data loader for additional Excel files
4. **Customize Reports**: Modify queries for your specific reporting needs
5. **Build Integrations**: Use the REST API for custom applications

## Support

This database structure accommodates your specific workflow of:
- Organizing takeoffs by Plan/Elevation/Option hierarchy
- Comparing different option types and configurations
- Analyzing costs by cost groups and codes
- Managing vendor relationships and pricing history
- Supporting both normalized data and detailed takeoffs
- Providing real-time web interface for daily operations

The system is designed to scale and can handle additional plans, options, and data fields as your construction business evolves.

## Core Tech Stack

- **Database**: PostgreSQL 13+ (hosted on Hostinger)
- **Database Schema**: 26 tables and views in the 'takeoff' schema
- **Database Connectivity**: psycopg2-binary for Python connections
- **Data Processing**: Pandas for Excel/CSV handling
- **API Layer**: Flask-based RESTful API
- **Query Optimization**: Indexed views for common query patterns
- **Data Integrity**: Foreign key constraints and transaction support
- **Security**: Connection credentials managed via environment variables
- **Backup System**: (Scripts now archived; see `archived/cleanup_2025/backups/` for historical backups)
