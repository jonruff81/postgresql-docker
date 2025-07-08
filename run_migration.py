#!/usr/bin/env python3
"""
Simple migration runner to execute SQL files
"""

import sys
import os
import psycopg2
from config import DB_CONFIG_DICT as DB_CONFIG

def run_migration(sql_file_path):
    """Run a SQL migration file"""
    try:
        # Read the SQL file
        with open(sql_file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        # Connect to database
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print(f"🔄 Running migration: {sql_file_path}")
        
        # Execute the SQL
        cursor.execute(sql_content)
        conn.commit()
        
        print("✅ Migration completed successfully")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
        return False

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python run_migration.py <sql_file_path>")
        sys.exit(1)
    
    sql_file = sys.argv[1]
    
    if not os.path.exists(sql_file):
        print(f"❌ SQL file not found: {sql_file}")
        sys.exit(1)
    
    success = run_migration(sql_file)
    sys.exit(0 if success else 1)