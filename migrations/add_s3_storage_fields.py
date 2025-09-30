"""
Add S3 storage fields to file_uploads table
"""
import sqlite3
import os


def run_migration():
    """Add S3 storage fields to file_uploads table"""
    db_path = 'ca_tadley_debt_tool.db'
    
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return False
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        print("Adding S3 storage fields to file_uploads table...")
        
        # Check if columns already exist
        cursor.execute("PRAGMA table_info(file_uploads)")
        columns = [column[1] for column in cursor.fetchall()]
        
        if 's3_key' not in columns:
            cursor.execute(
                'ALTER TABLE file_uploads ADD COLUMN s3_key VARCHAR(500)'
            )
            print("✅ Added s3_key field to file_uploads table")
        else:
            print("ℹ️ s3_key field already exists in file_uploads table")
        
        if 'storage_type' not in columns:
            cursor.execute(
                'ALTER TABLE file_uploads ADD COLUMN storage_type '
                'VARCHAR(10) DEFAULT "local"'
            )
            print("✅ Added storage_type field to file_uploads table")
        else:
            print("ℹ️ storage_type field already exists in file_uploads table")
        
        conn.commit()
        conn.close()
        
        print("✅ S3 storage migration completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ Error during S3 storage migration: {e}")
        return False


if __name__ == "__main__":
    run_migration()