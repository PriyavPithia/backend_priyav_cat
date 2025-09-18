#!/usr/bin/env python3
"""
Migration to add missing optional information fields to users table
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
        print("🔄 Adding missing optional information fields to users table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add missing optional information fields
        missing_fields = [
            ('nationality', 'TEXT'),
            ('nationality_prefer_not_to_say', 'BOOLEAN DEFAULT 0'),
            ('preferred_language', 'TEXT'),
            ('preferred_language_prefer_not_to_say', 'BOOLEAN DEFAULT 0'),
            ('religion', 'TEXT'),
            ('religion_prefer_not_to_say', 'BOOLEAN DEFAULT 0'),
            ('gender_identity', 'TEXT'),
            ('gender_identity_prefer_not_to_say', 'BOOLEAN DEFAULT 0'),
            ('sexual_orientation', 'TEXT'),
            ('sexual_orientation_prefer_not_to_say', 'BOOLEAN DEFAULT 0')
        ]
        
        for field_name, field_type in missing_fields:
            if field_name not in columns:
                cursor.execute(f"ALTER TABLE users ADD COLUMN {field_name} {field_type}")
                print(f"✅ Added {field_name} column")
            else:
                print(f"ℹ️ {field_name} column already exists")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
