#!/usr/bin/env python3
"""
New Data Loader for Construction Takeoff System
Loads Excel files from PlanElevOptions directory into PostgreSQL takeoff schema
Handles all 61 columns from Excel files
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
        self.cost_group_cache = {}
        self.cost_code_cache = {}
        self.vendor_cache = {}
        self.item_cache = {}
        self.product_cache = {}
        self.division_cache = {}
        self.community_cache = {}
        
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
    
    def safe_float(self, value):
        """Safely convert value to float"""
        if pd.isna(value) or value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def safe_int(self, value):
        """Safely convert value to int"""
        if pd.isna(value) or value is None or value == '':
            return None
        try:
            return int(float(value))  # Convert to float first to handle decimal strings
        except (ValueError, TypeError):
            return None
    
    def safe_str(self, value):
        """Safely convert value to string"""
        if pd.isna(value) or value is None:
            return None
        return str(value).strip()
    
    def safe_bool(self, value):
        """Safely convert value to boolean"""
        if pd.isna(value) or value is None or value == '':
            return None
        if isinstance(value, bool):
            return value
        str_val = str(value).lower().strip()
        return str_val in ['true', '1', 'yes', 'y']
    
    def parse_filename(self, filename):
        """Parse filename to extract plan, elevation, foundation, and option type"""
        # Format: PlanName_Elevation_Foundation_OptionType.xlsx
        # Example: Winchester_A_Basement_Base Home.xlsx
        
        # Remove .xlsx extension and any trailing spaces
        base_name = filename.replace('.xlsx', '').strip()
        parts = base_name.split('_')
        
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
    
    def get_or_create_division(self, division_name):
        """Get or create a division record"""
        if not division_name:
            return None
            
        if division_name in self.division_cache:
            return self.division_cache[division_name]
        
        self.cursor.execute("SELECT division_id FROM takeoff.divisions WHERE division_name = %s", (division_name,))
        result = self.cursor.fetchone()
        
        if result:
            division_id = result['division_id']
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.divisions (division_name)
                VALUES (%s) RETURNING division_id
            """, (division_name,))
            division_id = self.cursor.fetchone()['division_id']
            logger.info(f"Created new division: {division_name}")
        
        self.division_cache[division_name] = division_id
        return division_id
    
    def get_or_create_community(self, division_id, community_name):
        """Get or create a community record"""
        if not community_name:
            return None
            
        cache_key = f"{division_id}_{community_name}"
        if cache_key in self.community_cache:
            return self.community_cache[cache_key]
        
        self.cursor.execute("""
            SELECT community_id FROM takeoff.communities 
            WHERE division_id = %s AND community_name = %s
        """, (division_id, community_name))
        result = self.cursor.fetchone()
        
        if result:
            community_id = result['community_id']
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.communities (division_id, community_name)
                VALUES (%s, %s) RETURNING community_id
            """, (division_id, community_name))
            community_id = self.cursor.fetchone()['community_id']
            logger.info(f"Created new community: {community_name}")
        
        self.community_cache[cache_key] = community_id
        return community_id
    
    def get_or_create_plan(self, plan_name, architect=None, engineer=None):
        """Get or create a plan record"""
        if plan_name in self.plan_cache:
            return self.plan_cache[plan_name]
        
        self.cursor.execute("SELECT plan_id FROM takeoff.plans WHERE plan_name = %s", (plan_name,))
        result = self.cursor.fetchone()
        
        if result:
            plan_id = result['plan_id']
            # Update architect and engineer if provided
            if architect or engineer:
                self.cursor.execute("""
                    UPDATE takeoff.plans 
                    SET architect = COALESCE(%s, architect), engineer = COALESCE(%s, engineer)
                    WHERE plan_id = %s
                """, (architect, engineer, plan_id))
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.plans (plan_name, architect, engineer)
                VALUES (%s, %s, %s) RETURNING plan_id
            """, (plan_name, architect, engineer))
            plan_id = self.cursor.fetchone()['plan_id']
            logger.info(f"Created new plan: {plan_name}")
        
        self.plan_cache[plan_name] = plan_id
        return plan_id
    
    def get_or_create_elevation(self, plan_id, elevation_name, foundation, row_data):
        """Get or create a plan elevation record"""
        cache_key = f"{plan_id}_{elevation_name}_{foundation}"
        if cache_key in self.elevation_cache:
            return self.elevation_cache[cache_key]
        
        self.cursor.execute("""
            SELECT plan_elevation_id FROM takeoff.plan_elevations 
            WHERE plan_id = %s AND elevation_name = %s AND foundation = %s
        """, (plan_id, elevation_name, foundation))
        result = self.cursor.fetchone()
        
        if result:
            elevation_id = result['plan_elevation_id']
            # Update with any new data from this row
            self.cursor.execute("""
                UPDATE takeoff.plan_elevations 
                SET plan_full_name = COALESCE(%s, plan_full_name),
                    version_number = COALESCE(%s, version_number),
                    version_date = COALESCE(%s, version_date),
                    is_current_version = COALESCE(%s, is_current_version),
                    stair_count = COALESCE(%s, stair_count)
                WHERE plan_elevation_id = %s
            """, (
                self.safe_str(row_data.get('PlanFullName')),
                self.safe_str(row_data.get('VersionNumber')),
                self.safe_str(row_data.get('VersionDate')),
                self.safe_bool(row_data.get('IsCurrentVersion')),
                self.safe_int(row_data.get('StairCount')),
                elevation_id
            ))
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.plan_elevations (
                    plan_id, elevation_name, foundation, plan_full_name,
                    version_number, version_date, is_current_version, stair_count
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
                RETURNING plan_elevation_id
            """, (
                plan_id, elevation_name, foundation,
                self.safe_str(row_data.get('PlanFullName')),
                self.safe_str(row_data.get('VersionNumber')),
                self.safe_str(row_data.get('VersionDate')),
                self.safe_bool(row_data.get('IsCurrentVersion')),
                self.safe_int(row_data.get('StairCount'))
            ))
            elevation_id = self.cursor.fetchone()['plan_elevation_id']
            logger.info(f"Created new elevation: {elevation_name} for plan {plan_id}")
        
        self.elevation_cache[cache_key] = elevation_id
        return elevation_id
    
    def get_or_create_option(self, elevation_id, option_name, option_type, row_data):
        """Get or create a plan option record"""
        cache_key = f"{elevation_id}_{option_name}"
        if cache_key in self.option_cache:
            return self.option_cache[cache_key]
        
        self.cursor.execute("""
            SELECT plan_option_id FROM takeoff.plan_options 
            WHERE plan_elevation_id = %s AND option_name = %s
        """, (elevation_id, option_name))
        result = self.cursor.fetchone()
        
        if result:
            option_id = result['plan_option_id']
            # Update with any new data including SF fields
            self.cursor.execute("""
                UPDATE takeoff.plan_options 
                SET option_type = COALESCE(%s, option_type),
                    option_description = COALESCE(%s, option_description),
                    bedroom_count = COALESCE(%s, bedroom_count),
                    bathroom_count = COALESCE(%s, bathroom_count),
                    heated_sf_inside_studs = COALESCE(%s, heated_sf_inside_studs),
                    heated_sf_outside_studs = COALESCE(%s, heated_sf_outside_studs),
                    heated_sf_outside_veneer = COALESCE(%s, heated_sf_outside_veneer),
                    unheated_sf_inside_studs = COALESCE(%s, unheated_sf_inside_studs),
                    unheated_sf_outside_studs = COALESCE(%s, unheated_sf_outside_studs),
                    unheated_sf_outside_veneer = COALESCE(%s, unheated_sf_outside_veneer),
                    total_sf_inside_studs = COALESCE(%s, total_sf_inside_studs),
                    total_sf_outside_studs = COALESCE(%s, total_sf_outside_studs),
                    total_sf_outside_veneer = COALESCE(%s, total_sf_outside_veneer)
                WHERE plan_option_id = %s
            """, (
                option_type,
                self.safe_str(row_data.get('OptionDescription')),
                self.safe_int(row_data.get('Beds')),
                self.safe_int(row_data.get('Baths')),
                self.safe_int(row_data.get('HeatedSF(InsideStuds)')),
                self.safe_int(row_data.get('HeatedSF(OutsideStuds)')),
                self.safe_int(row_data.get('HeatedSF(OutsideVeneer)')),
                self.safe_int(row_data.get('UnHeatedSF(InsideStuds)')),
                self.safe_int(row_data.get('UnHeatedSF(OutsideStuds)')),
                self.safe_int(row_data.get('UnHeatedSF(OutsideVeneer)')),
                self.safe_int(row_data.get('TotalSF(InsideStuds)')),
                self.safe_int(row_data.get('TotalSF(OutsideStuds)')),
                self.safe_int(row_data.get('TotalSF(OutsideVeneer)')),
                option_id
            ))
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.plan_options (
                    plan_elevation_id, option_name, option_type, option_description,
                    bedroom_count, bathroom_count,
                    heated_sf_inside_studs, heated_sf_outside_studs, heated_sf_outside_veneer,
                    unheated_sf_inside_studs, unheated_sf_outside_studs, unheated_sf_outside_veneer,
                    total_sf_inside_studs, total_sf_outside_studs, total_sf_outside_veneer
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) RETURNING plan_option_id
            """, (
                elevation_id, option_name, option_type,
                self.safe_str(row_data.get('OptionDescription')),
                self.safe_int(row_data.get('Beds')),
                self.safe_int(row_data.get('Baths')),
                self.safe_int(row_data.get('HeatedSF(InsideStuds)')),
                self.safe_int(row_data.get('HeatedSF(OutsideStuds)')),
                self.safe_int(row_data.get('HeatedSF(OutsideVeneer)')),
                self.safe_int(row_data.get('UnHeatedSF(InsideStuds)')),
                self.safe_int(row_data.get('UnHeatedSF(OutsideStuds)')),
                self.safe_int(row_data.get('UnHeatedSF(OutsideVeneer)')),
                self.safe_int(row_data.get('TotalSF(InsideStuds)')),
                self.safe_int(row_data.get('TotalSF(OutsideStuds)')),
                self.safe_int(row_data.get('TotalSF(OutsideVeneer)'))
            ))
            option_id = self.cursor.fetchone()['plan_option_id']
            logger.info(f"Created new option: {option_name} for elevation {elevation_id}")
        
        self.option_cache[cache_key] = option_id
        return option_id
    
    def get_or_create_cost_group(self, cost_group_code, cost_group_name):
        """Get or create cost group"""
        if not cost_group_code and not cost_group_name:
            return None
            
        # Use code as primary key, fallback to name
        key = cost_group_code or cost_group_name
        if key in self.cost_group_cache:
            return self.cost_group_cache[key]
        
        # Try to find by code first, then by name
        if cost_group_code:
            self.cursor.execute("SELECT cost_group_id FROM takeoff.cost_groups WHERE cost_group_code = %s", (cost_group_code,))
        else:
            self.cursor.execute("SELECT cost_group_id FROM takeoff.cost_groups WHERE cost_group_name = %s", (cost_group_name,))
        
        result = self.cursor.fetchone()
        
        if result:
            cost_group_id = result['cost_group_id']
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.cost_groups (cost_group_code, cost_group_name)
                VALUES (%s, %s) RETURNING cost_group_id
            """, (cost_group_code or cost_group_name[:50], cost_group_name or cost_group_code))
            cost_group_id = self.cursor.fetchone()['cost_group_id']
        
        self.cost_group_cache[key] = cost_group_id
        return cost_group_id
    
    def get_or_create_cost_code(self, cost_group_id, cost_code, cost_code_description):
        """Get or create cost code"""
        if not cost_code:
            return None
            
        cache_key = f"{cost_group_id}_{cost_code}"
        if cache_key in self.cost_code_cache:
            return self.cost_code_cache[cache_key]
        
        self.cursor.execute("""
            SELECT cost_code_id FROM takeoff.cost_codes 
            WHERE cost_group_id = %s AND cost_code = %s
        """, (cost_group_id, cost_code))
        result = self.cursor.fetchone()
        
        if result:
            cost_code_id = result['cost_code_id']
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.cost_codes (cost_group_id, cost_code, cost_code_description)
                VALUES (%s, %s, %s) RETURNING cost_code_id
            """, (cost_group_id, cost_code, cost_code_description))
            cost_code_id = self.cursor.fetchone()['cost_code_id']
        
        self.cost_code_cache[cache_key] = cost_code_id
        return cost_code_id
    
    def get_or_create_vendor(self, vendor_name):
        """Get or create vendor"""
        if not vendor_name or pd.isna(vendor_name):
            return None
            
        if vendor_name in self.vendor_cache:
            return self.vendor_cache[vendor_name]
        
        self.cursor.execute("SELECT vendor_id FROM takeoff.vendors WHERE vendor_name = %s", (vendor_name,))
        result = self.cursor.fetchone()
        
        if result:
            vendor_id = result['vendor_id']
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.vendors (vendor_name)
                VALUES (%s) RETURNING vendor_id
            """, (vendor_name,))
            vendor_id = self.cursor.fetchone()['vendor_id']
        
        self.vendor_cache[vendor_name] = vendor_id
        return vendor_id
    
    def get_or_create_vendor_pricing(self, vendor_id, product_id, unit_price, unit_of_measure, price_type='standard'):
        """Get or create vendor pricing record"""
        if not vendor_id or not product_id or not unit_price:
            return None
            
        # Check if current pricing exists for this vendor/product
        self.cursor.execute("""
            SELECT pricing_id FROM takeoff.vendor_pricing 
            WHERE vendor_id = %s AND product_id = %s AND is_current = true AND is_active = true
        """, (vendor_id, product_id))
        result = self.cursor.fetchone()
        
        if result:
            pricing_id = result['pricing_id']
            # Check if price has changed
            self.cursor.execute("""
                SELECT price FROM takeoff.vendor_pricing WHERE pricing_id = %s
            """, (pricing_id,))
            current_price = self.cursor.fetchone()['price']
            
            if float(current_price) != float(unit_price):
                # Price has changed, create new pricing record
                self.cursor.execute("""
                    INSERT INTO takeoff.vendor_pricing (
                        vendor_id, product_id, price, unit_of_measure, 
                        effective_date, price_type, notes, created_by
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING pricing_id
                """, (
                    vendor_id, product_id, unit_price, unit_of_measure or 'EA',
                    'CURRENT_DATE', price_type, 
                    f'Updated price from ${current_price} to ${unit_price}',
                    'data_loader'
                ))
                pricing_id = self.cursor.fetchone()['pricing_id']
        else:
            # Create new pricing record
            self.cursor.execute("""
                INSERT INTO takeoff.vendor_pricing (
                    vendor_id, product_id, price, unit_of_measure, 
                    effective_date, price_type, notes, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING pricing_id
            """, (
                vendor_id, product_id, unit_price, unit_of_measure or 'EA',
                'CURRENT_DATE', price_type, 
                'Created from data load', 'data_loader'
            ))
            pricing_id = self.cursor.fetchone()['pricing_id']
        
        return pricing_id
    
    def get_or_create_item_and_product(self, item_name, item_description, cost_code_id, row_data):
        """Get or create item and product records"""
        if not item_name:
            return None, None
            
        cache_key = item_name
        if cache_key in self.item_cache:
            return self.item_cache[cache_key]
        
        # Get or create item
        self.cursor.execute("SELECT item_id FROM takeoff.items WHERE item_name = %s", (item_name,))
        result = self.cursor.fetchone()
        
        if result:
            item_id = result['item_id']
            # Update item with additional data if needed
            self.cursor.execute("""
                UPDATE takeoff.items 
                SET cost_code_id = COALESCE(%s, cost_code_id),
                    qty_type = COALESCE(%s, qty_type),
                    default_unit = COALESCE(%s, default_unit),
                    attribute_level = COALESCE(%s, attribute_level),
                    model = COALESCE(%s, model),
                    qty_formula = COALESCE(%s, qty_formula),
                    takeoff_type = COALESCE(%s, takeoff_type)
                WHERE item_id = %s
            """, (
                cost_code_id,
                self.safe_str(row_data.get('QtyType')),
                self.safe_str(row_data.get('UoM')),
                self.safe_str(row_data.get('AttributeLevel')),
                self.safe_str(row_data.get('Model')),
                self.safe_str(row_data.get('QTYFormula')),
                self.safe_str(row_data.get('TakeoffType')),
                item_id
            ))
        else:
            self.cursor.execute("""
                INSERT INTO takeoff.items (
                    item_name, cost_code_id, qty_type, default_unit,
                    attribute_level, model, qty_formula, takeoff_type
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING item_id
            """, (
                item_name, cost_code_id,
                self.safe_str(row_data.get('QtyType')),
                self.safe_str(row_data.get('UoM')),
                self.safe_str(row_data.get('AttributeLevel')),
                self.safe_str(row_data.get('Model')),
                self.safe_str(row_data.get('QTYFormula')),
                self.safe_str(row_data.get('TakeoffType'))
            ))
            item_id = self.cursor.fetchone()['item_id']
        
        # Get or create product
        product_cache_key = f"{item_id}_{item_description}"
        if product_cache_key in self.product_cache:
            product_id = self.product_cache[product_cache_key]
        else:
            self.cursor.execute("""
                SELECT product_id FROM takeoff.products 
                WHERE item_id = %s AND product_description = %s
            """, (item_id, item_description))
            result = self.cursor.fetchone()
            
            if result:
                product_id = result['product_id']
            else:
                self.cursor.execute("""
                    INSERT INTO takeoff.products (item_id, product_description, model)
                    VALUES (%s, %s, %s) RETURNING product_id
                """, (item_id, item_description, self.safe_str(row_data.get('Model'))))
                product_id = self.cursor.fetchone()['product_id']
            
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
                logger.error(f"Could not parse filename: {filename}")
                return False
            
            # Read Excel file
            df = pd.read_excel(filepath)
            
            if df.empty:
                logger.warning(f"File {filename} is empty")
                return False
            
            logger.info(f"File contains {len(df)} rows")
            
            # Process each row in the Excel file
            processed_rows = 0
            job_id = None
            
            for idx, row in df.iterrows():
                try:
                    # Skip rows with no TakeoffID or critical missing data
                    takeoff_id_source = self.safe_int(row.get('TakeoffID'))
                    if not takeoff_id_source:
                        continue
                    
                    item_name = self.safe_str(row.get('Item'))
                    if not item_name:
                        continue
                    
                    # Get data from row
                    plan_name = self.safe_str(row.get('Plan')) or file_info['plan_name']
                    elevation_name = self.safe_str(row.get('Elevation')) or file_info['elevation_name']
                    foundation = self.safe_str(row.get('Foundation')) or file_info['foundation']
                    
                    # Get or create division and community
                    division_id = None
                    community_id = None
                    division_name = self.safe_str(row.get('Division'))
                    community_name = self.safe_str(row.get('Community'))
                    
                    if division_name:
                        division_id = self.get_or_create_division(division_name)
                        if community_name:
                            community_id = self.get_or_create_community(division_id, community_name)
                    
                    # Get or create plan structure
                    plan_id = self.get_or_create_plan(
                        plan_name,
                        self.safe_str(row.get('Architect')),
                        self.safe_str(row.get('Engineer'))
                    )
                    
                    elevation_id = self.get_or_create_elevation(plan_id, elevation_name, foundation, row)
                    
                    option_name = self.safe_str(row.get('OptionName')) or file_info['option_type']
                    option_type = self.safe_str(row.get('OptionType')) or file_info['option_type']
                    
                    option_id = self.get_or_create_option(elevation_id, option_name, option_type, row)
                    
                    # Create job record if not exists for this file
                    if job_id is None:
                        job_name = self.safe_str(row.get('JobName')) or f"{plan_name}_{elevation_name}_{foundation}_{option_type}"
                        
                        self.cursor.execute("""
                            SELECT job_id FROM takeoff.jobs 
                            WHERE plan_option_id = %s AND job_name = %s
                        """, (option_id, job_name))
                        existing_job = self.cursor.fetchone()
                        
                        if existing_job:
                            job_id = existing_job['job_id']
                        else:
                            self.cursor.execute("""
                                INSERT INTO takeoff.jobs (
                                    job_name, plan_option_id, is_template, job_number,
                                    lot_number, customer_name, division_id, community_id
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s) RETURNING job_id
                            """, (
                                job_name, option_id, True,
                                self.safe_str(row.get('JobNumber')),
                                self.safe_str(row.get('LotNumber')),
                                self.safe_str(row.get('CustomerName')),
                                division_id, community_id
                            ))
                            job_id = self.cursor.fetchone()['job_id']
                    
                    # Get or create cost codes
                    cost_group_id = self.get_or_create_cost_group(
                        self.safe_str(row.get('CostGroup')),
                        self.safe_str(row.get('CostGroupName'))
                    )
                    
                    cost_code_id = None
                    if cost_group_id:
                        cost_code_id = self.get_or_create_cost_code(
                            cost_group_id,
                            self.safe_str(row.get('CostCodeNumber')),
                            self.safe_str(row.get('CostCodeDescription'))
                        )
                    
                    # Get or create vendor
                    vendor_id = self.get_or_create_vendor(self.safe_str(row.get('Vendor')))
                    
                    # Get or create item and product
                    item_id, product_id = self.get_or_create_item_and_product(
                        item_name,
                        self.safe_str(row.get('ItemDescription')) or item_name,
                        cost_code_id,
                        row
                    )
                    
                    if not product_id:
                        logger.warning(f"Could not create product for item: {item_name}")
                        continue
                    
                    # Get quantities and pricing
                    quantity = self.safe_float(row.get('QTY')) or 0
                    unit_price = self.safe_float(row.get('Price')) or 0
                    extended_price = self.safe_float(row.get('ExtendedPrice')) or 0
                    
                    # If extended price is 0 but we have quantity and unit price, calculate it
                    if extended_price == 0 and quantity > 0 and unit_price > 0:
                        extended_price = quantity * unit_price
                    
                    # Insert takeoff record (takeoff_id will be auto-generated)
                    self.cursor.execute("""
                        INSERT INTO takeoff.takeoffs (
                            takeoff_id_source, job_id, product_id, vendor_id,
                            quantity, unit_price, extended_price,
                            job_number, lot_number, customer_name,
                            unit_of_measure, price_factor, notes, room,
                            spec_name, spec_description, spec_level,
                            is_heated, floor_level, room_type, room_sqft,
                            selected_total
                        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, (
                        takeoff_id_source, job_id, product_id, vendor_id,
                        quantity, unit_price, extended_price,
                        self.safe_str(row.get('JobNumber')),
                        self.safe_str(row.get('LotNumber')),
                        self.safe_str(row.get('CustomerName')),
                        self.safe_str(row.get('UoM')),
                        self.safe_float(row.get('Factor')),
                        self.safe_str(row.get('Notes')),
                        self.safe_str(row.get('Room')),
                        self.safe_str(row.get('SpecName')),
                        self.safe_str(row.get('SpecDescription')),
                        self.safe_str(row.get('SpecLevel')),
                        self.safe_bool(row.get('IsHeated')),
                        self.safe_str(row.get('FloorLevel')),
                        self.safe_str(row.get('RoomType')),
                        self.safe_float(row.get('RoomSqFt')),
                        self.safe_float(row.get('SelectedTotal'))
                    ))
                    
                    processed_rows += 1
                    
                except Exception as e:
                    logger.warning(f"Error processing row {idx} in {filename}: {e}")
                    # Rollback this row's changes and continue
                    self.conn.rollback()
                    continue
            
            self.conn.commit()
            logger.info(f"Successfully processed {processed_rows} rows from {filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error processing file {filepath}: {e}")
            self.conn.rollback()
            return False
    
    def load_specific_files(self, file_patterns, directory='PlanElevOptions'):
        """Load specific Excel files based on patterns"""
        if not os.path.exists(directory):
            logger.error(f"Directory {directory} does not exist")
            return False
        
        if not self.connect_db():
            return False
        
        try:
            files_processed = 0
            files_failed = 0
            
            all_files = [f for f in os.listdir(directory) if f.endswith('.xlsx')]
            
            for pattern in file_patterns:
                matching_files = [f for f in all_files if pattern.lower() in f.lower()]
                for filename in matching_files:
                    filepath = os.path.join(directory, filename)
                    logger.info(f"Loading file: {filename}")
                    if self.process_excel_file(filepath):
                        files_processed += 1
                    else:
                        files_failed += 1
            
            logger.info(f"Processing complete. Files processed: {files_processed}, Files failed: {files_failed}")
            return True
            
        finally:
            self.close_db()
    
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
    
    # Check if specific files were requested
    if len(sys.argv) > 2:
        # Load specific files based on command line arguments
        file_patterns = sys.argv[2:]
        logger.info(f"Starting data load from directory: {directory} for patterns: {file_patterns}")
        success = loader.load_specific_files(file_patterns, directory)
    else:
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
