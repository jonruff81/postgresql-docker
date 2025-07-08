#!/usr/bin/env python3
"""
Simple Web UI for PostgreSQL Takeoff Database Management
Provides dashboard view of all tables with CRUD operations
"""

# ============================================================================
# == INDEX / TABLE OF CONTENTS ===============================================
# ============================================================================
# 1. Imports and Configuration [Lines 1-35]
#    - Environment variables, imports, logging setup, Flask app initialization
#
# 2. Database Manager Class [Lines 37-309]
#    - Database connection and operations
#    - Table structure and data retrieval
#    - CRUD operations for records
#
# 3. Helper Functions [Lines 528-533]
#    - Caching utilities
#
# 4. API Endpoints
#    4.1 General/Dashboard Endpoints [Lines 311-329]
#        - Dashboard view
#        - Tables list
#        - Table structure
#
#    4.2 Cost Codes Endpoints [Lines 332-343, 534-601, 878-1093, 1335-1352]
#        - Cost codes grid
#        - Cost codes with groups data
#        - Bulk update, export, import
#
#    4.3 Vendor Pricing Endpoints [Lines 346-350, 603-732, 842-876, 1429-1613]
#        - Vendor pricing grid
#        - Vendor pricing data
#        - Update, create, delete, duplicate
#
#    4.4 Products Endpoints [Lines 373-377, 734-840, 1615-1663, 2730-3238]
#        - Products grid
#        - Products data
#        - Create, update, delete, import, export
#
#    4.5 Plans Endpoints [Lines 384-526]
#        - Plans grid
#        - Plans data
#        - Create, update, delete
#
#    4.6 Plan Options Endpoints [Lines 357-360, 1969-2327]
#        - Plan options grid
#        - Plan options data
#        - Create, update, delete, duplicate, import, export
#
#    4.7 Qty Takeoffs Endpoints [Lines 362-370, 2330-2706]
#        - Qty takeoffs grid
#        - Comprehensive takeoff grid
#        - Qty takeoffs data
#        - Create, update, delete, import, export
#
#    4.8 Quotes Endpoints [Lines 352-355, 1223-1332]
#        - Quotes grid
#        - Quotes data
#        - Bulk update
#
#    4.9 Items Endpoints [Lines 379-382, 1354-1965]
#        - Items grid
#        - Items data
#        - Bulk update, import
#
#    4.10 Dropdown/Utility Endpoints [Lines 1373-1425, 1666-1683]
#        - Items with descriptions
#        - Vendors
#        - Formulas
#
# 5. Main App Run Block [Line 3241]
#    - Application entry point

# ============================================================================
# == 1. IMPORTS AND CONFIGURATION ===========================================
# ============================================================================

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

import os
import sys
import time
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import logging
from datetime import datetime

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_CONFIG_DICT as DB_CONFIG

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Log which database we're connecting to
logger.info(f"Database Configuration: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# AG-Grid License Configuration
app.config['AG_GRID_LICENSE_KEY'] = os.getenv('AG_GRID_LICENSE_KEY', '')  # Set via environment variable

# ============================================================================
# == 2. DATABASE MANAGER CLASS ==============================================
# ============================================================================

class DatabaseManager:
    def __init__(self):
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Connect to PostgreSQL database"""
        try:
            self.conn = psycopg2.connect(**DB_CONFIG)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            return True
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def disconnect(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def get_all_tables(self):
        """Get all tables in takeoff schema with record counts"""
        if not self.connect():
            return []
        
        try:
            self.cursor.execute("""
                SELECT 
                    t.table_name,
                    obj_description(pgc.oid) as table_comment,
                    COUNT(c.column_name) as column_count
                FROM information_schema.tables t
                LEFT JOIN information_schema.columns c ON t.table_schema = c.table_schema AND t.table_name = c.table_name
                LEFT JOIN pg_class pgc ON pgc.relname = t.table_name AND pgc.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'takeoff')
                WHERE t.table_schema = 'takeoff' 
                AND t.table_type = 'BASE TABLE'
                GROUP BY t.table_name, pgc.oid
                ORDER BY t.table_name
            """)
            tables = self.cursor.fetchall()
            
            # Get record counts for each table
            table_info = []
            for table in tables:
                table_name = table['table_name']
                self.cursor.execute(f"SELECT COUNT(*) as record_count FROM takeoff.{table_name}")
                count_result = self.cursor.fetchone()
                
                table_info.append({
                    'name': table_name,
                    'comment': table['table_comment'] or 'No description',
                    'column_count': table['column_count'],
                    'record_count': count_result['record_count']
                })
            
            return table_info
        except Exception as e:
            logger.error(f"Error getting tables: {e}")
            return []
        finally:
            self.disconnect()
    
    def get_table_structure(self, table_name):
        """Get column information for a table"""
        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    is_nullable,
                    column_default,
                    character_maximum_length
                FROM information_schema.columns 
                WHERE table_schema = 'takeoff' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting table structure: {e}")
            return []
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_table_data(self, table_name, page=1, per_page=50, search=None):
        """Get paginated data from a table"""
        conn = None
        cursor = None
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            offset = (page - 1) * per_page
            
            # Build search condition
            search_condition = ""
            search_params = []
            if search:
                # Get text columns for search
                cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'takeoff' AND table_name = %s 
                    AND data_type IN ('text', 'character varying', 'character')
                """, (table_name,))
                text_columns = [row['column_name'] for row in cursor.fetchall()]
                
                if text_columns:
                    search_conditions = [f"{col}::text ILIKE %s" for col in text_columns]
                    search_condition = "WHERE " + " OR ".join(search_conditions)
                    search_params = [f"%{search}%"] * len(text_columns)
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM takeoff.{table_name} {search_condition}"
            cursor.execute(count_query, search_params)
            total_records = cursor.fetchone()['total']
            
            # Get paginated data
            data_query = f"""
                SELECT * FROM takeoff.{table_name} 
                {search_condition}
                ORDER BY 1 
                LIMIT %s OFFSET %s
            """
            cursor.execute(data_query, search_params + [per_page, offset])
            records = cursor.fetchall()
            
            return records, total_records
        except Exception as e:
            logger.error(f"Error getting table data: {e}")
            return [], 0
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    def get_record(self, table_name, record_id, id_column=None):
        """Get a single record by ID"""
        if not self.connect():
            return None
        
        try:
            # If no ID column specified, use the first column (usually the primary key)
            if not id_column:
                self.cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'takeoff' AND table_name = %s
                    ORDER BY ordinal_position LIMIT 1
                """, (table_name,))
                result = self.cursor.fetchone()
                id_column = result['column_name'] if result else 'id'
            
            query = f"SELECT * FROM takeoff.{table_name} WHERE {id_column} = %s"
            self.cursor.execute(query, (record_id,))
            return self.cursor.fetchone()
        except Exception as e:
            logger.error(f"Error getting record: {e}")
            return None
        finally:
            self.disconnect()
    
    def delete_record(self, table_name, record_id, id_column=None):
        """Delete a record by ID"""
        if not self.connect():
            return False
        
        try:
            # If no ID column specified, use the first column
            if not id_column:
                self.cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'takeoff' AND table_name = %s
                    ORDER BY ordinal_position LIMIT 1
                """, (table_name,))
                result = self.cursor.fetchone()
                id_column = result['column_name'] if result else 'id'
            
            query = f"DELETE FROM takeoff.{table_name} WHERE {id_column} = %s"
            self.cursor.execute(query, (record_id,))
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting record: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()
    
    def update_record(self, table_name, record_id, update_data, id_column=None):
        """Update a record with new data"""
        if not self.connect():
            return False
        
        try:
            # If no ID column specified, use the first column
            if not id_column:
                self.cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'takeoff' AND table_name = %s
                    ORDER BY ordinal_position LIMIT 1
                """, (table_name,))
                result = self.cursor.fetchone()
                id_column = result['column_name'] if result else 'id'
            
            # Build UPDATE query
            set_clauses = []
            params = []
            for column, value in update_data.items():
                if column != id_column:  # Don't update the ID column
                    set_clauses.append(f"{column} = %s")
                    params.append(value if value != '' else None)
            
            if not set_clauses:
                return False
            
            query = f"UPDATE takeoff.{table_name} SET {', '.join(set_clauses)} WHERE {id_column} = %s"
            params.append(record_id)
            
            self.cursor.execute(query, params)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating record: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()
    
    def create_record(self, table_name, record_data):
        """Create a new record"""
        if not self.connect():
            return False
        
        try:
            # Get table columns
            self.cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'takeoff' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            columns = [row['column_name'] for row in self.cursor.fetchall()]
            
            # Filter data to only include valid columns
            filtered_data = {col: record_data.get(col) for col in columns if col in record_data}
            
            if not filtered_data:
                return False
            
            # Build INSERT query
            column_names = list(filtered_data.keys())
            placeholders = ['%s'] * len(column_names)
            values = [filtered_data[col] if filtered_data[col] != '' else None for col in column_names]
            
            query = f"INSERT INTO takeoff.{table_name} ({', '.join(column_names)}) VALUES ({', '.join(placeholders)})"
            
            self.cursor.execute(query, values)
            self.conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error creating record: {e}")
            self.conn.rollback()
            return False
        finally:
            self.disconnect()

# ============================================================================
# == 4. API ENDPOINTS =======================================================
# ============================================================================

# ============================================================================
# == 4.1 GENERAL/DASHBOARD ENDPOINTS ========================================
# ============================================================================

@app.route('/')
def dashboard():
    """Main dashboard showing AG-Grid views"""
    return render_template('dashboard.html')

@app.route('/api/tables')
def api_tables():
    """API endpoint to get all tables"""
    db = DatabaseManager()
    tables = db.get_all_tables()
    return jsonify(tables)

@app.route('/api/table/<table_name>/structure')
def api_table_structure(table_name):
    """API endpoint to get table structure"""
    db = DatabaseManager()
    columns = db.get_table_structure(table_name)
    return jsonify([dict(col) for col in columns])

# ============================================================================
# == 4.2 COST CODES ENDPOINTS ===============================================
# ============================================================================

@app.route('/cost-codes-grid')
def cost_codes_grid():
    """Cost codes with groups AG-Grid interface"""
    return render_template('cost_codes_grid.html')
    
# @app.route('/debug/cost-codes')
# def debug_cost_codes():
#     """
#     [DEPRECATED] Debug interface for cost codes.
#     The test-diagnose directory and related debug files are now archived under archived/cleanup_2025/test-diagnose/.
#     This endpoint is no longer available in the current system.
#     """
#     # from flask import send_from_directory
#     # import os
#     # return send_from_directory(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'test-diagnose'),
#     #                            'refresh_cost_codes.html')

# ============================================================================
# == 4.3 VENDOR PRICING ENDPOINTS ===========================================
# ============================================================================

@app.route('/vendor-pricing-grid')
def vendor_pricing_grid():
    """Vendor pricing AG-Grid interface"""
    ag_grid_license_key = app.config.get('AG_GRID_LICENSE_KEY', '')
    return render_template('vendor_pricing_grid.html', ag_grid_license_key=ag_grid_license_key)

# ============================================================================
# == 4.8 QUOTES ENDPOINTS ==================================================
# ============================================================================

@app.route('/quotes-grid')
def quotes_grid():
    """Quotes management AG-Grid interface"""
    return render_template('quotes_grid.html')

# ============================================================================
# == 4.6 PLAN OPTIONS ENDPOINTS ============================================
# ============================================================================

@app.route('/plan-options-grid')
def plan_options_grid():
    """Plan Options AG-Grid interface"""
    return render_template('plan_options_grid.html')

# ============================================================================
# == 4.7 QTY TAKEOFFS ENDPOINTS ============================================
# ============================================================================

@app.route('/qty-takeoffs-grid')
def qty_takeoffs_grid():
    """Qty Takeoffs AG-Grid interface using v_comprehensive_takeoff_analysis"""
    return render_template('qty_takeoffs_grid.html')

@app.route('/comprehensive-takeoff-grid')
def comprehensive_takeoff_grid():
    """Comprehensive takeoff analysis AG-Grid interface"""
    return render_template('comprehensive_takeoff_grid.html')

# ============================================================================
# == 4.4 PRODUCTS ENDPOINTS ================================================
# ============================================================================

@app.route('/products-grid')
def products_grid():
    """Products management AG-Grid interface with vendor pricing"""
    print("TEMPLATE PATH:", os.path.abspath(os.path.join(app.template_folder, 'products_grid.html')))
    return render_template('products_grid.html')

# ============================================================================
# == 4.9 ITEMS ENDPOINTS ===================================================
# ============================================================================

@app.route('/items-grid')
def items_grid():
    """Items management AG-Grid interface with enterprise features"""
    return render_template('items_grid.html')

# ============================================================================
# == 4.5 PLANS ENDPOINTS ===================================================
# ============================================================================

@app.route('/plans-grid')
def plans_grid():
    """Plans performance AG-Grid interface with advanced features"""
    return render_template('plans_grid.html')

@app.route('/api/plans')
def api_plans():
    """API endpoint to get plans data with elevation and option counts"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("""
            SELECT
                p.plan_id,
                p.plan_name,
                p.architect,
                p.engineer,
                COUNT(DISTINCT pe.plan_elevation_id) as elevation_count,
                COUNT(DISTINCT po.plan_option_id) as option_count
            FROM takeoff.plans p
            LEFT JOIN takeoff.plan_elevations pe ON p.plan_id = pe.plan_id
            LEFT JOIN takeoff.plan_options po ON pe.plan_elevation_id = po.plan_elevation_id
            GROUP BY p.plan_id, p.plan_name, p.architect, p.engineer
            ORDER BY p.plan_name
        """)
        records = db.cursor.fetchall()
        return jsonify([dict(record) for record in records])
    except Exception as e:
        logger.error(f"Error getting plans data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/plans/<int:plan_id>', methods=['PUT'])
def api_update_plan(plan_id):
    """API endpoint to update a plan"""
    db = DatabaseManager()
    data = request.get_json()
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        update_fields = []
        params = []
        
        if 'plan_name' in data:
            update_fields.append("plan_name = %s")
            params.append(data['plan_name'])
        if 'architect' in data:
            update_fields.append("architect = %s")
            params.append(data['architect'] if data['architect'] else None)
        if 'engineer' in data:
            update_fields.append("engineer = %s")
            params.append(data['engineer'] if data['engineer'] else None)
        
        if update_fields:
            params.append(plan_id)
            query = f"UPDATE takeoff.plans SET {', '.join(update_fields)} WHERE plan_id = %s"
            db.cursor.execute(query, params)
            db.conn.commit()
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'No fields to update'}), 400
    except Exception as e:
        logger.error(f"Error updating plan: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/plans', methods=['POST'])
def api_create_plan():
    """API endpoint to create a new plan"""
    db = DatabaseManager()
    data = request.get_json()
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        # Convert empty strings to None
        architect = data.get('architect') if data.get('architect') else None
        engineer = data.get('engineer') if data.get('engineer') else None
        
        db.cursor.execute("""
            INSERT INTO takeoff.plans (plan_name, architect, engineer)
            VALUES (%s, %s, %s)
            RETURNING plan_id
        """, (data.get('plan_name'), architect, engineer))
        
        plan_id = db.cursor.fetchone()['plan_id']
        db.conn.commit()
        return jsonify({'success': True, 'plan_id': plan_id})
    except Exception as e:
        logger.error(f"Error creating plan: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/plans/<int:plan_id>', methods=['DELETE'])
def api_delete_plan(plan_id):
    """API endpoint to delete a plan"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        logger.info(f"Attempting to delete plan {plan_id}")
        
        # Check if plan exists
        db.cursor.execute("SELECT COUNT(*) FROM takeoff.plans WHERE plan_id = %s", (plan_id,))
        plan_exists = db.cursor.fetchone()[0]
        
        if not plan_exists:
            logger.warning(f"Plan {plan_id} not found")
            return jsonify({'success': False, 'message': f"Plan {plan_id} not found"}), 404
        
        # Check if plan has associated plan_elevations  
        db.cursor.execute("SELECT COUNT(*) FROM takeoff.plan_elevations WHERE plan_id = %s", (plan_id,))
        result = db.cursor.fetchone()
        elevation_count = result[0] if result else 0
        
        logger.info(f"Plan {plan_id} has {elevation_count} associated elevations")
        
        if elevation_count > 0:
            return jsonify({
                'success': False, 
                'message': f"Cannot delete plan {plan_id}. It has {elevation_count} associated plan elevations. Delete those first."
            }), 400
        
        db.cursor.execute("DELETE FROM takeoff.plans WHERE plan_id = %s", (plan_id,))
        db.conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting plan: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 3. HELPER FUNCTIONS ===================================================
# ============================================================================

# Simple in-memory cache for API responses
response_cache = {}
cache_expiry = {}
response_etags = {}
CACHE_DURATION = 300  # Cache duration in seconds (5 minutes)

# ============================================================================
# == 4.2 COST CODES ENDPOINTS (CONTINUED) ==================================
# ============================================================================

@app.route('/api/cost-codes-with-groups')
def api_cost_codes_with_groups():
    """API endpoint to get cost codes with groups data with advanced caching"""
    # Get request parameters
    no_cache = request.args.get('no-cache', 'false').lower() == 'true'
    client_etag = request.headers.get('If-None-Match')
    cache_key = 'cost_codes_with_groups'
    current_time = time.time()
    
    # Check for HTTP conditional request (If-None-Match header)
    if not no_cache and client_etag and client_etag == response_etags.get(cache_key):
        logger.info("Returning 304 Not Modified response (ETag match)")
        return "", 304
    
    # Check if we have a valid cached response
    if not no_cache and cache_key in response_cache and current_time < cache_expiry.get(cache_key, 0):
        logger.info("Returning cached cost codes data")
        cached_response = response_cache[cache_key]
        # Set the ETag header on the cached response if not already present
        if 'ETag' not in cached_response.headers and cache_key in response_etags:
            cached_response.headers['ETag'] = response_etags[cache_key]
        return cached_response
    
    # If no valid cache, fetch from database
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        logger.info("Fetching cost codes data from database")
        start_time = time.time()
        
        db.cursor.execute("SELECT * FROM takeoff.v_cost_codes_with_groups ORDER BY cost_code")
        records = db.cursor.fetchall()
        
        # Convert to list of dictionaries for JSON serialization
        data = [dict(record) for record in records]
        
        # Generate ETag based on content hash
        import hashlib
        data_str = str(data).encode('utf-8')
        etag = hashlib.md5(data_str).hexdigest()
        
        # Check if data is unchanged from what we already have cached
        if cache_key in response_etags and etag == response_etags[cache_key] and client_etag == etag:
            logger.info("Data unchanged, returning 304 Not Modified")
            return "", 304
        
        # Create response with cache headers
        response = jsonify(data)
        response.headers['ETag'] = etag
        response.headers['Cache-Control'] = f'private, max-age={CACHE_DURATION}'
        
        # Cache the response
        if not no_cache:
            response_cache[cache_key] = response
            cache_expiry[cache_key] = current_time + CACHE_DURATION
            response_etags[cache_key] = etag
            
        query_time = time.time() - start_time
        logger.info(f"Cost codes data fetched in {query_time:.2f}s - {len(records)} records")
        
        return response
    except Exception as e:
        logger.error(f"Error getting cost codes with groups: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 4.3 VENDOR PRICING ENDPOINTS (CONTINUED) ==============================
# ============================================================================

@app.route('/api/vendor-pricing/update', methods=['POST'])
def api_vendor_pricing_update():
    """
    Update vendor pricing: create a new record with the new price, mark old as not current.
    Supports two input formats:
    1. Legacy: vendor_id, product_id, price, unit_of_measure
    2. New: pricing_id, new_price
    """
    db = DatabaseManager()
    data = request.get_json()
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        # Check if using new format (pricing_id + new_price)
        if 'pricing_id' in data and 'new_price' in data:
            pricing_id = data['pricing_id']
            new_price = data['new_price']
            
            # Get the current pricing record details
            db.cursor.execute("""
                SELECT vendor_id, product_id, price, unit_of_measure, price_type,
                       minimum_quantity, notes, expiration_date
                FROM takeoff.vendor_pricing
                WHERE pricing_id = %s AND is_current = true AND is_active = true
            """, (pricing_id,))
            
            current_record = db.cursor.fetchone()
            if not current_record:
                return jsonify({'success': False, 'message': 'Pricing record not found'}), 404
            
            # Check if the price actually changed
            if float(current_record['price']) == float(new_price):
                return jsonify({'success': True, 'message': 'Price unchanged'})
            
            # Insert new pricing record (this will automatically trigger the history tracking)
            db.cursor.execute("""
                INSERT INTO takeoff.vendor_pricing
                (vendor_id, product_id, price, unit_of_measure, effective_date,
                 expiration_date, is_current, is_active, price_type, minimum_quantity,
                 notes, created_date, updated_date)
                VALUES (%s, %s, %s, %s, CURRENT_DATE, %s, true, true, %s, %s, %s,
                        CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (
                current_record['vendor_id'],
                current_record['product_id'],
                new_price,
                current_record['unit_of_measure'],
                current_record['expiration_date'],
                current_record['price_type'],
                current_record['minimum_quantity'],
                current_record['notes']
            ))
            
            db.conn.commit()
            return jsonify({
                'success': True,
                'message': 'Price updated successfully',
                'old_price': float(current_record['price']),
                'new_price': float(new_price)
            })
            
        # Legacy format support
        else:
            required_fields = ['vendor_id', 'product_id', 'price', 'unit_of_measure']
            if not all(field in data for field in required_fields):
                return jsonify({'success': False, 'message': 'Missing required fields'}), 400

            # Mark old record as not current
            db.cursor.execute("""
                UPDATE takeoff.vendor_pricing
                SET is_current = FALSE
                WHERE vendor_id = %s AND product_id = %s AND is_current = TRUE
            """, (data['vendor_id'], data['product_id']))

            # Insert new record
            db.cursor.execute("""
                INSERT INTO takeoff.vendor_pricing
                (vendor_id, product_id, price, unit_of_measure, is_current, is_active)
                VALUES (%s, %s, %s, %s, TRUE, TRUE)
            """, (
                data['vendor_id'],
                data['product_id'],
                data['price'],
                data['unit_of_measure']
            ))

            db.conn.commit()
            return jsonify({'success': True})
            
    except Exception as e:
        logger.error(f"Error updating vendor pricing: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/vendor-pricing')
def api_vendor_pricing():
    """API endpoint to get vendor pricing data with optional product_id filtering"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        # Check if product_id filter is provided
        product_id = request.args.get('product_id')
        
        if product_id:
            # Filter by specific product_id
            db.cursor.execute("""
                SELECT * FROM takeoff.v_current_vendor_pricing
                WHERE product_id = %s
                ORDER BY vendor_name, price
            """, (product_id,))
        else:
            # Return all vendor pricing data
            db.cursor.execute("SELECT * FROM takeoff.v_current_vendor_pricing ORDER BY cost_code, vendor_name, item_name")
        
        records = db.cursor.fetchall()
        
        # Convert to list of dictionaries for JSON serialization
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting vendor pricing data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 4.4 PRODUCTS ENDPOINTS (CONTINUED) ====================================
# ============================================================================

@app.route('/api/products', methods=['GET', 'POST'])
def api_products():
    """API endpoint for products: GET all products, POST to create a new product"""
    if request.method == 'POST':
        return api_create_product()
    
    # Check if this is a request for dropdown data
    if request.args.get('for_dropdown') == 'true':
        return api_products_for_lookup()
    
    # Handle regular GET request
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            WITH RankedPricing AS (
                SELECT 
                    vp.product_id,
                    vp.price,
                    vp.created_date,
                    v.vendor_name,
                    ROW_NUMBER() OVER (PARTITION BY vp.product_id ORDER BY vp.price ASC) as price_rank
                FROM takeoff.vendor_pricing vp
                JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
                WHERE vp.is_current = TRUE
            ),
            PriceChanges AS (
                SELECT 
                    vp.product_id,
                    CASE 
                        WHEN vp_old.price > 0 THEN ((vp.price - vp_old.price) / vp_old.price * 100)
                        ELSE 0 
                    END as price_change
                FROM takeoff.vendor_pricing vp
                LEFT JOIN takeoff.vendor_pricing vp_old ON vp.product_id = vp_old.product_id
                    AND vp_old.created_date < vp.created_date
                WHERE vp.is_current = TRUE
                ORDER BY vp_old.created_date DESC
                LIMIT 1
            )
            SELECT
                p.product_id,
                i.item_id AS item_id,
                COALESCE(i.item_name, p.item_description) as item_name,
                COALESCE(cc.cost_code, 'N/A') as cost_code,
                p.item_description as product_description,
                p.model,
                p.brand,
                p.style,
                p.color,
                p.finish,
                p.size,
                p.material,
                p.item_type,
                p.image_url,
                p.is_active,
                p.min_stock_level,
                COALESCE(p.quantity, 0) as quantity,
                p.unit_of_measure,
                p.plan_option_id,
                pe.plan_full_name AS plan_full_name,
                po.option_name AS option_name,
                CASE
                    WHEN p.plan_option_id IS NOT NULL THEN
                        CONCAT(pe.plan_full_name, '_', po.option_name)
                    ELSE NULL
                END as plan_option_display,
                rp.price as unit_price,
                rp.vendor_name,
                pc.price_change,
                COUNT(vp.pricing_id) as vendor_count,
                MIN(vp.price) as min_price,
                MAX(vp.price) as max_price,
                AVG(vp.price) as avg_price,
                CASE
                    WHEN p.quantity <= p.min_stock_level THEN 'Low Stock'
                    WHEN p.is_active = FALSE THEN 'Inactive'
                    ELSE 'Active'
                END as status
            FROM takeoff.products p
            LEFT JOIN takeoff.items i ON p.item_id = i.item_id
            LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
            LEFT JOIN takeoff.plan_options po ON p.plan_option_id = po.plan_option_id
            LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            LEFT JOIN RankedPricing rp ON p.product_id = rp.product_id AND rp.price_rank = 1
            LEFT JOIN PriceChanges pc ON p.product_id = pc.product_id
            LEFT JOIN takeoff.vendor_pricing vp ON p.product_id = vp.product_id AND vp.is_current = TRUE
            GROUP BY
                p.product_id, i.item_id, i.item_name, cc.cost_code, p.item_description,
                p.model, p.brand, p.style, p.color, p.finish, p.size,
                p.material, p.item_type, p.image_url, p.is_active,
                p.min_stock_level, p.quantity, p.unit_of_measure, p.plan_option_id,
                pe.plan_full_name, po.option_name,
                rp.price, rp.vendor_name, pc.price_change
            ORDER BY COALESCE(i.item_name, p.item_description)
        """)
        records = cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting products data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ============================================================================
# == 4.3 VENDOR PRICING ENDPOINTS (CONTINUED) ==============================
# ============================================================================

@app.route('/api/products/<int:product_id>/vendor-pricing')
def api_product_vendor_pricing(product_id):
    """API endpoint to get vendor pricing for a specific product - uses direct psycopg2 connection"""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                vp.pricing_id,
                vp.product_id,
                v.vendor_name,
                vp.price,
                vp.unit_of_measure,
                vp.is_current,
                vp.created_date
            FROM takeoff.vendor_pricing vp
            JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
            WHERE vp.product_id = %s AND vp.is_active = TRUE
            ORDER BY vp.price ASC
        """, (product_id,))
        records = cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting vendor pricing for product {product_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ============================================================================
# == 4.2 COST CODES ENDPOINTS (CONTINUED) ==================================
# ============================================================================

@app.route('/api/cost-codes-with-groups/bulk-update', methods=['POST'])
def api_bulk_update_cost_codes():
    """API endpoint to bulk update cost codes and groups"""
    db = DatabaseManager()
    data = request.get_json()
    
    if not data or 'updates' not in data:
        return jsonify({'success': False, 'message': 'No updates provided'}), 400
    
    updates = data['updates']
    if not isinstance(updates, list):
        return jsonify({'success': False, 'message': 'Updates must be a list'}), 400
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        updated_count = 0
        errors = []
        
        for update in updates:
            try:
                # Get the cost_code_id and cost_group_id for this record
                db.cursor.execute("""
                    SELECT cc.cost_code_id, cg.cost_group_id 
                    FROM takeoff.cost_codes cc
                    LEFT JOIN takeoff.cost_groups cg ON cc.cost_group_id = cg.cost_group_id
                    WHERE cc.cost_code = %s
                """, (update.get('cost_code', ''),))
                
                existing = db.cursor.fetchone()
                if not existing:
                    errors.append(f"Cost code '{update.get('cost_code', '')}' not found")
                    continue
                
                cost_code_id = existing['cost_code_id']
                
                # Update cost_codes table
                db.cursor.execute("""
                    UPDATE takeoff.cost_codes 
                    SET cost_code = %s, cost_code_description = %s
                    WHERE cost_code_id = %s
                """, (
                    update.get('cost_code', ''),
                    update.get('cost_code_description', ''),
                    cost_code_id
                ))
                
                # Handle cost group updates
                cost_group_code = update.get('cost_group_code', '')
                cost_group_name = update.get('cost_group_name', '')
                
                if cost_group_code and cost_group_name:
                    # Check if cost group exists
                    db.cursor.execute("""
                        SELECT cost_group_id FROM takeoff.cost_groups 
                        WHERE cost_group_code = %s
                    """, (cost_group_code,))
                    
                    group_result = db.cursor.fetchone()
                    if group_result:
                        group_id = group_result['cost_group_id']
                        # Update existing group
                        db.cursor.execute("""
                            UPDATE takeoff.cost_groups 
                            SET cost_group_name = %s
                            WHERE cost_group_id = %s
                        """, (cost_group_name, group_id))
                    else:
                        # Create new group
                        db.cursor.execute("""
                            INSERT INTO takeoff.cost_groups (cost_group_code, cost_group_name)
                            VALUES (%s, %s) RETURNING cost_group_id
                        """, (cost_group_code, cost_group_name))
                        group_id = db.cursor.fetchone()['cost_group_id']
                    
                    # Update cost_code to reference the group
                    db.cursor.execute("""
                        UPDATE takeoff.cost_codes 
                        SET cost_group_id = %s
                        WHERE cost_code_id = %s
                    """, (group_id, cost_code_id))
                
                updated_count += 1
                
            except Exception as e:
                errors.append(f"Error updating record: {str(e)}")
                continue
        
        db.conn.commit()
        
        if errors:
            message = f"Updated {updated_count} records with {len(errors)} errors: {'; '.join(errors[:3])}"
        else:
            message = f"Successfully updated {updated_count} records"
        
        return jsonify({
            'success': True,
            'message': message,
            'updated_count': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in bulk update: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 400
    finally:
        db.disconnect()

@app.route('/api/cost-codes-with-groups/export/<format>')
def api_export_cost_codes(format):
    """API endpoint to export cost codes data in CSV or Excel format"""
    import pandas as pd
    import io
    from flask import make_response
    
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT * FROM takeoff.v_cost_codes_with_groups ORDER BY cost_code")
        records = db.cursor.fetchall()
        
        # Convert to DataFrame
        df = pd.DataFrame([dict(record) for record in records])
        
        if format.lower() == 'csv':
            # Export as CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=cost_codes_with_groups.csv'
            return response
            
        elif format.lower() == 'excel':
            # Export as Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Cost Codes', index=False)
            output.seek(0)
            
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=cost_codes_with_groups.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
            
    except Exception as e:
        logger.error(f"Error exporting cost codes: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/cost-codes-with-groups/template/<format>')
def api_cost_codes_template(format):
    """API endpoint to download import template for cost codes"""
    import pandas as pd
    import io
    from flask import make_response
    
    try:
        # Create template with headers and sample data
        template_data = {
            'cost_code': ['01.01', '01.02', '02.01'],
            'cost_code_description': ['Site Preparation', 'Excavation', 'Foundation Work'],
            'cost_group_code': ['01', '01', '02'],
            'cost_group_name': ['Site Work', 'Site Work', 'Foundation']
        }
        
        df = pd.DataFrame(template_data)
        
        if format.lower() == 'csv':
            # Template as CSV
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=cost_codes_import_template.csv'
            return response
            
        elif format.lower() == 'excel':
            # Template as Excel
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Cost Codes Template', index=False)
                
                # Add instructions sheet
                instructions = pd.DataFrame({
                    'Instructions': [
                        'Fill out the Cost Codes Template sheet with your data',
                        'cost_code: Unique identifier for the cost code (e.g., 01.01)',
                        'cost_code_description: Description of what this cost code covers',
                        'cost_group_code: Group identifier (e.g., 01, 02, 03)',
                        'cost_group_name: Name of the cost group',
                        'Save the file and upload it using the Import button',
                        'Empty rows will be skipped during import'
                    ]
                })
                instructions.to_excel(writer, sheet_name='Instructions', index=False)
            
            output.seek(0)
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=cost_codes_import_template.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
            
    except Exception as e:
        logger.error(f"Error creating cost codes template: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/cost-codes-with-groups/import', methods=['POST'])
def api_import_cost_codes():
    """API endpoint to import cost codes from Excel/CSV file"""
    import pandas as pd
    import io
    
    db = DatabaseManager()
    
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        
        # Check file extension
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            return jsonify({'success': False, 'message': 'Invalid file format. Please upload Excel (.xlsx, .xls) or CSV file'}), 400
        
        # Read file
        try:
            if file.filename.lower().endswith('.csv'):
                df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
            else:
                df = pd.read_excel(io.BytesIO(file.read()))
        except Exception as e:
            return jsonify({'success': False, 'message': f'Error reading file: {str(e)}'}), 400
        
        # Validate required columns
        required_columns = ['cost_code', 'cost_code_description']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'success': False, 'message': f'Missing required columns: {", ".join(missing_columns)}'}), 400
        
        if not db.connect():
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        
        imported_count = 0
        updated_count = 0
        errors = []
        
        # Process each row
        for index, row in df.iterrows():
            try:
                cost_code = str(row.get('cost_code', '')).strip()
                cost_code_description = str(row.get('cost_code_description', '')).strip()
                cost_group_code = str(row.get('cost_group_code', '')).strip() if pd.notna(row.get('cost_group_code')) else ''
                cost_group_name = str(row.get('cost_group_name', '')).strip() if pd.notna(row.get('cost_group_name')) else ''
                
                if not cost_code or not cost_code_description:
                    errors.append(f"Row {index + 2}: Missing cost_code or cost_code_description")
                    continue
                
                # Check if cost code exists
                db.cursor.execute("SELECT cost_code_id FROM takeoff.cost_codes WHERE cost_code = %s", (cost_code,))
                existing_cost_code = db.cursor.fetchone()
                
                cost_group_id = None
                
                # Handle cost group if provided
                if cost_group_code and cost_group_name:
                    # Check if cost group exists
                    db.cursor.execute("SELECT cost_group_id FROM takeoff.cost_groups WHERE cost_group_code = %s", (cost_group_code,))
                    existing_group = db.cursor.fetchone()
                    
                    if existing_group:
                        cost_group_id = existing_group['cost_group_id']
                        # Update group name if different
                        db.cursor.execute("""
                            UPDATE takeoff.cost_groups
                            SET cost_group_name = %s
                            WHERE cost_group_id = %s AND cost_group_name != %s
                        """, (cost_group_name, cost_group_id, cost_group_name))
                    else:
                        # Create new cost group
                        db.cursor.execute("""
                            INSERT INTO takeoff.cost_groups (cost_group_code, cost_group_name)
                            VALUES (%s, %s) RETURNING cost_group_id
                        """, (cost_group_code, cost_group_name))
                        cost_group_id = db.cursor.fetchone()['cost_group_id']
                
                if existing_cost_code:
                    # Update existing cost code
                    db.cursor.execute("""
                        UPDATE takeoff.cost_codes
                        SET cost_code_description = %s, cost_group_id = %s
                        WHERE cost_code_id = %s
                    """, (cost_code_description, cost_group_id, existing_cost_code['cost_code_id']))
                    updated_count += 1
                else:
                    # Insert new cost code
                    db.cursor.execute("""
                        INSERT INTO takeoff.cost_codes (cost_code, cost_code_description, cost_group_id)
                        VALUES (%s, %s, %s)
                    """, (cost_code, cost_code_description, cost_group_id))
                    imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue
        
        db.conn.commit()
        
        total_processed = imported_count + updated_count
        message = f"Import completed: {imported_count} new cost codes, {updated_count} updated"
        
        if errors:
            message += f", {len(errors)} errors"
        
        return jsonify({
            'success': True,
            'message': message,
            'imported_count': imported_count,
            'updated_count': updated_count,
            'total_processed': total_processed,
            'errors': errors[:10]  # Limit errors shown
        })
        
    except Exception as e:
        logger.error(f"Error importing cost codes: {e}")
        if db.conn:
            db.conn.rollback()
        return jsonify({'success': False, 'message': f'Import failed: {str(e)}'}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 4.8 QUOTES ENDPOINTS (CONTINUED) ======================================
# ============================================================================

@app.route('/api/quotes')
def api_quotes():
    """API endpoint to get quotes data"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT * FROM takeoff.v_quotes ORDER BY quote_id DESC")
        records = db.cursor.fetchall()
        
        # Convert to list of dictionaries for JSON serialization
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting quotes data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/quotes/bulk-update', methods=['POST'])
def api_bulk_update_quotes():
    """API endpoint to bulk update quotes"""
    db = DatabaseManager()
    data = request.get_json()
    
    if not data or 'updates' not in data:
        return jsonify({'success': False, 'message': 'No updates provided'}), 400
    
    updates = data['updates']
    if not isinstance(updates, list):
        return jsonify({'success': False, 'message': 'Updates must be a list'}), 400
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        updated_count = 0
        errors = []
        
        for update in updates:
            try:
                quote_id = update.get('quote_id')
                
                # Prepare update data
                update_fields = {}
                if 'cost_code_id' in update:
                    update_fields['cost_code_id'] = update['cost_code_id'] if update['cost_code_id'] else None
                if 'item_id' in update:
                    update_fields['item_id'] = update['item_id'] if update['item_id'] else None
                if 'plan_option_id' in update:
                    update_fields['plan_option_id'] = update['plan_option_id'] if update['plan_option_id'] else None
                if 'vendor_id' in update:
                    update_fields['vendor_id'] = update['vendor_id'] if update['vendor_id'] else None
                if 'price' in update:
                    update_fields['price'] = update['price'] if update['price'] else None
                if 'notes' in update:
                    update_fields['notes'] = update['notes'] if update['notes'] else None
                if 'effective_date' in update:
                    update_fields['effective_date'] = update['effective_date'] if update['effective_date'] else None
                if 'expiration_date' in update:
                    update_fields['expiration_date'] = update['expiration_date'] if update['expiration_date'] else None
                if 'quote_file' in update:
                    update_fields['quote_file'] = update['quote_file'] if update['quote_file'] else None
                
                if quote_id:
                    # Update existing quote
                    if update_fields:
                        set_clauses = [f"{field} = %s" for field in update_fields.keys()]
                        values = list(update_fields.values())
                        values.append(quote_id)
                        
                        query = f"UPDATE takeoff.quotes SET {', '.join(set_clauses)}, updated_date = CURRENT_TIMESTAMP WHERE quote_id = %s"
                        db.cursor.execute(query, values)
                else:
                    # Insert new quote
                    if update_fields:
                        columns = list(update_fields.keys())
                        values = list(update_fields.values())
                        placeholders = ['%s'] * len(columns)
                        
                        query = f"INSERT INTO takeoff.quotes ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                        db.cursor.execute(query, values)
                
                updated_count += 1
                
            except Exception as e:
                errors.append(f"Error updating quote: {str(e)}")
                continue
        
        db.conn.commit()
        
        if errors:
            message = f"Updated {updated_count} quotes with {len(errors)} errors: {'; '.join(errors[:3])}"
        else:
            message = f"Successfully updated {updated_count} quotes"
        
        return jsonify({
            'success': True,
            'message': message,
            'updated_count': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in quotes bulk update: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 400
    finally:
        db.disconnect()

# ============================================================================
# == 4.2 COST CODES ENDPOINTS (CONTINUED) ==================================
# ============================================================================

@app.route('/api/cost-codes')
def api_cost_codes():
    """API endpoint to get cost codes for dropdowns"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT cost_code_id, cost_code, cost_code_description FROM takeoff.cost_codes ORDER BY cost_code")
        records = db.cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting cost codes: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 4.9 ITEMS ENDPOINTS (CONTINUED) =======================================
# ============================================================================

@app.route('/api/items')
def api_items():
    """API endpoint to get items for dropdowns"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT item_id, item_name FROM takeoff.items ORDER BY item_name")
        records = db.cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting items: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 4.10 DROPDOWN/UTILITY ENDPOINTS =======================================
# ============================================================================

@app.route('/api/items-with-descriptions')
def api_items_with_descriptions():
    """API endpoint to get items with descriptions for item description dropdown"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("""
            SELECT i.item_name, p.item_description
            FROM takeoff.items i
            JOIN takeoff.products p ON i.item_id = p.item_id
            WHERE p.item_description IS NOT NULL AND p.item_description != ''
            AND i.item_name IS NOT NULL AND i.item_name != ''
            ORDER BY i.item_name, p.item_description
        """)
        records = db.cursor.fetchall()
        
        # Create a mapping for the dropdown
        data = {}
        for record in records:
            item_name = record['item_name']
            item_description = record['item_description']
            if item_name not in data:
                data[item_name] = []
            if item_description not in data[item_name]:
                data[item_name].append(item_description)
        
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting items with descriptions: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/vendors')
def api_vendors():
    """API endpoint to get vendors for dropdowns"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT vendor_id, vendor_name FROM takeoff.vendors ORDER BY vendor_name")
        records = db.cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting vendors: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()


# ============================================================================
# == 4.3 VENDOR PRICING ENDPOINTS (CONTINUED) ==============================
# ============================================================================

@app.route('/api/vendor-pricing', methods=['POST'])
def api_create_vendor_pricing():
    """API endpoint to create new vendor pricing"""
    db = DatabaseManager()
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        # Insert new vendor pricing
        db.cursor.execute("""
            INSERT INTO takeoff.vendor_pricing 
            (product_id, vendor_id, price, unit_of_measure, is_current, is_active)
            VALUES (%s, (SELECT vendor_id FROM takeoff.vendors WHERE vendor_name = %s), %s, %s, %s, TRUE)
        """, (
            data.get('product_id'),
            data.get('vendor_name'),
            data.get('price'),
            data.get('unit_of_measure', 'EA'),
            data.get('is_current', True)
        ))
        
        db.conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error creating vendor pricing: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/vendor-pricing/<int:pricing_id>', methods=['PUT'])
def api_update_vendor_pricing(pricing_id):
    """API endpoint to update vendor pricing (expanded for AG-Grid)"""
    db = DatabaseManager()
    data = request.get_json()

    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        update_fields = []
        params = []

        # Allow updating fields that actually exist in vendor_pricing table
        if 'vendor_name' in data:
            # Look up vendor_id from vendor_name
            db.cursor.execute("SELECT vendor_id FROM takeoff.vendors WHERE vendor_name = %s", (data['vendor_name'],))
            vendor_result = db.cursor.fetchone()
            if vendor_result:
                update_fields.append("vendor_id = %s")
                params.append(vendor_result['vendor_id'])
        
        if 'price' in data:
            update_fields.append("price = %s")
            params.append(data['price'])
        
        if 'unit_of_measure' in data:
            update_fields.append("unit_of_measure = %s")
            params.append(data['unit_of_measure'])
        
        if 'price_type' in data:
            update_fields.append("price_type = %s")
            params.append(data['price_type'])
        
        if 'notes' in data:
            update_fields.append("notes = %s")
            params.append(data['notes'])
        
        # Support updating product_id (from product_description editor)
        if 'product_id' in data:
            update_fields.append("product_id = %s")
            params.append(data['product_id'])

        # Note: cost_code and item_name are not directly editable in vendor_pricing table
        # They come from related tables through joins in the view

        if update_fields:
            update_fields.append("updated_date = CURRENT_TIMESTAMP")
            params.append(pricing_id)
            query = f"UPDATE takeoff.vendor_pricing SET {', '.join(update_fields)} WHERE pricing_id = %s"
            db.cursor.execute(query, params)
            db.conn.commit()

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error updating vendor pricing: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/vendor-pricing/<int:pricing_id>', methods=['DELETE'])
def api_delete_vendor_pricing(pricing_id):
    """API endpoint to delete vendor pricing"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("DELETE FROM takeoff.vendor_pricing WHERE pricing_id = %s", (pricing_id,))
        db.conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Error deleting vendor pricing: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/vendor-pricing/<int:pricing_id>/duplicate', methods=['POST'])
def api_duplicate_vendor_pricing(pricing_id):
    """API endpoint to duplicate a vendor pricing record"""
    db = DatabaseManager()
    data = request.get_json()
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        # Get the original record
        db.cursor.execute("""
            SELECT * FROM takeoff.vendor_pricing WHERE pricing_id = %s
        """, (pricing_id,))
        
        original = db.cursor.fetchone()
        if not original:
            return jsonify({'success': False, 'message': 'Original vendor pricing record not found'}), 404
        
        # Prepare the duplicate data - use provided data or fallback to original
        duplicate_data = {
            'vendor_id': data.get('vendor_id') or original['vendor_id'],
            'product_id': data.get('product_id') or original['product_id'],
            'price': data.get('price') or original['price'],
            'unit_of_measure': data.get('unit_of_measure') or original['unit_of_measure'],
            'price_type': data.get('price_type') or original['price_type'],
            'notes': data.get('notes') or original['notes'],
            'effective_date': data.get('effective_date') or original['effective_date'],
            'expiration_date': data.get('expiration_date') or original['expiration_date'],
            'minimum_quantity': data.get('minimum_quantity') or original['minimum_quantity'],
            'is_current': data.get('is_current', True),
            'is_active': data.get('is_active', True)
        }
        
        # Insert the duplicate record
        db.cursor.execute("""
            INSERT INTO takeoff.vendor_pricing 
            (vendor_id, product_id, price, unit_of_measure, price_type, notes, 
             effective_date, expiration_date, minimum_quantity, is_current, is_active,
             created_date, updated_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 
                    CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            RETURNING pricing_id
        """, (
            duplicate_data['vendor_id'],
            duplicate_data['product_id'],
            duplicate_data['price'],
            duplicate_data['unit_of_measure'],
            duplicate_data['price_type'],
            duplicate_data['notes'],
            duplicate_data['effective_date'],
            duplicate_data['expiration_date'],
            duplicate_data['minimum_quantity'],
            duplicate_data['is_current'],
            duplicate_data['is_active']
        ))
        
        new_pricing_id = db.cursor.fetchone()['pricing_id']
        db.conn.commit()
        
        return jsonify({'success': True, 'pricing_id': new_pricing_id})
        
    except Exception as e:
        logger.error(f"Error duplicating vendor pricing: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/products/<int:product_id>')
def api_single_product(product_id):
    """API endpoint to get a single product with pricing summary - uses direct psycopg2 connection"""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT 
                p.product_id,
                p.item_name,
                p.cost_code,
                p.product_description,
                p.model,
                p.brand,
                p.style,
                p.color,
                p.finish,
                p.size,
                p.material,
                p.item_type,
                COUNT(vp.pricing_id) as vendor_count,
                MIN(vp.price) as min_price,
                MAX(vp.price) as max_price,
                AVG(vp.price) as avg_price,
                STRING_AGG(DISTINCT v.vendor_name, ', ') as vendors
            FROM takeoff.products p
            LEFT JOIN takeoff.vendor_pricing vp ON p.product_id = vp.product_id AND vp.is_current = TRUE
            LEFT JOIN takeoff.vendors v ON vp.vendor_id = v.vendor_id
            WHERE p.product_id = %s
            GROUP BY p.product_id, p.item_name, p.cost_code, p.product_description, 
                     p.model, p.brand, p.style, p.color, p.finish, p.size, p.material, p.item_type
        """, (product_id,))
        record = cursor.fetchone()
        
        if record:
            return jsonify(dict(record))
        else:
            return jsonify({'error': 'Product not found'}), 404
    except Exception as e:
        logger.error(f"Error getting product {product_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# ============================================================================
# == 4.10 DROPDOWN/UTILITY ENDPOINTS (CONTINUED) ===========================
# ============================================================================

@app.route('/api/formulas')
def api_formulas():
    """API endpoint to get formulas for dropdowns"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT formula_id, formula_name, formula_text, formula_type FROM takeoff.formulas ORDER BY formula_name")
        records = db.cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting formulas: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 4.9 ITEMS ENDPOINTS (CONTINUED) =======================================
# ============================================================================

@app.route('/api/items-detailed')
def api_items_detailed():
    """API endpoint to get items with detailed information"""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        cursor.execute("""
            SELECT
                i.item_id,
                i.item_name,
                i.qty_formula,
                cc.cost_code,
                cc.cost_code_description,
                f.formula_name,
                f.formula_text,
                i.item_type,
                i.qty_type,
                i.default_unit,
                i.created_date,
                i.modified_date
            FROM takeoff.items i
            LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
            LEFT JOIN takeoff.formulas f ON i.formula_id = f.formula_id
            ORDER BY i.item_id
        """)
        records = cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting items detailed data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/items/bulk-update', methods=['POST'])
def api_bulk_update_items():
    """API endpoint to bulk update items"""
    db = DatabaseManager()
    data = request.get_json()
    
    if not data or 'updates' not in data:
        return jsonify({'success': False, 'message': 'No updates provided'}), 400
    
    updates = data['updates']
    if not isinstance(updates, list):
        return jsonify({'success': False, 'message': 'Updates must be a list'}), 400
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        updated_count = 0
        errors = []
        
        for update in updates:
            try:
                item_id = update.get('item_id')
                
                if item_id:
                    # Update existing item
                    update_fields = []
                    params = []
                    
                    if 'item_name' in update:
                        update_fields.append("item_name = %s")
                        params.append(update['item_name'])

                    if 'qty_formula' in update:
                        update_fields.append("qty_formula = %s")
                        params.append(update['qty_formula'])

                    if 'cost_code' in update and update['cost_code']:
                        # Get cost_code_id from cost_code
                        db.cursor.execute("SELECT cost_code_id FROM takeoff.cost_codes WHERE cost_code = %s", (update['cost_code'],))
                        cost_code_result = db.cursor.fetchone()
                        if cost_code_result:
                            update_fields.append("cost_code_id = %s")
                            params.append(cost_code_result['cost_code_id'])

                    if 'formula_name' in update and update['formula_name']:
                        # Get formula_id from formula_name
                        db.cursor.execute("SELECT formula_id FROM takeoff.formulas WHERE formula_name = %s", (update['formula_name'],))
                        formula_result = db.cursor.fetchone()
                        if formula_result:
                            update_fields.append("formula_id = %s")
                            params.append(formula_result['formula_id'])

                    if 'qty_type' in update:
                        update_fields.append("qty_type = %s")
                        params.append(update['qty_type'])

                    if 'default_unit' in update:
                        update_fields.append("default_unit = %s")
                        params.append(update['default_unit'])

                    if update_fields:
                        params.append(item_id)
                        query = f"UPDATE takeoff.items SET {', '.join(update_fields)} WHERE item_id = %s"
                        db.cursor.execute(query, params)
                else:
                    # Insert new item
                    insert_fields = ['item_name']
                    insert_values = [update.get('item_name', '')]
                    
                    # Handle qty_formula
                    if update.get('qty_formula') is not None:
                        insert_fields.append('qty_formula')
                        insert_values.append(update['qty_formula'])

                    # Handle cost code
                    if update.get('cost_code'):
                        db.cursor.execute("SELECT cost_code_id FROM takeoff.cost_codes WHERE cost_code = %s", (update['cost_code'],))
                        cost_code_result = db.cursor.fetchone()
                        if cost_code_result:
                            insert_fields.append('cost_code_id')
                            insert_values.append(cost_code_result['cost_code_id'])

                    # Handle formula
                    if update.get('formula_name'):
                        db.cursor.execute("SELECT formula_id FROM takeoff.formulas WHERE formula_name = %s", (update['formula_name'],))
                        formula_result = db.cursor.fetchone()
                        if formula_result:
                            insert_fields.append('formula_id')
                            insert_values.append(formula_result['formula_id'])

                    if update.get('qty_type'):
                        insert_fields.append('qty_type')
                        insert_values.append(update['qty_type'])

                    if update.get('default_unit'):
                        insert_fields.append('default_unit')
                        insert_values.append(update['default_unit'])

                    placeholders = ['%s'] * len(insert_fields)
                    query = f"INSERT INTO takeoff.items ({', '.join(insert_fields)}) VALUES ({', '.join(placeholders)})"
                    db.cursor.execute(query, insert_values)
                
                updated_count += 1
                
            except Exception as e:
                errors.append(f"Error updating item: {str(e)}")
                continue
        
        db.conn.commit()
        
        if errors:
            message = f"Updated {updated_count} items with {len(errors)} errors: {'; '.join(errors[:3])}"
        else:
            message = f"Successfully updated {updated_count} items"
        
        return jsonify({
            'success': True,
            'message': message,
            'updated_count': updated_count,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in items bulk update: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 400
    finally:
        db.disconnect()

@app.route('/api/items/import', methods=['POST'])
def api_import_items():
    """API endpoint to import items from Excel data"""
    db = DatabaseManager()
    request_data = request.get_json()
    
    if not request_data or 'data' not in request_data:
        return jsonify({'success': False, 'message': 'No import data provided'}), 400
    
    import_data = request_data['data']
    options = request_data.get('options', {})
    
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    
    try:
        imported_count = 0
        updated_count = 0
        errors = []
        
        for row in import_data:
            try:
                # Map common column names
                item_name = row.get('item_name') or row.get('Item Name') or row.get('name') or ''
                cost_code = row.get('cost_code') or row.get('Cost Code') or ''
                formula_name = row.get('formula_name') or row.get('Formula') or ''
                qty_type = row.get('qty_type') or row.get('Quantity Type') or 'Count'
                default_unit = row.get('default_unit') or row.get('Unit') or row.get('Default Unit') or 'EA'
                
                if not item_name:
                    errors.append("Skipping row with missing item name")
                    continue
                
                # Check if item exists (for update mode)
                if options.get('updateExisting', False):
                    db.cursor.execute("SELECT item_id FROM takeoff.items WHERE item_name = %s", (item_name,))
                    existing_item = db.cursor.fetchone()
                else:
                    existing_item = None
                
                # Prepare data for insert/update
                item_data = {
                    'item_name': item_name,
                    'qty_type': qty_type,
                    'default_unit': default_unit
                }
                
                # Handle cost code
                if cost_code:
                    db.cursor.execute("SELECT cost_code_id FROM takeoff.cost_codes WHERE cost_code = %s", (cost_code,))
                    cost_code_result = db.cursor.fetchone()
                    if cost_code_result:
                        item_data['cost_code_id'] = cost_code_result['cost_code_id']
                
                # Handle formula
                if formula_name:
                    db.cursor.execute("SELECT formula_id FROM takeoff.formulas WHERE formula_name = %s", (formula_name,))
                    formula_result = db.cursor.fetchone()
                    if formula_result:
                        item_data['formula_id'] = formula_result['formula_id']
                
                if existing_item:
                    # Update existing item
                    set_clauses = [f"{field} = %s" for field in item_data.keys()]
                    values = list(item_data.values())
                    values.append(existing_item['item_id'])
                    
                    query = f"UPDATE takeoff.items SET {', '.join(set_clauses)} WHERE item_id = %s"
                    db.cursor.execute(query, values)
                    updated_count += 1
                else:
                    # Insert new item
                    columns = list(item_data.keys())
                    values = list(item_data.values())
                    placeholders = ['%s'] * len(columns)
                    
                    query = f"INSERT INTO takeoff.items ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    db.cursor.execute(query, values)
                    imported_count += 1
                
            except Exception as e:
                if options.get('skipErrors', False):
                    errors.append(f"Error processing row: {str(e)}")
                    continue
                else:
                    raise e
        
        db.conn.commit()
        
        total_processed = imported_count + updated_count
        message = f"Import completed: {imported_count} new items, {updated_count} updated"
        
        if errors:
            message += f", {len(errors)} errors"
        
        return jsonify({
            'success': True,
            'message': message,
            'imported_count': imported_count,
            'updated_count': updated_count,
            'total_processed': total_processed,
            'errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error in items import: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': f'Import failed: {str(e)}'}), 400
    finally:
        db.disconnect()

# ============================================================================
# == 4.6 PLAN OPTIONS ENDPOINTS (CONTINUED) ================================
# ============================================================================

@app.route('/api/plan-options/<int:plan_option_id>', methods=['DELETE'])
def api_delete_plan_option(plan_option_id):
    """API endpoint to delete a plan option by ID"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    try:
        db.cursor.execute("DELETE FROM takeoff.plan_options WHERE plan_option_id = %s", (plan_option_id,))
        db.conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/plan-options/<int:plan_option_id>/duplicate', methods=['POST'])
def api_duplicate_plan_option(plan_option_id):
    """API endpoint to duplicate a plan option row"""
    db = DatabaseManager()
    data = request.get_json()
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    try:
        # Get the original row
        db.cursor.execute("""
            SELECT * FROM takeoff.plan_options WHERE plan_option_id = %s
        """, (plan_option_id,))
        orig = db.cursor.fetchone()
        if not orig:
            return jsonify({'success': False, 'message': 'Original plan option not found'}), 404

        # Find plan_elevation_id from plan_full_name (required)
        plan_full_name = data.get('plan_full_name') or orig.get('plan_full_name')
        db.cursor.execute("SELECT plan_elevation_id FROM takeoff.plan_elevations WHERE plan_full_name = %s", (plan_full_name,))
        pe = db.cursor.fetchone()
        if not pe:
            return jsonify({'success': False, 'message': f"Plan '{plan_full_name}' not found"}), 400
        plan_elevation_id = pe['plan_elevation_id']

        # Prepare insert fields
        insert_fields = [
            'plan_elevation_id', 'option_name', 'option_type', 'option_description',
            'bedroom_count', 'bathroom_count', 'heated_sf_inside_studs', 'heated_sf_outside_studs',
            'heated_sf_outside_veneer', 'unheated_sf_inside_studs', 'unheated_sf_outside_studs',
            'unheated_sf_outside_veneer', 'total_sf_inside_studs', 'total_sf_outside_studs',
            'total_sf_outside_veneer'
        ]
        # Use provided data or fallback to original
        values = [
            plan_elevation_id,
            data.get('option_name', orig.get('option_name')),
            data.get('option_type', orig.get('option_type')),
            data.get('option_description', orig.get('option_description')),
            data.get('bedroom_count', orig.get('bedroom_count')),
            data.get('bathroom_count', orig.get('bathroom_count')),
            data.get('heated_sf_inside_studs', orig.get('heated_sf_inside_studs')),
            data.get('heated_sf_outside_studs', orig.get('heated_sf_outside_studs')),
            data.get('heated_sf_outside_veneer', orig.get('heated_sf_outside_veneer')),
            data.get('unheated_sf_inside_studs', orig.get('unheated_sf_inside_studs')),
            data.get('unheated_sf_outside_studs', orig.get('unheated_sf_outside_studs')),
            data.get('unheated_sf_outside_veneer', orig.get('unheated_sf_outside_veneer')),
            data.get('total_sf_inside_studs', orig.get('total_sf_inside_studs')),
            data.get('total_sf_outside_studs', orig.get('total_sf_outside_studs')),
            data.get('total_sf_outside_veneer', orig.get('total_sf_outside_veneer'))
        ]
        db.cursor.execute(f"""
            INSERT INTO takeoff.plan_options
            ({', '.join(insert_fields)})
            VALUES ({', '.join(['%s'] * len(insert_fields))})
            RETURNING plan_option_id
        """, values)
        new_id = db.cursor.fetchone()['plan_option_id']
        db.conn.commit()
        return jsonify({'success': True, 'plan_option_id': new_id})
    except Exception as e:
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

# Plan Options endpoints
@app.route('/api/plan-options')
def api_plan_options():
    """API endpoint to get plan options data (all columns, robust join)"""
    db = DatabaseManager()
    if not db.connect():
        logger.error("Database connection failed in /api/plan-options")
        return jsonify([]), 200
    try:
        # Select only the specific fields needed for the dropdown
        db.cursor.execute("""
            SELECT
                po.plan_option_id,
                po.option_name,
                po.plan_elevation_id,
                COALESCE(pe.plan_full_name, '') AS plan_full_name
            FROM takeoff.plan_options po
            LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            ORDER BY po.plan_option_id
        """)
        records = db.cursor.fetchall()
        data = [dict(record) for record in records] if records else []
        return jsonify(data)
    except Exception as e:
        import traceback
        logger.error(f"Error in /api/plan-options: {e}")
        traceback.print_exc()
        return jsonify([]), 200
    finally:
        db.disconnect()

@app.route('/api/plan-options/export/<format>')
def api_export_plan_options(format):
    """API endpoint to export plan options data in CSV or Excel format"""
    import pandas as pd
    import io
    from flask import make_response
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        db.cursor.execute("""
            SELECT
                po.plan_option_id,
                pe.plan_full_name,
                po.option_name,
                po.option_description,
                po.total_sf_outside_studs,
                po.created_date,
                po.modified_date
            FROM takeoff.plan_options po
            JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            ORDER BY po.plan_option_id
        """)
        records = db.cursor.fetchall()
        df = pd.DataFrame([dict(record) for record in records])
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=plan_options.csv'
            return response
        elif format.lower() == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Plan Options', index=False)
            output.seek(0)
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=plan_options.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/plan-options/template/<format>')
def api_plan_options_template(format):
    """API endpoint to download import template for plan options"""
    import pandas as pd
    import io
    from flask import make_response
    try:
        template_data = {
            'plan_option_id': [''],
            'plan_full_name': ['Sample Plan'],
            'option_name': ['BaseHome'],
            'option_description': ['Description'],
            'total_sf_outside_studs': [1000.0],
            'created_date': [''],
            'modified_date': ['']
        }
        df = pd.DataFrame(template_data)
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=plan_options_import_template.csv'
            return response
        elif format.lower() == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Plan Options Template', index=False)
                instructions = pd.DataFrame({
                    'Instructions': [
                        'Fill out the Plan Options Template sheet with your data',
                        'plan_full_name: Plan name',
                        'option_name: Option name',
                        'option_description: Description',
                        'total_sf_outside_studs: Numeric value',
                        'created_date, modified_date: Leave blank for new rows',
                        'Save the file and upload it using the Import button',
                        'Empty rows will be skipped during import'
                    ]
                })
                instructions.to_excel(writer, sheet_name='Instructions', index=False)
            output.seek(0)
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=plan_options_import_template.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/plan-options/import', methods=['POST'])
def api_import_plan_options():
    """API endpoint to import plan options from Excel/CSV file"""
    import pandas as pd
    import io
    db = DatabaseManager()
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            return jsonify({'success': False, 'message': 'Invalid file format. Please upload Excel (.xlsx, .xls) or CSV file'}), 400
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file.read()))
        required_columns = ['plan_full_name', 'option_name']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'success': False, 'message': f'Missing required columns: {", ".join(missing_columns)}'}), 400
        if not db.connect():
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        imported_count = 0
        errors = []
        for index, row in df.iterrows():
            try:
                # Get plan_elevation_id from plan_full_name
                db.cursor.execute("SELECT plan_elevation_id FROM takeoff.plan_elevations WHERE plan_full_name = %s", (row.get('plan_full_name', ''),))
                pe = db.cursor.fetchone()
                if not pe:
                    errors.append(f"Row {index + 2}: Plan '{row.get('plan_full_name', '')}' not found")
                    continue
                db.cursor.execute("""
                    INSERT INTO takeoff.plan_options
                    (plan_elevation_id, option_name, option_description, total_sf_outside_studs)
                    VALUES (%s, %s, %s, %s)
                """, (
                    pe['plan_elevation_id'],
                    row.get('option_name', ''),
                    row.get('option_description', ''),
                    row.get('total_sf_outside_studs', 0)
                ))
                imported_count += 1
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue
        db.conn.commit()
        message = f"Import completed: {imported_count} new plan options"
        if errors:
            message += f", {len(errors)} errors"
        return jsonify({
            'success': True,
            'message': message,
            'imported_count': imported_count,
            'errors': errors[:10]
        })
    except Exception as e:
        if db.conn:
            db.conn.rollback()
        return jsonify({'success': False, 'message': f'Import failed: {str(e)}'}), 500
    finally:
        db.disconnect()

@app.route('/api/plan-options/bulk-update', methods=['POST'])
def api_bulk_update_plan_options():
    """API endpoint to bulk update plan options (all fields)"""
    db = DatabaseManager()
    data = request.get_json()
    if not data or 'updates' not in data:
        return jsonify({'success': False, 'message': 'No updates provided'}), 400
    updates = data['updates']
    if not isinstance(updates, list):
        return jsonify({'success': False, 'message': 'Updates must be a list'}), 400
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    try:
        updated_count = 0
        errors = []
        # List of all editable fields in plan_options (excluding PK and computed fields)
        editable_fields = [
            'plan_elevation_id', 'option_name', 'option_type', 'option_description',
            'bedroom_count', 'bathroom_count',
            'heated_sf_inside_studs', 'heated_sf_outside_studs', 'heated_sf_outside_veneer',
            'unheated_sf_inside_studs', 'unheated_sf_outside_studs', 'unheated_sf_outside_veneer',
            'total_sf_inside_studs', 'total_sf_outside_studs', 'total_sf_outside_veneer'
        ]
        for update in updates:
            try:
                plan_option_id = update.get('plan_option_id')
                if plan_option_id:
                    update_fields = []
                    params = []
                    # Handle plan_full_name -> plan_elevation_id
                    if 'plan_full_name' in update:
                        db.cursor.execute("SELECT plan_elevation_id FROM takeoff.plan_elevations WHERE plan_full_name = %s", (update['plan_full_name'],))
                        pe = db.cursor.fetchone()
                        if pe:
                            update_fields.append("plan_elevation_id = %s")
                            params.append(pe['plan_elevation_id'])
                    # Handle all other editable fields
                    for field in editable_fields:
                        if field in update and field != 'plan_elevation_id':
                            update_fields.append(f"{field} = %s")
                            params.append(update[field])
                    if update_fields:
                        params.append(plan_option_id)
                        query = f"UPDATE takeoff.plan_options SET {', '.join(update_fields)} WHERE plan_option_id = %s"
                        db.cursor.execute(query, params)
                else:
                    # Insert new (not common from UI, but support basic fields)
                    fields = []
                    values = []
                    if 'plan_full_name' in update:
                        db.cursor.execute("SELECT plan_elevation_id FROM takeoff.plan_elevations WHERE plan_full_name = %s", (update['plan_full_name'],))
                        pe = db.cursor.fetchone()
                        if pe:
                            fields.append('plan_elevation_id')
                            values.append(pe['plan_elevation_id'])
                    for field in editable_fields:
                        if field in update and field != 'plan_elevation_id':
                            fields.append(field)
                            values.append(update[field])
                    if fields:
                        placeholders = ','.join(['%s'] * len(fields))
                        query = f"INSERT INTO takeoff.plan_options ({','.join(fields)}) VALUES ({placeholders})"
                        db.cursor.execute(query, values)
                updated_count += 1
            except Exception as e:
                errors.append(f"Error updating plan_option: {str(e)}")
                continue
        db.conn.commit()
        if errors:
            message = f"Updated {updated_count} plan options with {len(errors)} errors: {'; '.join(errors[:3])}"
        else:
            message = f"Successfully updated {updated_count} plan options"
        return jsonify({
            'success': True,
            'message': message,
            'updated_count': updated_count,
            'errors': errors
        })
    except Exception as e:
        db.conn.rollback()
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 400
    finally:
        db.disconnect()

# ============================================================================
# == 4.7 QTY TAKEOFFS ENDPOINTS (CONTINUED) ================================
# ============================================================================

@app.route('/api/qty-takeoffs')
def api_qty_takeoffs():
    """API endpoint to get Qty Takeoffs data directly from takeoffs table with joins"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        # Query the takeoffs table directly with necessary joins
        db.cursor.execute("""
            SELECT
                t.takeoff_id,
                t.plan_option_id,
                po.option_name,
                pe.plan_full_name,
                t.cost_code_id,
                cc.cost_code,
                t.item_id,
                i.item_name,
                t.item_description,
                t.quantity_source,
                t.quantity,
                COALESCE(t.quantity * COALESCE(t.price_factor, 1), 0) AS calculated_quantity,
                t.unit_price,
                t.price_factor,
                t.unit_of_measure,
                t.extended_price,
                t.vendor_id,
                v.vendor_name,
                t.notes,
                t.job_name,
                t.job_number,
                t.lot_number,
                t.customer_name,
                t.room,
                t.spec_name,
                t.job_id,
                t.product_id
            FROM takeoff.takeoffs t
            LEFT JOIN takeoff.plan_options po ON t.plan_option_id = po.plan_option_id
            LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            LEFT JOIN takeoff.cost_codes cc ON t.cost_code_id = cc.cost_code_id
            LEFT JOIN takeoff.items i ON t.item_id = i.item_id
            LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
            ORDER BY t.takeoff_id
        """)
        records = db.cursor.fetchall()
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting qty takeoffs data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/qty-takeoffs/export/<format>')
def api_export_qty_takeoffs(format):
    """API endpoint to export Qty Takeoffs data in CSV or Excel format"""
    import pandas as pd
    import io
    from flask import make_response
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        # Use the same query as the api_qty_takeoffs endpoint
        db.cursor.execute("""
            SELECT
                t.takeoff_id,
                t.plan_option_id,
                po.option_name,
                pe.plan_full_name,
                COALESCE(t.quantity * COALESCE(t.price_factor, 1), 0) AS calculated_quantity,
                t.cost_code_id,
                cc.cost_code,
                t.item_id,
                i.item_name,
                t.item_description,
                t.quantity_source,
                t.quantity,
                t.calculated_quantity,
                t.unit_price,
                t.price_factor,
                t.unit_of_measure,
                t.extended_price,
                t.vendor_id,
                v.vendor_name,
                t.notes,
                t.job_name,
                t.job_number,
                t.lot_number,
                t.customer_name,
                t.room,
                t.spec_name,
                t.job_id,
                t.product_id
            FROM takeoff.takeoffs t
            LEFT JOIN takeoff.plan_options po ON t.plan_option_id = po.plan_option_id
            LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            LEFT JOIN takeoff.cost_codes cc ON t.cost_code_id = cc.cost_code_id
            LEFT JOIN takeoff.items i ON t.item_id = i.item_id
            LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
            ORDER BY t.takeoff_id
        """)
        records = db.cursor.fetchall()
        df = pd.DataFrame([dict(record) for record in records])
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=qty_takeoffs.csv'
            return response
        elif format.lower() == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Qty Takeoffs', index=False)
            output.seek(0)
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=qty_takeoffs.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
    except Exception as e:
        logger.error(f"Error exporting qty takeoffs: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/qty-takeoffs/template/<format>')
def api_qty_takeoffs_template(format):
    """API endpoint to download import template for Qty Takeoffs (all 26 fields)"""
    import pandas as pd
    import io
    from flask import make_response
    try:
        template_data = {
            'takeoff_id': [''],
            'plan_full_name': ['Sample Plan'],
            'option_name': ['BaseHome'],
            'cost_code': ['10-200'],
            'item_name': ['Plan Development'],
            'item_description': ['Plan Development'],
            'quantity_source': ['Manual'],
            'quantity': [1.0],
            'unit_price': [100.0],
            'price_factor': [1.0],
            'unit_of_measure': ['EA'],
            'extended_price': [100.0],
            'vendor_name': ['Sample Vendor'],
            'notes': ['Sample notes'],
            'job_name': ['Sample Job'],
            'job_number': ['J-1001'],
            'lot_number': ['L-12'],
            'customer_name': ['Sample Customer'],
            'room': ['Living Room'],
            'spec_name': ['Spec A'],
            'job_id': [''],
            'product_id': [''],
            'vendor_id': [''],
            'plan_option_id': [''],
            'item_id': [''],
            'cost_code_id': ['']
        }
        df = pd.DataFrame(template_data)
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=qty_takeoffs_import_template.csv'
            return response
        elif format.lower() == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Qty Takeoffs Template', index=False)
                instructions = pd.DataFrame({
                    'Instructions': [
                        'Fill out the Qty Takeoffs Template sheet with your data',
                        'All columns are required for import. Use blank for IDs if creating new records.',
                        'takeoff_id: Leave blank for new rows, or provide to update existing',
                        'plan_full_name: Plan name',
                        'option_name: Option name',
                        'cost_code: Cost code',
                        'item_name: Item name',
                        'item_description: Description',
                        'quantity_source: Source of quantity',
                        'quantity: Numeric value',
                        'unit_price: Unit price',
                        'price_factor: Price factor',
                        'unit_of_measure: Unit of measure',
                        'extended_price: Extended price',
                        'vendor_name: Vendor name',
                        'notes: Any notes',
                        'job_name: Job name',
                        'job_number: Job number',
                        'lot_number: Lot number',
                        'customer_name: Customer name',
                        'room: Room',
                        'spec_name: Specification name',
                        'job_id, product_id, vendor_id, plan_option_id, item_id, cost_code_id: Use if updating existing records, otherwise leave blank',
                        'Save the file and upload it using the Import button',
                        'Empty rows will be skipped during import'
                    ]
                })
                instructions.to_excel(writer, sheet_name='Instructions', index=False)
            output.seek(0)
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=qty_takeoffs_import_template.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
    except Exception as e:
        logger.error(f"Error creating qty takeoffs template: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/qty-takeoffs/import', methods=['POST'])
def api_import_qty_takeoffs():
    """API endpoint to import Qty Takeoffs from Excel/CSV file"""
    import pandas as pd
    import io
    db = DatabaseManager()
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'}), 400
        file = request.files['file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'}), 400
        if not file.filename.lower().endswith(('.xlsx', '.xls', '.csv')):
            return jsonify({'success': False, 'message': 'Invalid file format. Please upload Excel (.xlsx, .xls) or CSV file'}), 400
        if file.filename.lower().endswith('.csv'):
            df = pd.read_csv(io.StringIO(file.read().decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(file.read()))
        required_columns = ['plan_full_name', 'option_name', 'cost_code', 'item_name', 'item_description', 'quantity_source', 'quantity']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'success': False, 'message': f'Missing required columns: {", ".join(missing_columns)}'}), 400
        if not db.connect():
            return jsonify({'success': False, 'message': 'Database connection failed'}), 500
        imported_count = 0
        errors = []
        for index, row in df.iterrows():
            try:
                # Insert into a staging table or main table as appropriate
                db.cursor.execute("""
                    INSERT INTO takeoff.qty_takeoffs_staging
                    (plan_full_name, option_name, cost_code, item_name, item_description, quantity_source, quantity)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    row.get('plan_full_name', ''),
                    row.get('option_name', ''),
                    row.get('cost_code', ''),
                    row.get('item_name', ''),
                    row.get('item_description', ''),
                    row.get('quantity_source', ''),
                    row.get('quantity', 0)
                ))
                imported_count += 1
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue
        db.conn.commit()
        message = f"Import completed: {imported_count} new qty takeoffs"
        if errors:
            message += f", {len(errors)} errors"
        return jsonify({
            'success': True,
            'message': message,
            'imported_count': imported_count,
            'errors': errors[:10]
        })
    except Exception as e:
        logger.error(f"Error importing qty takeoffs: {e}")
        if db.conn:
            db.conn.rollback()
        return jsonify({'success': False, 'message': f'Import failed: {str(e)}'}), 500
    finally:
        db.disconnect()

@app.route('/api/qty-takeoffs/delete', methods=['POST'])
def api_delete_qty_takeoffs():
    """API endpoint to delete qty takeoffs by takeoff_id"""
    db = DatabaseManager()
    data = request.get_json()
    ids = data.get('takeoff_ids', [])
    if not ids or not isinstance(ids, list):
        return jsonify({'success': False, 'message': 'No takeoff_ids provided'}), 400
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    try:
        deleted = 0
        for takeoff_id in ids:
            db.cursor.execute("DELETE FROM takeoff.takeoffs WHERE takeoff_id = %s", (takeoff_id,))
            deleted += db.cursor.rowcount
        db.conn.commit()
        return jsonify({'success': True, 'deleted': deleted})
    except Exception as e:
        logger.error(f"Error deleting takeoffs: {e}")
        if db.conn:
            db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/qty-takeoffs/bulk-update', methods=['POST'])
def api_bulk_update_qty_takeoffs():
    """API endpoint to bulk update Qty Takeoffs"""
    db = DatabaseManager()
    data = request.get_json()
    if not data or 'updates' not in data:
        return jsonify({'success': False, 'message': 'No updates provided'}), 400
    updates = data['updates']
    if not isinstance(updates, list):
        return jsonify({'success': False, 'message': 'Updates must be a list'}), 400
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500
    try:
        updated_count = 0
        errors = []
        for update in updates:
            try:
                takeoff_id = update.get('takeoff_id')
                if takeoff_id:
                    # Update existing takeoff record
                    update_fields = []
                    params = []
                    
                    # Build dynamic update based on available fields
                    field_mappings = {
                        'quantity_source': 'quantity_source',
                        'quantity': 'quantity', 
                        'unit_price': 'unit_price',
                        'price_factor': 'price_factor',
                        'unit_of_measure': 'unit_of_measure',
                        'notes': 'notes',
                        'room': 'room',
                        'spec_name': 'spec_name'
                    }
                    
                    for field, db_field in field_mappings.items():
                        if field in update:
                            update_fields.append(f"{db_field} = %s")
                            params.append(update[field])
                    
                    if update_fields:
                        params.append(takeoff_id)
                        query = f"UPDATE takeoff.takeoffs SET {', '.join(update_fields)} WHERE takeoff_id = %s"
                        db.cursor.execute(query, params)
                        updated_count += 1
                else:
                    # Insert new takeoff record - this would need proper job_id, product_id, vendor_id lookups
                    # For now, we'll skip new inserts as they require more complex logic
                    errors.append("Creating new takeoff records not supported via bulk update")
                    continue
                    
            except Exception as e:
                errors.append(f"Error updating takeoff {takeoff_id}: {str(e)}")
                continue
        db.conn.commit()
        if errors:
            message = f"Updated {updated_count} takeoffs with {len(errors)} errors: {'; '.join(errors[:3])}"
        else:
            message = f"Successfully updated {updated_count} takeoffs"
        return jsonify({
            'success': True,
            'message': message,
            'updated_count': updated_count,
            'errors': errors
        })
    except Exception as e:
        logger.error(f"Error in qty takeoffs bulk update: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': f'Update failed: {str(e)}'}), 400
    finally:
        db.disconnect()

@app.route('/api/comprehensive-takeoff-analysis')
def api_comprehensive_takeoff_analysis():
    """API endpoint to get comprehensive takeoff analysis data"""
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT * FROM takeoff.v_comprehensive_takeoff_analysis ORDER BY cost_code, item_name")
        records = db.cursor.fetchall()
        
        # Convert to list of dictionaries for JSON serialization
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting comprehensive takeoff analysis data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

# ============================================================================
# == 4.4 PRODUCTS ENDPOINTS (CONTINUED) ====================================
# ============================================================================

def api_create_product():
    """API endpoint to create a new product (with optional cost code and item linkage)"""
    logger.info("api_create_product called")
    conn = None
    cursor = None
    try:
        data = request.get_json()
        logger.info(f"Received data: {data}")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        item_id = data.get('item_id')
        logger.info(f"Initial item_id: {item_id}")
        try:
            item_id = int(item_id) if item_id else None
            if item_id and item_id <= 0:
                item_id = None
        except (TypeError, ValueError):
            item_id = None
        logger.info(f"Processed item_id: {item_id}")

        if not item_id:
            logger.warning("No item_id provided for duplication. A new product cannot be created without linking to an item.")
            return jsonify({'error': 'item_id is required to duplicate a product'}), 400

        # Insert new product, linking to item if provided or created
        insert_fields = [
            'item_description', 'brand', 'model', 'item_type', 'style', 'color', 'finish',
            'material', 'size', 'unit_of_measure', 'image_url', 'is_active',
            'plan_option_id', 'min_stock_level', 'quantity'
        ]
        insert_values = [data.get(f) for f in insert_fields]
        if item_id:
            insert_fields.insert(0, 'item_id')
            insert_values.insert(0, item_id)

        logger.info(f"Inserting product with fields: {insert_fields}")
        query = f"""
            INSERT INTO takeoff.products ({', '.join(insert_fields)})
            VALUES ({', '.join(['%s'] * len(insert_fields))})
            RETURNING product_id
        """
        cursor.execute(query, insert_values)
        product_id = cursor.fetchone()['product_id']
        logger.info(f"Successfully inserted product_id: {product_id}")
        conn.commit()
        return jsonify({'success': True, 'product_id': product_id}), 201

    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating product: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        logger.info("api_create_product finished")

@app.route('/api/products/<int:product_id>', methods=['PUT'])
def api_update_product(product_id):
    """API endpoint to update a product - supports partial updates for inline editing"""
    conn = None
    cursor = None
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Build dynamic UPDATE query for only the fields provided
        update_fields = []
        update_values = {}
        
        # Map of allowed fields for update
        allowed_fields = {
            'item_description': 'item_description',
            'product_description': 'item_description',  # Frontend uses product_description, maps to item_description in DB
            'brand': 'brand',
            'model': 'model',
            'item_type': 'item_type',
            'style': 'style',
            'color': 'color',
            'finish': 'finish',
            'material': 'material',
            'size': 'size',
            'unit_of_measure': 'unit_of_measure',
            'image_url': 'image_url',
            'is_active': 'is_active',
            'plan_option_id': 'plan_option_id',
            'min_stock_level': 'min_stock_level',
            'quantity': 'quantity'
        }
        
        # Build the SET clause dynamically
        for field, db_column in allowed_fields.items():
            if field in data:
                update_fields.append(f"{db_column} = %({field})s")
                update_values[field] = data[field]
        
        if not update_fields:
            return jsonify({'error': 'No valid fields to update'}), 400
        
        # Execute the dynamic update
        update_query = f"""
            UPDATE takeoff.products SET
                {', '.join(update_fields)}
            WHERE product_id = %(product_id)s
        """
        
        update_values['product_id'] = product_id
        cursor.execute(update_query, update_values)
        
        if cursor.rowcount == 0:
            return jsonify({'error': 'Product not found'}), 404
        
        conn.commit()
        
        # Return the updated product data
        cursor.execute("""
            SELECT
                p.product_id,
                p.item_description,
                p.brand,
                p.model,
                p.item_type,
                p.style,
                p.color,
                p.finish,
                p.material,
                p.size,
                p.unit_of_measure,
                p.image_url,
                p.is_active,
                p.plan_option_id,
                p.min_stock_level,
                p.quantity,
                CASE
                    WHEN p.plan_option_id IS NOT NULL THEN
                        CONCAT(pe.plan_full_name, '_', po.option_name)
                    ELSE NULL
                END as plan_option_display
            FROM takeoff.products p
            LEFT JOIN takeoff.plan_options po ON p.plan_option_id = po.plan_option_id
            LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            WHERE p.product_id = %s
        """, (product_id,))
        
        updated_product = cursor.fetchone()
        if updated_product:
            return jsonify(dict(updated_product)), 200
        else:
            return jsonify({'success': True}), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error updating product: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/products/import', methods=['POST'])
def api_import_products():
    """API endpoint to import products from Excel file"""
    import pandas as pd
    import io
    
    conn = None
    cursor = None
    try:
        # Check if file was uploaded
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Check file extension
        if not file.filename.lower().endswith(('.xlsx', '.xls')):
            return jsonify({'error': 'Invalid file format. Please upload an Excel file (.xlsx or .xls)'}), 400
        
        # Read Excel file
        try:
            df = pd.read_excel(io.BytesIO(file.read()))
        except Exception as e:
            return jsonify({'error': f'Error reading Excel file: {str(e)}'}), 400
        
        # Validate required columns
        required_columns = ['item_description', 'brand', 'model']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            return jsonify({'error': f'Missing required columns: {", ".join(missing_columns)}'}), 400
        
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        imported_count = 0
        errors = []
        
        # Process each row
        for index, row in df.iterrows():
            try:
                # Prepare data with defaults
                product_data = {
                    'item_description': row.get('item_description', ''),
                    'brand': row.get('brand', ''),
                    'model': row.get('model', ''),
                    'item_type': row.get('item_type', 'Product'),
                    'style': row.get('style', ''),
                    'color': row.get('color', ''),
                    'finish': row.get('finish', ''),
                    'material': row.get('material', ''),
                    'size': row.get('size', ''),
                    'unit_of_measure': row.get('unit_of_measure', 'Each'),
                    'image_url': row.get('image_url', '/static/images/default-product.png'),
                    'is_active': bool(row.get('is_active', True)),
                    'plan_option_id': int(row.get('plan_option_id')) if pd.notna(row.get('plan_option_id')) else None,
                    'min_stock_level': int(row.get('min_stock_level', 0)),
                    'quantity': int(row.get('quantity', 0))
                }
                
                # Insert product
                cursor.execute("""
                    INSERT INTO takeoff.products (
                        item_description, brand, model, item_type, style, color,
                        finish, material, size, unit_of_measure, image_url,
                        is_active, plan_option_id, min_stock_level, quantity
                    ) VALUES (
                        %(item_description)s, %(brand)s, %(model)s, %(item_type)s,
                        %(style)s, %(color)s, %(finish)s, %(material)s, %(size)s,
                        %(unit_of_measure)s, %(image_url)s, %(is_active)s,
                        %(plan_option_id)s, %(min_stock_level)s, %(quantity)s
                    )
                """, product_data)
                
                imported_count += 1
                
            except Exception as e:
                errors.append(f"Row {index + 2}: {str(e)}")
                continue
        
        conn.commit()
        
        result = {
            'success': True,
            'imported': imported_count,
            'total': len(df),
            'message': f'Successfully imported {imported_count} out of {len(df)} products'
        }
        
        if errors:
            result['errors'] = errors[:10]  # Limit to first 10 errors
            if len(errors) > 10:
                result['errors'].append(f'... and {len(errors) - 10} more errors')
        
        return jsonify(result), 200
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error importing products: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/api/products/<int:product_id>', methods=['DELETE'])
def api_delete_product(product_id):
    """API endpoint to delete a product"""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Delete related takeoffs first
        cursor.execute("DELETE FROM takeoff.takeoffs WHERE product_id = %s", (product_id,))
        takeoffs_deleted = cursor.rowcount

        # Delete product
        cursor.execute("DELETE FROM takeoff.products WHERE product_id = %s", (product_id,))
        product_deleted = cursor.rowcount

        conn.commit()
        
        return jsonify({'success': True, 'takeoffs_deleted': takeoffs_deleted, 'product_deleted': product_deleted}), 200
        
    except Exception as e:
        import traceback
        if conn:
            conn.rollback()
        logger.error(f"Error deleting product: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f"{type(e).__name__}: {e}", 'traceback': traceback.format_exc()}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# --- NEW: Products Export Endpoint ---
@app.route('/api/products/export/<format>')
def api_export_products(format):
    """API endpoint to export products data in CSV or Excel format"""
    import pandas as pd
    import io
    from flask import make_response

    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("""
            SELECT
                p.product_id,
                COALESCE(i.item_name, p.item_description) as item_name,
                COALESCE(cc.cost_code, 'N/A') as cost_code,
                p.item_description as product_description,
                p.model,
                p.brand,
                p.style,
                p.color,
                p.finish,
                p.size,
                p.material,
                p.item_type,
                p.image_url,
                p.is_active,
                p.min_stock_level,
                COALESCE(p.quantity, 0) as quantity,
                p.unit_of_measure,
                p.plan_option_id
            FROM takeoff.products p
            LEFT JOIN takeoff.items i ON p.item_id = i.item_id
            LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
            ORDER BY COALESCE(i.item_name, p.item_description)
        """)
        records = cursor.fetchall()
        df = pd.DataFrame([dict(record) for record in records])

        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=products.csv'
            return response
        elif format.lower() == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Products', index=False)
            output.seek(0)
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=products.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error exporting products: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# --- NEW: Products Import Template Endpoint ---
@app.route('/api/products/template/<format>')
def api_products_template(format):
    """API endpoint to download import template for products"""
    import pandas as pd
    import io
    from flask import make_response
    try:
        # Template with headers and sample data
        template_data = {
            'item_description': ['Sample Product'],
            'brand': ['BrandX'],
            'model': ['ModelY'],
            'item_type': ['Product'],
            'style': ['Style1'],
            'color': ['Red'],
            'finish': ['Matte'],
            'material': ['Steel'],
            'size': ['M'],
            'unit_of_measure': ['EA'],
            'image_url': ['/static/images/default-product.png'],
            'is_active': [True],
            'plan_option_id': [''],
            'min_stock_level': [0],
            'quantity': [0]
        }
        df = pd.DataFrame(template_data)
        if format.lower() == 'csv':
            output = io.StringIO()
            df.to_csv(output, index=False)
            response = make_response(output.getvalue())
            response.headers['Content-Type'] = 'text/csv'
            response.headers['Content-Disposition'] = 'attachment; filename=products_import_template.csv'
            return response
        elif format.lower() == 'excel':
            output = io.BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Products Template', index=False)
                instructions = pd.DataFrame({
                    'Instructions': [
                        'Fill out the Products Template sheet with your data',
                        'item_description: Product name/description',
                        'brand, model, style, color, finish, material, size: Optional fields',
                        'unit_of_measure: EA, SF, LF, LB, GAL, etc.',
                        'image_url: Optional, defaults to /static/images/default-product.png',
                        'is_active: TRUE for active, FALSE for inactive',
                        'plan_option_id: Optional, link to plan option if needed',
                        'min_stock_level, quantity: Numeric fields',
                        'Save the file and upload it using the Import button',
                        'Empty rows will be skipped during import'
                    ]
                })
                instructions.to_excel(writer, sheet_name='Instructions', index=False)
            output.seek(0)
            response = make_response(output.read())
            response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            response.headers['Content-Disposition'] = 'attachment; filename=products_import_template.xlsx'
            return response
        else:
            return jsonify({'error': 'Invalid format. Use csv or excel'}), 400
    except Exception as e:
        logger.error(f"Error creating products template: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/products-by-cost-code')
def api_products_by_cost_code():
    """
    API endpoint to get products grouped by cost code.
    Returns: {cost_code: [{product_id, product_description}], ...}
    """
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        db.cursor.execute("""
            SELECT cc.cost_code, p.product_id, p.item_description AS product_description
            FROM takeoff.products p
            LEFT JOIN takeoff.items i ON p.item_id = i.item_id
            LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
            WHERE p.item_description IS NOT NULL AND cc.cost_code IS NOT NULL
            ORDER BY cc.cost_code, p.item_description
        """)
        records = db.cursor.fetchall()
        mapping = {}
        for row in records:
            code = row['cost_code']
            prod = {'product_id': row['product_id'], 'product_description': row['product_description']}
            if code not in mapping:
                mapping[code] = []
            if prod not in mapping[code]:
                mapping[code].append(prod)
        return jsonify(mapping)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/products-by-item-name')
def api_products_by_item_name():
    """
    API endpoint to get products grouped by item name.
    Returns: {item_name: [{product_id, product_description}], ...}
    """
    db = DatabaseManager()
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    try:
        db.cursor.execute("""
            SELECT i.item_name, p.product_id, p.item_description AS product_description
            FROM takeoff.products p
            LEFT JOIN takeoff.items i ON p.item_id = i.item_id
            WHERE p.item_description IS NOT NULL AND i.item_name IS NOT NULL
            ORDER BY i.item_name, p.item_description
        """)
        records = db.cursor.fetchall()
        mapping = {}
        for row in records:
            item_name = row['item_name']
            prod = {'product_id': row['product_id'], 'product_description': row['product_description']}
            if item_name not in mapping:
                mapping[item_name] = []
            if prod not in mapping[item_name]:
                mapping[item_name].append(prod)
        return jsonify(mapping)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/products-test')
def api_products_test():
    """Test endpoint that returns a static sample product"""
    sample_product = {
        "product_id": 1,
        "item_id": 100,
        "item_name": "Sample Item",
        "product_description": "Sample Product Description",
        "cost_code_id": 200,
        "cost_code": "01-100",
        "cost_code_name": "Sample Cost Code"
    }
    return jsonify([sample_product])

def api_products_for_lookup():
    """
    Helper function to get products for dropdown/lookup selection.
    Returns a JSON array with product_id, item_id, item_name, product_description, cost_code_id, cost_code, cost_code_description

    Query parameters:
    - cost_code_id: Optional filter by cost_code_id
    - item_id: Optional filter by item_id

    Returns sorted by item_name, product_description
    """
    conn = None
    cursor = None
    try:
        # Get query parameters
        cost_code_id = request.args.get('cost_code_id')
        item_id = request.args.get('item_id')

        # Build WHERE clause based on parameters
        where_clauses = []
        params = []

        if cost_code_id:
            where_clauses.append("i.cost_code_id = %s")
            params.append(cost_code_id)

        if item_id:
            where_clauses.append("p.item_id = %s")
            params.append(item_id)

        where_clause = ""
        if where_clauses:
            where_clause = "WHERE " + " AND ".join(where_clauses)

        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        query = f"""
            SELECT
                p.product_id,
                p.item_id,
                i.item_name,
                p.item_description AS product_description,
                i.cost_code_id,
                cc.cost_code,
                cc.cost_code_description
            FROM takeoff.products p
            LEFT JOIN takeoff.items i ON p.item_id = i.item_id
            LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
            {where_clause}
            ORDER BY i.item_name, p.item_description
        """

        cursor.execute(query, params)
        records = cursor.fetchall()

        return jsonify([dict(record) for record in records])
    except Exception as e:
        logger.error(f"Error getting products for lookup: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Legacy endpoint - keeping for backward compatibility
@app.route('/api/products-for-dropdown')
def api_products_for_dropdown():
    """Legacy endpoint that redirects to /api/products?for_dropdown=true"""
    return api_products_for_lookup()

# ============================================================================
# == 5. MAIN APP RUN BLOCK =================================================
# ============================================================================

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
