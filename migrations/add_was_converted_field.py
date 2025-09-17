#!/usr/bin/env python3
"""
Migration: Add was_converted field to file_uploads table
"""

import sqlite3
import os
import sys

# Add the src directory to the path so we can import our models
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

def run_migration():
    """Add was_converted column to file_uploads table"""
    
    # Database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'ca_tadley_debt_tool.db')
    
    if not os.path.exists(db_path):
        print(f"❌ Database not found at {db_path}")
        return False
    
    try:
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("🔄 Adding was_converted column to file_uploads table...")
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(file_uploads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'was_converted' in columns:
            print("✅ was_converted column already exists")
            return True
        
        # Add the was_converted column
        cursor.execute("""
            ALTER TABLE file_uploads 
            ADD COLUMN was_converted BOOLEAN DEFAULT 0
        """)
        
        # Commit changes
        conn.commit()
        print("✅ Successfully added was_converted column to file_uploads table")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    print("🚀 Starting migration: Add was_converted field to file_uploads table")
    success = run_migration()
    if success:
        print("✅ Migration completed successfully")
    else:
        print("❌ Migration failed")
        sys.exit(1)
