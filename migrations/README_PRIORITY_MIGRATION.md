# Priority System Migration: HIGH → URGENT

## Overview
This migration updates the case priority system from using "HIGH" priority to "URGENT" priority, and ensures that all emergency cases automatically receive URGENT priority.

## Changes Made

### 1. Backend Changes
- **CasePriority Enum**: Updated `backend/src/models/case.py` to use `URGENT = "URGENT"` instead of `HIGH = "HIGH"`
- **Automatic Emergency Priority**: Added logic in `backend/src/routes/cases.py` to automatically set cases to URGENT priority when `has_debt_emergency` is true
- **Error Messages**: Updated validation messages in `backend/src/routes/admin.py` to reflect new priority values

### 2. Frontend Changes
- **All Case Management Components**: Updated priority dropdowns and display logic to show "Urgent" instead of "High"
- **TypeScript Types**: Updated `frontend/src/types/global.d.ts` to use `URGENT = 'urgent'` instead of `HIGH = 'high'`

### 3. Database Migration
- **Migration Scripts**: Created two migration scripts to handle the transition:
  - `update_high_priority_to_urgent.py`: Updates existing HIGH priority cases to URGENT
  - `update_emergency_cases_to_urgent.py`: Updates emergency cases to have URGENT priority

## Migration Results

### Migration 1: HIGH → URGENT Priority
```bash
python migrations/update_high_priority_to_urgent.py
```
**Result**: Found 0 cases with HIGH priority (no existing HIGH priority cases to update)

### Migration 2: Emergency Cases → URGENT Priority
```bash
python migrations/update_emergency_cases_to_urgent.py
```
**Result**: 
- Found 1 emergency case that needed URGENT priority
- Updated case `22bf131e-900f-4701-9c7a-a0f8e969604a` from NORMAL to URGENT priority
- Successfully updated 1 emergency cases to URGENT priority

## New Priority System

| Priority | Display | Color | Description |
|----------|---------|-------|-------------|
| LOW | Low | Green | Low priority cases |
| NORMAL | Normal | Blue | Standard priority cases |
| URGENT | Urgent | Red | High priority cases (replaces HIGH) |

## Automatic Emergency Priority
- When a case is marked as having a debt emergency (`has_debt_emergency = true`), it automatically gets set to URGENT priority
- This ensures emergency cases are always visible and prioritized appropriately
- The logic is implemented in the emergency check endpoint (`/emergency-check`)

## Files Modified

### Backend
- `backend/src/models/case.py` - Updated CasePriority enum
- `backend/src/routes/cases.py` - Added automatic emergency priority logic
- `backend/src/routes/admin.py` - Updated error messages
- `backend/migrations/update_high_priority_to_urgent.py` - Migration script
- `backend/migrations/update_emergency_cases_to_urgent.py` - Emergency cases migration

### Frontend
- `frontend/src/components/CaseManagement.jsx`
- `frontend/src/components/features/cases/CaseManagement.jsx`
- `frontend/src/components/features/dashboard/AdviserCaseManagement.jsx`
- `frontend/src/components/features/cases/EditCaseModal.jsx`
- `frontend/src/components/ui/tableColumns.jsx`
- `frontend/src/types/global.d.ts`

## Verification
After running the migrations:
1. All emergency cases should now display as "Urgent" priority in the case management tables
2. New emergency cases will automatically get URGENT priority
3. The priority dropdowns show "Urgent" instead of "High"
4. All priority displays use the new terminology

## Rollback (if needed)
If rollback is required:
1. Revert the CasePriority enum to use `HIGH = "HIGH"`
2. Revert all frontend changes to use "High" instead of "Urgent"
3. Remove the automatic emergency priority logic
4. Run a migration to convert URGENT back to HIGH (if needed)

## Date of Migration
Migration completed on: $(date)
