#!/usr/bin/env python3
"""
Simple Web UI for PostgreSQL Takeoff Database Management
Provides dashboard view of all tables with CRUD operations
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'takeoff_pricing_db',
    'user': 'Jon',
    'password': 'Transplant4real'
}

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'  # Change this in production

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
        if not self.connect():
            return []
        
        try:
            self.cursor.execute("""
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
            return self.cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting table structure: {e}")
            return []
        finally:
            self.disconnect()
    
    def get_table_data(self, table_name, page=1, per_page=50, search=None):
        """Get paginated data from a table"""
        if not self.connect():
            return [], 0
        
        try:
            offset = (page - 1) * per_page
            
            # Build search condition
            search_condition = ""
            search_params = []
            if search:
                # Get text columns for search
                self.cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'takeoff' AND table_name = %s 
                    AND data_type IN ('text', 'character varying', 'character')
                """, (table_name,))
                text_columns = [row['column_name'] for row in self.cursor.fetchall()]
                
                if text_columns:
                    search_conditions = [f"{col}::text ILIKE %s" for col in text_columns]
                    search_condition = "WHERE " + " OR ".join(search_conditions)
                    search_params = [f"%{search}%"] * len(text_columns)
            
            # Get total count
            count_query = f"SELECT COUNT(*) as total FROM takeoff.{table_name} {search_condition}"
            self.cursor.execute(count_query, search_params)
            total_records = self.cursor.fetchone()['total']
            
            # Get paginated data
            data_query = f"""
                SELECT * FROM takeoff.{table_name} 
                {search_condition}
                ORDER BY 1 
                LIMIT %s OFFSET %s
            """
            self.cursor.execute(data_query, search_params + [per_page, offset])
            records = self.cursor.fetchall()
            
            return records, total_records
        except Exception as e:
            logger.error(f"Error getting table data: {e}")
            return [], 0
        finally:
            self.disconnect()
    
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

# Initialize database manager
db = DatabaseManager()

@app.route('/')
def dashboard():
    """Main dashboard showing AG-Grid views"""
    return render_template('dashboard.html')

# Old table view routes removed - will be replaced with AG-Grid implementations

# API Endpoints
@app.route('/api/tables')
def api_tables():
    """API endpoint to get all tables"""
    tables = db.get_all_tables()
    return jsonify(tables)

@app.route('/api/table/<table_name>/structure')
def api_table_structure(table_name):
    """API endpoint to get table structure"""
    columns = db.get_table_structure(table_name)
    return jsonify([dict(col) for col in columns])

# Cost Codes with Groups endpoints
@app.route('/cost-codes-grid')
def cost_codes_grid():
    """Cost codes with groups AG-Grid interface"""
    return render_template('cost_codes_grid.html')

# Vendor Pricing endpoints
@app.route('/vendor-pricing-grid')
def vendor_pricing_grid():
    """Vendor pricing AG-Grid interface"""
    return render_template('vendor_pricing_grid.html')

@app.route('/quotes-grid')
def quotes_grid():
    """Quotes management AG-Grid interface"""
    return render_template('quotes_grid.html')

@app.route('/comprehensive-takeoff-grid')
def comprehensive_takeoff_grid():
    """Comprehensive takeoff analysis AG-Grid interface"""
    return render_template('comprehensive_takeoff_grid.html')

@app.route('/api/cost-codes-with-groups')
def api_cost_codes_with_groups():
    """API endpoint to get cost codes with groups data"""
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT * FROM takeoff.v_cost_codes_with_groups ORDER BY cost_code")
        records = db.cursor.fetchall()
        
        # Convert to list of dictionaries for JSON serialization
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting cost codes with groups: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/vendor-pricing')
def api_vendor_pricing():
    """API endpoint to get vendor pricing data"""
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
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

@app.route('/api/cost-codes-with-groups/bulk-update', methods=['POST'])
def api_bulk_update_cost_codes():
    """API endpoint to bulk update cost codes and groups"""
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

# Quotes API endpoints
@app.route('/api/quotes')
def api_quotes():
    """API endpoint to get quotes data"""
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

# Dropdown data endpoints
@app.route('/api/cost-codes')
def api_cost_codes():
    """API endpoint to get cost codes for dropdowns"""
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

@app.route('/api/items')
def api_items():
    """API endpoint to get items for dropdowns"""
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT item_id, item_name, cost_code_id FROM takeoff.items ORDER BY item_name")
        records = db.cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting items: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/plan-options')
def api_plan_options():
    """API endpoint to get plan options for dropdowns"""
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("""
            SELECT po.plan_option_id, pe.plan_full_name, po.option_name
            FROM takeoff.plan_options po
            JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            ORDER BY pe.plan_full_name, po.option_name
        """)
        records = db.cursor.fetchall()
        
        data = [dict(record) for record in records]
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting plan options: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/vendors')
def api_vendors():
    """API endpoint to get vendors for dropdowns"""
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

@app.route('/api/items/<int:item_id>/description')
def api_item_description(item_id):
    """API endpoint to get item description by item_id"""
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("""
            SELECT 
                i.item_name,
                CASE 
                    WHEN p.item_type = 'Product' THEN i.item_name
                    WHEN p.item_type = 'Quote' THEN 'Quote for ' || i.item_name
                    ELSE i.item_name
                END as description
            FROM takeoff.items i
            LEFT JOIN takeoff.products p ON i.item_id = p.item_id
            WHERE i.item_id = %s
        """, (item_id,))
        
        record = db.cursor.fetchone()
        if record:
            return jsonify({'description': record['description']})
        else:
            return jsonify({'description': 'Item not found'}), 404
    except Exception as e:
        logger.error(f"Error getting item description: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/comprehensive-takeoff-analysis/duplicate', methods=['POST'])
def api_comprehensive_takeoff_analysis_duplicate():
    """
    API endpoint to duplicate (insert) a row into the comprehensive takeoff analysis.
    Expects JSON with all required fields for a new row.
    Inserts into takeoff.takeoffs, creating or finding referenced products, jobs, and vendors as needed.
    """
    data = request.get_json()
    required_fields = [
        'plan_full_name', 'option_name', 'cost_code', 'item_name', 'item_description',
        'quantity_source', 'quantity', 'unit_price', 'price_factor', 'unit_of_measure',
        'vendor_name', 'notes', 'job_name', 'job_number', 'customer_name', 'room', 'spec_name'
    ]
    if not all(field in data for field in required_fields):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        # 1. Find or create cost_code
        db.cursor.execute("SELECT cost_code_id FROM takeoff.cost_codes WHERE cost_code = %s", (data['cost_code'],))
        cost_code_row = db.cursor.fetchone()
        if not cost_code_row:
            return jsonify({'success': False, 'message': 'Cost code not found'}), 400
        cost_code_id = cost_code_row['cost_code_id']

        # 2. Find or create item
        db.cursor.execute("SELECT item_id FROM takeoff.items WHERE item_name = %s", (data['item_name'],))
        item_row = db.cursor.fetchone()
        if not item_row:
            db.cursor.execute(
                "INSERT INTO takeoff.items (item_name, cost_code_id) VALUES (%s, %s) RETURNING item_id",
                (data['item_name'], cost_code_id)
            )
            item_id = db.cursor.fetchone()['item_id']
        else:
            item_id = item_row['item_id']

        # 3. Find or create product
        db.cursor.execute("SELECT product_id FROM takeoff.products WHERE item_id = %s", (item_id,))
        product_row = db.cursor.fetchone()
        if not product_row:
            db.cursor.execute(
                "INSERT INTO takeoff.products (item_id, product_description) VALUES (%s, %s) RETURNING product_id",
                (item_id, data['item_description'])
            )
            product_id = db.cursor.fetchone()['product_id']
        else:
            product_id = product_row['product_id']

        # 4. Find or create vendor
        db.cursor.execute("SELECT vendor_id FROM takeoff.vendors WHERE vendor_name = %s", (data['vendor_name'],))
        vendor_row = db.cursor.fetchone()
        if not vendor_row:
            db.cursor.execute(
                "INSERT INTO takeoff.vendors (vendor_name) VALUES (%s) RETURNING vendor_id",
                (data['vendor_name'],)
            )
            vendor_id = db.cursor.fetchone()['vendor_id']
        else:
            vendor_id = vendor_row['vendor_id']

        # 5. Find or create plan_option (and plan_elevation, plan)
        db.cursor.execute("SELECT plan_id FROM takeoff.plans WHERE plan_name = %s", (data['plan_full_name'],))
        plan_row = db.cursor.fetchone()
        if not plan_row:
            db.cursor.execute(
                "INSERT INTO takeoff.plans (plan_name) VALUES (%s) RETURNING plan_id",
                (data['plan_full_name'],)
            )
            plan_id = db.cursor.fetchone()['plan_id']
        else:
            plan_id = plan_row['plan_id']

        db.cursor.execute("SELECT plan_elevation_id FROM takeoff.plan_elevations WHERE plan_id = %s LIMIT 1", (plan_id,))
        plan_elevation_row = db.cursor.fetchone()
        if not plan_elevation_row:
            db.cursor.execute(
                "INSERT INTO takeoff.plan_elevations (plan_id, elevation_name, foundation) VALUES (%s, %s, %s) RETURNING plan_elevation_id",
                (plan_id, 'Default', 'Default')
            )
            plan_elevation_id = db.cursor.fetchone()['plan_elevation_id']
        else:
            plan_elevation_id = plan_elevation_row['plan_elevation_id']

        db.cursor.execute("SELECT plan_option_id FROM takeoff.plan_options WHERE plan_elevation_id = %s AND option_name = %s", (plan_elevation_id, data['option_name']))
        plan_option_row = db.cursor.fetchone()
        if not plan_option_row:
            db.cursor.execute(
                "INSERT INTO takeoff.plan_options (plan_elevation_id, option_name) VALUES (%s, %s) RETURNING plan_option_id",
                (plan_elevation_id, data['option_name'])
            )
            plan_option_id = db.cursor.fetchone()['plan_option_id']
        else:
            plan_option_id = plan_option_row['plan_option_id']

        # 6. Find or create job
        db.cursor.execute("SELECT job_id FROM takeoff.jobs WHERE job_name = %s AND plan_option_id = %s", (data['job_name'], plan_option_id))
        job_row = db.cursor.fetchone()
        if not job_row:
            db.cursor.execute(
                "INSERT INTO takeoff.jobs (job_name, plan_option_id, is_template) VALUES (%s, %s, TRUE) RETURNING job_id",
                (data['job_name'], plan_option_id)
            )
            job_id = db.cursor.fetchone()['job_id']
        else:
            job_id = job_row['job_id']

        # 7. Generate new takeoff_id (ensure uniqueness)
        db.cursor.execute("SELECT COALESCE(MAX(takeoff_id), 0) + 1 AS new_id FROM takeoff.takeoffs")
        takeoff_id = db.cursor.fetchone()['new_id']

        # 8. Insert into takeoffs, with error handling
        try:
            db.cursor.execute("""
                INSERT INTO takeoff.takeoffs
                (takeoff_id, job_id, product_id, vendor_id, quantity, unit_price, quantity_source, notes, room, spec_name)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                takeoff_id,
                job_id,
                product_id,
                vendor_id,
                data['quantity'],
                data['unit_price'],
                data['quantity_source'],
                data.get('notes', ''),
                data.get('room', ''),
                data.get('spec_name', '')
            ))
        except Exception as insert_err:
            logger.error(f"Error inserting into takeoffs: {insert_err}")
            db.conn.rollback()
            return jsonify({'success': False, 'message': f'Insert error: {insert_err}'}), 500

        db.conn.commit()
        return jsonify({'success': True, 'takeoff_id': takeoff_id})
    except Exception as e:
        logger.error(f"Error duplicating row: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/comprehensive-takeoff-analysis/delete', methods=['POST'])
def api_comprehensive_takeoff_analysis_delete():
    """
    API endpoint to delete a row from the comprehensive takeoff analysis.
    Expects JSON with: takeoff_id.
    """
    data = request.get_json()
    if 'takeoff_id' not in data:
        return jsonify({'success': False, 'message': 'Missing takeoff_id'}), 400

    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'}), 500

    try:
        db.cursor.execute("DELETE FROM takeoff.takeoffs WHERE takeoff_id = %s", (data['takeoff_id'],))
        db.conn.commit()
        if db.cursor.rowcount > 0:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'Row not found'}), 404
    except Exception as e:
        logger.error(f"Error deleting row: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': str(e)}), 500
    finally:
        db.disconnect()

@app.route('/api/comprehensive-takeoff-analysis')
def api_comprehensive_takeoff_analysis():
    """API endpoint to get comprehensive takeoff analysis data"""
    if not db.connect():
        return jsonify({'error': 'Database connection failed'}), 500
    
    try:
        db.cursor.execute("SELECT * FROM takeoff.v_comprehensive_takeoff_analysis ORDER BY plan_full_name, option_name, cost_code, item_name")
        records = db.cursor.fetchall()
        
        # Convert to list of dictionaries for JSON serialization and add a unique customRowId
        data = []
        for record in records:
            row = dict(record)
            # Build a unique, stable row ID from key fields
            row['customRowId'] = f"{row.get('plan_full_name','')}|{row.get('option_name','')}|{row.get('cost_code','')}|{row.get('item_name','')}"
            data.append(row)
        return jsonify(data)
    except Exception as e:
        logger.error(f"Error getting comprehensive takeoff analysis data: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        db.disconnect()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
