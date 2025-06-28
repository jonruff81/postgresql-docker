#!/usr/bin/env python3
"""
Simple Web UI for PostgreSQL Takeoff Database Management
Provides dashboard view of all tables with CRUD operations
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, make_response
import logging
from datetime import datetime
import random
import uuid
from werkzeug.utils import secure_filename
import re

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection settings
DB_CONFIG = {
    'host': 'localhost',
    'port': 5432,
    'database': 'takeoff_pricing_db',
    'user': 'Jon',
    'password': 'Transplant4real'
}

app = Flask(__name__, static_folder='static', static_url_path='/static')
app.secret_key = 'your-secret-key-change-this'  # Change this in production

# File upload configuration
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create upload directory if it doesn't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
            # Simplified query to get all tables in takeoff schema
            self.cursor.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'takeoff'
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = self.cursor.fetchall()
            
            # Get record counts and descriptions for each table
            table_info = []
            for table in tables:
                table_name = table['table_name']
                try:
                    # Get record count
                    self.cursor.execute(f"SELECT COUNT(*) as record_count FROM takeoff.{table_name}")
                    count_result = self.cursor.fetchone()
                    record_count = count_result['record_count'] if count_result else 0
                    
                    # Get column count
                    self.cursor.execute("""
                        SELECT COUNT(*) as column_count
                        FROM information_schema.columns
                        WHERE table_schema = 'takeoff' AND table_name = %s
                    """, (table_name,))
                    col_result = self.cursor.fetchone()
                    column_count = col_result['column_count'] if col_result else 0
                    
                    # Try to get table description
                    try:
                        self.cursor.execute("""
                            SELECT obj_description(pgc.oid) as table_comment
                            FROM pg_class pgc
                            WHERE pgc.relname = %s 
                            AND pgc.relnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'takeoff')
                        """, (table_name,))
                        desc_result = self.cursor.fetchone()
                        table_comment = desc_result['table_comment'] if desc_result and desc_result['table_comment'] else 'No description'
                    except:
                        table_comment = 'No description'
                    
                    table_info.append({
                        'name': table_name,
                        'comment': table_comment,
                        'column_count': column_count,
                        'record_count': record_count
                    })
                    
                except Exception as table_error:
                    logger.error(f"Error processing table {table_name}: {table_error}")
                    # Still add the table with basic info
                    table_info.append({
                        'name': table_name,
                        'comment': 'Error loading details',
                        'column_count': 0,
                        'record_count': 0
                    })
            
            logger.info(f"Successfully loaded {len(table_info)} tables")
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

    def get_foreign_keys(self, table_name):
        """Get foreign key relationships for a table in takeoff schema"""
        if not self.connect():
            return []
        try:
            return self._get_foreign_keys_internal(table_name)
        except Exception as e:
            logger.error(f"Error getting foreign keys for {table_name}: {e}")
            return []
        finally:
            self.disconnect()

    def _get_foreign_keys_internal(self, table_name):
        """Internal method to get foreign keys without managing connection"""
        self.cursor.execute("""
            SELECT
                kcu.column_name AS fk_column,
                ccu.table_name AS referenced_table,
                ccu.column_name AS referenced_column
            FROM information_schema.table_constraints tc
            JOIN information_schema.key_column_usage kcu
                ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage ccu
                ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_schema = 'takeoff'
                AND tc.table_name = %s
        """, (table_name,))
        return self.cursor.fetchall()

    def get_descriptive_columns(self, table_name):
        """Get candidate descriptive columns for a referenced table"""
        if not self.connect():
            return []
        try:
            return self._get_descriptive_columns_internal(table_name)
        except Exception as e:
            logger.error(f"Error getting descriptive columns for {table_name}: {e}")
            return []
        finally:
            self.disconnect()

    def _get_descriptive_columns_internal(self, table_name):
        """Internal method to get descriptive columns without managing connection"""
        try:
            logger.debug(f"Getting descriptive columns for table: {table_name}")
            
            # Hardcoded mappings for known tables to avoid database query issues
            column_mappings = {
                'divisions': ['division_name'],
                'communities': ['community_name'],
                'plans': ['plan_name'],
                'vendors': ['vendor_name'],
                'plan_options': ['option_name'],
                'plan_elevations': ['plan_full_name'],
                'items': ['item_name'],
                'jobs': ['job_name'],
                'cost_codes': ['cost_code_description'],
                'formulas': ['formula_name'],
                'cost_groups': ['cost_group_name'],
                'products': ['product_description'],
                'takeoffs': ['product_id'],
                'vendor_pricing': ['product_description'],
                'vendor_quotes': ['quote_number'],
                'vendor_quote_lines': ['product_description'],
                'file_attachments': ['file_name'],
                'files': ['file_name'],
                'file_links': ['file_id']
            }
            
            if table_name in column_mappings:
                return column_mappings[table_name]
            
            # Try the database query for other tables
            try:
                self.cursor.execute("""
                    SELECT column_name FROM information_schema.columns 
                    WHERE table_schema = 'takeoff' AND table_name = %s 
                    AND column_name LIKE '%%_name' 
                    ORDER BY ordinal_position LIMIT 3
                """, (table_name,))
                cols = self.cursor.fetchall()
                if cols:
                    result = [col['column_name'] for col in cols]
                    logger.debug(f"Found descriptive columns for {table_name}: {result}")
                    return result
            except Exception as simple_error:
                logger.error(f"Database query failed for {table_name}: {simple_error}")
                
            # Default fallback - return first column that might be descriptive
            return [f"{table_name[:-1]}_name"] if table_name.endswith('s') else [f"{table_name}_name"]
                    
        except Exception as e:
            logger.error(f"Error in _get_descriptive_columns_internal for table {table_name}: {e}")
            return []
    
    def get_table_data(self, table_name, page=1, per_page=50, search=None):
        """Get paginated data from a table with joins on foreign keys to fetch descriptive fields"""
        if not self.connect():
            logger.error(f"Failed to connect to database for table {table_name}")
            return [], 0
        
        try:
            offset = (page - 1) * per_page
            logger.debug(f"Getting data for table: {table_name}, page: {page}, per_page: {per_page}")
            
            # Get foreign keys for the table
            # We need to call get_foreign_keys without connect/disconnect decorators
            foreign_keys = self._get_foreign_keys_internal(table_name)
            logger.debug(f"Found {len(foreign_keys)} foreign keys for {table_name}")
            
            # Build JOIN clauses and select columns
            join_clauses = []
            select_columns = [f"takeoff.{table_name}.*"]  # Always prefix with schema
            join_aliases = {}
            alias_count = 1
            
            for fk in foreign_keys:
                fk_col = fk['fk_column']
                ref_table = fk['referenced_table']
                ref_col = fk['referenced_column']
                
                # Get descriptive columns for referenced table
                desc_cols = self._get_descriptive_columns_internal(ref_table)
                if not desc_cols:
                    # fallback to referenced column itself
                    desc_cols = [ref_col]
                
                alias = f"t{alias_count}"
                alias_count += 1
                join_aliases[fk_col] = alias
                
                join_clauses.append(
                    f"LEFT JOIN takeoff.{ref_table} {alias} ON takeoff.{table_name}.{fk_col} = {alias}.{ref_col}"
                )
                
                for col in desc_cols:
                    select_columns.append(f"{alias}.{col} AS {fk_col}__{col}")
            
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
                    search_conditions = [f"takeoff.{table_name}.{col}::text ILIKE %s" for col in text_columns]
                    search_condition = "WHERE " + " OR ".join(search_conditions)
                    search_params = [f"%{search}%"] * len(text_columns)
            
            # Get total count first
            count_query = f"SELECT COUNT(*) as total FROM takeoff.{table_name} {search_condition}"
            logger.debug(f"Count query: {count_query}")
            self.cursor.execute(count_query, search_params)
            total_records = self.cursor.fetchone()['total']
            logger.debug(f"Total records found: {total_records}")
            
            # Get paginated data with joins
            data_query = f"""
                SELECT {', '.join(select_columns)} FROM takeoff.{table_name}
                {' '.join(join_clauses)}
                {search_condition}
                ORDER BY 1
                LIMIT %s OFFSET %s
            """
            logger.debug(f"Data query: {data_query}")
            logger.debug(f"Query params: {search_params + [per_page, offset]}")
            
            self.cursor.execute(data_query, search_params + [per_page, offset])
            records = self.cursor.fetchall()
            logger.debug(f"Retrieved {len(records)} records")
            
            return records, total_records
        except Exception as e:
            logger.error(f"Error getting table data for {table_name}: {e}")
            logger.error(f"Exception details: {str(e)}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return [], 0
        finally:
            self.disconnect()
    
    def get_record(self, table_name, record_id, id_column=None):
        """Get a single record by ID with joins on foreign keys to fetch descriptive fields"""
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
            
            # Get foreign keys for the table
            foreign_keys = self.get_foreign_keys(table_name)
            
            # Build JOIN clauses and select columns
            join_clauses = []
            select_columns = [f"{table_name}.*"]
            join_aliases = {}
            alias_count = 1
            
            for fk in foreign_keys:
                fk_col = fk['fk_column']
                ref_table = fk['referenced_table']
                ref_col = fk['referenced_column']
                
                # Get descriptive columns for referenced table
                desc_cols = self.get_descriptive_columns(ref_table)
                if not desc_cols:
                    desc_cols = [ref_col]
                
                alias = f"t{alias_count}"
                alias_count += 1
                join_aliases[fk_col] = alias
                
                join_clauses.append(
                    f"LEFT JOIN takeoff.{ref_table} {alias} ON {table_name}.{fk_col} = {alias}.{ref_col}"
                )
                
                for col in desc_cols:
                    select_columns.append(f"{alias}.{col} AS {fk_col}__{col}")
            
            query = f"""
                SELECT {', '.join(select_columns)} FROM takeoff.{table_name}
                {' '.join(join_clauses)}
                WHERE {table_name}.{id_column} = %s
            """
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

    def get_referenced_table_data(self, table_name):
        """Get all records from a referenced table for dropdowns"""
        if not self.connect():
            return [], None, []
        
        try:
            # Get primary key and descriptive columns
            pk_query = """
                SELECT c.column_name
                FROM information_schema.table_constraints tc 
                JOIN information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name) 
                JOIN information_schema.columns AS c ON c.table_schema = tc.table_schema AND tc.table_name = c.table_name AND ccu.column_name = c.column_name
                WHERE tc.constraint_type = 'PRIMARY KEY' AND tc.table_schema = 'takeoff' AND tc.table_name = %s;
            """
            self.cursor.execute(pk_query, (table_name,))
            pk_result = self.cursor.fetchone()
            pk_column = pk_result['column_name'] if pk_result else 'id'

            desc_cols = self._get_descriptive_columns_internal(table_name)
            if not desc_cols:
                desc_cols = [pk_column]
            
            select_cols = [pk_column] + [col for col in desc_cols if col != pk_column]
            
            query = f"SELECT {', '.join(select_cols)} FROM takeoff.{table_name} ORDER BY {desc_cols[0]}"
            self.cursor.execute(query)
            records = self.cursor.fetchall()
            return records, pk_column, desc_cols

        except Exception as e:
            logger.error(f"Error getting referenced table data for {table_name}: {e}")
            return [], None, []
        finally:
            self.disconnect()

# Initialize database manager
db = DatabaseManager()

def update_record(table_name, record_id, data, id_column=None):
    """Update a record by ID"""
    if not db.connect():
        return False
    try:
        # If no ID column specified, use the first column
        if not id_column:
            db.cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'takeoff' AND table_name = %s
                ORDER BY ordinal_position LIMIT 1
            """, (table_name,))
            result = db.cursor.fetchone()
            id_column = result['column_name'] if result else 'id'
        set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
        values = list(data.values()) + [record_id]
        query = f"UPDATE takeoff.{table_name} SET {set_clause} WHERE {id_column} = %s"
        db.cursor.execute(query, values)
        db.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error updating record: {e}")
        db.conn.rollback()
        return False
    finally:
        db.disconnect()

def create_record(table_name, data):
    """Create a new record"""
    if not db.connect():
        return False, None
    try:
        columns = list(data.keys())
        values = list(data.values())
        placeholders = ', '.join(['%s'] * len(values))
        columns_str = ', '.join(columns)
        
        query = f"INSERT INTO takeoff.{table_name} ({columns_str}) VALUES ({placeholders}) RETURNING *"
        db.cursor.execute(query, values)
        new_record = db.cursor.fetchone()
        db.conn.commit()
        return True, new_record
    except Exception as e:
        logger.error(f"Error creating record: {e}")
        db.conn.rollback()
        return False, None
    finally:
        db.disconnect()

def duplicate_record(table_name, record_id, id_column=None):
    """Duplicate a record by creating a copy"""
    if not db.connect():
        return False, None
    try:
        # Get the original record
        if not id_column:
            db.cursor.execute("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_schema = 'takeoff' AND table_name = %s
                ORDER BY ordinal_position LIMIT 1
            """, (table_name,))
            result = db.cursor.fetchone()
            id_column = result['column_name'] if result else 'id'
        
        # Get all column names except primary key
        db.cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'takeoff' AND table_name = %s
            AND column_name != %s
            ORDER BY ordinal_position
        """, (table_name, id_column))
        columns = [row['column_name'] for row in db.cursor.fetchall()]
        
        # Get the record data
        columns_str = ', '.join(columns)
        query = f"SELECT {columns_str} FROM takeoff.{table_name} WHERE {id_column} = %s"
        db.cursor.execute(query, (record_id,))
        record_data = db.cursor.fetchone()
        
        if not record_data:
            return False, None
        
        # Insert the duplicate
        placeholders = ', '.join(['%s'] * len(columns))
        insert_query = f"INSERT INTO takeoff.{table_name} ({columns_str}) VALUES ({placeholders}) RETURNING {id_column}"
        db.cursor.execute(insert_query, list(record_data.values()))
        new_id = db.cursor.fetchone()[id_column]
        db.conn.commit()
        
        return True, new_id
    except Exception as e:
        logger.error(f"Error duplicating record: {e}")
        db.conn.rollback()
        return False, None
    finally:
        db.disconnect()

def save_file(file, table_name, record_id):
    """Save uploaded file and create database record"""
    if not db.connect():
        return False
    try:
        # Generate unique filename
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4()}_{filename}"
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        
        # Save file to disk
        file.save(file_path)
        
        # Save file record to database
        db.cursor.execute("""
            INSERT INTO takeoff.files (file_name, file_path, file_type)
            VALUES (%s, %s, %s) RETURNING file_id
        """, (filename, file_path, filename.rsplit('.', 1)[1].lower() if '.' in filename else ''))
        file_id = db.cursor.fetchone()['file_id']
        
        # Link file to record (assuming we have the primary key name)
        # We'll need to get the primary key column name for the table
        db.cursor.execute("""
            SELECT column_name FROM information_schema.columns 
            WHERE table_schema = 'takeoff' AND table_name = %s
            ORDER BY ordinal_position LIMIT 1
        """, (table_name,))
        result = db.cursor.fetchone()
        pk_column = result['column_name'] if result else 'id'
        
        # Create the link based on table type
        if table_name == 'jobs':
            db.cursor.execute("""
                INSERT INTO takeoff.file_links (file_id, job_id) VALUES (%s, %s)
            """, (file_id, record_id))
        elif table_name == 'plan_options':
            db.cursor.execute("""
                INSERT INTO takeoff.file_links (file_id, plan_option_id) VALUES (%s, %s)
            """, (file_id, record_id))
        elif table_name == 'items':
            db.cursor.execute("""
                INSERT INTO takeoff.file_links (file_id, item_id) VALUES (%s, %s)
            """, (file_id, record_id))
        
        db.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error saving file: {e}")
        db.conn.rollback()
        return False
    finally:
        db.disconnect()

def execute_formulas():
    """Execute all active formulas in calculation order"""
    if not db.connect():
        return False
    try:
        # Get all active formulas ordered by calculation_order
        db.cursor.execute("""
            SELECT formula_id, formula_name, formula_text, depends_on_fields
            FROM takeoff.formulas 
            WHERE is_active = TRUE 
            ORDER BY calculation_order
        """)
        formulas = db.cursor.fetchall()
        
        for formula in formulas:
            try:
                # This is a simplified formula engine
                # In a real implementation, you'd want a more robust parser
                formula_text = formula['formula_text']
                
                if formula_text == '1':
                    # Per build formula - no calculation needed
                    continue
                elif 'heated_sf_inside_studs' in formula_text:
                    # Calculate based on heated square footage
                    db.cursor.execute("""
                        UPDATE takeoff.takeoffs 
                        SET quantity = (
                            SELECT pe.heated_sf_inside_studs 
                            FROM takeoff.jobs j
                            JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                            JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
                            WHERE j.job_id = takeoffs.job_id
                        )
                        WHERE EXISTS (
                            SELECT 1 FROM takeoff.items i 
                            WHERE i.item_id = takeoffs.product_id 
                            AND i.formula_id = %s
                        )
                    """, (formula['formula_id'],))
                elif 'total_sf_outside_studs' in formula_text:
                    # Calculate based on total square footage
                    db.cursor.execute("""
                        UPDATE takeoff.takeoffs 
                        SET quantity = (
                            SELECT pe.total_sf_outside_studs 
                            FROM takeoff.jobs j
                            JOIN takeoff.plan_options po ON j.plan_option_id = po.plan_option_id
                            JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
                            WHERE j.job_id = takeoffs.job_id
                        )
                        WHERE EXISTS (
                            SELECT 1 FROM takeoff.items i 
                            WHERE i.item_id = takeoffs.product_id 
                            AND i.formula_id = %s
                        )
                    """, (formula['formula_id'],))
                
            except Exception as formula_error:
                logger.error(f"Error executing formula {formula['formula_name']}: {formula_error}")
                continue
        
        # Update extended prices
        db.cursor.execute("""
            UPDATE takeoff.takeoffs 
            SET extended_price = quantity * unit_price 
            WHERE quantity IS NOT NULL AND unit_price IS NOT NULL
        """)
        
        db.conn.commit()
        return True
    except Exception as e:
        logger.error(f"Error executing formulas: {e}")
        db.conn.rollback()
        return False
    finally:
        db.disconnect()

# Add request logging
@app.before_request
def log_request_info():
    logger.debug('Request Headers: %s', dict(request.headers))
    logger.debug('Request Path: %s', request.path)

@app.after_request
def log_response_info(response):
    logger.debug('Response Status: %s', response.status)
    logger.debug('Response Headers: %s', dict(response.headers))
    return response

@app.route('/debug')
def debug():
    """Debug page to show database connection status"""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    error = None
    db_ok = False
    tables = []
    db_status = "Not Connected"
    
    try:
        if db.connect():
            db_ok = True
            db_status = "Connected"
            tables = db.get_all_tables()
            if not tables:
                db_status = "Connected but no tables found"
        else:
            db_status = "Connection Failed"
    except Exception as e:
        error = str(e)
        db_status = f"Error: {str(e)}"
    finally:
        db.disconnect()
    
    return render_template('debug.html',
                         now=now,
                         db_ok=db_ok,
                         db_status=db_status,
                         tables=tables,
                         error=error)

@app.route('/')
def dashboard():
    """Main dashboard showing all tables"""
    tables = db.get_all_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    response = make_response(render_template('dashboard_enhanced.html', tables=tables, now=now))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

@app.route('/test')
def test():
    """Test page to verify server is working"""
    try:
        return send_file('test.html')
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route('/nojs')
def dashboard_nojs():
    """Dashboard without any JavaScript"""
    tables = db.get_all_tables()
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return render_template('dashboard_nojs.html', tables=tables, now=now, random=random)

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

@app.route('/table/<table_name>/edit/<record_id>', methods=['GET', 'POST'])
def edit_record(table_name, record_id):
    columns = db.get_table_structure(table_name)
    record = db.get_record(table_name, record_id)
    if not record:
        flash('Record not found', 'error')
        return redirect(url_for('view_table', table_name=table_name))

    # Get foreign key data for dropdowns
    foreign_keys = db.get_foreign_keys(table_name)
    fk_data = {}
    for fk in foreign_keys:
        ref_table = fk['referenced_table']
        options, pk_col, desc_cols = db.get_referenced_table_data(ref_table)
        fk_data[fk['fk_column']] = {
            'options': options,
            'pk_col': pk_col,
            'desc_cols': desc_cols
        }

    if request.method == 'POST':
        data = {}
        for column in columns:
            col_name = column['column_name']
            value = request.form.get(col_name)
            
            # Skip primary key columns if they are not in the form
            if value is None and col_name in (c['column_name'] for c in columns if c.get('is_primary_key')):
                continue

            if column['data_type'] in ['integer', 'bigint', 'smallint']:
                value = int(value) if value and value.strip() != '' else None
            elif column['data_type'] in ['numeric', 'decimal', 'real', 'double precision']:
                value = float(value) if value and value.strip() != '' else None
            elif column['data_type'] == 'boolean':
                value = (value == 'true')
            elif column['data_type'] in ['timestamp without time zone', 'date', 'timestamp with time zone']:
                value = value if value and value.strip() != '' else None
            # else keep as string
            data[col_name] = value
        
        # Get the primary key column name
        id_column = 'id' # default
        for col in columns:
            # A bit of a hack, assuming first column is PK
            id_column = columns[0]['column_name']
            break

        # Check if this is a "save as copy" operation
        if request.form.get('save_as_copy'):
            # Remove primary key from data to create a new record
            data_for_copy = {k: v for k, v in data.items() if k != id_column}
            success, new_record = create_record(table_name, data_for_copy)
            if success:
                new_id = list(new_record.values())[0]  # First column is usually the PK
                flash('Record duplicated successfully', 'success')
                return redirect(url_for('edit_record', table_name=table_name, record_id=new_id))
            else:
                flash('Error duplicating record', 'error')
        else:
            # Regular update
            if update_record(table_name, record_id, data, id_column=id_column):
                flash('Record updated successfully', 'success')
                return redirect(url_for('view_record', table_name=table_name, record_id=record_id))
            else:
                flash('Error updating record', 'error')

    return render_template('edit_record.html', 
                         table_name=table_name, 
                         columns=columns, 
                         record=record,
                         fk_data=fk_data)

@app.route('/table/<table_name>/delete/<record_id>', methods=['POST'])
def delete_record(table_name, record_id):
    """Delete a record"""
    if db.delete_record(table_name, record_id):
        flash('Record deleted successfully', 'success')
    else:
        flash('Error deleting record', 'error')
    
    return redirect(url_for('view_table', table_name=table_name))

@app.route('/table/<table_name>/duplicate/<record_id>', methods=['POST'])
def duplicate_record_route(table_name, record_id):
    """Duplicate a record"""
    success, new_id = duplicate_record(table_name, record_id)
    if success:
        flash(f'Record duplicated successfully with ID {new_id}', 'success')
        return redirect(url_for('edit_record', table_name=table_name, record_id=new_id))
    else:
        flash('Error duplicating record', 'error')
        return redirect(url_for('view_table', table_name=table_name))

@app.route('/table/<table_name>/new', methods=['GET', 'POST'])
def new_record(table_name):
    """Create a new record"""
    columns = db.get_table_structure(table_name)
    
    # Get foreign key data for dropdowns
    foreign_keys = db.get_foreign_keys(table_name)
    fk_data = {}
    for fk in foreign_keys:
        ref_table = fk['referenced_table']
        options, pk_col, desc_cols = db.get_referenced_table_data(ref_table)
        fk_data[fk['fk_column']] = {
            'options': options,
            'pk_col': pk_col,
            'desc_cols': desc_cols
        }

    if request.method == 'POST':
        data = {}
        for column in columns:
            col_name = column['column_name']
            value = request.form.get(col_name)
            
            # Skip primary key columns that are auto-generated
            if col_name.endswith('_id') and column['column_default'] and 'nextval' in str(column['column_default']):
                continue

            if column['data_type'] in ['integer', 'bigint', 'smallint']:
                value = int(value) if value and value.strip() != '' else None
            elif column['data_type'] in ['numeric', 'decimal', 'real', 'double precision']:
                value = float(value) if value and value.strip() != '' else None
            elif column['data_type'] == 'boolean':
                value = (value == 'true')
            elif column['data_type'] in ['timestamp without time zone', 'date', 'timestamp with time zone']:
                value = value if value and value.strip() != '' else None
            # else keep as string
            
            if value is not None:
                data[col_name] = value
        
        success, new_record = create_record(table_name, data)
        if success:
            flash('Record created successfully', 'success')
            # Get the primary key value from the new record
            pk_value = list(new_record.values())[0]  # First column is usually the PK
            return redirect(url_for('view_record', table_name=table_name, record_id=pk_value))
        else:
            flash('Error creating record', 'error')

    return render_template('new_record.html', 
                         table_name=table_name, 
                         columns=columns, 
                         fk_data=fk_data)

@app.route('/table/<table_name>/upload/<record_id>', methods=['POST'])
def upload_file(table_name, record_id):
    """Upload file and attach to record"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('edit_record', table_name=table_name, record_id=record_id))
    
    files = request.files.getlist('file')
    successful_uploads = 0
    
    for file in files:
        if file.filename == '':
            continue
        
        if file and allowed_file(file.filename):
            if save_file(file, table_name, record_id):
                successful_uploads += 1
            else:
                flash(f'Error uploading {file.filename}', 'error')
        else:
            flash(f'File type not allowed: {file.filename}', 'error')
    
    if successful_uploads > 0:
        flash(f'{successful_uploads} file(s) uploaded successfully', 'success')
    
    return redirect(url_for('edit_record', table_name=table_name, record_id=record_id))

@app.route('/files/<file_id>')
def download_file(file_id):
    """Download an uploaded file"""
    if not db.connect():
        return "Database connection failed", 500
    
    try:
        db.cursor.execute("SELECT file_name, file_path FROM takeoff.files WHERE file_id = %s", (file_id,))
        file_record = db.cursor.fetchone()
        
        if not file_record:
            return "File not found", 404
        
        return send_file(file_record['file_path'], as_attachment=True, download_name=file_record['file_name'])
    except Exception as e:
        logger.error(f"Error downloading file: {e}")
        return "Error downloading file", 500
    finally:
        db.disconnect()

@app.route('/formulas/execute', methods=['POST'])
def execute_formulas_route():
    """Execute all formulas to update calculated fields"""
    if execute_formulas():
        flash('Formulas executed successfully', 'success')
    else:
        flash('Error executing formulas', 'error')
    
    return redirect(url_for('dashboard'))

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

@app.route('/api/formulas/execute', methods=['POST'])
def api_execute_formulas():
    """API endpoint to execute formulas"""
    success = execute_formulas()
    return jsonify({'success': success})

# ============ QUOTE MANAGEMENT ROUTES ============

@app.route('/quotes')
def quotes_list():
    """List all vendor quotes with search and filtering"""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    per_page = 25
    
    if not db.connect():
        flash('Database connection failed', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        # Build search and filter conditions
        where_conditions = []
        params = []
        
        if search:
            where_conditions.append("(vq.quote_number ILIKE %s OR v.vendor_name ILIKE %s OR vq.notes ILIKE %s)")
            params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])
        
        if status_filter:
            where_conditions.append("vq.status = %s")
            params.append(status_filter)
        
        where_clause = "WHERE " + " AND ".join(where_conditions) if where_conditions else ""
        
        # Get total count
        count_query = f"""
            SELECT COUNT(*) as total 
            FROM takeoff.vendor_quotes vq
            JOIN takeoff.vendors v ON vq.vendor_id = v.vendor_id
            {where_clause}
        """
        db.cursor.execute(count_query, params)
        total_quotes = db.cursor.fetchone()['total']
        
        # Get paginated quotes with line item and attachment counts
        offset = (page - 1) * per_page
        quotes_query = f"""
            SELECT 
                vq.*,
                v.vendor_name,
                COUNT(DISTINCT vql.quote_line_id) as line_item_count,
                COUNT(DISTINCT fa.file_id) as attachment_count
            FROM takeoff.vendor_quotes vq
            JOIN takeoff.vendors v ON vq.vendor_id = v.vendor_id
            LEFT JOIN takeoff.vendor_quote_lines vql ON vq.quote_id = vql.quote_id
            LEFT JOIN takeoff.file_attachments fa ON vq.quote_id = fa.quote_id
            {where_clause}
            GROUP BY vq.quote_id, v.vendor_name
            ORDER BY vq.quote_date DESC, vq.quote_id DESC
            LIMIT %s OFFSET %s
        """
        db.cursor.execute(quotes_query, params + [per_page, offset])
        quotes = db.cursor.fetchall()
        
        # Calculate summary statistics
        stats_query = f"""
            SELECT 
                COUNT(*) as total_quotes,
                COUNT(CASE WHEN status = 'active' THEN 1 END) as active_quotes,
                COALESCE(SUM(total_amount), 0) as total_value,
                COUNT(DISTINCT vendor_id) as unique_vendors
            FROM takeoff.vendor_quotes vq
            {where_clause}
        """
        db.cursor.execute(stats_query, params)
        stats = db.cursor.fetchone()
        
        total_pages = (total_quotes + per_page - 1) // per_page
        today = datetime.now().date()
        
        return render_template('quotes_list.html',
                             quotes=quotes,
                             current_page=page,
                             total_pages=total_pages,
                             total_quotes=stats['total_quotes'],
                             active_quotes=stats['active_quotes'],
                             total_value=stats['total_value'],
                             unique_vendors=stats['unique_vendors'],
                             search=search,
                             status_filter=status_filter,
                             today=today)
        
    except Exception as e:
        logger.error(f"Error listing quotes: {e}")
        flash('Error loading quotes', 'error')
        return redirect(url_for('dashboard'))
    finally:
        db.disconnect()

@app.route('/quotes/new', methods=['GET', 'POST'])
def new_quote():
    """Create a new vendor quote"""
    if not db.connect():
        flash('Database connection failed', 'error')
        return redirect(url_for('quotes_list'))
    
    try:
        # Get vendors, plans, items, and jobs for dropdowns
        db.cursor.execute("SELECT vendor_id, vendor_name FROM takeoff.vendors ORDER BY vendor_name")
        vendors = db.cursor.fetchall()
        
        db.cursor.execute("""
            SELECT 
                po.plan_option_id, 
                po.option_name, 
                pe.plan_full_name
            FROM takeoff.plan_options po
            JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            ORDER BY pe.plan_full_name, po.option_name
        """)
        plan_options = db.cursor.fetchall()
        
        db.cursor.execute("SELECT item_id, item_name FROM takeoff.items ORDER BY item_name")
        items = db.cursor.fetchall()
        
        db.cursor.execute("SELECT job_id, job_name, plan_option_id FROM takeoff.jobs ORDER BY job_name")
        jobs = db.cursor.fetchall()
        
        if request.method == 'POST':
            # Process form data
            quote_data = {
                'vendor_id': request.form.get('vendor_id'),
                'quote_number': request.form.get('quote_number') or None,
                'quote_date': request.form.get('quote_date'),
                'expiration_date': request.form.get('expiration_date') or None,
                'contact_person': request.form.get('contact_person') or None,
                'contact_email': request.form.get('contact_email') or None,
                'contact_phone': request.form.get('contact_phone') or None,
                'total_amount': float(request.form.get('total_amount')) if request.form.get('total_amount') else None,
                'status': request.form.get('status', 'active'),
                'notes': request.form.get('notes') or None,
                'created_date': datetime.now()
            }
            
            # Add plan_option_id if provided and column exists
            if request.form.get('plan_option_id'):
                quote_data['plan_option_id'] = request.form.get('plan_option_id')
            
            # Add item_id if provided and column exists
            if request.form.get('item_id'):
                quote_data['item_id'] = request.form.get('item_id')
            
            # Auto-generate quote number if not provided
            if not quote_data['quote_number']:
                db.cursor.execute("SELECT MAX(quote_id) as max_id FROM takeoff.vendor_quotes")
                max_id = db.cursor.fetchone()['max_id'] or 0
                quote_data['quote_number'] = f"Q-{datetime.now().year}-{(max_id + 1):04d}"
            
            # Insert quote
            columns = ', '.join(quote_data.keys())
            placeholders = ', '.join(['%s'] * len(quote_data))
            insert_query = f"INSERT INTO takeoff.vendor_quotes ({columns}) VALUES ({placeholders}) RETURNING quote_id"
            
            db.cursor.execute(insert_query, list(quote_data.values()))
            quote_id = db.cursor.fetchone()['quote_id']
            
            # Handle file uploads
            if 'quote_files' in request.files:
                files = request.files.getlist('quote_files')
                for file in files:
                    if file and file.filename and allowed_file(file.filename):
                        # Save file
                        filename = secure_filename(file.filename)
                        unique_filename = f"{uuid.uuid4()}_{filename}"
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                        file.save(file_path)
                        
                        # Insert file record and link to quote
                        db.cursor.execute("""
                            INSERT INTO takeoff.file_attachments (quote_id, file_name, file_path, file_type, uploaded_date)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (quote_id, filename, file_path, filename.rsplit('.', 1)[1].lower(), datetime.now()))
            
            db.conn.commit()
            flash('Quote created successfully', 'success')
            
            # Check if user wants to add line items immediately
            if request.form.get('action') == 'save_and_add_items':
                return redirect(url_for('quote_line_items', quote_id=quote_id))
            else:
                return redirect(url_for('view_quote', quote_id=quote_id))
        
        today = datetime.now().strftime('%Y-%m-%d')
        return render_template('quote_new.html',
                             vendors=vendors,
                             plan_options=plan_options,
                             items=items,
                             jobs=jobs,
                             today=today)
        
    except Exception as e:
        logger.error(f"Error creating quote: {e}")
        flash('Error creating quote', 'error')
        db.conn.rollback()
        return redirect(url_for('quotes_list'))
    finally:
        db.disconnect()

@app.route('/quotes/<int:quote_id>')
def view_quote(quote_id):
    """View quote details"""
    if not db.connect():
        flash('Database connection failed', 'error')
        return redirect(url_for('quotes_list'))
    
    try:
        # Get quote with vendor and plan information
        db.cursor.execute("""
            SELECT vq.*, 
                   v.vendor_name,
                   po.option_name,
                   pe.plan_full_name,
                   pe.plan_name
            FROM takeoff.vendor_quotes vq
            JOIN takeoff.vendors v ON vq.vendor_id = v.vendor_id
            LEFT JOIN takeoff.plan_options po ON vq.plan_option_id = po.plan_option_id
            LEFT JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            WHERE vq.quote_id = %s
        """, (quote_id,))
        quote = db.cursor.fetchone()
        
        if not quote:
            flash('Quote not found', 'error')
            return redirect(url_for('quotes_list'))
        
        # Get line items
        db.cursor.execute("""
            SELECT vql.*, i.item_name 
            FROM takeoff.vendor_quote_lines vql
            LEFT JOIN takeoff.items i ON vql.product_id = i.item_id
            WHERE vql.quote_id = %s
            ORDER BY vql.cost_code, vql.quote_line_id
        """, (quote_id,))
        line_items = db.cursor.fetchall()
        
        # Get file attachments
        db.cursor.execute("""
            SELECT file_id, file_name, uploaded_date
            FROM takeoff.file_attachments
            WHERE quote_id = %s
            ORDER BY uploaded_date DESC
        """, (quote_id,))
        attachments = db.cursor.fetchall()
        
        today = datetime.now().date()
        
        return render_template('quote_view.html',
                             quote=quote,
                             line_items=line_items,
                             attachments=attachments,
                             today=today)
        
    except Exception as e:
        logger.error(f"Error viewing quote: {e}")
        flash('Error loading quote', 'error')
        return redirect(url_for('quotes_list'))
    finally:
        db.disconnect()

@app.route('/quotes/<int:quote_id>/items')
def quote_line_items(quote_id):
    """Manage quote line items"""
    if not db.connect():
        flash('Database connection failed', 'error')
        return redirect(url_for('quotes_list'))
    
    try:
        # Get quote with vendor information
        db.cursor.execute("""
            SELECT vq.*, v.vendor_name
            FROM takeoff.vendor_quotes vq
            JOIN takeoff.vendors v ON vq.vendor_id = v.vendor_id
            WHERE vq.quote_id = %s
        """, (quote_id,))
        quote = db.cursor.fetchone()
        
        if not quote:
            flash('Quote not found', 'error')
            return redirect(url_for('quotes_list'))
        
        # Get line items
        db.cursor.execute("""
            SELECT vql.*, i.item_name 
            FROM takeoff.vendor_quote_lines vql
            LEFT JOIN takeoff.items i ON vql.product_id = i.item_id
            WHERE vql.quote_id = %s
            ORDER BY vql.cost_code, vql.quote_line_id
        """, (quote_id,))
        line_items = db.cursor.fetchall()
        
        # Calculate total from line items
        calculated_total = sum(item['line_total'] or 0 for item in line_items)
        
        # Get products for linking
        db.cursor.execute("""
            SELECT product_id, item_name, product_description
            FROM takeoff.items
            ORDER BY item_name
        """)
        products = db.cursor.fetchall()
        
        return render_template('quote_line_items.html',
                             quote=quote,
                             line_items=line_items,
                             calculated_total=calculated_total,
                             products=products)
        
    except Exception as e:
        logger.error(f"Error loading quote line items: {e}")
        flash('Error loading line items', 'error')
        return redirect(url_for('quotes_list'))
    finally:
        db.disconnect()

@app.route('/quotes/<int:quote_id>/items/new', methods=['POST'])
def add_quote_line_item(quote_id):
    """Add a new line item to a quote"""
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'})
    
    try:
        # Validate quote exists
        db.cursor.execute("SELECT quote_id FROM takeoff.vendor_quotes WHERE quote_id = %s", (quote_id,))
        if not db.cursor.fetchone():
            return jsonify({'success': False, 'message': 'Quote not found'})
        
        # Get form data
        line_data = {
            'quote_id': quote_id,
            'cost_code': request.form.get('cost_code') or None,
            'product_description': request.form.get('product_description'),
            'quantity': float(request.form.get('quantity')) if request.form.get('quantity') else None,
            'unit_price': float(request.form.get('unit_price')) if request.form.get('unit_price') else None,
            'unit_of_measure': request.form.get('unit_of_measure') or None,
            'line_total': float(request.form.get('line_total')) if request.form.get('line_total') else None,
            'notes': request.form.get('notes') or None,
            'product_id': request.form.get('product_id') or None
        }
        
        # Calculate line total if not provided
        if not line_data['line_total'] and line_data['quantity'] and line_data['unit_price']:
            line_data['line_total'] = line_data['quantity'] * line_data['unit_price']
        
        # Insert line item
        columns = ', '.join(line_data.keys())
        placeholders = ', '.join(['%s'] * len(line_data))
        insert_query = f"INSERT INTO takeoff.vendor_quote_lines ({columns}) VALUES ({placeholders})"
        
        db.cursor.execute(insert_query, list(line_data.values()))
        db.conn.commit()
        
        flash('Line item added successfully', 'success')
        return redirect(url_for('quote_line_items', quote_id=quote_id))
        
    except Exception as e:
        logger.error(f"Error adding line item: {e}")
        flash('Error adding line item', 'error')
        db.conn.rollback()
        return redirect(url_for('quote_line_items', quote_id=quote_id))
    finally:
        db.disconnect()

@app.route('/quotes/<int:quote_id>/items/<int:line_item_id>', methods=['DELETE'])
def delete_quote_line_item(quote_id, line_item_id):
    """Delete a quote line item"""
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'})
    
    try:
        # Verify line item belongs to quote
        db.cursor.execute("""
            SELECT quote_line_id FROM takeoff.vendor_quote_lines 
            WHERE quote_line_id = %s AND quote_id = %s
        """, (line_item_id, quote_id))
        
        if not db.cursor.fetchone():
            return jsonify({'success': False, 'message': 'Line item not found'})
        
        # Delete line item
        db.cursor.execute("DELETE FROM takeoff.vendor_quote_lines WHERE quote_line_id = %s", (line_item_id,))
        db.conn.commit()
        
        return jsonify({'success': True, 'message': 'Line item deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting line item: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': 'Error deleting line item'})
    finally:
        db.disconnect()

@app.route('/quotes/<int:quote_id>/edit', methods=['GET', 'POST'])
def edit_quote(quote_id):
    """Edit an existing vendor quote"""
    if not db.connect():
        flash('Database connection failed', 'error')
        return redirect(url_for('quotes_list'))
    
    try:
        # Get vendors and plan options for dropdowns
        db.cursor.execute("SELECT vendor_id, vendor_name FROM takeoff.vendors ORDER BY vendor_name")
        vendors = db.cursor.fetchall()
        
        db.cursor.execute("""
            SELECT po.plan_option_id, po.option_name, pe.plan_full_name
            FROM takeoff.plan_options po
            JOIN takeoff.plan_elevations pe ON po.plan_elevation_id = pe.plan_elevation_id
            ORDER BY pe.plan_full_name, po.option_name
        """)
        plan_options = db.cursor.fetchall()
        
        # Get existing quote
        db.cursor.execute("""
            SELECT * FROM takeoff.vendor_quotes WHERE quote_id = %s
        """, (quote_id,))
        quote = db.cursor.fetchone()
        
        if not quote:
            flash('Quote not found', 'error')
            return redirect(url_for('quotes_list'))
        
        if request.method == 'POST':
            # Process form data
            quote_data = {
                'vendor_id': request.form.get('vendor_id'),
                'quote_number': request.form.get('quote_number'),
                'quote_date': request.form.get('quote_date'),
                'expiration_date': request.form.get('expiration_date') or None,
                'contact_person': request.form.get('contact_person') or None,
                'contact_email': request.form.get('contact_email') or None,
                'contact_phone': request.form.get('contact_phone') or None,
                'total_amount': float(request.form.get('total_amount')) if request.form.get('total_amount') else None,
                'status': request.form.get('status', 'active'),
                'notes': request.form.get('notes') or None,
                'updated_date': datetime.now()
            }
            
            # Add plan_option_id if provided
            if request.form.get('plan_option_id'):
                quote_data['plan_option_id'] = request.form.get('plan_option_id')
            
            # Update quote
            set_clause = ', '.join([f"{k} = %s" for k in quote_data.keys()])
            values = list(quote_data.values()) + [quote_id]
            update_query = f"UPDATE takeoff.vendor_quotes SET {set_clause} WHERE quote_id = %s"
            
            db.cursor.execute(update_query, values)
            db.conn.commit()
            flash('Quote updated successfully', 'success')
            return redirect(url_for('view_quote', quote_id=quote_id))
        
        return render_template('quote_edit.html',
                             quote=quote,
                             vendors=vendors,
                             plan_options=plan_options)
        
    except Exception as e:
        logger.error(f"Error editing quote: {e}")
        flash('Error editing quote', 'error')
        if db.conn:
            db.conn.rollback()
        return redirect(url_for('quotes_list'))
    finally:
        db.disconnect()

@app.route('/quotes/<int:quote_id>/sync-pricing', methods=['POST'])
def sync_quote_to_pricing(quote_id):
    """Sync quote line items to vendor pricing table"""
    if not db.connect():
        return jsonify({'success': False, 'message': 'Database connection failed'})
    
    try:
        # Get quote and vendor information
        db.cursor.execute("""
            SELECT vq.vendor_id, v.vendor_name
            FROM takeoff.vendor_quotes vq
            JOIN takeoff.vendors v ON vq.vendor_id = v.vendor_id
            WHERE vq.quote_id = %s
        """, (quote_id,))
        quote_info = db.cursor.fetchone()
        
        if not quote_info:
            return jsonify({'success': False, 'message': 'Quote not found'})
        
        # Get line items with cost codes
        db.cursor.execute("""
            SELECT cost_code, product_description, unit_price, unit_of_measure, product_id
            FROM takeoff.vendor_quote_lines
            WHERE quote_id = %s AND cost_code IS NOT NULL AND unit_price IS NOT NULL
        """, (quote_id,))
        line_items = db.cursor.fetchall()
        
        updated_count = 0
        vendor_id = quote_info['vendor_id']
        
        for item in line_items:
            # Check if pricing record exists
            db.cursor.execute("""
                SELECT vendor_pricing_id FROM takeoff.vendor_pricing
                WHERE vendor_id = %s AND cost_code = %s
            """, (vendor_id, item['cost_code']))
            
            existing = db.cursor.fetchone()
            
            if existing:
                # Update existing record
                db.cursor.execute("""
                    UPDATE takeoff.vendor_pricing
                    SET unit_price = %s, last_updated = %s, product_description = %s
                    WHERE vendor_pricing_id = %s
                """, (item['unit_price'], datetime.now(), item['product_description'], existing['vendor_pricing_id']))
            else:
                # Insert new record
                db.cursor.execute("""
                    INSERT INTO takeoff.vendor_pricing 
                    (vendor_id, cost_code, unit_price, product_description, unit_of_measure, product_id, last_updated)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (vendor_id, item['cost_code'], item['unit_price'], item['product_description'], 
                     item['unit_of_measure'], item['product_id'], datetime.now()))
            
            updated_count += 1
        
        db.conn.commit()
        return jsonify({'success': True, 'updated_count': updated_count})
        
    except Exception as e:
        logger.error(f"Error syncing quote to pricing: {e}")
        db.conn.rollback()
        return jsonify({'success': False, 'message': 'Error syncing pricing'})
    finally:
        db.disconnect()

@app.route('/quotes/<int:quote_id>/delete', methods=['POST'])
def delete_quote(quote_id):
    """Delete a vendor quote and its related data"""
    if not db.connect():
        flash('Database connection failed', 'error')
        return redirect(url_for('quotes_list'))
    
    try:
        # Check if quote exists
        db.cursor.execute("SELECT quote_id FROM takeoff.vendor_quotes WHERE quote_id = %s", (quote_id,))
        if not db.cursor.fetchone():
            flash('Quote not found', 'error')
            return redirect(url_for('quotes_list'))
        
        # Delete related records first (due to foreign keys)
        # Delete line items
        db.cursor.execute("DELETE FROM takeoff.vendor_quote_lines WHERE quote_id = %s", (quote_id,))
        
        # Delete file attachments (files will remain on disk for now)
        db.cursor.execute("DELETE FROM takeoff.file_attachments WHERE quote_id = %s", (quote_id,))
        
        # Delete the quote
        db.cursor.execute("DELETE FROM takeoff.vendor_quotes WHERE quote_id = %s", (quote_id,))
        
        db.conn.commit()
        flash('Quote deleted successfully', 'success')
        
    except Exception as e:
        logger.error(f"Error deleting quote: {e}")
        flash('Error deleting quote', 'error')
        db.conn.rollback()
    finally:
        db.disconnect()
    
    return redirect(url_for('quotes_list'))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=8002)
