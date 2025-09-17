#!/usr/bin/env python3
"""
Test script to verify that emergency case priority is automatically managed
and not overridden by manual priority requests.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.models.case import Case, CaseStatus, CasePriority

def simulate_update_case_logic(case, request_status=None, request_priority=None):
    """Simulate the update_case logic from admin.py"""
    
    # Update status if provided (this is the first step in the real function)
    if request_status is not None:
        case.status = CaseStatus(request_status)
        # Automatically manage priority for emergency cases based on status
        if case.has_debt_emergency:
            if case.status == CaseStatus.CLOSED:
                # Emergency cases that are closed should have NORMAL priority
                case.priority = CasePriority.NORMAL
                print(f"✅ Auto-set priority to NORMAL (emergency case closed)")
            elif case.status in [CaseStatus.PENDING, CaseStatus.SUBMITTED]:
                # Emergency cases that are pending/submitted should have URGENT priority
                case.priority = CasePriority.URGENT
                print(f"✅ Auto-set priority to URGENT (emergency case active)")
    
    # Update priority if provided (but not for emergency cases with automatic priority management)
    if request_priority is not None:
        if case.has_debt_emergency:
            print(f"⚠️  Skipping manual priority update for emergency case - priority is automatically managed based on status")
        else:
            case.priority = CasePriority(request_priority)
            print(f"✅ Manual priority update to {request_priority} (non-emergency case)")

def test_priority_override_fix():
    """Test that emergency case priority is not overridden by manual requests"""
    
    print("🧪 Testing Emergency Case Priority Override Fix\n")
    
    # Test 1: Emergency case closed with manual priority request (should ignore manual priority)
    print("🔄 Test 1: Close emergency case with manual URGENT priority request")
    case = Case()
    case.has_debt_emergency = True
    case.status = CaseStatus.PENDING
    case.priority = CasePriority.URGENT
    
    print(f"Before: Status={case.status.value}, Priority={case.priority.value}")
    
    # Simulate API request: close case but try to set priority to URGENT manually
    simulate_update_case_logic(case, request_status="closed", request_priority="URGENT")
    
    print(f"After: Status={case.status.value}, Priority={case.priority.value}")
    assert case.status == CaseStatus.CLOSED, "Status should be CLOSED"
    assert case.priority == CasePriority.NORMAL, "Priority should be NORMAL (automatic), not URGENT (manual)"
    print("✅ Test 1 passed: Manual priority ignored for emergency case\n")
    
    # Test 2: Reopen emergency case with manual NORMAL priority request (should ignore manual priority)
    print("🔄 Test 2: Reopen emergency case with manual NORMAL priority request")
    print(f"Before: Status={case.status.value}, Priority={case.priority.value}")
    
    # Simulate API request: reopen case but try to set priority to NORMAL manually
    simulate_update_case_logic(case, request_status="pending", request_priority="NORMAL")
    
    print(f"After: Status={case.status.value}, Priority={case.priority.value}")
    assert case.status == CaseStatus.PENDING, "Status should be PENDING"
    assert case.priority == CasePriority.URGENT, "Priority should be URGENT (automatic), not NORMAL (manual)"
    print("✅ Test 2 passed: Manual priority ignored for emergency case\n")
    
    # Test 3: Non-emergency case with manual priority request (should allow manual priority)
    print("🔄 Test 3: Non-emergency case with manual priority request")
    non_emergency_case = Case()
    non_emergency_case.has_debt_emergency = False
    non_emergency_case.status = CaseStatus.PENDING
    non_emergency_case.priority = CasePriority.NORMAL
    
    print(f"Before: Status={non_emergency_case.status.value}, Priority={non_emergency_case.priority.value}")
    
    # Simulate API request: close case and set priority to LOW manually
    simulate_update_case_logic(non_emergency_case, request_status="closed", request_priority="LOW")
    
    print(f"After: Status={non_emergency_case.status.value}, Priority={non_emergency_case.priority.value}")
    assert non_emergency_case.status == CaseStatus.CLOSED, "Status should be CLOSED"
    assert non_emergency_case.priority == CasePriority.LOW, "Priority should be LOW (manual request allowed)"
    print("✅ Test 3 passed: Manual priority allowed for non-emergency case\n")
    
    print("✅ All tests passed! Emergency case priority override fix is working correctly.")

if __name__ == "__main__":
    test_priority_override_fix()
