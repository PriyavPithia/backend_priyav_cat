#!/usr/bin/env python3
"""
Migration to add invitation fields to users table
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
        print("🔄 Adding invitation fields to users table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        # Add invitation_token column if it doesn't exist
        if 'invitation_token' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN invitation_token TEXT UNIQUE")
            print("✅ Added invitation_token column")
        
        # Add invitation_expires_at column if it doesn't exist
        if 'invitation_expires_at' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN invitation_expires_at DATETIME")
            print("✅ Added invitation_expires_at column")
        
        # Add invited_by_id column if it doesn't exist
        if 'invited_by_id' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN invited_by_id TEXT REFERENCES users(id)")
            print("✅ Added invited_by_id column")
        
        # Create index on invitation_token for faster lookups
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_invitation_token ON users (invitation_token)")
        print("✅ Created index on invitation_token")
        
        conn.commit()
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
