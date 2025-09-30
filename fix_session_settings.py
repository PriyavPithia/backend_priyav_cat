#!/usr/bin/env python3
"""
Fix session settings in the database
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings
from src.models.session_settings import SessionSettings

def fix_session_settings():
    """Fix session settings in the database"""
    print("🔧 Fixing session settings...")
    
    # Create engine and session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Delete any existing session settings
        db.execute(text("DELETE FROM session_settings"))
        
        # Create new session settings with correct values
        session_settings = SessionSettings(
            id="singleton",
            session_timeout_seconds=420,  # 7 minutes
            session_warning_seconds=300,  # 5 minutes
            inactivity_threshold_seconds=120,  # 2 minutes
            client_session_timeout_seconds=420,
            client_session_warning_seconds=300,
            client_inactivity_threshold_seconds=120,
            adviser_session_timeout_seconds=150,  # 2.5 minutes
            adviser_session_warning_seconds=120,
            adviser_inactivity_threshold_seconds=30,
            admin_session_timeout_seconds=100,  # 100 seconds
            admin_session_warning_seconds=90,
            admin_inactivity_threshold_seconds=10,
            enable_session_management=True,
            enable_session_debugger=True
        )
        
        db.add(session_settings)
        db.commit()
        
        print("✅ Session settings fixed successfully!")
        
        # Verify the settings
        settings_check = db.query(SessionSettings).filter(SessionSettings.id == "singleton").first()
        if settings_check:
            print(f"✅ Verified: Session timeout = {settings_check.session_timeout_seconds}s")
            print(f"✅ Verified: Session management = {settings_check.enable_session_management}")
        else:
            print("❌ Failed to verify session settings")
            
    except Exception as e:
        print(f"❌ Error fixing session settings: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_session_settings()

