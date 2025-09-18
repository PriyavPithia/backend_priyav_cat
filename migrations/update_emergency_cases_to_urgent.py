#!/usr/bin/env python3
"""
Migration script to update emergency cases to URGENT priority.
This ensures all cases with has_debt_emergency=True have URGENT priority.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_db
from src.models.case import Case, CasePriority
from sqlalchemy.orm import Session

def update_emergency_cases_to_urgent():
    """Update all emergency cases to have URGENT priority"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Find all cases with emergency status but not URGENT priority
        emergency_cases = db.query(Case).filter(
            Case.has_debt_emergency == True,
            Case.priority != CasePriority.URGENT
        ).all()
        
        print(f"Found {len(emergency_cases)} emergency cases that need URGENT priority")
        
        # Update each emergency case to URGENT priority
        for case in emergency_cases:
            old_priority = case.priority.value if case.priority else 'None'
            case.priority = CasePriority.URGENT
            print(f"Updated case {case.id} from {old_priority} to URGENT priority (emergency case)")
        
        # Commit the changes
        db.commit()
        print(f"Successfully updated {len(emergency_cases)} emergency cases to URGENT priority")
        
        # Also check for any remaining HIGH priority cases (just in case)
        high_priority_cases = db.query(Case).filter(
            Case.priority == 'HIGH'
        ).all()
        
        if high_priority_cases:
            print(f"Found {len(high_priority_cases)} cases with HIGH priority, updating to URGENT")
            for case in high_priority_cases:
                case.priority = CasePriority.URGENT
                print(f"Updated case {case.id} from HIGH to URGENT priority")
            db.commit()
            print(f"Successfully updated {len(high_priority_cases)} HIGH priority cases to URGENT")
        
    except Exception as e:
        print(f"Error updating priorities: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_emergency_cases_to_urgent()
