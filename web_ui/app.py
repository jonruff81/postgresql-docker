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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
