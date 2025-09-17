#!/usr/bin/env python3
"""
Migration script to add notifications table
"""

import sqlite3
import os
from datetime import datetime

def migrate():
    """Add notifications table to the database"""
    
    # Get the database path
    db_path = "ca_tadley_debt_tool.db"
    
    if not os.path.exists(db_path):
        print(f"Database file {db_path} not found. Please run the application first to create the database.")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if notifications table already exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='notifications'
        """)
        
        if cursor.fetchone():
            print("Notifications table already exists. Skipping migration.")
            return
        
        # Create notifications table
        cursor.execute("""
            CREATE TABLE notifications (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                case_id TEXT,
                data TEXT,
                read BOOLEAN DEFAULT FALSE,
                read_at DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
                FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX idx_notifications_user_id ON notifications (user_id)")
        cursor.execute("CREATE INDEX idx_notifications_type ON notifications (type)")
        cursor.execute("CREATE INDEX idx_notifications_read ON notifications (read)")
        cursor.execute("CREATE INDEX idx_notifications_created_at ON notifications (created_at)")
        
        # Commit the changes
        conn.commit()
        
        print("✅ Notifications table created successfully")
        print("   - Added notifications table with proper foreign key constraints")
        print("   - Created indexes for user_id, type, read status, and created_at")
        print("   - Added support for case_closed, case_updated, case_assigned, mention, and system notification types")
        
    except Exception as e:
        print(f"❌ Error creating notifications table: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
