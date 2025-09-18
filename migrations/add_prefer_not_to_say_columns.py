#!/usr/bin/env python3
"""
Migration to add prefer_not_to_say columns to users table for optional information
"""

import sqlite3
import os

def migrate():
    db_path = 'ca_tadley_debt_tool.db'
    
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔄 Adding prefer_not_to_say columns to users table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add prefer_not_to_say columns if they don't exist
        prefer_not_to_say_columns = [
            'ethnicity_prefer_not_to_say',
            'marital_status_prefer_not_to_say',
            'household_type_prefer_not_to_say',
            'occupation_prefer_not_to_say',
            'housing_tenure_prefer_not_to_say'
        ]
        
        for column_name in prefer_not_to_say_columns:
            if column_name not in columns:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {column_name} BOOLEAN DEFAULT 0")
                print(f"✅ Added {column_name} column")
            else:
                print(f"ℹ️ {column_name} column already exists")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
