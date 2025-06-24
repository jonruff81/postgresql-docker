#!/usr/bin/env python3
"""
Phase 1 Data Loader for Construction Takeoff System
Loads Excel template files into the simplified database structure
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

class Phase1DataLoader:
    def __init__(self):
        self.conn = None
        self.cursor = None
        # Caching for performance
        self.division_cache = {}
        self.community_cache = {}
        self.plan_cache = {}
        self.plan_elevation_cache = {}
        self.plan_option_cache = {}
        self.cost_group_cache = {}
        self.cost_code_cache = {}
        self.vendor_cache = {}
        self.item_cache = {}
        self.product_cache = {}
        
    def connect_db(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            self.cursor.execute("SET search_path TO takeoff, public")
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
        """Parse filename: PlanName_Elevation_Foundation_OptionType.xlsx"""
        parts = filename.replace('.xlsx', '').replace(' ', '_').split('_')
        if len(parts) >= 4:
            plan_name = parts[0]
            elevation_name = parts[1] 
            foundation = parts[2]
            option_name = ' '.join(parts[3:]).replace('_', ' ')  # Handle "Base Home"
            
            return {
                'plan_name': plan_name,
                'elevation_name': elevation_name,
                'foundation': foundation,
                'option_name': option_name
            }
        else:
            logger.warning(f"Could not parse filename: {filename}")
            return None
    
    def safe_int(self, value):
        """Safely convert to int"""
        if pd.isna(value) or value == '':
            return None
        try:
            return int(float(value))
        except:
            return None
    
    def safe_float(self, value):
        """Safely convert to float"""
        if pd.isna(value) or value == '':
            return None
        try:
            return float(value)
        except:
            return None
    
    def safe_date(self, value):
        """Safely convert to date"""
        if pd.isna(value) or value == '':
            return None
        try:
            if isinstance(value, str):
                return pd.to_datetime(value).date()
            return value
        except:
            return None
    
    def get_or_create_division(self, division_name):
        """Get or create division"""
        if not division_name or pd.isna(division_name):
            return None
            
        if division_name in self.division_cache:
            return self.division_cache[division_name]
        
        self.cursor.execute("SELECT division_id FROM divisions WHERE division_name = %s", (division_name,))
        result = self.cursor.fetchone()
        
        if result:
            division_id = result['division_id']
        else:
            self.cursor.execute("""
                INSERT INTO divisions (division_name) VALUES (%s) RETURNING division_id
            """, (division_name,))
            division_id = self.cursor.fetchone()['division_id']
            logger.info(f"Created division: {division_name}")
        
        self.division_cache[division_name] = division_id
        return division_id
    
    def get_or_create_community(self, community_name, division_id):
        """Get or create community"""
        if not community_name or pd.isna(community_name):
            return None
            
        cache_key = f"{division_id}_{community_name}"
        if cache_key in self.community_cache:
            return self.community_cache[cache_key]
        
        self.cursor.execute("""
            SELECT community_id FROM communities 
            WHERE community_name = %s AND division_id = %s
        """, (community_name, division_id))
        result = self.cursor.fetchone()
        
        if result:
            community_id = result['community_id']
        else:
            self.cursor.execute("""
                INSERT INTO communities (community_name, division_id) 
                VALUES (%s, %s) RETURNING community_id
            """, (community_name, division_id))
            community_id = self.cursor.fetchone()['community_id']
            logger.info(f"Created community: {community_name}")
        
        self.community_cache[cache_key] = community_id
        return community_id
    
    def get_or_create_plan(self, plan_name, architect=None, engineer=None):
        """Get or create plan"""
        if plan_name in self.plan_cache:
            return self.plan_cache[plan_name]
        
        self.cursor.execute("SELECT plan_id FROM plans WHERE plan_name = %s", (plan_name,))
        result = self.cursor.fetchone()
        
        if result:
            plan_id = result['plan_id']
        else:
            self.cursor.execute("""
                INSERT INTO plans (plan_name, architect, engineer) 
                VALUES (%s, %s, %s) RETURNING plan_id
            """, (plan_name, architect, engineer))
            plan_id = self.cursor.fetchone()['plan_id']
            logger.info(f"Created plan: {plan_name}")
        
        self.plan_cache[plan_name] = plan_id
        return plan_id
    
    def get_or_create_plan_elevation(self, plan_id, elevation_name, foundation, row_data):
        """Get or create plan elevation with square footage data"""
        cache_key = f"{plan_id}_{elevation_name}_{foundation}"
        if cache_key in self.plan_elevation_cache:
            return self.plan_elevation_cache[cache_key]
        
        self.cursor.execute("""
            SELECT plan_elevation_id FROM plan_elevations 
            WHERE plan_id = %s AND elevation_name = %s AND foundation = %s
        """, (plan_id, elevation_name, foundation))
        result = self.cursor.fetchone()
        
        if result:
            plan_elevation_id = result['plan_elevation_id']
        else:
            # Extract square footage and other data from row
            self.cursor.execute("""
                INSERT INTO plan_elevations (
                    plan_id, elevation_name, foundation, 
                    heated_sf_inside_studs, heated_sf_outside_studs, heated_sf_outside_veneer,
                    unheated_sf_inside_studs, unheated_sf_outside_studs, unheated_sf_outside_veneer,
                    total_sf_inside_studs, total_sf_outside_studs, total_sf_outside_veneer,
                    stair_count, bedroom_count, bathroom_count,
                    version_number, version_date
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) 
                RETURNING plan_elevation_id
            """, (
                plan_id, elevation_name, foundation,
                self.safe_int(row_data.get('HeatedSF(InsideStuds)')),
                self.safe_int(row_data.get('HeatedSF(OutsideStuds)')),
                self.safe_int(row_data.get('HeatedSF(OutsideVeneer)')),
                self.safe_int(row_data.get('UnHeatedSF(InsideStuds)')),
                self.safe_int(row_data.get('UnHeatedSF(OutsideStuds)')),
                self.safe_int(row_data.get('UnHeatedSF(OutsideVeneer)')),
                self.safe_int(row_data.get('TotalSF(InsideStuds)')),
                self.safe_int(row_data.get('TotalSF(OutsideStuds)')),
                self.safe_int(row_data.get('TotalSF(OutsideVeneer)')),
                self.safe_int(row_data.get('StairCount')),
                self.safe_int(row_data.get('Beds')),
                self.safe_float(row_data.get('Baths')),
                row_data.get('VersionNumber'),
                self.safe_date(row_data.get('VersionDate'))
            ))
            plan_elevation_id = self.cursor.fetchone()['plan_elevation_id']
            logger.info(f"Created plan elevation: {elevation_name} - {foundation}")
        
        self.plan_elevation_cache[cache_key] = plan_elevation_id
        return plan_elevation_id
    
    def get_or_create_plan_option(self, plan_elevation_id, option_name, option_type, option_description=None):
        """Get or create plan option"""
        cache_key = f"{plan_elevation_id}_{option_name}"
        if cache_key in self.plan_option_cache:
            return self.plan_option_cache[cache_key]
        
        self.cursor.execute("""
            SELECT plan_option_id FROM plan_options 
            WHERE plan_elevation_id = %s AND option_name = %s
        """, (plan_elevation_id, option_name))
        result = self.cursor.fetchone()
        
        if result:
            plan_option_id = result['plan_option_id']
        else:
            self.cursor.execute("""
                INSERT INTO plan_options (plan_elevation_id, option_name, option_type, option_description) 
                VALUES (%s, %s, %s, %s) RETURNING plan_option_id
            """, (plan_elevation_id, option_name, option_type, option_description))
            plan_option_id = self.cursor.fetchone()['plan_option_id']
            logger.info(f"Created plan option: {option_name}")
        
        self.plan_option_cache[cache_key] = plan_option_id
        return plan_option_id
    
    def get_or_create_cost_group(self, cost_group_code, cost_group_name):
        """Get or create cost group"""
        if cost_group_code in self.cost_group_cache:
            return self.cost_group_cache[cost_group_code]
        
        self.cursor.execute("SELECT cost_group_id FROM cost_groups WHERE cost_group_code = %s", (cost_group_code,))
        result = self.cursor.fetchone()
        
        if result:
            cost_group_id = result['cost_group_id']
        else:
            self.cursor.execute("""
                INSERT INTO cost_groups (cost_group_code, cost_group_name) 
                VALUES (%s, %s) RETURNING cost_group_id
            """, (cost_group_code, cost_group_name))
            cost_group_id = self.cursor.fetchone()['cost_group_id']
        
        self.cost_group_cache[cost_group_code] = cost_group_id
        return cost_group_id
    
    def get_or_create_cost_code(self, cost_group_id, cost_code, cost_code_description):
        """Get or create cost code"""
        if cost_code in self.cost_code_cache:
            return self.cost_code_cache[cost_code]
        
        self.cursor.execute("SELECT cost_code_id FROM cost_codes WHERE cost_code = %s", (cost_code,))
        result = self.cursor.fetchone()
        
        if result:
            cost_code_id = result['cost_code_id']
        else:
            self.cursor.execute("""
                INSERT INTO cost_codes (cost_group_id, cost_code, cost_code_description) 
                VALUES (%s, %s, %s) RETURNING cost_code_id
            """, (cost_group_id, cost_code, cost_code_description))
            cost_code_id = self.cursor.fetchone()['cost_code_id']
        
        self.cost_code_cache[cost_code] = cost_code_id
        return cost_code_id
    
    def get_or_create_vendor(self, vendor_name):
        """Get or create vendor"""
        if not vendor_name or pd.isna(vendor_name):
            return None
            
        if vendor_name in self.vendor_cache:
            return self.vendor_cache[vendor_name]
        
        self.cursor.execute("SELECT vendor_id FROM vendors WHERE vendor_name = %s", (vendor_name,))
        result = self.cursor.fetchone()
        
        if result:
            vendor_id = result['vendor_id']
        else:
            self.cursor.execute("""
                INSERT INTO vendors (vendor_name) VALUES (%s) RETURNING vendor_id
            """, (vendor_name,))
            vendor_id = self.cursor.fetchone()['vendor_id']
        
        self.vendor_cache[vendor_name] = vendor_id
        return vendor_id
    
    def get_or_create_item(self, item_name, cost_code_id, qty_type, takeoff_type, qty_formula=None):
        """Get or create item"""
        cache_key = f"{item_name}_{cost_code_id}"
        if cache_key in self.item_cache:
            return self.item_cache[cache_key]
        
        self.cursor.execute("SELECT item_id FROM items WHERE item_name = %s", (item_name,))
        result = self.cursor.fetchone()
        
        if result:
            item_id = result['item_id']
        else:
            self.cursor.execute("""
                INSERT INTO items (item_name, cost_code_id, qty_type, takeoff_type, qty_formula) 
                VALUES (%s, %s, %s, %s, %s) RETURNING item_id
            """, (item_name, cost_code_id, qty_type, takeoff_type, qty_formula))
            item_id = self.cursor.fetchone()['item_id']
        
        self.item_cache[cache_key] = item_id
        return item_id
    
    def get_or_create_product(self, item_id, product_description, model=None, brand=None, sku=None):
        """Get or create product"""
        cache_key = f"{item_id}_{product_description}"
        if cache_key in self.product_cache:
            return self.product_cache[cache_key]
        
        self.cursor.execute("""
            SELECT product_id FROM products 
            WHERE item_id = %s AND product_description = %s
        """, (item_id, product_description))
        result = self.cursor.fetchone()
        
        if result:
            product_id = result['product_id']
        else:
            self.cursor.execute("""
                INSERT INTO products (item_id, product_description, model, brand, sku) 
                VALUES (%s, %s, %s, %s, %s) RETURNING product_id
            """, (item_id, product_description, model, brand, sku))
            product_id = self.cursor.fetchone()['product_id']
        
        self.product_cache[cache_key] = product_id
        return product_id
    
    def process_excel_file(self, filepath):
        """Process a single Excel file"""
        try:
            filename = os.path.basename(filepath)
            logger.info(f"Processing file: {filename}")
            
            # Parse filename for plan/elevation/option info
            file_info = self.parse_filename(filename)
            if not file_info:
                return False
            
            # Read Excel file
            df = pd.read_excel(filepath)
            if df.empty:
                logger.warning(f"File {filename} is empty")
                return False
            
            logger.info(f"File contains {len(df)} rows and {len(df.columns)} columns")
            logger.info(f"Columns: {list(df.columns)[:10]}...")  # Show first 10 columns
            
            # Show first few rows for verification
            logger.info("First row data:")
            for col in df.columns[:15]:  # Show first 15 columns
                val = df.iloc[0][col] if not df.empty else 'N/A'
                logger.info(f"  {col}: {val}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
            return False
    
    def load_all_files(self, directory='PlanElevOptions'):
        """Load all Excel files from directory"""
        if not os.path.exists(directory):
            logger.error(f"Directory {directory} does not exist")
            return False
        
        if not self.connect_db():
            return False
        
        try:
            files_processed = 0
            files_failed = 0
            
            for filename in sorted(os.listdir(directory)):
                if filename.endswith('.xlsx'):
                    filepath = os.path.join(directory, filename)
                    logger.info(f"Processing {filename}...")
                    if self.process_excel_file(filepath):
                        files_processed += 1
                    else:
                        files_failed += 1
                    break  # Process just one file for now
            
            logger.info(f"Loading complete. Files processed: {files_processed}, Files failed: {files_failed}")
            return files_processed > 0
            
        finally:
            self.close_db()

def main():
    """Main execution function"""
    loader = Phase1DataLoader()
    
    if len(sys.argv) > 1:
        directory = sys.argv[1]
    else:
        directory = 'PlanElevOptions'
    
    logger.info(f"Starting Phase 1 data load from directory: {directory}")
    success = loader.load_all_files(directory)
    
    if success:
        logger.info("Data loading completed successfully!")
        return 0
    else:
        logger.error("Data loading failed")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 