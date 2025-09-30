#!/usr/bin/env python3
"""
Run migrations safely - skip ones that have already been applied
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from src.config.settings import settings

def check_column_exists(table_name, column_name):
    """Check if a column exists in a table"""
    engine = create_engine(settings.database_url)
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = :table_name AND column_name = :column_name
        """), {"table_name": table_name, "column_name": column_name}).fetchone()
        return result is not None

def run_migrations_safe():
    """Run migrations safely, skipping already applied ones"""
    print("🚀 Running migrations safely...")
    
    # List of migrations with their checks
    migrations = [
        {
            "name": "add_default_office_field",
            "check": lambda: check_column_exists("offices", "is_default"),
            "import": "from migrations.add_default_office_field import migrate as add_default_office_field",
            "run": "add_default_office_field()"
        },
        {
            "name": "add_file_type_fields", 
            "check": lambda: check_column_exists("file_uploads", "debt_type"),
            "import": "from migrations.add_file_type_fields import run_migration as add_file_type_fields",
            "run": "add_file_type_fields()"
        },
        {
            "name": "add_invitation_details",
            "check": lambda: check_column_exists("users", "invitation_token"),
            "import": "from migrations.add_invitation_details import migrate as add_invitation_details", 
            "run": "add_invitation_details()"
        },
        {
            "name": "add_invitation_fields",
            "check": lambda: check_column_exists("users", "invited_by"),
            "import": "from migrations.add_invitation_fields import migrate as add_invitation_fields",
            "run": "add_invitation_fields()"
        },
        {
            "name": "add_last_step",
            "check": lambda: check_column_exists("cases", "last_step"),
            "import": "from migrations.add_last_step_column import migrate as add_last_step",
            "run": "add_last_step()"
        },
        {
            "name": "add_missing_optional_fields",
            "check": lambda: check_column_exists("client_details", "prefer_not_to_say"),
            "import": "from migrations.add_missing_optional_fields import migrate as add_missing_optional_fields",
            "run": "add_missing_optional_fields()"
        },
        {
            "name": "add_notifications",
            "check": lambda: check_column_exists("notifications", "id"),
            "import": "from migrations.add_notifications_table import migrate as add_notifications",
            "run": "add_notifications()"
        },
        {
            "name": "add_office_admin_field",
            "check": lambda: check_column_exists("offices", "admin_user_id"),
            "import": "from migrations.add_office_admin_field import migrate as add_office_admin",
            "run": "add_office_admin()"
        },
        {
            "name": "add_prefer_not_to_say_columns",
            "check": lambda: check_column_exists("client_details", "prefer_not_to_say_income"),
            "import": "from migrations.add_prefer_not_to_say_columns import migrate as add_prefer_not_to_say_columns",
            "run": "add_prefer_not_to_say_columns()"
        },
        {
            "name": "add_property_postcode_field",
            "check": lambda: check_column_exists("assets", "property_postcode"),
            "import": "from migrations.add_property_postcode_field import run_migration as add_property_postcode_field",
            "run": "add_property_postcode_field()"
        },
        {
            "name": "add_user_contact_fields",
            "check": lambda: check_column_exists("users", "phone_number"),
            "import": "from migrations.add_user_contact_fields import migrate as add_user_contact_fields",
            "run": "add_user_contact_fields()"
        },
        {
            "name": "add_user_preferences_column",
            "check": lambda: check_column_exists("users", "preferences"),
            "import": "from migrations.add_user_preferences_column import add_user_preferences_column",
            "run": "add_user_preferences_column()"
        },
        {
            "name": "add_was_converted_field",
            "check": lambda: check_column_exists("cases", "was_converted"),
            "import": "from migrations.add_was_converted_field import run_migration as add_was_converted_field",
            "run": "add_was_converted_field()"
        },
        {
            "name": "add_joint_flags_to_debt_asset",
            "check": lambda: check_column_exists("debts", "is_joint"),
            "import": "from migrations.add_joint_flags_to_debt_asset import migrate as add_joint_flags_to_debt_asset",
            "run": "add_joint_flags_to_debt_asset()"
        },
        {
            "name": "add_session_settings_columns",
            "check": lambda: check_column_exists("session_settings", "id"),
            "import": "from migrations.add_session_settings_columns import run_migration as add_session_settings_columns",
            "run": "add_session_settings_columns()"
        },
        {
            "name": "add_role_based_session_settings",
            "check": lambda: check_column_exists("session_settings", "client_session_timeout_seconds"),
            "import": "from migrations.add_role_based_session_settings import upgrade as add_role_based_session_settings",
            "run": "add_role_based_session_settings()"
        }
    ]
    
    for migration in migrations:
        print(f"\n🔄 Checking {migration['name']}...")
        
        if migration['check']():
            print(f"✅ {migration['name']} already applied, skipping")
        else:
            print(f"🔄 Running {migration['name']}...")
            try:
                exec(migration['import'])
                exec(migration['run'])
                print(f"✅ {migration['name']} completed successfully")
            except Exception as e:
                print(f"❌ {migration['name']} failed: {e}")
                # Continue with other migrations
                continue
    
    print("\n✅ All migrations processed!")

if __name__ == "__main__":
    run_migrations_safe()
