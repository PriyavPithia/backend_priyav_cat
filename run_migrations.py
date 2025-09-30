#!/usr/bin/env python3
"""
Run all migrations in order
"""

from migrations.add_invitation_fields import migrate as add_invitation_fields
from migrations.add_last_step_column import migrate as add_last_step
from migrations.add_notifications_table import migrate as add_notifications
from migrations.add_office_admin_field import migrate as add_office_admin
from migrations.make_office_code_optional import migrate as make_office_code_optional
from migrations.fix_case_priority_enum import migrate as fix_case_priority_enum
from migrations.add_prefer_not_to_say_columns import migrate as add_prefer_not_to_say_columns
from migrations.fix_payment_frequency_enum import migrate as fix_payment_frequency_enum
from migrations.add_joint_flags_to_debt_asset import migrate as add_joint_flags_to_debt_asset

def run_migrations():
    """Run all migrations in order"""
    print("🚀 Running migrations...")
    
    # Run migrations in order
    add_invitation_fields()
    add_last_step()
    add_notifications()
    add_office_admin()
    make_office_code_optional()
    fix_case_priority_enum()
    add_prefer_not_to_say_columns()
    fix_payment_frequency_enum()
    add_joint_flags_to_debt_asset()
    
    print("✅ All migrations completed!")

if __name__ == "__main__":
    run_migrations()
