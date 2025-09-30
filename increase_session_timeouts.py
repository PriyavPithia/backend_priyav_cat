#!/usr/bin/env python3
"""
Increase session timeouts to prevent auto-logout during slow API responses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.config.settings import settings

def increase_session_timeouts():
    """Increase session timeouts to prevent auto-logout"""
    print("🔧 Increasing session timeouts...")
    
    # Create engine and session
    engine = create_engine(settings.database_url)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Update session settings with much longer timeouts
        db.execute(text("""
            UPDATE session_settings SET
                session_timeout_seconds = 1800,
                session_warning_seconds = 1500,
                inactivity_threshold_seconds = 600,
                client_session_timeout_seconds = 1800,
                client_session_warning_seconds = 1500,
                client_inactivity_threshold_seconds = 600,
                adviser_session_timeout_seconds = 1800,
                adviser_session_warning_seconds = 1500,
                adviser_inactivity_threshold_seconds = 600,
                admin_session_timeout_seconds = 1800,
                admin_session_warning_seconds = 1500,
                admin_inactivity_threshold_seconds = 600
            WHERE id = 'singleton'
        """))
        
        db.commit()
        print("✅ Session timeouts increased successfully!")
        print("✅ All roles now have 30-minute sessions with 25-minute warnings")
        
    except Exception as e:
        print(f"❌ Error increasing session timeouts: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    increase_session_timeouts()
