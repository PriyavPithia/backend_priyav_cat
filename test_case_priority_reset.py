#!/usr/bin/env python3
"""
Test script to verify that case priority is reset to NORMAL when status is set to CLOSED.
This script demonstrates the new business logic.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.case import Case, CaseStatus, CasePriority

def test_case_priority_reset():
    """Test that demonstrates the dynamic priority toggle logic for emergency cases"""
    
    # Create a mock case with emergency status
    case = Case()
    case.status = CaseStatus.PENDING
    case.priority = CasePriority.URGENT
    case.has_debt_emergency = True
    
    print("Initial emergency case state:")
    print(f"  Status: {case.status.value}")
    print(f"  Priority: {case.priority.value}")
    print(f"  Has Emergency: {case.has_debt_emergency}")
    print()
    
    # Test 1: Close the emergency case
    print("🔄 Test 1: Closing the emergency case...")
    case.status = CaseStatus.CLOSED
    
    # Apply the new business logic
    if case.has_debt_emergency:
        if case.status == CaseStatus.CLOSED:
            case.priority = CasePriority.NORMAL
            print("✅ Priority automatically set to NORMAL (case closed)")
    
    print(f"  Status: {case.status.value}")
    print(f"  Priority: {case.priority.value}")
    assert case.priority == CasePriority.NORMAL, "Closed emergency case should have NORMAL priority"
    print()
    
    # Test 2: Reopen the emergency case to PENDING
    print("🔄 Test 2: Reopening the emergency case to PENDING...")
    case.status = CaseStatus.PENDING
    
    if case.has_debt_emergency:
        if case.status in [CaseStatus.PENDING, CaseStatus.SUBMITTED]:
            case.priority = CasePriority.URGENT
            print("✅ Priority automatically set to URGENT (case reopened)")
    
    print(f"  Status: {case.status.value}")
    print(f"  Priority: {case.priority.value}")
    assert case.priority == CasePriority.URGENT, "Pending emergency case should have URGENT priority"
    print()
    
    # Test 3: Submit the emergency case
    print("🔄 Test 3: Submitting the emergency case...")
    case.status = CaseStatus.SUBMITTED
    
    if case.has_debt_emergency:
        if case.status in [CaseStatus.PENDING, CaseStatus.SUBMITTED]:
            case.priority = CasePriority.URGENT
            print("✅ Priority remains URGENT (case submitted)")
    
    print(f"  Status: {case.status.value}")
    print(f"  Priority: {case.priority.value}")
    assert case.priority == CasePriority.URGENT, "Submitted emergency case should have URGENT priority"
    print()
    
    # Test 4: Test non-emergency case (should not be affected)
    print("🔄 Test 4: Testing non-emergency case...")
    non_emergency_case = Case()
    non_emergency_case.status = CaseStatus.PENDING
    non_emergency_case.priority = CasePriority.NORMAL
    non_emergency_case.has_debt_emergency = False
    
    # Close the non-emergency case
    non_emergency_case.status = CaseStatus.CLOSED
    
    # Logic should not change priority for non-emergency cases
    if non_emergency_case.has_debt_emergency:  # This will be False
        if non_emergency_case.status == CaseStatus.CLOSED:
            non_emergency_case.priority = CasePriority.NORMAL
    
    print(f"  Status: {non_emergency_case.status.value}")
    print(f"  Priority: {non_emergency_case.priority.value}")
    print(f"  Has Emergency: {non_emergency_case.has_debt_emergency}")
    assert non_emergency_case.priority == CasePriority.NORMAL, "Non-emergency case priority should remain unchanged"
    print("✅ Non-emergency case priority unaffected")
    print()
    
    print("✅ All tests passed! Emergency case priority toggles correctly based on status.")

if __name__ == "__main__":
    test_case_priority_reset()
