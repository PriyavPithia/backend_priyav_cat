#!/usr/bin/env python3
"""
Migration script to reset priority to NORMAL for all closed cases.
This fixes cases that were closed before the automatic priority reset logic was implemented.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_db
from src.models.case import Case, CaseStatus, CasePriority
from sqlalchemy.orm import Session

def reset_closed_case_priorities():
    """Reset priority to NORMAL for all closed cases"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Find all closed cases that still have URGENT priority
        closed_urgent_cases = db.query(Case).filter(
            Case.status == CaseStatus.CLOSED,
            Case.priority == CasePriority.URGENT
        ).all()
        
        print(f"Found {len(closed_urgent_cases)} closed cases with URGENT priority")
        
        if len(closed_urgent_cases) == 0:
            print("✅ No closed cases need priority reset")
            return
        
        # Update each closed case to NORMAL priority
        for case in closed_urgent_cases:
            print(f"Resetting case {case.id} priority from URGENT to NORMAL")
            case.priority = CasePriority.NORMAL
        
        # Commit the changes
        db.commit()
        print(f"✅ Successfully reset priority to NORMAL for {len(closed_urgent_cases)} closed cases")
        
        # Verify the changes
        remaining_urgent_closed = db.query(Case).filter(
            Case.status == CaseStatus.CLOSED,
            Case.priority == CasePriority.URGENT
        ).count()
        
        if remaining_urgent_closed == 0:
            print("✅ Verification passed: No closed cases have URGENT priority")
        else:
            print(f"⚠️  Warning: {remaining_urgent_closed} closed cases still have URGENT priority")
        
    except Exception as e:
        print(f"❌ Error updating closed case priorities: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Starting migration to reset closed case priorities...")
    reset_closed_case_priorities()
    print("✅ Migration completed!")
