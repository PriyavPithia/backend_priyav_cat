import sqlite3
import os

def migrate():
    """Add is_office_admin field to users table"""
    
    # Get the database path
    db_path = os.path.join(os.path.dirname(__file__), '..', 'ca_tadley_debt_tool.db')
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        # Check if the column already exists
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 'is_office_admin' not in columns:
            # Add the new column
            cursor.execute("ALTER TABLE users ADD COLUMN is_office_admin BOOLEAN DEFAULT 0")
            print("✅ Added is_office_admin column to users table")
        else:
            print("ℹ️  is_office_admin column already exists")
        
        # Commit the changes
        conn.commit()
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
