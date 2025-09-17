#!/usr/bin/env python3
"""
Migration script to add property_postcode field to assets table
"""

import sqlite3
import os
import sys

def run_migration():
    # Get the database path
    db_path = 'ca_tadley_debt_tool.db'
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Adding property_postcode field to assets table...")
        
        # Add the property_postcode column
        cursor.execute('''
            ALTER TABLE assets 
            ADD COLUMN property_postcode VARCHAR(20) NULL
        ''')
        
        conn.commit()
        print("✅ Successfully added property_postcode field to assets table")
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(assets)")
        columns = cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if 'property_postcode' in column_names:
            print("✅ Verification successful: property_postcode column exists")
        else:
            print("❌ Verification failed: property_postcode column not found")
            return False
        
        conn.close()
        return True
        
    except sqlite3.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

if __name__ == "__main__":
    success = run_migration()
    if success:
        print("\n🎉 Migration completed successfully!")
        sys.exit(0)
    else:
        print("\n💥 Migration failed!")
        sys.exit(1)
