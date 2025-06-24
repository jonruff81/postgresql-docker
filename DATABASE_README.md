# Construction Takeoff Database System

This database system is designed to manage construction takeoff data, organize it by Plan/Elevation/Option combinations, and provide normalized storage for efficient reuse and comparison.

## Database Structure

### Core Hierarchy
```
TblPlans (Winchester, Oxford, etc.)
  └── TblPlanElevations (A, B, C + Foundation type)
      └── TblPlanElevationOptions (Base Home, Design Option, Structural)
          └── TblJobs (Individual takeoffs)
              └── TblTakeoffs (Line items)
```

### Key Features

1. **Normalized Data**: Items, products, vendors, and cost codes are normalized for reuse
2. **Flexible Options**: Support for Base Home, Design Options, and Structural packages
3. **Square Footage Tracking**: Multiple measurement types (Inside/Outside Studs, Veneer, Heated/Unheated)
4. **Cost Management**: Hierarchical cost groups and codes
5. **Version Control**: Support for plan versions and current version tracking
6. **Audit Trail**: Timestamps and update tracking on all tables

## Setup Instructions

### 1. Initialize Database
```bash
# Make setup script executable
chmod +x setup_database.sh

# Run setup (this will recreate the database)
./setup_database.sh
```

### 2. Install Python Dependencies
```bash
# Using pip
pip install pandas openpyxl psycopg2-binary

# Or using conda
conda install pandas openpyxl psycopg2
```

### 3. Load Data from Excel Files
```bash
# Load all files from PlanElevOptions directory
python3 data_loader.py

# Or specify a different directory
python3 data_loader.py /path/to/excel/files
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
Based on your mapping file, ensure your Excel files contain these columns:

| Excel Column | Database Field | Required |
|-------------|----------------|----------|
| Plan | TblPlans.PlanName | Yes |
| Elevation | TblPlanElevations.ElevationName | Yes |
| Foundation | TblPlanElevations.Foundation | Yes |
| CostGroupName | TblCostGroups.CostGroupName | Yes |
| CostCodeNumber | TblCostCodes.CostCode | Yes |
| CostCodeDescription | TblCostCodes.CostCodeDescription | Yes |
| Item | TblItems.ItemName | Yes |
| ItemDescription | TblProducts.ProductDescription | Yes |
| QTY | TblTakeoffs.Quantity | Yes |
| ExtendedPrice | TblTakeoffs.ExtendedPrice | Yes |
| Vendor | TblVendors.VendorName | No |
| Notes | TblTakeoffs.Notes | No |

## Useful Queries

### 1. Compare Costs Between Options
```sql
-- Compare total costs between Base Home, Design Option, and Structural for same plan/elevation
SELECT 
    p.PlanName,
    pe.ElevationName,
    pe.Foundation,
    ot.OptionTypeName,
    SUM(t.ExtendedPrice) as TotalCost,
    COUNT(t.TakeoffID) as LineItems
FROM pricing.TblTakeoffs t
JOIN pricing.TblJobs j ON t.JobID = j.JobID
JOIN pricing.TblPlanElevationOptions peo ON j.PlanElevationOptionID = peo.PlanElevationOptionID
JOIN pricing.TblOptionTypes ot ON peo.OptionTypeID = ot.OptionTypeID
JOIN pricing.TblPlanElevations pe ON peo.PlanElevationID = pe.PlanElevationID
JOIN pricing.TblPlans p ON pe.PlanID = p.PlanID
GROUP BY p.PlanName, pe.ElevationName, pe.Foundation, ot.OptionTypeName
ORDER BY p.PlanName, pe.ElevationName, ot.OptionTypeName;
```

### 2. Cost Breakdown by Cost Group
```sql
-- Get cost breakdown by cost group for a specific plan/elevation/option
SELECT 
    cg.CostGroupName,
    SUM(t.ExtendedPrice) as GroupTotal,
    COUNT(t.TakeoffID) as LineItems,
    AVG(t.ExtendedPrice) as AvgLineItem
FROM pricing.TblTakeoffs t
JOIN pricing.TblProducts pr ON t.ProductID = pr.ProductID
JOIN pricing.TblItems i ON pr.ItemID = i.ItemID
JOIN pricing.TblCostCodes cc ON i.CostCodeID = cc.CostCodeID
JOIN pricing.TblCostGroups cg ON cc.CostGroupID = cg.CostGroupID
JOIN pricing.TblJobs j ON t.JobID = j.JobID
JOIN pricing.TblPlanElevationOptions peo ON j.PlanElevationOptionID = peo.PlanElevationOptionID
JOIN pricing.TblPlanElevations pe ON peo.PlanElevationID = pe.PlanElevationID
JOIN pricing.TblPlans p ON pe.PlanID = p.PlanID
WHERE p.PlanName = 'Winchester' 
  AND pe.ElevationName = 'A' 
  AND pe.Foundation = 'Basement'
GROUP BY cg.CostGroupName
ORDER BY GroupTotal DESC;
```

### 3. Find Most Expensive Items Across All Plans
```sql
-- Top 20 most expensive line items across all takeoffs
SELECT 
    p.PlanName,
    pe.ElevationName || ' - ' || pe.Foundation as Elevation,
    ot.OptionTypeName,
    i.ItemName,
    pr.ProductDescription,
    t.Quantity,
    t.UnitPrice,
    t.ExtendedPrice,
    cg.CostGroupName
FROM pricing.TblTakeoffs t
JOIN pricing.TblProducts pr ON t.ProductID = pr.ProductID
JOIN pricing.TblItems i ON pr.ItemID = i.ItemID
JOIN pricing.TblCostCodes cc ON i.CostCodeID = cc.CostCodeID
JOIN pricing.TblCostGroups cg ON cc.CostGroupID = cg.CostGroupID
JOIN pricing.TblJobs j ON t.JobID = j.JobID
JOIN pricing.TblPlanElevationOptions peo ON j.PlanElevationOptionID = peo.PlanElevationOptionID
JOIN pricing.TblOptionTypes ot ON peo.OptionTypeID = ot.OptionTypeID
JOIN pricing.TblPlanElevations pe ON peo.PlanElevationID = pe.PlanElevationID
JOIN pricing.TblPlans p ON pe.PlanID = p.PlanID
ORDER BY t.ExtendedPrice DESC
LIMIT 20;
```

### 4. Plan Comparison Summary
```sql
-- Summary of all plans with totals by option type
SELECT 
    p.PlanName,
    pe.ElevationName,
    pe.Foundation,
    COUNT(CASE WHEN ot.OptionTypeName LIKE '%Base%' THEN 1 END) as HasBaseHome,
    COUNT(CASE WHEN ot.OptionTypeName LIKE '%Design%' THEN 1 END) as HasDesignOption,
    COUNT(CASE WHEN ot.OptionTypeName LIKE '%Structural%' THEN 1 END) as HasStructural,
    SUM(CASE WHEN ot.OptionTypeName LIKE '%Base%' THEN t.ExtendedPrice ELSE 0 END) as BaseHomeCost,
    SUM(CASE WHEN ot.OptionTypeName LIKE '%Design%' THEN t.ExtendedPrice ELSE 0 END) as DesignOptionCost,
    SUM(CASE WHEN ot.OptionTypeName LIKE '%Structural%' THEN t.ExtendedPrice ELSE 0 END) as StructuralCost
FROM pricing.TblTakeoffs t
JOIN pricing.TblJobs j ON t.JobID = j.JobID
JOIN pricing.TblPlanElevationOptions peo ON j.PlanElevationOptionID = peo.PlanElevationOptionID
JOIN pricing.TblOptionTypes ot ON peo.OptionTypeID = ot.OptionTypeID
JOIN pricing.TblPlanElevations pe ON peo.PlanElevationID = pe.PlanElevationID
JOIN pricing.TblPlans p ON pe.PlanID = p.PlanID
GROUP BY p.PlanName, pe.ElevationName, pe.Foundation
ORDER BY p.PlanName, pe.ElevationName;
```

### 5. Vendor Analysis
```sql
-- Vendor usage and spending analysis
SELECT 
    v.VendorName,
    COUNT(DISTINCT p.PlanName) as PlansUsed,
    COUNT(t.TakeoffID) as LineItems,
    SUM(t.ExtendedPrice) as TotalSpending,
    AVG(t.ExtendedPrice) as AvgLineItem
FROM pricing.TblTakeoffs t
JOIN pricing.TblVendors v ON t.VendorID = v.VendorID
JOIN pricing.TblJobs j ON t.JobID = j.JobID
JOIN pricing.TblPlanElevationOptions peo ON j.PlanElevationOptionID = peo.PlanElevationOptionID
JOIN pricing.TblPlanElevations pe ON peo.PlanElevationID = pe.PlanElevationID
JOIN pricing.TblPlans p ON pe.PlanID = p.PlanID
GROUP BY v.VendorName
ORDER BY TotalSpending DESC;
```

## Database Connection

### Direct PostgreSQL Connection
```bash
# Connect via Docker
docker exec -it takeoff_postgres psql -U Jon -d takeoff_pricing_db

# Connect via local psql (if installed)
psql -h localhost -p 5432 -U Jon -d takeoff_pricing_db
```

### Python Connection
```python
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='takeoff_pricing_db',
    user='Jon',
    password='Transplant4real'
)
cursor = conn.cursor(cursor_factory=RealDictCursor)
```

## Data Integrity Features

1. **Foreign Key Constraints**: Ensure referential integrity
2. **Cascading Updates**: UpdatedAt fields automatically updated
3. **Default Values**: Sensible defaults for optional fields
4. **Indexes**: Optimized for common query patterns
5. **Data Types**: Proper precision for monetary values

## Troubleshooting

### Common Issues

1. **Docker not running**: Ensure Docker Desktop is started
2. **Port conflicts**: Check if port 5432 is available
3. **Excel file format**: Ensure files are .xlsx format with correct column headers
4. **Python dependencies**: Install all required packages

### Logging

The data loader provides detailed logging. Check the output for:
- Files processed successfully
- Rows skipped due to missing data
- Database connection issues
- Data validation errors

## Next Steps

1. **Load your data**: Run the data loader on your Excel files
2. **Verify data**: Use the provided queries to check data integrity
3. **Customize queries**: Modify the example queries for your specific needs
4. **Add business logic**: Implement any additional calculations or rules
5. **Build reports**: Create views or stored procedures for common reports

## Support

This database structure accommodates your specific workflow of:
- Grouping takeoffs by Plan/Elevation/Option
- Comparing different option types
- Analyzing costs by cost groups and codes
- Supporting both normalized data and detailed takeoffs

The system is designed to scale and can handle additional plans, options, and data fields as your needs evolve. 