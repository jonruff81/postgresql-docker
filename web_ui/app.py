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
    
    def update_record(self, table_name, record_id, update_data, id_column=None):
        finally:
            self.disconnect()
    
    def update_record(self, table_name, record_id, update_data, id_column=None):
=======
    
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
    
    def bulk_import_csv(self, table_name, csv_data):
        """Import records from CSV data"""
        if not self.connect():
            return False, "Database connection failed"
        
        try:
            import csv
            import io
            
            # Parse CSV
            csv_file = io.StringIO(csv_data)
            reader = csv.DictReader(csv_file)
            
            # Get table columns
            self.cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'takeoff' AND table_name = %s
                ORDER BY ordinal_position
            """, (table_name,))
            valid_columns = [row['column_name'] for row in self.cursor.fetchall()]
            
            # Import records
            imported_count = 0
            errors = []
            
            for row_num, row in enumerate(reader, start=1):
                try:
                    # Filter to valid columns only
                    filtered_row = {col: value for col, value in row.items() if col in valid_columns}
                    
                    if not filtered_row:
                        continue
                    
                    # Create record
                    column_names = list(filtered_row.keys())
                    placeholders = ['%s'] * len(column_names)
                    values = [filtered_row[col] if filtered_row[col] != '' else None for col in column_names]
                    
                    query = f"INSERT INTO takeoff.{table_name} ({', '.join(column_names)}) VALUES ({', '.join(placeholders)})"
                    self.cursor.execute(query, values)
                    imported_count += 1
                    
                except Exception as e:
                    errors.append(f"Row {row_num}: {str(e)}")
                    continue
            
            self.conn.commit()
            
            if errors:
                return True, f"Imported {imported_count} records with {len(errors)} errors: {'; '.join(errors[:5])}"
            else:
                return True, f"Successfully imported {imported_count} records"
                
        except Exception as e:
            logger.error(f"Error in bulk import: {e}")
            self.conn.rollback()
            return False, f"Import failed: {str(e)}"
        finally:
            self.disconnect()
    
    def get_enhanced_takeoffs_data(self, page=1, per_page=50, cost_code_filter=None, vendor_filter=None, plan_filter=None, option_filter=None, search=None):
        """Get enhanced takeoffs data with filtering and summary"""
        if not self.connect():
            return [], 0, 0
        
        try:
            offset = (page - 1) * per_page
            
            # Build the main query with all joins
            base_query = """
                FROM takeoff.takeoffs t
                LEFT JOIN takeoff.products p ON t.product_id = p.product_id
                LEFT JOIN takeoff.items i ON p.item_id = i.item_id
                LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
                LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
                LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
                LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
                LEFT JOIN takeoff.plans pl ON pe.plan_id = pl.plan_id
            """
            
            # Build WHERE conditions
            where_conditions = []
            params = []
            
            if cost_code_filter:
                where_conditions.append("cc.cost_code = %s")
                params.append(cost_code_filter)
            
            if vendor_filter:
                where_conditions.append("v.vendor_name = %s")
                params.append(vendor_filter)
            
            if plan_filter:
                where_conditions.append("pe.plan_full_name = %s")
                params.append(plan_filter)
            
            if option_filter:
                where_conditions.append("po.option_name = %s")
                params.append(option_filter)
            
            if search:
                search_conditions = [
                    "cc.cost_code ILIKE %s",
                    "cc.cost_code_description ILIKE %s",
                    "v.vendor_name ILIKE %s",
                    "pe.plan_full_name ILIKE %s",
                    "po.option_name ILIKE %s",
                    "p.product_description ILIKE %s"
                ]
                where_conditions.append("(" + " OR ".join(search_conditions) + ")")
                search_param = f"%{search}%"
                params.extend([search_param] * 6)
            
            where_clause = ""
            if where_conditions:
                where_clause = "WHERE " + " AND ".join(where_conditions)
            
            # Get total count and sum of extended prices
            count_query = f"""
                SELECT 
                    COUNT(*) as total_count,
                    COALESCE(SUM(t.extended_price), 0) as total_extended_price
                {base_query}
                {where_clause}
            """
            self.cursor.execute(count_query, params)
            count_result = self.cursor.fetchone()
            total_records = count_result['total_count']
            total_extended_price = float(count_result['total_extended_price'])
            
            # Get paginated data
            data_query = f"""
                SELECT 
                    t.takeoff_id,
                    cc.cost_code,
                    v.vendor_name as vendor,
                    pe.plan_full_name as planfullname,
                    po.option_name as optionname,
                    t.quantity as qty,
                    p.product_description as product,
                    t.unit_price as price,
                    t.extended_price
                {base_query}
                {where_clause}
                ORDER BY t.takeoff_id
                LIMIT %s OFFSET %s
            """
            self.cursor.execute(data_query, params + [per_page, offset])
            records = self.cursor.fetchall()
            
            return records, total_records, total_extended_price
        except Exception as e:
            logger.error(f"Error getting enhanced takeoffs data: {e}")
            return [], 0, 0
        finally:
            self.disconnect()
    
    def get_takeoffs_filter_options(self):
        """Get unique values for filter dropdowns"""
        if not self.connect():
            return {}
        
        try:
            filter_options = {}
            
            # Get unique cost codes
            self.cursor.execute("""
                SELECT DISTINCT cc.cost_code
                FROM takeoff.takeoffs t
                LEFT JOIN takeoff.products p ON t.product_id = p.product_id
                LEFT JOIN takeoff.items i ON p.item_id = i.item_id
                LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
                WHERE cc.cost_code IS NOT NULL
                ORDER BY cc.cost_code
            """)
            filter_options['cost_codes'] = [row['cost_code'] for row in self.cursor.fetchall()]
            
            # Get unique vendors
            self.cursor.execute("""
                SELECT DISTINCT v.vendor_name
                FROM takeoff.takeoffs t
                LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
                WHERE v.vendor_name IS NOT NULL
                ORDER BY v.vendor_name
            """)
            filter_options['vendors'] = [row['vendor_name'] for row in self.cursor.fetchall()]
            
            # Get unique plan full names
            self.cursor.execute("""
                SELECT DISTINCT pe.plan_full_name
                FROM takeoff.takeoffs t
                LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
                LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
                WHERE pe.plan_full_name IS NOT NULL
                ORDER BY pe.plan_full_name
            """)
            filter_options['plans'] = [row['plan_full_name'] for row in self.cursor.fetchall()]
            
            # Get unique option names
            self.cursor.execute("""
                SELECT DISTINCT po.option_name
                FROM takeoff.takeoffs t
                LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
                LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                WHERE po.option_name IS NOT NULL
                ORDER BY po.option_name
            """)
            filter_options['options'] = [row['option_name'] for row in self.cursor.fetchall()]
            
            return filter_options
        except Exception as e:
            logger.error(f"Error getting filter options: {e}")
            return {}
        finally:
            self.disconnect()
    
    def get_smart_takeoffs_data(self, page=1, per_page=50, search=None):
        """Get takeoffs data with all meaningful names for smart editing"""
        if not self.connect():
            return [], 0, 0
        
        try:
            offset = (page - 1) * per_page
            
            # Build search condition
            search_condition = ""
            search_params = []
            if search:
                search_conditions = [
                    "cc.cost_code ILIKE %s",
                    "cc.cost_code_description ILIKE %s", 
                    "v.vendor_name ILIKE %s",
                    "CONCAT(pl.plan_name, '_', pe.elevation_name, '_', pe.foundation) ILIKE %s",
                    "po.option_name ILIKE %s",
                    "p.product_description ILIKE %s"
                ]
                search_condition = "WHERE " + " OR ".join(search_conditions)
                search_param = f"%{search}%"
                search_params = [search_param] * 6
            
            # Get total count and sum
            count_query = f"""
                SELECT 
                    COUNT(*) as total_count,
                    COALESCE(SUM(t.extended_price), 0) as total_extended_price
                FROM takeoff.takeoffs t
                LEFT JOIN takeoff.products p ON t.product_id = p.product_id
                LEFT JOIN takeoff.items i ON p.item_id = i.item_id
                LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
                LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
                LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
                LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
                LEFT JOIN takeoff.plans pl ON pe.plan_id = pl.plan_id
                {search_condition}
            """
            self.cursor.execute(count_query, search_params)
            count_result = self.cursor.fetchone()
            total_records = count_result['total_count']
            total_extended_price = float(count_result['total_extended_price'])
            
            # Get paginated data with all the info we need for smart editing
            data_query = f"""
                SELECT 
                    t.takeoff_id,
                    t.job_id,
                    t.product_id,
                    t.vendor_id,
                    t.quantity,
                    t.unit_price,
                    t.extended_price,
                    t.quantity_source,
                    -- Display names
                    cc.cost_code,
                    cc.cost_code_description,
                    v.vendor_name,
                    CONCAT(pl.plan_name, '_', pe.elevation_name, '_', pe.foundation) as plan_full_name,
                    po.option_name,
                    p.product_description,
                    i.item_name,
                    -- Additional context
                    j.job_name,
                    pl.plan_name,
                    pe.elevation_name,
                    pe.foundation
                FROM takeoff.takeoffs t
                LEFT JOIN takeoff.products p ON t.product_id = p.product_id
                LEFT JOIN takeoff.items i ON p.item_id = i.item_id
                LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
                LEFT JOIN takeoff.vendors v ON t.vendor_id = v.vendor_id
                LEFT JOIN takeoff.jobs j ON t.job_id = j.job_id
                LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
                LEFT JOIN takeoff.plans pl ON pe.plan_id = pl.plan_id
                {search_condition}
                ORDER BY t.takeoff_id
                LIMIT %s OFFSET %s
            """
            self.cursor.execute(data_query, search_params + [per_page, offset])
            records = self.cursor.fetchall()
            
            return records, total_records, total_extended_price
        except Exception as e:
            logger.error(f"Error getting smart takeoffs data: {e}")
            return [], 0, 0
        finally:
            self.disconnect()
    
    def get_lookup_data(self):
        """Get all lookup data for smart dropdowns"""
        if not self.connect():
            return {}
        
        try:
            lookup_data = {}
            
            # Get vendors
            self.cursor.execute("SELECT vendor_id, vendor_name FROM takeoff.vendors ORDER BY vendor_name")
            lookup_data['vendors'] = [{'id': row['vendor_id'], 'name': row['vendor_name']} for row in self.cursor.fetchall()]
            
            # Get products with item info
            self.cursor.execute("""
                SELECT p.product_id, p.product_description, i.item_name, cc.cost_code
                FROM takeoff.products p
                LEFT JOIN takeoff.items i ON p.item_id = i.item_id
                LEFT JOIN takeoff.cost_codes cc ON i.cost_code_id = cc.cost_code_id
                ORDER BY p.product_description
            """)
            lookup_data['products'] = [
                {
                    'id': row['product_id'], 
                    'description': row['product_description'],
                    'item_name': row['item_name'],
                    'cost_code': row['cost_code'],
                    'display_name': f"{row['cost_code']} - {row['item_name']} - {row['product_description']}" if row['cost_code'] else f"{row['item_name']} - {row['product_description']}"
                } 
                for row in self.cursor.fetchall()
            ]
            
            # Get jobs with plan info
            self.cursor.execute("""
                SELECT j.job_id, j.job_name, 
                       CONCAT(pl.plan_name, '_', pe.elevation_name, '_', pe.foundation) as plan_full_name,
                       po.option_name
                FROM takeoff.jobs j
                LEFT JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
                LEFT JOIN takeoff.plans pl ON pe.plan_id = pl.plan_id
                ORDER BY plan_full_name, po.option_name
            """)
            lookup_data['jobs'] = [
                {
                    'id': row['job_id'],
                    'name': row['job_name'],
                    'plan_full_name': row['plan_full_name'],
                    'option_name': row['option_name'],
                    'display_name': f"{row['plan_full_name']} - {row['option_name']}"
                }
                for row in self.cursor.fetchall()
            ]
            
            return lookup_data
        except Exception as e:
            logger.error(f"Error getting lookup data: {e}")
            return {}
        finally:
            self.disconnect()
    
    def update_takeoff_field(self, takeoff_id, field_name, field_value):
        """Update a single field in a takeoff record"""
        if not self.connect():
            return False, "Database connection failed"
        
        try:
            # Validate field name to prevent SQL injection
            valid_fields = ['quantity', 'unit_price', 'vendor_id', 'product_id', 'job_id', 'quantity_source']
            if field_name not in valid_fields:
                return False, f"Invalid field name: {field_name}"
            
            # Convert empty strings to None for numeric fields
            if field_name in ['quantity', 'unit_price'] and field_value == '':
                field_value = None
            
            # Update the field
            query = f"UPDATE takeoff.takeoffs SET {field_name} = %s WHERE takeoff_id = %s"
            self.cursor.execute(query, (field_value, takeoff_id))
            
            # If we updated quantity or unit_price, recalculate extended_price
            if field_name in ['quantity', 'unit_price']:
                self.cursor.execute("""
                    UPDATE takeoff.takeoffs 
                    SET extended_price = COALESCE(quantity, 0) * COALESCE(unit_price, 0)
                    WHERE takeoff_id = %s
                """, (takeoff_id,))
            
            self.conn.commit()
            return True, "Updated successfully"
        except Exception as e:
            logger.error(f"Error updating takeoff field: {e}")
            self.conn.rollback()
            return False, str(e)
        finally:
            self.disconnect()
>>>>>>> 83fd5a998064fe02eb59cf1916948d74f7a65a81

# Initialize database manager
db = DatabaseManager()

@app.route('/')
def dashboard():
    """Main dashboard showing all tables"""
    tables = db.get_all_tables()
    return render_template('dashboard.html', tables=tables)

@app.route('/table/<table_name>')
def view_table(table_name):
    """View table data with pagination"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    per_page = 50
    
    # Get table structure
    columns = db.get_table_structure(table_name)
    
    # Get table data
    records, total_records = db.get_table_data(table_name, page, per_page, search if search else None)
    
    # Calculate pagination
    total_pages = (total_records + per_page - 1) // per_page
    
    return render_template('table_view.html', 
                         table_name=table_name,
                         columns=columns,
                         records=records,
                         current_page=page,
                         total_pages=total_pages,
                         total_records=total_records,
                         search=search)

@app.route('/table/<table_name>/record/<record_id>')
def view_record(table_name, record_id):
    """View single record details"""
    columns = db.get_table_structure(table_name)
    record = db.get_record(table_name, record_id)
    
    if not record:
        flash('Record not found', 'error')
        return redirect(url_for('view_table', table_name=table_name))
    
    return render_template('record_view.html',
                         table_name=table_name,
                         columns=columns,
                         record=record)

@app.route('/table/<table_name>/delete/<record_id>', methods=['POST'])
def delete_record(table_name, record_id):
    """Delete a record"""
    if db.delete_record(table_name, record_id):
        flash('Record deleted successfully', 'success')
    else:
        flash('Error deleting record', 'error')
    
    return redirect(url_for('view_table', table_name=table_name))

<<<<<<< HEAD
=======
@app.route('/table/<table_name>/edit/<record_id>', methods=['GET', 'POST'])
def edit_record(table_name, record_id):
    """Edit a record"""
    columns = db.get_table_structure(table_name)
    
    if request.method == 'POST':
        # Handle form submission
        update_data = {}
        for column in columns:
            col_name = column['column_name']
            if col_name in request.form:
                update_data[col_name] = request.form[col_name]
        
        if db.update_record(table_name, record_id, update_data):
            flash('Record updated successfully', 'success')
            return redirect(url_for('view_table', table_name=table_name))
        else:
            flash('Error updating record', 'error')
    
    # GET request - show edit form
    record = db.get_record(table_name, record_id)
    if not record:
        flash('Record not found', 'error')
        return redirect(url_for('view_table', table_name=table_name))
    
    return render_template('edit_record.html',
                         table_name=table_name,
                         columns=columns,
                         record=record)

@app.route('/table/<table_name>/create', methods=['GET', 'POST'])
def create_record(table_name):
    """Create a new record"""
    columns = db.get_table_structure(table_name)
    
    if request.method == 'POST':
        # Handle form submission
        record_data = {}
        for column in columns:
            col_name = column['column_name']
            if col_name in request.form:
                record_data[col_name] = request.form[col_name]
        
        if db.create_record(table_name, record_data):
            flash('Record created successfully', 'success')
            return redirect(url_for('view_table', table_name=table_name))
        else:
            flash('Error creating record', 'error')
    
    # GET request - show create form
    return render_template('create_record.html',
                         table_name=table_name,
                         columns=columns)

@app.route('/table/<table_name>/import', methods=['GET', 'POST'])
def bulk_import(table_name):
    """Bulk import records from CSV"""
    columns = db.get_table_structure(table_name)
    
    if request.method == 'POST':
        # Handle CSV upload
        if 'csv_file' not in request.files:
            flash('No file selected', 'error')
            return redirect(request.url)
        
        file = request.files['csv_file']
        if file.filename == '':
            flash('No file selected', 'error')
            return redirect(request.url)
        
        if file and file.filename.lower().endswith('.csv'):
            csv_data = file.read().decode('utf-8')
            success, message = db.bulk_import_csv(table_name, csv_data)
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
            
            return redirect(url_for('view_table', table_name=table_name))
        else:
            flash('Please upload a CSV file', 'error')
    
    # GET request - show import form
    return render_template('bulk_import.html',
                         table_name=table_name,
                         columns=columns)

>>>>>>> 83fd5a998064fe02eb59cf1916948d74f7a65a81
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

<<<<<<< HEAD
=======
@app.route('/takeoffs/enhanced')
def enhanced_takeoffs():
    """Enhanced takeoffs view with filtering and summary"""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    # Get filter parameters
    cost_code_filter = request.args.get('cost_code', '', type=str)
    vendor_filter = request.args.get('vendor', '', type=str)
    plan_filter = request.args.get('plan', '', type=str)
    option_filter = request.args.get('option', '', type=str)
    search = request.args.get('search', '', type=str)
    
    # Get enhanced takeoffs data with filters
    records, total_records, total_extended_price = db.get_enhanced_takeoffs_data(
        page, per_page, cost_code_filter, vendor_filter, plan_filter, option_filter, search
    )
    
    # Get unique values for filter dropdowns
    filter_options = db.get_takeoffs_filter_options()
    
    # Calculate pagination
    total_pages = (total_records + per_page - 1) // per_page
    
    return render_template('takeoffs_enhanced.html',
                         records=records,
                         current_page=page,
                         total_pages=total_pages,
                         total_records=total_records,
                         total_extended_price=total_extended_price,
                         filter_options=filter_options,
                         cost_code_filter=cost_code_filter,
                         vendor_filter=vendor_filter,
                         plan_filter=plan_filter,
                         option_filter=option_filter,
                         search=search)

@app.route('/takeoffs/smart')
def smart_takeoffs():
    """Smart takeoffs view with inline editing and meaningful names"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    per_page = 50
    
    # Get smart takeoffs data
    records, total_records, total_extended_price = db.get_smart_takeoffs_data(
        page, per_page, search if search else None
    )
    
    # Get lookup data for dropdowns
    lookup_data = db.get_lookup_data()
    
    # Calculate pagination
    total_pages = (total_records + per_page - 1) // per_page
    
    return render_template('smart_takeoffs.html',
                         records=records,
                         current_page=page,
                         total_pages=total_pages,
                         total_records=total_records,
                         total_extended_price=total_extended_price,
                         lookup_data=lookup_data,
                         search=search)

# API Endpoints for Smart Editing
@app.route('/api/takeoffs/<int:takeoff_id>/update', methods=['POST'])
def api_update_takeoff_field(takeoff_id):
    """API endpoint to update a single takeoff field"""
    data = request.get_json()
    
    if not data or 'field_name' not in data or 'field_value' not in data:
        return jsonify({'success': False, 'message': 'Missing field_name or field_value'}), 400
    
    field_name = data['field_name']
    field_value = data['field_value']
    
    success, message = db.update_takeoff_field(takeoff_id, field_name, field_value)
    
    if success:
        # Get the updated record to return current values
        updated_record = db.get_record('takeoffs', takeoff_id)
        return jsonify({
            'success': True,
            'message': message,
            'updated_record': dict(updated_record) if updated_record else None
        })
    else:
        return jsonify({'success': False, 'message': message}), 400

@app.route('/api/lookup-data')
def api_lookup_data():
    """API endpoint to get lookup data for dropdowns"""
    lookup_data = db.get_lookup_data()
    return jsonify(lookup_data)

@app.route('/api/takeoffs/create', methods=['POST'])
def api_create_takeoff():
    """API endpoint to create a new takeoff record"""
    data = request.get_json()
    
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Create the record
    success = db.create_record('takeoffs', data)
    
    if success:
        return jsonify({'success': True, 'message': 'Takeoff created successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to create takeoff'}), 400

@app.route('/api/takeoffs/<int:takeoff_id>/delete', methods=['DELETE'])
def api_delete_takeoff():
    """API endpoint to delete a takeoff record"""
    takeoff_id = request.view_args['takeoff_id']
    
    success = db.delete_record('takeoffs', takeoff_id)
    
    if success:
        return jsonify({'success': True, 'message': 'Takeoff deleted successfully'})
    else:
        return jsonify({'success': False, 'message': 'Failed to delete takeoff'}), 400

# Cost Codes with Groups endpoints
@app.route('/cost-codes-grid')
def cost_codes_grid():
    """Cost codes with groups AG-Grid interface"""
    return render_template('cost_codes_grid.html')

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

>>>>>>> 83fd5a998064fe02eb59cf1916948d74f7a65a81
if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
