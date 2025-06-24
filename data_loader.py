#!/usr/bin/env python3
"""
Data Loader for Construction Takeoff System
Loads Excel files from PlanElevOptions directory into PostgreSQL database
Based on Excel_Column_to_Database_Mapping.csv
"""

import os
import sys
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import logging
from datetime import datetime
import re

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'takeoff_pricing_db',
    'user': 'Jon',
    'password': 'Transplant4real'
}

class TakeoffDataLoader:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.plan_cache = {}
        self.elevation_cache = {}
        self.option_cache = {}
        self.cost_code_cache = {}
        self.vendor_cache = {}
        self.item_cache = {}
        self.product_cache = {}
        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            logger.info("Connected to database successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to connect to database: {e}")
            return False
    
    def close_db(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def parse_filename(self, filename):
        """Parse filename to extract plan, elevation, foundation, and option type"""
        # Format: PlanName_Elevation_Foundation_OptionType.xlsx
        # Example: Winchester_A_Basement_Base Home.xlsx
        
        parts = filename.replace('.xlsx', '').split('_')
        if len(parts) >= 4:
            plan_name = parts[0]
            elevation_name = parts[1]
            foundation = parts[2]
            option_type = '_'.join(parts[3:])  # Handle multi-word option types
            
            return {
                'plan_name': plan_name,
                'elevation_name': elevation_name,
                'foundation': foundation,
                'option_type': option_type
            }
        else:
            logger.warning(f"Could not parse filename: {filename}")
            return None
    
    def get_or_create_plan(self, plan_name):
        """Get or create a plan record"""
        if plan_name in self.plan_cache:
            return self.plan_cache[plan_name]
        
        # Check if plan exists
        self.cursor.execute("SELECT PlanID FROM pricing.TblPlans WHERE PlanName = %s", (plan_name,))
        result = self.cursor.fetchone()
        
        if result:
            plan_id = result['planid']
        else:
            # Create new plan
            self.cursor.execute("""
                INSERT INTO pricing.TblPlans (PlanName, IsActive)
                VALUES (%s, %s) RETURNING PlanID
            """, (plan_name, True))
            plan_id = self.cursor.fetchone()['planid']
            logger.info(f"Created new plan: {plan_name}")
        
        self.plan_cache[plan_name] = plan_id
        return plan_id
    
    def get_or_create_elevation(self, plan_id, elevation_name, foundation):
        """Get or create a plan elevation record"""
        cache_key = f"{plan_id}_{elevation_name}_{foundation}"
        if cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]
        
        # Check if elevation exists
        self.cursor.execute("""
            SELECT PlanElevationID FROM pricing.TblPlanElevations 
            WHERE PlanID = %s AND ElevationName = %s AND Foundation = %s
        """, (plan_id, elevation_name, foundation))
        result = self.cursor.fetchone()
        
        if result:
            elevation_id = result['planelevationid']
        else:
            # Create new elevation
            self.cursor.execute("""
                INSERT INTO pricing.TblPlanElevations (PlanID, ElevationName, Foundation, IsActive)
                VALUES (%s, %s, %s, %s) RETURNING PlanElevationID
            """, (plan_id, elevation_name, foundation, True))
            elevation_id = self.cursor.fetchone()['planelevationid']
            logger.info(f"Created new elevation: {elevation_name} for plan {plan_id}")
        
        self.elevation_cache[cache_key] = elevation_id
        return elevation_id
    
    def get_or_create_option_type(self, option_type_name):
        """Get or create an option type record"""
        if option_type_name in self.option_cache:
            return self.option_cache[option_type_name]
        
        # Check if option type exists
        self.cursor.execute("SELECT OptionTypeID FROM pricing.TblOptionTypes WHERE OptionTypeName = %s", (option_type_name,))
        result = self.cursor.fetchone()
        
        if result:
            option_type_id = result['optiontypeid']
        else:
            # Create new option type
            self.cursor.execute("""
                INSERT INTO pricing.TblOptionTypes (OptionTypeName, IsActive)
                VALUES (%s, %s) RETURNING OptionTypeID
            """, (option_type_name, True))
            option_type_id = self.cursor.fetchone()['optiontypeid']
            logger.info(f"Created new option type: {option_type_name}")
        
        self.option_cache[option_type_name] = option_type_id
        return option_type_id
    
    def get_or_create_cost_code(self, cost_group_name, cost_code, cost_code_description):
        """Get or create cost group and cost code"""
        cache_key = f"{cost_group_name}_{cost_code}"
        if cache_key in self.cost_code_cache:
            return self.cost_code_cache[cache_key]
        
        # Get or create cost group
        self.cursor.execute("SELECT CostGroupID FROM pricing.TblCostGroups WHERE CostGroupName = %s", (cost_group_name,))
        result = self.cursor.fetchone()
        
        if result:
            cost_group_id = result['costgroupid']
        else:
            self.cursor.execute("""
                INSERT INTO pricing.TblCostGroups (CostGroup, CostGroupName)
                VALUES (%s, %s) RETURNING CostGroupID
            """, (cost_group_name[:50], cost_group_name))
            cost_group_id = self.cursor.fetchone()['costgroupid']
        
        # Get or create cost code
        self.cursor.execute("""
            SELECT CostCodeID FROM pricing.TblCostCodes 
            WHERE CostGroupID = %s AND CostCode = %s
        """, (cost_group_id, cost_code))
        result = self.cursor.fetchone()
        
        if result:
            cost_code_id = result['costcodeid']
        else:
            self.cursor.execute("""
                INSERT INTO pricing.TblCostCodes (CostGroupID, CostCode, CostCodeDescription)
                VALUES (%s, %s, %s) RETURNING CostCodeID
            """, (cost_group_id, cost_code, cost_code_description))
            cost_code_id = self.cursor.fetchone()['costcodeid']
        
        self.cost_code_cache[cache_key] = cost_code_id
        return cost_code_id
    
    def get_or_create_vendor(self, vendor_name):
        """Get or create vendor"""
        if not vendor_name or pd.isna(vendor_name):
            return None
            
        if vendor_name in self.vendor_cache:
            return self.vendor_cache[vendor_name]
        
        self.cursor.execute("SELECT VendorID FROM pricing.TblVendors WHERE VendorName = %s", (vendor_name,))
        result = self.cursor.fetchone()
        
        if result:
            vendor_id = result['vendorid']
        else:
            self.cursor.execute("""
                INSERT INTO pricing.TblVendors (VendorName, IsActive)
                VALUES (%s, %s) RETURNING VendorID
            """, (vendor_name, True))
            vendor_id = self.cursor.fetchone()['vendorid']
        
        self.vendor_cache[vendor_name] = vendor_id
        return vendor_id
    
    def get_or_create_item_and_product(self, item_name, item_description, cost_code_id, qty_type):
        """Get or create item and product records"""
        cache_key = item_name
        if cache_key in self.item_cache:
            return self.item_cache[cache_key]
        
        # Get or create item
        self.cursor.execute("SELECT ItemID FROM pricing.TblItems WHERE ItemName = %s", (item_name,))
        result = self.cursor.fetchone()
        
        if result:
            item_id = result['itemid']
        else:
            self.cursor.execute("""
                INSERT INTO pricing.TblItems (ItemName, ItemType, CostCodeID, IsActive)
                VALUES (%s, %s, %s, %s) RETURNING ItemID
            """, (item_name, qty_type, cost_code_id, True))
            item_id = self.cursor.fetchone()['itemid']
        
        # Get or create product
        product_cache_key = f"{item_id}_{item_description}"
        if product_cache_key in self.product_cache:
            product_id = self.product_cache[product_cache_key]
        else:
            self.cursor.execute("""
                SELECT ProductID FROM pricing.TblProducts 
                WHERE ItemID = %s AND ProductDescription = %s
            """, (item_id, item_description))
            result = self.cursor.fetchone()
            
            if result:
                product_id = result['productid']
            else:
                self.cursor.execute("""
                    INSERT INTO pricing.TblProducts (ItemID, ProductDescription)
                    VALUES (%s, %s) RETURNING ProductID
                """, (item_id, item_description))
                product_id = self.cursor.fetchone()['productid']
            
            self.product_cache[product_cache_key] = product_id
        
        self.item_cache[cache_key] = (item_id, product_id)
        return item_id, product_id
    
    def process_excel_file(self, filepath):
        """Process a single Excel file"""
        try:
            filename = os.path.basename(filepath)
            logger.info(f"Processing file: {filename}")
            
            # Parse filename for plan/elevation info
            file_info = self.parse_filename(filename)
            if not file_info:
                return False
            
            # Read Excel file
            df = pd.read_excel(filepath)
            
            if df.empty:
                logger.warning(f"File {filename} is empty")
                return False
            
            # Get or create plan structure
            plan_id = self.get_or_create_plan(file_info['plan_name'])
            elevation_id = self.get_or_create_elevation(plan_id, file_info['elevation_name'], file_info['foundation'])
            option_type_id = self.get_or_create_option_type(file_info['option_type'])
            
            # Create plan elevation option
            self.cursor.execute("""
                INSERT INTO pricing.TblPlanElevationOptions (
                    PlanElevationID, OptionName, OptionTypeID
                ) VALUES (%s, %s, %s) RETURNING PlanElevationOptionID
            """, (elevation_id, file_info['option_type'], option_type_id))
            plan_elevation_option_id = self.cursor.fetchone()['planelevationoptionid']
            
            # Create job record for this takeoff
            job_number = f"{file_info['plan_name']}_{file_info['elevation_name']}_{file_info['foundation']}_{file_info['option_type']}"
            self.cursor.execute("""
                INSERT INTO pricing.TblJobs (
                    JobNumber, PlanElevationOptionID, IsTemplate
                ) VALUES (%s, %s, %s) RETURNING JobID
            """, (job_number, plan_elevation_option_id, True))
            job_id = self.cursor.fetchone()['jobid']
            
            # Process each row in the Excel file
            processed_rows = 0
            for idx, row in df.iterrows():
                try:
                    # Extract data from row (adjust column names based on your Excel structure)
                    cost_group_name = row.get('CostGroupName', '')
                    cost_code = row.get('CostCodeNumber', '')
                    cost_code_description = row.get('CostCodeDescription', '')
                    item_name = row.get('Item', '')
                    item_description = row.get('ItemDescription', '')
                    qty_type = row.get('QtyType', '')
                    quantity = row.get('QTY', 0)
                    extended_price = row.get('ExtendedPrice', 0)
                    vendor_name = row.get('Vendor', '')
                    notes = row.get('Notes', '')
                    
                    # Skip rows with missing critical data
                    if not item_name or pd.isna(item_name):
                        continue
                    
                    # Clean and validate data
                    quantity = float(quantity) if pd.notna(quantity) else 0
                    extended_price = float(extended_price) if pd.notna(extended_price) else 0
                    
                    # Get or create related records
                    cost_code_id = self.get_or_create_cost_code(cost_group_name, cost_code, cost_code_description)
                    vendor_id = self.get_or_create_vendor(vendor_name)
                    item_id, product_id = self.get_or_create_item_and_product(item_name, item_description, cost_code_id, qty_type)
                    
                    # Calculate unit price
                    unit_price = extended_price / quantity if quantity > 0 else 0
                    
                    # Insert takeoff record
                    self.cursor.execute("""
                        INSERT INTO pricing.TblTakeoffs (
                            JobID, ProductID, Quantity, UnitPrice, ExtendedPrice, 
                            VendorID, Notes, Status
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """, (job_id, product_id, quantity, unit_price, extended_price, 
                          vendor_id, notes, 'Active'))
                    
                    processed_rows += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing row {idx} in {filename}: {e}")
                    continue
            
            self.conn.commit()
            logger.info(f"Successfully processed {processed_rows} rows from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
            self.conn.rollback()
            return False
    
    def load_all_files(self, directory='PlanElevOptions'):
        """Load all Excel files from the specified directory"""
        if not os.path.exists(directory):
            logger.error(f"Directory {directory} does not exist")
            return False
        
        if not self.connect_db():
            return False
        
        try:
            files_processed = 0
            files_failed = 0
            
            for filename in os.listdir(directory):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(directory, filename)
                    if self.process_excel_file(filepath):
                        files_processed += 1
                    else:
                        files_failed += 1
            
            logger.info(f"Processing complete. Files processed: {files_processed}, Files failed: {files_failed}")
            return True
            
        finally:
            self.close_db()

def main():
    """Main execution function"""
    loader = TakeoffDataLoader()
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = 'PlanElevOptions'
    
    logger.info(f"Starting data load from directory: {directory}")
    success = loader.load_all_files(directory)
    
    if success:
        logger.info("Data loading completed successfully")
        return 0
    else:
        logger.error("Data loading failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 