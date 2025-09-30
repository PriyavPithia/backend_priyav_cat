#!/usr/bin/env python3
"""
Run all migrations in order
"""

# Import all migrations
from migrations.add_default_office_field import migrate as add_default_office_field
from migrations.add_file_type_fields import run_migration as add_file_type_fields
from migrations.add_invitation_details import migrate as add_invitation_details
from migrations.add_invitation_fields import migrate as add_invitation_fields
from migrations.add_last_step_column import migrate as add_last_step
from migrations.add_missing_optional_fields import migrate as add_missing_optional_fields
from migrations.add_notifications_table import migrate as add_notifications
from migrations.add_office_admin_field import migrate as add_office_admin
from migrations.add_prefer_not_to_say_columns import migrate as add_prefer_not_to_say_columns
from migrations.add_property_postcode_field import run_migration as add_property_postcode_field
from migrations.add_user_contact_fields import migrate as add_user_contact_fields
from migrations.add_user_preferences_column import add_user_preferences_column
from migrations.add_was_converted_field import run_migration as add_was_converted_field
from migrations.add_joint_flags_to_debt_asset import migrate as add_joint_flags_to_debt_asset
from migrations.add_session_settings_columns import run_migration as add_session_settings_columns
from migrations.add_role_based_session_settings import upgrade as add_role_based_session_settings

def run_migrations():
    """Run all migrations in order"""
    print("🚀 Running migrations...")
    
    # Run migrations in order
    add_default_office_field()
    add_file_type_fields()
    add_invitation_details()
    add_invitation_fields()
    add_last_step()
    add_missing_optional_fields()
    add_notifications()
    add_office_admin()
    add_prefer_not_to_say_columns()
    add_property_postcode_field()
    add_user_contact_fields()
    add_user_preferences_column()
    add_was_converted_field()
    add_joint_flags_to_debt_asset()
    add_session_settings_columns()
    add_role_based_session_settings()
    
    print("✅ All migrations completed!")

if __name__ == "__main__":
    run_migrations()
