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
        
        # Add the new columns (SQLite requires separate statements)
        db.execute(text("ALTER TABLE file_uploads ADD COLUMN debt_type VARCHAR(50)"))
        db.execute(text("ALTER TABLE file_uploads ADD COLUMN asset_type VARCHAR(50)"))
        db.execute(text("ALTER TABLE file_uploads ADD COLUMN income_type VARCHAR(50)"))
        db.execute(text("ALTER TABLE file_uploads ADD COLUMN expenditure_type VARCHAR(50)"))
        
        db.commit()
        print("✅ Successfully added type fields to file_uploads table")
        
    except Exception as e:
        print(f"❌ Error adding type fields: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()
