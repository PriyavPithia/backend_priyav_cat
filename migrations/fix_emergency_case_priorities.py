#!/usr/bin/env python3
"""
Migration script to fix priority for all emergency cases based on their current status.
This ensures all emergency cases have the correct priority:
- Emergency cases that are CLOSED → Priority should be NORMAL
- Emergency cases that are PENDING/SUBMITTED → Priority should be URGENT
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_db
from src.models.case import Case, CaseStatus, CasePriority
from sqlalchemy.orm import Session

def fix_emergency_case_priorities():
    """Fix priority for all emergency cases based on their status"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Find all emergency cases
        emergency_cases = db.query(Case).filter(
            Case.has_debt_emergency == True
        ).all()
        
        print(f"Found {len(emergency_cases)} emergency cases to check")
        
        if len(emergency_cases) == 0:
            print("✅ No emergency cases found")
            return
        
        fixed_cases = 0
        
        for case in emergency_cases:
            original_priority = case.priority.value if case.priority else 'None'
            expected_priority = None
            
            if case.status == CaseStatus.CLOSED:
                # Closed emergency cases should have NORMAL priority
                expected_priority = CasePriority.NORMAL
            elif case.status in [CaseStatus.PENDING, CaseStatus.SUBMITTED]:
                # Active emergency cases should have URGENT priority
                expected_priority = CasePriority.URGENT
            
            if expected_priority and case.priority != expected_priority:
                print(f"Fixing case {case.id}:")
                print(f"  Status: {case.status.value}")
                print(f"  Priority: {original_priority} → {expected_priority.value}")
                case.priority = expected_priority
                fixed_cases += 1
        
        if fixed_cases > 0:
            # Commit the changes
            db.commit()
            print(f"✅ Successfully fixed priority for {fixed_cases} emergency cases")
        else:
            print("✅ All emergency cases already have correct priorities")
        
        # Summary report
        print("\n📊 Final Summary:")
        closed_emergency_cases = db.query(Case).filter(
            Case.has_debt_emergency == True,
            Case.status == CaseStatus.CLOSED
        ).all()
        
        active_emergency_cases = db.query(Case).filter(
            Case.has_debt_emergency == True,
            Case.status.in_([CaseStatus.PENDING, CaseStatus.SUBMITTED])
        ).all()
        
        print(f"  Closed emergency cases: {len(closed_emergency_cases)}")
        for case in closed_emergency_cases:
            print(f"    Case {case.id}: Priority = {case.priority.value}")
        
        print(f"  Active emergency cases: {len(active_emergency_cases)}")
        for case in active_emergency_cases:
            print(f"    Case {case.id}: Status = {case.status.value}, Priority = {case.priority.value}")
        
    except Exception as e:
        print(f"❌ Error fixing emergency case priorities: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    print("🔄 Starting migration to fix emergency case priorities...")
    fix_emergency_case_priorities()
    print("✅ Migration completed!")
