#!/usr/bin/env python3
"""
Migration script to add preferences column to users table
"""

import sqlite3
import os
import json
from datetime import datetime

def add_user_preferences_column():
    """Add preferences column to users table"""
    
    # Get the database path
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ca_tadley_debt_tool.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        print("🔍 Adding preferences column to users table...")
        
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'preferences' in columns:
            print("✅ Preferences column already exists in users table")
            return
        
        # Add the preferences column
        cursor.execute('''
            ALTER TABLE users 
            ADD COLUMN preferences TEXT DEFAULT '{}'
        ''')
        
        # Initialize existing users with default preferences
        default_preferences = {
            "happy_voicemail": True,
            "happy_text_messages": True,
            "preferred_contact_email": True,
            "preferred_contact_mobile": True,
            "preferred_contact_home_phone": False,
            "preferred_contact_address": False,
            "agree_to_feedback": True,
            "do_not_contact_methods": [],
            "do_not_contact_feedback_methods": []
        }
        
        default_preferences_json = json.dumps(default_preferences)
        
        # Update all existing users with default preferences
        cursor.execute('''
            UPDATE users 
            SET preferences = ? 
            WHERE preferences IS NULL OR preferences = ''
        ''', (default_preferences_json,))
        
        updated_count = cursor.rowcount
        print(f"✅ Updated {updated_count} users with default preferences")
        
        # Commit the changes
        conn.commit()
        
        # Verify the column was added
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'preferences' in columns:
            print("✅ Preferences column successfully added to users table")
        else:
            print("❌ Failed to add preferences column")
            
    except Exception as e:
        print(f"❌ Error adding preferences column: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    add_user_preferences_column()
