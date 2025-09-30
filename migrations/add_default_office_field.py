#!/usr/bin/env python3
"""
Migration to add is_default field to offices table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, Boolean, text
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings
from src.models.office import Office

def migrate():
    """Add is_default field to offices table and set first office as default"""
    print("🔄 Adding is_default field to offices table...")
    
    # Create engine and session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'offices' AND column_name = 'is_default'
        """)).fetchone()
        
        if result:
            print("✅ is_default column already exists in offices table")
        else:
            # Add the is_default column
            db.execute(text("ALTER TABLE offices ADD COLUMN is_default BOOLEAN DEFAULT FALSE"))
            print("✅ Added is_default column to offices table")
        
        # Set the first office as default
        first_office = db.query(Office).order_by(Office.created_at).first()
        if first_office:
            first_office.is_default = True
            db.commit()
            print(f"✅ Set first office '{first_office.name}' as default office")
        else:
            print("⚠️  No offices found to set as default")
        
        print("✅ Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    migrate()
