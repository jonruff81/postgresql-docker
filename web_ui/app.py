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
    """Main dashboard showing all tables"""
    tables = db.get_all_tables()
    return render_template('dashboard.html', tables=tables)

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
