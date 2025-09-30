#!/usr/bin/env python3
"""
Migration to add type fields to file_uploads table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import engine, SessionLocal
from sqlalchemy import text

def run_migration():
    """Add type fields to file_uploads table"""
    db = SessionLocal()
    try:
        print("Adding type fields to file_uploads table...")
        
        # Check which columns already exist
        existing_columns = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'file_uploads'
        """)).fetchall()
        
        existing_column_names = [row[0] for row in existing_columns]
        
        # Add columns only if they don't exist
        columns_to_add = [
            ("debt_type", "VARCHAR(50)"),
            ("asset_type", "VARCHAR(50)"),
            ("income_type", "VARCHAR(50)"),
            ("expenditure_type", "VARCHAR(50)")
        ]
        
        for column_name, column_type in columns_to_add:
            if column_name not in existing_column_names:
                db.execute(text(f"ALTER TABLE file_uploads ADD COLUMN {column_name} {column_type}"))
                print(f"✅ Added {column_name} column")
            else:
                print(f"✅ {column_name} column already exists")
        
        db.commit()
        print("✅ Successfully processed type fields for file_uploads table")
        
    except Exception as e:
        print(f"❌ Error adding type fields: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
