#!/usr/bin/env python3
"""
Migration to add is_joint boolean to debts and assets tables
"""

import sqlite3
import os

def migrate():
    db_path = 'ca_tadley_debt_tool.db'
    if not os.path.exists(db_path):
        print("❌ Database file not found")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        print("🔄 Adding is_joint columns to debts and assets tables...")

        # debts
        cursor.execute("PRAGMA table_info(debts)")
        debt_columns = [column[1] for column in cursor.fetchall()]
        if 'is_joint' not in debt_columns:
            cursor.execute("ALTER TABLE debts ADD COLUMN is_joint BOOLEAN")
            print("✅ Added is_joint to debts")
        else:
            print("ℹ️ is_joint already exists on debts")

        # assets
        cursor.execute("PRAGMA table_info(assets)")
        asset_columns = [column[1] for column in cursor.fetchall()]
        if 'is_joint' not in asset_columns:
            cursor.execute("ALTER TABLE assets ADD COLUMN is_joint BOOLEAN")
            print("✅ Added is_joint to assets")
        else:
            print("ℹ️ is_joint already exists on assets")

        conn.commit()
        print("✅ Migration completed successfully!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()


