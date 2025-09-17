#!/usr/bin/env python3
"""
Migration script to update HIGH priority cases to URGENT priority.
This script should be run after updating the CasePriority enum.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_db
from src.models.case import Case, CasePriority
from sqlalchemy.orm import Session

def update_high_priority_to_urgent():
    """Update all cases with HIGH priority to URGENT priority"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Find all cases with HIGH priority (stored as string in database)
        high_priority_cases = db.query(Case).filter(
            Case.priority == 'HIGH'
        ).all()
        
        print(f"Found {len(high_priority_cases)} cases with HIGH priority")
        
        # Update each case to URGENT priority
        for case in high_priority_cases:
            case.priority = CasePriority.URGENT
            print(f"Updated case {case.id} from HIGH to URGENT priority")
        
        # Commit the changes
        db.commit()
        print(f"Successfully updated {len(high_priority_cases)} cases to URGENT priority")
        
    except Exception as e:
        print(f"Error updating priorities: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    update_high_priority_to_urgent()
