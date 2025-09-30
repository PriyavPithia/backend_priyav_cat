from sqlalchemy import create_engine, text
from src.config.settings import settings

def run_migration():
    """Drop and recreate session_settings table"""
    engine = create_engine(settings.database_url)
    
    # SQL statements to recreate table
    statements = [
        "DROP TABLE IF EXISTS session_settings",
        """
        CREATE TABLE session_settings (
            id VARCHAR PRIMARY KEY DEFAULT 'singleton',
            session_timeout_seconds INTEGER NOT NULL DEFAULT 300,
            session_warning_seconds INTEGER NOT NULL DEFAULT 60,
            inactivity_threshold_seconds INTEGER NOT NULL DEFAULT 5,
            enable_session_management BOOLEAN NOT NULL DEFAULT 1,
            enable_session_debugger BOOLEAN NOT NULL DEFAULT 1,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_by VARCHAR
        )
        """,
        """
        INSERT INTO session_settings (
            id, 
            session_timeout_seconds,
            session_warning_seconds,
            inactivity_threshold_seconds,
            enable_session_management,
            enable_session_debugger
        ) VALUES (
            'singleton',
            300,
            60,
            5,
            1,
            1
        )
        """
    ]
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        try:
            # Execute all statements in a single transaction
            for statement in statements:
                conn.execute(text(statement))
            # Commit if all successful
            trans.commit()
            print("✅ Successfully recreated session_settings table")
        except Exception as e:
            # Rollback on any error
            trans.rollback()
            print(f"⚠️ Error recreating session_settings table: {str(e)}")
            raise

if __name__ == "__main__":
    run_migration()
