"""
Add role-based session settings columns
This migration adds columns for role-specific session timeouts, warnings, and inactivity thresholds.
"""

from sqlalchemy import text
from src.config.database import engine

def upgrade():
    """Add role-based session settings columns"""
    with engine.connect() as conn:
        try:
            # Check if columns already exist by trying to add them
            # SQLite doesn't support IF NOT EXISTS for ALTER TABLE ADD COLUMN
            
            # Add client session settings columns
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN client_session_timeout_seconds INTEGER DEFAULT 420 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
                    
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN client_session_warning_seconds INTEGER DEFAULT 300 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
                    
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN client_inactivity_threshold_seconds INTEGER DEFAULT 120 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
            
            # Add adviser session settings columns
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN adviser_session_timeout_seconds INTEGER DEFAULT 150 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
                    
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN adviser_session_warning_seconds INTEGER DEFAULT 120 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
                    
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN adviser_inactivity_threshold_seconds INTEGER DEFAULT 30 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
            
            # Add admin session settings columns
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN admin_session_timeout_seconds INTEGER DEFAULT 100 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
                    
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN admin_session_warning_seconds INTEGER DEFAULT 90 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
                    
            try:
                conn.execute(text("ALTER TABLE session_settings ADD COLUMN admin_inactivity_threshold_seconds INTEGER DEFAULT 10 NOT NULL"))
            except Exception as e:
                if "duplicate column name" not in str(e).lower():
                    raise e
            
            # Update existing settings to use client defaults for legacy fields
            conn.execute(text("""
                UPDATE session_settings 
                SET 
                    session_timeout_seconds = 420,
                    session_warning_seconds = 300,
                    inactivity_threshold_seconds = 120
                WHERE id = 'singleton'
            """))
            
            conn.commit()
            print("✅ Role-based session settings columns added successfully")
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Error adding role-based session settings columns: {str(e)}")
            raise e

def downgrade():
    """Remove role-based session settings columns"""
    with engine.connect() as conn:
        # Remove client session settings columns
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS client_session_timeout_seconds"))
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS client_session_warning_seconds"))
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS client_inactivity_threshold_seconds"))
        
        # Remove adviser session settings columns
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS adviser_session_timeout_seconds"))
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS adviser_session_warning_seconds"))
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS adviser_inactivity_threshold_seconds"))
        
        # Remove admin session settings columns
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS admin_session_timeout_seconds"))
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS admin_session_warning_seconds"))
        conn.execute(text("ALTER TABLE session_settings DROP COLUMN IF EXISTS admin_inactivity_threshold_seconds"))
        
        # Restore legacy defaults
        conn.execute(text("""
            UPDATE session_settings 
            SET 
                session_timeout_seconds = 300,
                session_warning_seconds = 60,
                inactivity_threshold_seconds = 5
            WHERE id = 'singleton'
        """))
        
        conn.commit()
        print("✅ Role-based session settings columns removed successfully")

if __name__ == "__main__":
    upgrade()
