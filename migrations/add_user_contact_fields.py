#!/usr/bin/env python3
"""
Database migration to add contact detail fields to users table
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
        print("🔄 Adding contact detail fields to users table...")
        
        # Check current table structure
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        print(f"📋 Current columns: {columns}")
        
        # Add new contact detail fields if they don't exist
        new_fields = {
            'title': 'TEXT',
            'home_phone': 'TEXT', 
            'home_address': 'TEXT',
            'postcode': 'TEXT',
            'date_of_birth': 'TEXT',
            'gender': 'TEXT'
        }
        
        for field_name, field_type in new_fields.items():
            if field_name not in columns:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                print(f"✅ Added {field_name} column")
            else:
                print(f"⚠️ Column {field_name} already exists")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
