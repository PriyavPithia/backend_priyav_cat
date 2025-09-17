#!/usr/bin/env python3
"""
Migration to add invitation_details column to users table
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
        print("🔄 Adding invitation_details column to users table...")
        
        # Check if column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add invitation_details column if it doesn't exist
        if 'invitation_details' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN invitation_details TEXT")
            print("✅ Added invitation_details column")
        else:
            print("ℹ️ invitation_details column already exists")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
