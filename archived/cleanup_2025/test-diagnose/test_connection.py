#!/usr/bin/env python3
"""
Test database connection to Hostinger PostgreSQL
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import DB_CONFIG

def test_connection():
    """Test the Hostinger database connection"""
    print(f"\n🔍 Testing Hostinger PostgreSQL connection...")
    print(f"   Host: {DB_CONFIG.host}:{DB_CONFIG.port}")
    print(f"   Database: {DB_CONFIG.database}")
    print(f"   User: {DB_CONFIG.user}")
    
    try:
        # Attempt connection
        conn = psycopg2.connect(**DB_CONFIG.to_dict())
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        
        # Test basic query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        print(f"   ✅ Connection successful!")
        print(f"   📊 PostgreSQL Version: {version['version'][:50]}...")
        
        # Test schema access
        cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'takeoff';")
        schema_result = cursor.fetchone()
        if schema_result:
            print(f"   📁 Schema 'takeoff' exists")
            
            # Count tables in takeoff schema
            cursor.execute("""
                SELECT COUNT(*) as table_count 
                FROM information_schema.tables 
                WHERE table_schema = 'takeoff'
            """)
            table_count = cursor.fetchone()['table_count']
            print(f"   📋 Tables in takeoff schema: {table_count}")
            
            if table_count > 0:
                # List some key tables
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'takeoff' 
                    AND table_name IN ('plans', 'takeoffs', 'vendors', 'products', 'items')
                    ORDER BY table_name
                """)
                tables = cursor.fetchall()
                print(f"   📝 Key tables: {', '.join([t['table_name'] for t in tables])}")
                
                # Get record counts for key tables
                for table in ['plans', 'takeoffs', 'vendors', 'products']:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as count FROM takeoff.{table}")
                        count = cursor.fetchone()['count']
                        print(f"   📊 {table}: {count} records")
                    except:
                        pass
        else:
            print(f"   ⚠️  Schema 'takeoff' does not exist")
        
        cursor.close()
        conn.close()
        return True
        
    except psycopg2.OperationalError as e:
        print(f"   ❌ Connection failed: {e}")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    """Test the database connection"""
    print("🚀 Hostinger PostgreSQL Connection Test")
    print("=" * 50)
    
    # Test connection
    success = test_connection()
    
    print("\n" + "=" * 50)
    print("📊 Summary:")
    print(f"   Hostinger Database: {'✅ Working' if success else '❌ Failed'}")
    
    if success:
        print("\n🎉 Database connection successful!")
        print("💡 To start the web application:")
        print("   python web_ui/app.py")
        print("   or")
        print("   test-diagnose/run_hostinger.bat")
    else:
        print("\n⚠️  Database connection failed.")
        print("🔧 Please check:")
        print("   1. Database credentials in config.py")
        print("   2. Firewall settings on Hostinger")
        print("   3. Network connectivity to 31.97.137.221:5432")
        print("   4. Database name and user permissions")

if __name__ == "__main__":
    main()
