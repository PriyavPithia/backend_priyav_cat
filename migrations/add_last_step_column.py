import sqlite3
import os


def migrate():
    """Add last_step INTEGER column to cases table for server-side step persistence."""

    db_path = os.path.join(os.path.dirname(__file__), '..', 'ca_tadley_debt_tool.db')
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    try:
        cursor.execute("PRAGMA table_info(cases)")
        columns = [column[1] for column in cursor.fetchall()]

        if 'last_step' not in columns:
            cursor.execute("ALTER TABLE cases ADD COLUMN last_step INTEGER")
            print("✅ Added last_step column to cases table")
        else:
            print("ℹ️  last_step column already exists")

        conn.commit()
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()


if __name__ == "__main__":
    migrate()


