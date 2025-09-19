from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, text
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime, timedelta
import secrets
import string
import json
import os
import logging

from ..config.database import get_db
from ..models import User, Case, Office, UserRole, UserStatus, CaseStatus, CasePriority, AuditLog, Notification, NotificationType, Debt, Asset, Income, Expenditure, FileUpload, ClientDetails
from .auth import get_current_user, TokenResponse, UserResponse
from ..utils.auth import hash_password, get_lockout_remaining_time, get_client_ip_address, generate_reset_token
from ..utils.ses_email_service import send_password_reset_email, send_invitation_email

router = APIRouter()
logger = logging.getLogger(__name__)

class AdminCaseResponse(BaseModel):
    id: str
    client_id: str
    client_name: str
    client_email: str
    client_phone: Optional[str]
    ca_client_number: str
    office_id: str
    office_name: str
    office_code: Optional[str]
    assigned_adviser_id: Optional[str]
    assigned_adviser_name: Optional[str]
    status: str
    priority: str
    completion_percentage: float
    has_debt_emergency: bool
    total_debt: Optional[str]
    total_assets: Optional[str]
    total_income: Optional[str]
    total_expenditure: Optional[str]
    created_at: datetime
    updated_at: datetime
    last_activity: Optional[datetime]
    notes: Optional[str]

class DetailedDebtResponse(BaseModel):
    id: str
    debt_type: str
    debt_type_display: str
    amount_owed: Optional[str]
    creditor_name: Optional[str]
    additional_info: Optional[str]
    other_parent_name: Optional[str]
    benefit_type: Optional[str]
    fine_reason: Optional[str]
    is_priority_debt: bool
    created_at: datetime

class DetailedAssetResponse(BaseModel):
    id: str
    asset_type: str
    asset_type_display: str
    description: Optional[str]
    estimated_value: Optional[str]
    property_address: Optional[str]
    property_postcode: Optional[str]
    vehicle_registration: Optional[str]
    savings_institution: Optional[str]
    additional_info: Optional[str]
    created_at: datetime

class DetailedIncomeResponse(BaseModel):
    id: str
    income_type: str
    income_type_display: str
    amount: Optional[str]
    frequency: Optional[str]
    employer_name: Optional[str]
    source_description: Optional[str]
    is_regular_amount: Optional[str]
    additional_info: Optional[str]
    created_at: datetime

class DetailedExpenditureResponse(BaseModel):
    id: str
    expenditure_type: str
    expenditure_type_display: str
    amount: Optional[str]
    frequency: Optional[str]
    provider_name: Optional[str]
    additional_info: Optional[str]
    created_at: datetime

class FileUploadResponse(BaseModel):
    id: str
    original_filename: str
    stored_filename: Optional[str]
    display_filename: Optional[str]
    file_size: int
    file_size_formatted: str
    file_extension: str
    category: str
    description: Optional[str]
    is_image: bool
    is_document: bool
    created_at: datetime
    was_converted: Optional[bool] = False
    uploaded_by_id: str

class DetailedCaseResponse(BaseModel):
    case: AdminCaseResponse
    debts: List[DetailedDebtResponse]
    assets: List[DetailedAssetResponse]
    income: List[DetailedIncomeResponse]
    expenditure: List[DetailedExpenditureResponse]
    files: List[FileUploadResponse]

class InviteUserRequest(BaseModel):
    email: EmailStr
    role: str = "client"
    ca_client_number: str = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    
    # Additional client details for prefilling (only used when role is "client")
    title: Optional[str] = None
    home_address: Optional[str] = None
    postcode: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    home_phone: Optional[str] = None
    mobile_phone: Optional[str] = None

class CreateUserRequest(BaseModel):
    # Basic user info
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: str = "client"
    office_id: Optional[str] = None
    ca_client_number: Optional[str] = None
    phone: Optional[str] = None
    is_office_admin: bool = False
    
    # Essential client details (only used when role is "client")
    title: Optional[str] = None
    home_address: Optional[str] = None
    postcode: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None
    home_phone: Optional[str] = None
    mobile_phone: Optional[str] = None

class UpdateUserRequest(BaseModel):
    email: EmailStr
    first_name: str = None
    last_name: str = None
    role: str = None
    office_id: str = None
    phone: str = None
    is_office_admin: bool = None
    
    # Additional contact details (for clients)
    title: Optional[str] = None
    home_phone: Optional[str] = None
    home_address: Optional[str] = None
    postcode: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None

class InviteAdviserRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    office_id: str
    is_office_admin: bool = False

class InviteLinkResponse(BaseModel):
    invite_url: str
    expires_at: datetime
    email: str

class AcceptInvitationRequest(BaseModel):
    password: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    phone: Optional[str] = None

def require_admin_access(current_user: User):
    """Require admin access (adviser or superuser)"""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )

def require_superuser_access(current_user: User):
    """Require superuser access"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Superuser access required"
        )

def generate_invitation_token():
    """Generate a secure invitation token"""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(32))

@router.get("/cases", response_model=List[AdminCaseResponse])
async def list_cases(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List cases visible to the current user.

    - Superusers: all cases
    - Advisers: all cases in their office (assigned and unassigned)
    - Office admins: treated as advisers in their office
    """

    # Allow superusers and advisers (including office admins). Block clients.
    if not (current_user.is_superuser or current_user.role == UserRole.ADVISER):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # For superusers, show all cases. For advisers, show all cases in their office
    if current_user.is_superuser:
        cases = db.query(Case).all()
    else:
        # Advisers can see all cases in their office (assigned and unassigned)
        cases = db.query(Case).filter(Case.office_id == current_user.office_id).all()
    
    result = []
    for case in cases:
        # Skip malformed cases without a client
        client = getattr(case, 'client', None)
        if client is None:
            continue

        # Get assigned adviser info (optional)
        assigned_adviser = None
        if getattr(case, 'assigned_adviser_id', None):
            assigned_adviser = db.query(User).filter(User.id == case.assigned_adviser_id).first()

        # Get office info (optional)
        office = None
        if getattr(case, 'office_id', None):
            office = db.query(Office).filter(Office.id == case.office_id).first()

        # Safely get priority value with fallback
        try:
            priority_value = case.priority.value if getattr(case, 'priority', None) else 'NORMAL'
        except (AttributeError, ValueError):
            priority_value = 'NORMAL'  # Fallback if enum value is invalid
        
        result.append(AdminCaseResponse(
            id=str(case.id),
            client_id=str(client.id),
            client_name=f"{(client.first_name or '').strip()} {(client.last_name or '').strip()}".strip() or client.email,
            client_email=client.email,
            client_phone=getattr(client, 'phone', None),
            ca_client_number=getattr(client, 'ca_client_number', '') or '',
            office_id=str(case.office_id) if getattr(case, 'office_id', None) else '',
            office_name=office.name if office else "Unknown Office",
            office_code=office.code if office else None,
            assigned_adviser_id=str(case.assigned_adviser_id) if getattr(case, 'assigned_adviser_id', None) else None,
            assigned_adviser_name=(f"{(assigned_adviser.first_name or '').strip()} {(assigned_adviser.last_name or '').strip()}".strip()
                                   if assigned_adviser else None),
            status=case.status.value if getattr(case, 'status', None) else 'pending',
            priority=priority_value,
            completion_percentage=getattr(case, 'completion_percentage', 0.0) or 0.0,
            has_debt_emergency=getattr(case, 'has_debt_emergency', False) or False,
            total_debt=getattr(case, 'total_priority_debt', None),
            total_assets=getattr(case, 'total_assets_value', None),
            total_income=getattr(case, 'total_monthly_income', None),
            total_expenditure=getattr(case, 'total_monthly_expenditure', None),
            created_at=getattr(case, 'created_at', datetime.utcnow()),
            updated_at=getattr(case, 'updated_at', getattr(case, 'created_at', datetime.utcnow())),
            last_activity=getattr(case, 'updated_at', None),
            notes=getattr(case, 'additional_notes', None)
        ))
    
    return result



@router.get("/case/{case_id}", response_model=DetailedCaseResponse)
async def get_case_details(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed case information including all captured data"""
    
    try:
        require_admin_access(current_user)
        
        # For superusers, allow access to any case. For advisers, enforce visibility rules
        if current_user.is_superuser:
            case = db.query(Case).filter(Case.id == case_id).first()
        else:
            case = db.query(Case).filter(
                Case.id == case_id,
                or_(
                    and_(Case.assigned_adviser_id == None, Case.office_id == current_user.office_id),
                    Case.assigned_adviser_id == current_user.id
                )
            ).first()
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accessing case: {str(e)}"
        )
    
    try:
        # Get client info
        client = case.client
        if not client:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Client not found for this case"
            )
        
        # Get assigned adviser info
        assigned_adviser = None
        if case.assigned_adviser_id:
            try:
                assigned_adviser = db.query(User).filter(User.id == case.assigned_adviser_id).first()
            except Exception as e:
                print(f"Warning: Could not fetch assigned adviser {case.assigned_adviser_id}: {e}")
                assigned_adviser = None
        
        # Get office info
        try:
            office = case.office
        except Exception as e:
            print(f"Warning: Could not fetch office for case {case.id}: {e}")
            office = None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error accessing case relationships: {str(e)}"
        )
    
    try:
        # Safely get priority value with fallback
        try:
            priority_value = case.priority.value if getattr(case, 'priority', None) else 'NORMAL'
        except (AttributeError, ValueError):
            priority_value = 'NORMAL'  # Fallback if enum value is invalid

        # Build case response
        case_response = AdminCaseResponse(
            id=str(case.id),
            client_id=str(client.id),
            client_name=f"{(client.first_name or '').strip()} {(client.last_name or '').strip()}".strip() or client.email,
            client_email=client.email,
            client_phone=getattr(client, 'phone', None),
            ca_client_number=getattr(client, 'ca_client_number', '') or '',
            office_id=str(case.office_id) if case.office_id else '',
            office_name=office.name if office else "Unknown Office",
            office_code=office.code if office else None,
            assigned_adviser_id=str(case.assigned_adviser_id) if case.assigned_adviser_id else None,
            assigned_adviser_name=(f"{(assigned_adviser.first_name or '').strip()} {(assigned_adviser.last_name or '').strip()}".strip()
                                   if assigned_adviser else None),
            status=case.status.value if case.status else 'pending',
            priority=priority_value,
            completion_percentage=getattr(case, 'completion_percentage', 0.0) or 0.0,
            has_debt_emergency=getattr(case, 'has_debt_emergency', False) or False,
            total_debt=getattr(case, 'total_priority_debt', None),
            total_assets=getattr(case, 'total_assets_value', None),
            total_income=getattr(case, 'total_monthly_income', None),
            total_expenditure=getattr(case, 'total_monthly_expenditure', None),
            created_at=getattr(case, 'created_at', datetime.utcnow()),
            updated_at=getattr(case, 'updated_at', getattr(case, 'created_at', datetime.utcnow())),
            last_activity=getattr(case, 'updated_at', None),
            notes=getattr(case, 'additional_notes', None)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error building case response: {str(e)}"
        )
    
    # Get detailed debts
    debts = db.query(Debt).filter(Debt.case_id == case.id).all()
    debt_responses = []
    for debt in debts:
        debt_responses.append(DetailedDebtResponse(
            id=str(debt.id),
            debt_type=debt.debt_type.value,
            debt_type_display=debt.debt_type_display,
            amount_owed=debt.amount_owed,
            creditor_name=debt.creditor_name,
            additional_info=debt.additional_info,
            other_parent_name=debt.other_parent_name,
            benefit_type=debt.benefit_type,
            fine_reason=debt.fine_reason,
            is_priority_debt=debt.is_priority_debt,
            created_at=debt.created_at
        ))
    
    # Get detailed assets
    assets = db.query(Asset).filter(Asset.case_id == case.id).all()
    asset_responses = []
    for asset in assets:
        asset_responses.append(DetailedAssetResponse(
            id=str(asset.id),
            asset_type=asset.asset_type.value,
            asset_type_display=asset.asset_type_display,
            description=asset.description,
            estimated_value=asset.estimated_value,
            property_address=asset.property_address,
            property_postcode=asset.property_postcode,
            vehicle_registration=asset.vehicle_registration,
            savings_institution=asset.savings_institution,
            additional_info=asset.additional_info,
            created_at=asset.created_at
        ))
    
    # Get detailed income
    try:
        incomes = db.query(Income).filter(Income.case_id == case.id).all()
        income_responses = []
        for income in incomes:
            try:
                # Handle frequency enum safely
                frequency_value = None
                if income.frequency:
                    try:
                        frequency_value = income.frequency.value
                    except (AttributeError, LookupError) as e:
                        print(f"Warning: Invalid frequency value for income {income.id}: {e}")
                        frequency_value = str(income.frequency) if income.frequency else None
                
                income_responses.append(DetailedIncomeResponse(
                    id=str(income.id),
                    income_type=income.income_type.value,
                    income_type_display=income.income_type_display,
                    amount=income.amount,
                    frequency=frequency_value,
                    employer_name=income.employer_name,
                    source_description=income.source_description,
                    is_regular_amount=income.is_regular_amount,
                    additional_info=income.additional_info,
                    created_at=income.created_at
                ))
            except Exception as e:
                print(f"Warning: Error processing income {income.id}: {e}")
                # Skip this income record if it has invalid data
                continue
    except Exception as e:
        print(f"Warning: Error querying incomes for case {case.id}: {e}")
        income_responses = []
    
    # Get detailed expenditure
    try:
        expenditures = db.query(Expenditure).filter(Expenditure.case_id == case.id).all()
        expenditure_responses = []
        for expenditure in expenditures:
            try:
                # Handle frequency enum safely
                frequency_value = None
                if expenditure.frequency:
                    try:
                        frequency_value = expenditure.frequency.value
                    except (AttributeError, LookupError) as e:
                        print(f"Warning: Invalid frequency value for expenditure {expenditure.id}: {e}")
                        frequency_value = str(expenditure.frequency) if expenditure.frequency else None
                
                expenditure_responses.append(DetailedExpenditureResponse(
                    id=str(expenditure.id),
                    expenditure_type=expenditure.expenditure_type.value,
                    expenditure_type_display=expenditure.expenditure_type_display,
                    amount=expenditure.amount,
                    frequency=frequency_value,
                    provider_name=expenditure.provider_name,
                    additional_info=expenditure.additional_info,
                    created_at=expenditure.created_at
                ))
            except Exception as e:
                print(f"Warning: Error processing expenditure {expenditure.id}: {e}")
                # Skip this expenditure record if it has invalid data
                continue
    except Exception as e:
        print(f"Warning: Error querying expenditures for case {case.id}: {e}")
        expenditure_responses = []
    
    # Get detailed files
    files = db.query(FileUpload).filter(FileUpload.case_id == case.id).all()
    file_responses = []
    for file_upload in files:
        # Generate display filename with proper logic
        display_filename = file_upload.original_filename
        if file_upload.was_converted and file_upload.original_filename.lower().endswith('.heic'):
            # Show converted extension for HEIC files, but keep the client prefix from stored_filename
            if file_upload.stored_filename:
                # Use the stored filename which already includes client prefix, just change the extension
                base_name = os.path.splitext(file_upload.stored_filename)[0]
                converted_ext = os.path.splitext(file_upload.stored_filename)[1] if file_upload.stored_filename else '.jpg'
                display_filename = f"{base_name}{converted_ext}"
            else:
                # Fallback to original filename if no stored filename
                base_name = os.path.splitext(file_upload.original_filename)[0]
                display_filename = f"{base_name}.jpg"
        elif file_upload.stored_filename:
            # Use stored filename which includes client prefix
            display_filename = file_upload.stored_filename
        
        file_responses.append(FileUploadResponse(
            id=str(file_upload.id),
            original_filename=file_upload.original_filename,
            stored_filename=file_upload.stored_filename,
            display_filename=display_filename,
            file_size=file_upload.file_size,
            file_size_formatted=file_upload.file_size_formatted,
            file_extension=file_upload.file_extension,
            category=file_upload.category.value,
            description=file_upload.description,
            is_image=file_upload.is_image,
            is_document=file_upload.is_document,
            created_at=file_upload.created_at,
            was_converted=file_upload.was_converted if hasattr(file_upload, 'was_converted') else False,
            uploaded_by_id=str(file_upload.uploaded_by_id)
        ))
    
    try:
        return DetailedCaseResponse(
            case=case_response,
            debts=debt_responses,
            assets=asset_responses,
            income=income_responses,
            expenditure=expenditure_responses,
            files=file_responses
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error building final response: {str(e)}"
        )

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    user_status: str = Query(...)
):
    """Update user status (suspend/activate) - superusers and office admins can do this"""
    
    require_admin_access(current_user)
    
    # Only superusers or office admins can update user status
    if not current_user.is_superuser and not current_user.is_office_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only office administrators can update user status"
        )
    
    # Validate status
    if user_status not in ['active', 'suspended']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Status must be 'active' or 'suspended'"
        )
    
    # Get user to update
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Office admins can only manage users in their own office
    if not current_user.is_superuser and user.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage users in your own office"
        )
    
    # Cannot suspend yourself
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot suspend your own account"
        )
    
    # Store old status for audit log
    old_status = user.status.value
    
    # Update user status
    user.status = UserStatus(user_status)
    db.commit()
    db.refresh(user)
    
    # Create audit log for status change
    action = "account_suspended" if user_status == "suspended" else "account_activated"
    description = f"Account {user_status} by admin {current_user.email} for user {user.email}"
    
    AuditLog.log_action(
        db,
        action=action,
        user_id=user.id,
        office_id=user.office_id,
        description=description,
        ip_address=get_client_ip_address(request),
        success=True
    )
    db.commit()
    
    return {
        "message": f"User {user.email} status updated to {user_status}",
        "user_id": user.id,
        "status": user.status.value
    }

@router.put("/users/{user_id}/office-admin")
async def update_office_admin_status(
    user_id: str,
    is_office_admin: bool,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user's office admin status - superusers and office admins can do this"""
    
    require_admin_access(current_user)
    
    # Only superusers or office admins can update office admin status
    if not current_user.is_superuser and not current_user.is_office_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only office administrators can update office admin status"
        )
    
    # Get user to update
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Can only set office admin for advisers
    if user.role != UserRole.ADVISER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Office admin rights can only be granted to advisers"
        )
    
    # Superusers can manage any office admin, but office admins can only manage their own office
    if not current_user.is_superuser and user.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only manage users in your own office"
        )
    
    # Update office admin status
    user.is_office_admin = is_office_admin
    db.commit()
    db.refresh(user)
    
    return {
        "message": f"User {user.email} office admin status updated to {is_office_admin}",
        "user_id": user.id,
        "is_office_admin": user.is_office_admin
    }

@router.put("/users/{user_id}")
async def update_user(
    user_id: str,
    request: UpdateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user details - only superusers or office admins can do this"""
    
    require_admin_access(current_user)
    
    # Get user to update
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check permissions
    if current_user.is_superuser:
        # Superusers can update any user
        pass
    elif current_user.is_office_admin:
        # Office admins can only update users in their own office
        if user.office_id != current_user.office_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only update users in your own office"
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only office administrators can update users"
        )
    
    # Update user fields
    if request.email is not None:
        # Check if email is already taken by another user
        existing_user = db.query(User).filter(
            User.email == request.email,
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = request.email
    
    if request.first_name is not None:
        user.first_name = request.first_name
    if request.last_name is not None:
        user.last_name = request.last_name
    if request.phone is not None:
        user.phone = request.phone
    
    # Role and office changes require superuser permissions
    if request.role is not None and current_user.is_superuser:
        user.role = UserRole(request.role)
    
    if request.office_id is not None and current_user.is_superuser:
        # Verify office exists
        office = db.query(Office).filter(Office.id == request.office_id).first()
        if not office:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Office not found"
            )
        
        # Update user office
        user.office_id = request.office_id
        
        # If this is a client, also update their case office to maintain consistency
        if user.role == UserRole.CLIENT:
            case = db.query(Case).filter(Case.client_id == user.id).first()
            if case:
                case.office_id = request.office_id
                print(f"Updated case {case.id} office from {case.office_id} to {request.office_id}")
            else:
                print(f"Warning: No case found for client {user.email}")
    
    # Office admin rights can only be managed by superusers
    if request.is_office_admin is not None and current_user.is_superuser:
        if user.role != UserRole.ADVISER:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Office admin rights can only be granted to advisers"
            )
        user.is_office_admin = request.is_office_admin
    
    # Handle additional contact details for users (typically clients)
    print(f"🔍 Received update request for user {user.email}")
    print(f"🔍 Contact details in request: title='{request.title}', home_phone='{request.home_phone}', home_address='{request.home_address}', postcode='{request.postcode}', date_of_birth='{request.date_of_birth}', gender='{request.gender}'")
    
    contact_fields_updated = False
    if request.title is not None:
        user.title = request.title
        contact_fields_updated = True
        # Set title
    if request.home_phone is not None:
        user.home_phone = request.home_phone  
        contact_fields_updated = True
        # Set home_phone
    if request.home_address is not None:
        user.home_address = request.home_address
        contact_fields_updated = True
        # Set home_address
    if request.postcode is not None:
        user.postcode = request.postcode
        contact_fields_updated = True
        # Set postcode
    if request.date_of_birth is not None:
        user.date_of_birth = request.date_of_birth
        contact_fields_updated = True
        # Set date_of_birth
    if request.gender is not None:
        user.gender = request.gender
        contact_fields_updated = True
        # Set gender
    
    if contact_fields_updated:
        # Updated contact details
        pass
    else:
        # No contact details were updated
        pass
    
    db.commit()
    db.refresh(user)
    
    # Verify the data was saved
    print(f"🔍 Verification - User data after save:")
    print(f"  Title: '{user.title}'")
    print(f"  Home Phone: '{user.home_phone}'")
    print(f"  Home Address: '{user.home_address}'")
    print(f"  Postcode: '{user.postcode}'")
    print(f"  Date of Birth: '{user.date_of_birth}'")
    print(f"  Gender: '{user.gender}'")
    
    return {
        "message": f"User {user.email} updated successfully",
        "user_id": user.id
    }

@router.get("/users/{user_id}/cases")
async def get_user_cases(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get cases associated with a user (superuser only)"""
    
    require_superuser_access(current_user)
    
    # Find the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Get client cases
    client_cases = db.query(Case).filter(Case.client_id == user_id).all()
    client_cases_data = [
        {
            "id": case.id,
            "status": case.status.value,
            "priority": case.priority.value,
            "created_at": case.created_at.isoformat() if case.created_at else None
        }
        for case in client_cases
    ]
    
    # Get adviser cases
    adviser_cases = db.query(Case).filter(Case.assigned_adviser_id == user_id).all()
    adviser_cases_data = [
        {
            "id": case.id,
            "status": case.status.value,
            "priority": case.priority.value,
            "created_at": case.created_at.isoformat() if case.created_at else None
        }
        for case in adviser_cases
    ]
    
    return {
        "client_cases": client_cases_data,
        "adviser_cases": adviser_cases_data
    }

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a user from the system (superuser or adviser deleting clients in their office)"""
    
    # Require authenticated admin/adviser access
    require_admin_access(current_user)
    
    # Prevent self-deletion
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account"
        )
    
    # Find the user to delete
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Permission checks
    if current_user.is_superuser:
        pass
    else:
        # Allow office admins and advisers to delete ONLY clients in their own office
        if user.role != UserRole.CLIENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete client users"
            )
        if user.office_id != current_user.office_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete users in your own office"
            )
    
    # Check if user has any associated cases as client
    client_case_count = db.query(Case).filter(Case.client_id == user_id).count()
    client_cases = db.query(Case).filter(Case.client_id == user_id).all() if client_case_count > 0 else []
    
    # Check if user has any assigned cases as adviser
    adviser_case_count = db.query(Case).filter(Case.assigned_adviser_id == user_id).count()
    adviser_cases = db.query(Case).filter(Case.assigned_adviser_id == user_id).all() if adviser_case_count > 0 else []
    
    # For non-superusers, prevent deletion if user has cases
    if not current_user.is_superuser:
        if client_case_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete user with {client_case_count} associated cases as client. Please transfer or delete cases first."
            )
        
        if adviser_case_count > 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot delete user with {adviser_case_count} assigned cases as adviser. Please reassign cases first."
            )
    
    # For superusers, allow deletion but return warning information
    warning_info = {}
    if client_case_count > 0:
        warning_info["client_cases"] = {
            "count": client_case_count,
            "cases": [
                {
                    "id": case.id,
                    "status": case.status.value,
                    "priority": case.priority.value,
                    "created_at": case.created_at.isoformat() if case.created_at else None
                }
                for case in client_cases
            ]
        }
    
    if adviser_case_count > 0:
        warning_info["adviser_cases"] = {
            "count": adviser_case_count,
            "cases": [
                {
                    "id": case.id,
                    "status": case.status.value,
                    "priority": case.priority.value,
                    "created_at": case.created_at.isoformat() if case.created_at else None
                }
                for case in adviser_cases
            ]
        }
    
    # Check if user has invited other users (and nullify the reference)
    invited_users = db.query(User).filter(User.invited_by_id == user_id).all()
    if invited_users:
        # Nullify the invited_by_id reference for all users they invited
        for invited_user in invited_users:
            invited_user.invited_by_id = None
        db.commit()
    
    # The related records with cascade="all, delete-orphan" will be automatically deleted:
    # - notifications (handled by cascade)
    # - client_details (handled by relationship)
    # - audit_logs will remain but user_id will be set to NULL as it's nullable
    
    # Store email for response
    user_email = user.email
    
    # Delete the user
    try:
        # For superusers, delete associated cases first to avoid foreign key constraint violations
        if current_user.is_superuser:
            from ..utils.file_utils import delete_case_files
            
            # Delete client cases first (with file cleanup)
            if client_case_count > 0:
                client_cases = db.query(Case).filter(Case.client_id == user_id).all()
                for case in client_cases:
                    try:
                        file_cleanup_result = await delete_case_files(case.id, db)
                        print(f"🔍 Cleaned up {file_cleanup_result.get('files_deleted', 0)} files for case {case.id}")
                    except Exception as file_error:
                        print(f"⚠️ File cleanup failed for case {case.id}: {file_error}")
                        # Continue with deletion even if file cleanup fails
                
                db.query(Case).filter(Case.client_id == user_id).delete()
                print(f"🔍 Deleted {client_case_count} client case(s) for user {user_id}")
            
            # Delete adviser cases (with file cleanup)
            if adviser_case_count > 0:
                adviser_cases = db.query(Case).filter(Case.assigned_adviser_id == user_id).all()
                for case in adviser_cases:
                    try:
                        file_cleanup_result = await delete_case_files(case.id, db)
                        print(f"🔍 Cleaned up {file_cleanup_result.get('files_deleted', 0)} files for case {case.id}")
                    except Exception as file_error:
                        print(f"⚠️ File cleanup failed for case {case.id}: {file_error}")
                        # Continue with deletion even if file cleanup fails
                
                db.query(Case).filter(Case.assigned_adviser_id == user_id).delete()
                print(f"🔍 Deleted {adviser_case_count} adviser case(s) for user {user_id}")
        
        # Handle any potential enum validation issues in ClientDetails by using raw SQL
        # This avoids SQLAlchemy's enum validation during deletion
        try:
            result = db.execute(text("DELETE FROM client_details WHERE user_id = :user_id"), {"user_id": user_id})
            if result.rowcount > 0:
                print(f"🔍 Deleted {result.rowcount} client_details record(s) for user {user_id}")
        except Exception as client_details_error:
            print(f"⚠️ Client details deletion failed: {client_details_error}")
            # Continue with user deletion even if client details deletion fails
        
        # Delete the user
        db.delete(user)
        
        # Create audit log for the deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            office_id=current_user.office_id,  # Add the required office_id
            action="user_deleted",
            resource_type="user",
            resource_id=user_id,
            details=f"Deleted user {user_email}"
        )
        db.add(audit_log)
        
        # Single commit for all operations
        db.commit()
        
        response_data = {
            "message": f"User {user_email} deleted successfully",
            "user_id": user_id
        }
        
        # Add warning information if user had active cases
        if warning_info:
            response_data["warning"] = warning_info
            response_data["message"] += f" (Warning: User had {client_case_count + adviser_case_count} active cases that were also deleted)"
        
        return response_data
    except Exception as e:
        db.rollback()
        # Error deleting user
        
        # Handle specific enum validation errors
        if "is not among the defined enum values" in str(e):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Cannot delete user due to invalid data in client details. Please contact administrator to fix data integrity issues."
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete user: {str(e)}"
            )

@router.post("/create-user")
async def create_user(
    request: CreateUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new user in the system"""
    
    require_admin_access(current_user)
    
    # Only superusers, office admins, or advisers can create users
    # Advisers can only create client users in their own office
    if not current_user.is_superuser and not current_user.is_office_admin and not current_user.is_adviser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators and advisers can create users"
        )
    
    # Regular advisers can only create clients
    if current_user.is_adviser and not current_user.is_office_admin and request.role != "client":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Advisers can only create client users"
        )
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Determine office_id based on user role
    office_id = request.office_id
    if not office_id:
        if current_user.is_superuser:
            # For superusers, use the default office if no office specified
            default_office = db.query(Office).filter(Office.is_default == True, Office.is_active == True).first()
            if default_office:
                office_id = default_office.id
            else:
                # Fall back to first active office
                first_office = db.query(Office).filter(Office.is_active == True).first()
                if first_office:
                    office_id = first_office.id
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="No active office available"
                    )
        else:
            # Administrators can only create users in their own office
            office_id = current_user.office_id
    
    # Validate office access
    if not current_user.is_superuser and office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create users in your own office"
        )
    
    # Auto-generate client number for client users
    ca_client_number = None
    if request.role == "client":
        if request.ca_client_number:
            # If a client number is provided, use it (for manual assignment)
            ca_client_number = request.ca_client_number
        else:
            # Auto-generate client number
            from .auth import generate_next_client_number
            ca_client_number = generate_next_client_number(db)
    
    # Create new user
    new_user = User(
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        role=UserRole(request.role),
        office_id=office_id,
        ca_client_number=ca_client_number,
        phone=request.phone,
        is_office_admin=request.is_office_admin,
        status=UserStatus.ACTIVE,
        password_hash=hash_password("TemporaryPassword123!"),  # TODO: Send password reset email
        # Contact details - save directly to User model
        title=request.title,
        home_phone=request.home_phone,
        mobile_phone=request.mobile_phone,
        home_address=request.home_address,
        postcode=request.postcode,
        date_of_birth=request.date_of_birth,
        gender=request.gender
    )
    
    # Debug: Log the contact details being saved
    print(f"🔍 Creating user {request.email} with contact details:")
    print(f"  Title: '{request.title}'")
    print(f"  Home Phone: '{request.home_phone}'")
    print(f"  Mobile Phone: '{request.mobile_phone}'")
    print(f"  Home Address: '{request.home_address}'")
    print(f"  Postcode: '{request.postcode}'")
    print(f"  Date of Birth: '{request.date_of_birth}'")
    print(f"  Gender: '{request.gender}'")
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Verify the data was saved
    print(f"🔍 Verification - User data after creation:")
    print(f"  Title: '{new_user.title}'")
    print(f"  Home Phone: '{new_user.home_phone}'")
    print(f"  Mobile Phone: '{new_user.mobile_phone}'")
    print(f"  Home Address: '{new_user.home_address}'")
    print(f"  Postcode: '{new_user.postcode}'")
    print(f"  Date of Birth: '{new_user.date_of_birth}'")
    print(f"  Gender: '{new_user.gender}'")
    
    # If this is a client user, also create client details
    if request.role == "client":
        from ..models.client_details import ClientDetails

        # Convert date string to date object if provided
        from datetime import datetime, date
        date_of_birth = None
        if request.date_of_birth:
            try:
                date_of_birth = datetime.strptime(request.date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                # If date parsing fails, use default
                date_of_birth = date(1900, 1, 1)
        else:
            date_of_birth = date(1900, 1, 1)

        client_details = ClientDetails(
            user_id=new_user.id,
            title=request.title,
            first_name=request.first_name,
            surname=request.last_name,
            home_address=request.home_address,
            postcode=request.postcode,
            date_of_birth=date_of_birth,
            gender=request.gender,
            home_phone=request.home_phone,
            mobile_phone=request.mobile_phone,
            email=request.email
        )
        
        db.add(client_details)
        db.commit()
    
    # Generate password reset token and send welcome email
    try:
        reset_token = generate_reset_token()
        new_user.reset_token = reset_token
        new_user.reset_token_expires = datetime.utcnow() + timedelta(hours=24)
        db.commit()
        
        # Send welcome email with password setup instructions
        user_name = f"{new_user.first_name} {new_user.last_name}".strip() or "User"
        inviter_name = f"{current_user.first_name} {current_user.last_name}".strip() or "Administrator"
        
        # Get office name for the email
        office = db.query(Office).filter(Office.id == office_id).first()
        office_name = office.name if office else "Citizens Advice Tadley"
        client_number = ca_client_number or "TBD"
        
        # Create invitation URL for new user to set up their account
        invite_url = f"/register?token={reset_token}"
        
        email_sent = await send_invitation_email(
            new_user.email, 
            reset_token, 
            inviter_name,
            invite_url,
            office_name,
            client_number
        )
        
        if not email_sent:
            logger.warning(f"Failed to send welcome email to {new_user.email}")
        else:
            logger.info(f"Welcome email sent to {new_user.email}")
            
    except Exception as e:
        logger.error(f"Error sending welcome email: {str(e)}")
    
    return {
        "message": f"User {request.email} created successfully",
        "user_id": new_user.id,
        "client_details_created": request.role == "client"
    }

@router.post("/invite-user", response_model=InviteLinkResponse)
async def invite_user(
    request: InviteUserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Invite a new user to the system"""
    
    require_admin_access(current_user)
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Determine office_id based on user role
    office_id = current_user.office_id
    if current_user.is_superuser:
        # For superusers, we need to determine the office
        # For now, use the current user's office, but this could be enhanced
        office_id = current_user.office_id
    
    # Generate invitation token
    invitation_token = generate_invitation_token()
    expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days expiry
    
    # Prepare invitation details for prefilling
    invitation_details = {}
    if request.first_name:
        invitation_details['first_name'] = request.first_name
    if request.last_name:
        invitation_details['last_name'] = request.last_name
    if request.phone:
        invitation_details['phone'] = request.phone
    if request.title:
        invitation_details['title'] = request.title
    if request.home_address:
        invitation_details['home_address'] = request.home_address
    if request.postcode:
        invitation_details['postcode'] = request.postcode
    if request.date_of_birth:
        invitation_details['date_of_birth'] = request.date_of_birth
    if request.gender:
        invitation_details['gender'] = request.gender
    if request.home_phone:
        invitation_details['home_phone'] = request.home_phone
    if request.mobile_phone:
        invitation_details['mobile_phone'] = request.mobile_phone
    
    # Create invitation
    
    # Auto-generate client number for client users
    ca_client_number = None
    if request.role == "client":
        if request.ca_client_number:
            # If a client number is provided, use it (for manual assignment)
            ca_client_number = request.ca_client_number
        else:
            # Auto-generate client number
            from .auth import generate_next_client_number
            ca_client_number = generate_next_client_number(db)
    
    # Create the user with pending status and a temporary password
    temp_password = secrets.token_urlsafe(16)
    new_user = User(
        email=request.email,
        first_name="",  # Will be filled when they accept invitation
        last_name="",   # Will be filled when they accept invitation
        role=UserRole(request.role),
        status=UserStatus.PENDING_VERIFICATION,
        office_id=office_id,
        ca_client_number=ca_client_number,
        is_office_admin=False,  # Default to False for invited users
        invitation_token=invitation_token,
        invitation_expires_at=expires_at,
        invited_by_id=current_user.id,
        invitation_details=json.dumps(invitation_details) if invitation_details else None,
        password_hash=hash_password(temp_password)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="user_invited",
        resource_type="user",
        resource_id=new_user.id,
        details=f"Invited {request.role} {request.email} to office {office_id}"
    )
    db.add(audit_log)
    db.commit()
    
    # Get office code for the URL
    office = db.query(Office).filter(Office.id == office_id).first()
    office_code = office.code if office else "DEFAULT"
    
    # Generate invite URL with office code
    invite_url = f"/register?officecode={office_code}&invite={invitation_token}"
    
    # Send invitation email
    try:
        inviter_name = f"{current_user.first_name} {current_user.last_name}".strip() or "Administrator"
        email_sent = await send_invitation_email(
            request.email, 
            invitation_token, 
            inviter_name,
            invite_url
        )
        
        if not email_sent:
            logger.warning(f"Failed to send invitation email to {request.email}")
        else:
            logger.info(f"Invitation email sent to {request.email}")
            
    except Exception as e:
        logger.error(f"Error sending invitation email: {str(e)}")
    
    return InviteLinkResponse(
        invite_url=invite_url,
        expires_at=expires_at,
        email=request.email
    )

@router.post("/invite-adviser", response_model=InviteLinkResponse)
async def invite_adviser(
    request: InviteAdviserRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an invitation link for a new adviser"""
    
    require_admin_access(current_user)
    
    # Check if email already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate invitation token
    invitation_token = generate_invitation_token()
    expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days expiry
    
    # Create the user with pending status and a temporary password
    temp_password = secrets.token_urlsafe(16)  # Generate a secure temporary password
    new_user = User(
        email=request.email,
        first_name=request.first_name,
        last_name=request.last_name,
        role=UserRole.ADVISER,
        status=UserStatus.PENDING_VERIFICATION,
        office_id=request.office_id,
        is_office_admin=request.is_office_admin,
        invitation_token=invitation_token,
        invitation_expires_at=expires_at,
        invited_by_id=current_user.id,
        password_hash=hash_password(temp_password)  # Set a temporary password hash
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Create audit log
    audit_log = AuditLog(
        user_id=current_user.id,
        action="adviser_invited",
        resource_type="user",
        resource_id=new_user.id,
        details=f"Invited adviser {request.email} to office {request.office_id}"
    )
    db.add(audit_log)
    db.commit()
    
    # Get office code for the URL
    office = db.query(Office).filter(Office.id == request.office_id).first()
    office_code = office.code if office else "DEFAULT"
    
    # Generate invite URL with office code
    invite_url = f"/register?officecode={office_code}&invite={invitation_token}"
    
    # Send invitation email
    try:
        inviter_name = f"{current_user.first_name} {current_user.last_name}".strip() or "Administrator"
        email_sent = await send_invitation_email(
            request.email, 
            invitation_token, 
            inviter_name,
            invite_url
        )
        
        if not email_sent:
            logger.warning(f"Failed to send invitation email to {request.email}")
        else:
            logger.info(f"Invitation email sent to {request.email}")
            
    except Exception as e:
        logger.error(f"Error sending invitation email: {str(e)}")
    
    return InviteLinkResponse(
        invite_url=invite_url,
        expires_at=expires_at,
        email=request.email
    )

@router.post("/users/{user_id}/reinvite", response_model=InviteLinkResponse)
async def reinvite_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Regenerate an invitation link for an existing pending user.

    Only allowed for users in PENDING_VERIFICATION status. Generates a new
    invitation token and expiry and returns the invite_url the frontend can use.
    """

    require_admin_access(current_user)

    # Find user and permission checks
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not current_user.is_superuser and user.office_id != current_user.office_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage users in your own office")

    # Only pending users can be re-invited
    if user.status != UserStatus.PENDING_VERIFICATION:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not pending verification")

    # Generate new token and expiry
    invitation_token = generate_invitation_token()
    expires_at = datetime.utcnow() + timedelta(days=7)

    user.invitation_token = invitation_token
    user.invitation_expires_at = expires_at
    # Track who re-invited most recently
    user.invited_by_id = current_user.id

    db.commit()
    db.refresh(user)

    # Get office code for the URL
    office = db.query(Office).filter(Office.id == user.office_id).first()
    office_code = office.code if office else "DEFAULT"
    
    # Generate invite URL with office code
    invite_url = f"/register?officecode={office_code}&invite={invitation_token}"

    # Send reinvitation email
    try:
        inviter_name = f"{current_user.first_name} {current_user.last_name}".strip() or "Administrator"
        email_sent = await send_invitation_email(
            user.email, 
            invitation_token, 
            inviter_name,
            invite_url
        )
        
        if not email_sent:
            logger.warning(f"Failed to send reinvitation email to {user.email}")
        else:
            logger.info(f"Reinvitation email sent to {user.email}")
            
    except Exception as e:
        logger.error(f"Error sending reinvitation email: {str(e)}")

    return InviteLinkResponse(
        invite_url=invite_url,
        expires_at=expires_at,
        email=user.email
    )

@router.post("/users/{user_id}/generate-invite", response_model=InviteLinkResponse)
async def generate_invite_for_user(
    user_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Generate an invitation link for any user (creates invitation if user is active, re-invites if pending)"""

    require_admin_access(current_user)

    # Find user and permission checks
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if not current_user.is_superuser and user.office_id != current_user.office_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only manage users in your own office")

    # Generate new token and expiry
    invitation_token = generate_invitation_token()
    expires_at = datetime.utcnow() + timedelta(days=7)

    # Prepare invitation details from user's existing data
    invitation_details = {}
    if user.first_name:
        invitation_details['first_name'] = user.first_name
    if user.last_name:
        invitation_details['last_name'] = user.last_name
    if user.phone:
        invitation_details['phone'] = user.phone
    if user.title:
        invitation_details['title'] = user.title
    if user.home_address:
        invitation_details['home_address'] = user.home_address
    if user.postcode:
        invitation_details['postcode'] = user.postcode
    if user.date_of_birth:
        invitation_details['date_of_birth'] = user.date_of_birth
    if user.gender:
        invitation_details['gender'] = user.gender
    if user.home_phone:
        invitation_details['home_phone'] = user.home_phone
    if user.mobile_phone:
        invitation_details['mobile_phone'] = user.mobile_phone

    # Update user to pending status and add invitation details
    user.status = UserStatus.PENDING_VERIFICATION
    user.invitation_token = invitation_token
    user.invitation_expires_at = expires_at
    user.invited_by_id = current_user.id
    user.invitation_details = json.dumps(invitation_details) if invitation_details else None

    db.commit()
    db.refresh(user)

    # Get office code for the URL
    office = db.query(Office).filter(Office.id == user.office_id).first()
    office_code = office.code if office else "DEFAULT"
    
    # Generate invite URL with office code
    invite_url = f"/register?officecode={office_code}&invite={invitation_token}"

    return InviteLinkResponse(
        invite_url=invite_url,
        expires_at=expires_at,
        email=user.email
    )

@router.get("/invite/{token}")
async def validate_invitation(
    token: str,
    db: Session = Depends(get_db)
):
    """Validate an invitation token and return user details"""
    
    user = db.query(User).filter(
        User.invitation_token == token,
        User.status == UserStatus.PENDING_VERIFICATION
    ).first()
    
    if not user:
        # No user found with token
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation link"
        )
    
    if user.invitation_expires_at < datetime.utcnow():
        # Invitation expired
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation link has expired"
        )
    
    # Get office details
    office = db.query(Office).filter(Office.id == user.office_id).first()
    
    # Parse invitation details if available
    invitation_data = {}
    if user.invitation_details:
        try:
            invitation_data = json.loads(user.invitation_details)
        except json.JSONDecodeError:
            invitation_data = {}
    
    # Prepare response with base fields and invitation details
    response_data = {
        "email": user.email,
        "first_name": user.first_name or invitation_data.get('first_name', ''),
        "last_name": user.last_name or invitation_data.get('last_name', ''),
        "office_name": office.name if office else "Unknown Office",
        "office_code": office.code if office else "DEFAULT",
        "office_id": user.office_id,
        "invited_by": user.invited_by.email if user.invited_by else None,
        "expires_at": user.invitation_expires_at,
        "role": user.role.value,
        "is_office_admin": user.is_office_admin,
        "phone": user.phone or invitation_data.get('phone', ''),
        "ca_client_number": user.ca_client_number,
        # Add contact details for prefilling
        "title": invitation_data.get('title', ''),
        "home_address": invitation_data.get('home_address', ''),
        "postcode": invitation_data.get('postcode', ''),
        "date_of_birth": invitation_data.get('date_of_birth', ''),
        "gender": invitation_data.get('gender', ''),
        "home_phone": invitation_data.get('home_phone', ''),
        "mobile_phone": invitation_data.get('mobile_phone', '')
    }

    # Add any additional invitation details for prefilling
    response_data.update(invitation_data)
    
    return response_data

@router.post("/invite/{token}/accept", response_model=TokenResponse)
async def accept_invitation(
    token: str,
    request: AcceptInvitationRequest,
    db: Session = Depends(get_db)
):
    """Accept invitation and set password"""
    
    user = db.query(User).filter(
        User.invitation_token == token,
        User.status == UserStatus.PENDING_VERIFICATION
    ).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid or expired invitation link"
        )
    
    if user.invitation_expires_at < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invitation link has expired"
        )
    
    # Apply editable fields if provided
    if request.email and request.email != user.email:
        # Ensure email unique
        existing = db.query(User).filter(User.email == request.email).first()
        if existing and existing.id != user.id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already exists"
            )
        user.email = request.email

    if request.first_name is not None:
        user.first_name = request.first_name
    if request.last_name is not None:
        user.last_name = request.last_name
    if request.phone is not None:
        user.phone = request.phone

    # Set password and activate account
    user.password_hash = hash_password(request.password)
    user.status = UserStatus.ACTIVE
    user.invitation_token = None
    user.invitation_expires_at = None
    user.email_verified = True
    user.email_verified_at = datetime.utcnow()
    
    # Update last_login and last_activity since this is effectively a login
    user.last_login = datetime.utcnow()
    user.last_activity = datetime.utcnow()
    
    db.commit()
    
    # Create audit log
    audit_log = AuditLog(
        user_id=user.id,
        office_id=user.office_id,  # Add the required office_id
        action="invitation_accepted",
        resource_type="user",
        resource_id=user.id,
        details=f"Adviser {user.email} accepted invitation"
    )
    db.add(audit_log)
    db.commit()
    
    # Create login tokens for automatic login
    from ..utils.auth import create_access_token, create_refresh_token
    access_token = create_access_token({"sub": user.id, "role": user.role.value})
    refresh_token = create_refresh_token({"sub": user.id})
    
    # Create user response
    user_response = UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        role=user.role.value,
        office_id=user.office_id,
        status=user.status.value,
        is_office_admin=user.is_office_admin,
        is_superuser=user.is_superuser,
        ca_client_number=user.ca_client_number,
        phone=user.phone,
        last_login=user.last_login,
        optional_info_completed=user.optional_info_completed,
        optional_info_never_show=user.optional_info_never_show
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=user_response
    )

@router.get("/users")
async def list_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List users based on role permissions"""
    
    require_admin_access(current_user)
    
    if current_user.is_superuser:
        # Superusers can see all users
        users = db.query(User).all()
    elif current_user.role == UserRole.ADVISER:
        # Advisers can see advisers in same office + clients assigned to their office cases
        # Get advisers in same office
        office_advisers = db.query(User).filter(
            User.office_id == current_user.office_id,
            User.role == UserRole.ADVISER
        ).all()
        
        # Get clients assigned to cases in their office
        office_cases = db.query(Case).filter(Case.office_id == current_user.office_id).all()
        office_case_client_ids = [case.client_id for case in office_cases if case.client_id]
        office_clients = db.query(User).filter(
            User.id.in_(office_case_client_ids),
            User.role == UserRole.CLIENT
        ).all()
        
        users = office_advisers + office_clients
    else:
        # Administrators can see all advisers + all clients
        advisers = db.query(User).filter(User.role == UserRole.ADVISER).all()
        clients = db.query(User).filter(User.role == UserRole.CLIENT).all()
        users = advisers + clients
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "status": user.status.value,
            "ca_client_number": user.ca_client_number,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "last_activity": user.last_activity,
            "phone": user.phone,
            "is_2fa_enabled": user.is_2fa_enabled,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until,
            "office_id": user.office_id,
            "office_name": user.office.name if user.office else None,
            "is_office_admin": user.is_office_admin,
            # Contact details
            "title": user.title,
            "home_phone": user.home_phone,
            "home_address": user.home_address,
            "postcode": user.postcode,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender
        }
        for user in users
    ]

@router.get("/offices/{office_id}/users")
async def list_office_users(
    office_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List users in a specific office"""
    
    require_admin_access(current_user)
    
    # Check if user has access to this office
    if not current_user.is_superuser and current_user.office_id != office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied to this office"
        )
    
    # Only superusers or office admins can access office user management
    if not current_user.is_superuser and not current_user.is_office_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only office administrators can access user management"
        )
    
    users = db.query(User).filter(User.office_id == office_id).all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "status": user.status.value,
            "ca_client_number": user.ca_client_number,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "last_activity": user.last_activity,
            "phone": user.phone,
            "is_2fa_enabled": user.is_2fa_enabled,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until,
            "office_id": user.office_id,
            "office_name": user.office.name if user.office else None,
            "is_office_admin": user.is_office_admin,
            # Contact details
            "title": user.title,
            "home_phone": user.home_phone,
            "home_address": user.home_address,
            "postcode": user.postcode,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender
        }
        for user in users
    ]

@router.get("/users/advisers")
async def list_advisers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List advisers based on role permissions"""
    
    require_admin_access(current_user)
    
    if current_user.is_superuser:
        # Superusers can see all advisers
        advisers = db.query(User).filter(User.role == UserRole.ADVISER).all()
    elif current_user.role == UserRole.ADVISER:
        # Advisers can see advisers in same office
        advisers = db.query(User).filter(
            User.office_id == current_user.office_id,
            User.role == UserRole.ADVISER
        ).all()
    else:
        # Administrators can see all advisers
        advisers = db.query(User).filter(User.role == UserRole.ADVISER).all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "status": user.status.value,
            "ca_client_number": user.ca_client_number,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "last_activity": user.last_activity,
            "phone": user.phone,
            "is_2fa_enabled": user.is_2fa_enabled,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until,
            "office_id": user.office_id,
            "office_name": user.office.name if user.office else None,
            "is_office_admin": user.is_office_admin,
            # Contact details
            "title": user.title,
            "home_phone": user.home_phone,
            "home_address": user.home_address,
            "postcode": user.postcode,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender
        }
        for user in advisers
    ]


@router.get("/users/clients")
async def list_clients(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List clients based on role permissions"""
    
    require_admin_access(current_user)
    
    if current_user.is_superuser:
        # Superusers can see all clients
        clients = db.query(User).filter(User.role == UserRole.CLIENT).all()
    elif current_user.role == UserRole.ADVISER:
        # Advisers can see clients assigned to cases in their office
        office_cases = db.query(Case).filter(Case.office_id == current_user.office_id).all()
        office_case_client_ids = [case.client_id for case in office_cases if case.client_id]
        clients = db.query(User).filter(
            User.id.in_(office_case_client_ids),
            User.role == UserRole.CLIENT
        ).all()
    else:
        # Administrators can see all clients
        clients = db.query(User).filter(User.role == UserRole.CLIENT).all()
    
    return [
        {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "status": user.status.value,
            "ca_client_number": user.ca_client_number,
            "created_at": user.created_at,
            "last_login": user.last_login,
            "last_activity": user.last_activity,
            "phone": user.phone,
            "is_2fa_enabled": user.is_2fa_enabled,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until,
            "office_id": user.office_id,
            "office_name": user.office.name if user.office else None,
            "is_office_admin": user.is_office_admin,
            # Contact details
            "title": user.title,
            "home_phone": user.home_phone,
            "home_address": user.home_address,
            "postcode": user.postcode,
            "date_of_birth": user.date_of_birth,
            "gender": user.gender
        }
        for user in clients
    ]

class UpdateCaseRequest(BaseModel):
    status: Optional[str] = None
    office_id: Optional[str] = None
    assigned_adviser_id: Optional[str] = None
    notes: Optional[str] = None
    priority: Optional[str] = None

@router.delete("/cases/{case_id}")
async def delete_case(
    case_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a case (superuser only)"""
    
    require_superuser_access(current_user)
    
    # Find the case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Get client info for audit log
    client = case.client
    client_name = f"{(client.first_name or '').strip()} {(client.last_name or '').strip()}".strip() or client.email if client else "Unknown Client"
    
    # Store case info for response
    case_info = {
        "id": case.id,
        "client_name": client_name,
        "client_email": client.email if client else "Unknown",
        "status": case.status.value if case.status else "unknown",
        "created_at": case.created_at.isoformat() if case.created_at else None
    }
    
    try:
        # First, delete all associated files from storage and database
        from ..utils.file_utils import delete_case_files
        file_cleanup_result = await delete_case_files(case_id, db)
        
        # Check if file cleanup had critical errors
        if file_cleanup_result.get("error"):
            print(f"⚠️ File cleanup error for case {case_id}: {file_cleanup_result['error']}")
            # Continue with case deletion even if some files couldn't be deleted
        
        # Delete the case (cascade will handle related records)
        db.delete(case)
        db.commit()
        
        # Create audit log for the deletion
        audit_log = AuditLog(
            user_id=current_user.id,
            office_id=current_user.office_id,
            action="case_deleted",
            resource_type="case",
            resource_id=case_id,
            details=f"Deleted case for client {client_name} ({client.email if client else 'Unknown'}) - Files: {file_cleanup_result.get('files_deleted', 0)} deleted, {file_cleanup_result.get('files_failed', 0)} failed, Case dir: {file_cleanup_result.get('case_directory_removed', False)}, Parent dir: {file_cleanup_result.get('parent_directory_removed', False)}"
        )
        db.add(audit_log)
        db.commit()
        
        response_data = {
            "message": f"Case for {client_name} deleted successfully",
            "case_info": case_info,
            "file_cleanup": {
                "files_found": file_cleanup_result.get("files_found", 0),
                "files_deleted": file_cleanup_result.get("files_deleted", 0),
                "files_failed": file_cleanup_result.get("files_failed", 0),
                "case_directory_removed": file_cleanup_result.get("case_directory_removed", False),
                "parent_directory_removed": file_cleanup_result.get("parent_directory_removed", False)
            }
        }
        
        # Add warnings if there were file cleanup issues
        if file_cleanup_result.get("files_failed", 0) > 0:
            response_data["warnings"] = file_cleanup_result.get("storage_errors", [])
        
        return response_data
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error deleting case {case_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case: {str(e)}"
        )

@router.put("/cases/{case_id}")
async def update_case(
    case_id: str,
    request: UpdateCaseRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update case details (admin only)"""
    
    require_admin_access(current_user)
    
    # Find the case
    case = db.query(Case).filter(Case.id == case_id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Check office access permissions
    if not current_user.is_superuser and case.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only update cases in your own office"
        )
    
    # Store original status for comparison (before any changes)
    original_status = case.status
    
    # Update status if provided
    if request.status is not None:
        try:
            case.status = CaseStatus(request.status)
            # Automatically manage priority for emergency cases based on status
            if case.has_debt_emergency:
                if case.status == CaseStatus.CLOSED:
                    # Emergency cases that are closed should have NORMAL priority
                    case.priority = CasePriority.NORMAL
                elif case.status in [CaseStatus.PENDING, CaseStatus.SUBMITTED]:
                    # Emergency cases that are pending/submitted should have URGENT priority
                    case.priority = CasePriority.URGENT
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid status value"
            )
    
    # Update office if provided (superuser only)
    if request.office_id is not None:
        if not current_user.is_superuser:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only superusers can change case office assignment"
            )
        
        # Verify office exists
        office = db.query(Office).filter(Office.id == request.office_id).first()
        if not office:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Office not found"
            )
        
        # Update case office
        case.office_id = request.office_id
        
        # Also update the client's office to maintain consistency (one-to-one mapping)
        client = db.query(User).filter(User.id == case.client_id).first()
        if client:
            client.office_id = request.office_id
            print(f"Updated client {client.email} office from {client.office_id} to {request.office_id}")
        else:
            print(f"Warning: No client found for case {case.id}")
    
    # Update assigned adviser if provided
    if request.assigned_adviser_id is not None:
        if request.assigned_adviser_id == "":
            case.assigned_adviser_id = None
        else:
            # Verify adviser exists and is in the same office
            adviser = db.query(User).filter(
                User.id == request.assigned_adviser_id,
                User.role == UserRole.ADVISER
            ).first()
            
            if not adviser:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Adviser not found"
                )
            
            if not current_user.is_superuser and adviser.office_id != current_user.office_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You can only assign advisers from your own office"
                )
            
            case.assigned_adviser_id = request.assigned_adviser_id
    
    # Update notes if provided
    if request.notes is not None:
        case.additional_notes = request.notes
    
    # Update priority if provided (but not for emergency cases with automatic priority management)
    if request.priority is not None:
        if case.has_debt_emergency:
            print(f"⚠️  Skipping manual priority update for emergency case {case.id} - priority is automatically managed based on status")
        else:
            print(f"Updating priority for case {case.id}: {case.priority.value if case.priority else 'None'} -> {request.priority}")
            try:
                case.priority = CasePriority(request.priority)
                print(f"Priority updated successfully to: {case.priority.value}")
            except ValueError:
                print(f"Invalid priority value: {request.priority}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid priority value. Must be one of: LOW, NORMAL, URGENT"
                )
    
    db.commit()
    db.refresh(case)
    
    # Create notifications based on changes
    notifications_created = []
    
    try:
        # Handle case status changes
        if request.status is not None:
            old_status = original_status.value if original_status else "unknown"
            new_status = request.status
            if old_status != new_status:
                # Create appropriate notification based on status
                notification_type = NotificationType.CASE_CLOSED if new_status == "closed" else NotificationType.CASE_UPDATED
                title = "Your case has been closed" if new_status == "closed" else "Your case status has changed"
                message = (
                    "Your debt advice case has been closed by an adviser. Please contact us if you need further assistance."
                    if new_status == "closed"
                    else f"The status of your case has changed from {old_status} to {new_status}."
                )
                
                client_notification = Notification(
                    user_id=case.client_id,
                    type=notification_type,
                    title=title,
                    message=message,
                    case_id=case.id,
                    data={
                        "updated_by": current_user.email,
                        "old_status": old_status,
                        "new_status": new_status
                    }
                )
                db.add(client_notification)
                notifications_created.append(notification_type.value)
                has_meaningful_changes = True
        
        # Check adviser reassignment
        if request.assigned_adviser_id is not None:
            old_adviser = case.assigned_adviser_id
            new_adviser = request.assigned_adviser_id if request.assigned_adviser_id != "" else None
            if old_adviser != new_adviser:
                message_parts.append("Your case has been reassigned to a different adviser")
                has_meaningful_changes = True
        
        # Check priority change
        if request.priority is not None:
            old_priority = case.priority.value if case.priority else "normal"
            new_priority = request.priority
            if old_priority != new_priority:
                message_parts.append(f"The priority of your case has changed to {new_priority}")
                has_meaningful_changes = True
        
        # Only create notification if there are meaningful changes
        if has_meaningful_changes:
            print(f"Creating CASE_UPDATED notification for client {case.client_id}")
            message = f"{', '.join(message_parts)}"
            
            # Create notification for client about case update
            client_notification = Notification(
                user_id=case.client_id,
                type=NotificationType.CASE_UPDATED,
                title="Your case has been updated",
                message=message,
                case_id=case.id,
                data={"updated_by": current_user.email, "changes": {
                    "status": request.status,
                    "notes": bool(request.notes),
                    "priority": request.priority,
                    "assigned_adviser": bool(request.assigned_adviser_id)
                }}
            )
            db.add(client_notification)
            notifications_created.append("CASE_UPDATED")
        else:
            print(f"ℹ️ No meaningful changes detected for case {case.id} - skipping notification")
        
        # If case was assigned to a new adviser, notify the adviser
        if (request.assigned_adviser_id is not None and 
            request.assigned_adviser_id != "" and 
            request.assigned_adviser_id != case.assigned_adviser_id):
            
            print(f"Creating CASE_ASSIGNED notification for adviser {request.assigned_adviser_id}")
            adviser_notification = Notification(
                user_id=request.assigned_adviser_id,
                type=NotificationType.CASE_ASSIGNED,
                title="New case assigned to you",
                message=f"A new case has been assigned to you by {current_user.full_name}.",
                case_id=case.id,
                data={"assigned_by": current_user.email}
            )
            db.add(adviser_notification)
            notifications_created.append("CASE_ASSIGNED")
        
        # Commit notifications
        if notifications_created:
            db.commit()
            print(f"✅ Successfully created notifications: {', '.join(notifications_created)}")
        else:
            print("ℹ️ No notifications created (no relevant changes)")
        
    except Exception as e:
        # Log the error but don't fail the case update
        print(f"❌ Error creating notifications for case {case.id}: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        print(f"   Attempted to create: {notifications_created}")
        
        # Try to rollback and re-commit just the case update
        try:
            db.rollback()
            # Re-commit the case update without notifications
            db.commit()
            print("✅ Case update committed successfully (notifications failed)")
        except Exception as rollback_error:
            print(f"❌ Critical error during rollback: {str(rollback_error)}")
            # This is a critical error - the case update might be lost
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update case due to database error"
            )
    
    return {
        "message": f"Case {case_id} updated successfully",
        "case_id": case.id
    }

@router.post("/users/{user_id}/reactivate")
async def reactivate_user(
    user_id: str,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reactivate a locked or suspended user account"""
    
    require_admin_access(current_user)
    
    # Find the user
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )
    
    # Check office access permissions (superusers can reactivate any user)
    if not current_user.is_superuser and user.office_id != current_user.office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only reactivate users in your own office"
        )
    
    # Check if user is actually locked or suspended
    if user.status not in [UserStatus.LOCKED, UserStatus.SUSPENDED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User account is not locked or suspended"
        )
    
    # Reactivate the account
    user.status = UserStatus.ACTIVE
    user.failed_login_attempts = 0
    user.first_failed_attempt = None
    user.locked_until = None
    
    # Log the reactivation
    AuditLog.log_action(
        db,
        action="account_reactivated",
        user_id=user.id,
        office_id=user.office_id,
        description=f"Account reactivated by admin {current_user.email} for user {user.email}",
        ip_address=get_client_ip_address(request),
        success=True
    )
    
    try:
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to reactivate user: {str(e)}"
        )
    
    return {
        "message": f"User {user.email} has been reactivated successfully",
        "user_id": user.id,
        "email": user.email,
        "status": user.status.value
    }

@router.get("/logs/auth")
async def get_authentication_logs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    user_id: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    action_type: Optional[str] = Query(None)
):
    """Get authentication logs (superuser only)"""
    
    require_superuser_access(current_user)
    
    # Define authentication and security-related actions
    auth_actions = [
        # Authentication actions
        "login", "logout", "login_failed", "password_reset_requested", 
        "password_reset_completed", "password_changed", "account_locked", 
        "account_unlocked", "account_suspended", "account_activated", "account_reactivated",
        "account_created", "account_updated", "account_deleted",
        
        # File operations (from data logging requirements)
        "file_view", "file_upload", "file_download", "file_deletion",
        
        # Client setup
        "client_account_setup",
        
        # 2FA actions
        "totp_enabled", "totp_disabled", "totp_verified", "totp_failed",
        
        # Admin/Security actions
        "user_invited", "user_role_changed", "superuser_access_granted", 
        "superuser_access_revoked",
        
        # System actions
        "system_backup", "system_restore", "system_maintenance", 
        "data_export", "data_import"
    ]
    
    # Build query
    query = db.query(AuditLog).filter(AuditLog.action.in_(auth_actions))
    
    # Apply filters
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    
    if start_date:
        try:
            start_dt = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at >= start_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid start_date format. Use ISO format (e.g., 2025-01-15T00:00:00Z)"
            )
    
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
            query = query.filter(AuditLog.created_at <= end_dt)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid end_date format. Use ISO format (e.g., 2025-01-15T23:59:59Z)"
            )
    
    if action_type:
        query = query.filter(AuditLog.action == action_type)
    
    # Get total count
    total_count = query.count()
    
    # Apply pagination and ordering - newest first, then by action type for consistency
    logs = query.order_by(AuditLog.created_at.desc(), AuditLog.action.asc()).offset(offset).limit(limit).all()
    
    # Helper function to clean up descriptions
    def clean_description(description, action):
        if not description:
            return "No description"
        
        # Remove email addresses from descriptions
        import re
        description = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '', description)
        
        # Clean up common patterns
        description = description.replace(' for ', '').replace('  ', ' ').strip()
        
        # If description is empty after cleaning, provide a default based on action
        if not description or description == "No description":
            action_defaults = {
                # Authentication actions
                'login': 'User logged in successfully',
                'logout': 'User logged out',
                'login_failed': 'Login attempt failed',
                'password_reset_requested': 'Password reset requested',
                'password_reset_completed': 'Password reset completed',
                'password_changed': 'Password changed',
                
                # Account management
                'account_created': 'Account created',
                'account_updated': 'Account updated',
                'account_deleted': 'Account deleted',
                'account_locked': 'Account locked',
                'account_unlocked': 'Account unlocked',
                'account_suspended': 'Account suspended',
                'account_activated': 'Account activated',
                'account_reactivated': 'Account reactivated',
                
                # File operations
                'file_view': 'File viewed',
                'file_upload': 'File uploaded',
                'file_download': 'File downloaded',
                'file_deletion': 'File deleted',
                
                # Client setup
                'client_account_setup': 'Client account setup completed',
                
                # 2FA actions
                'totp_enabled': 'Two-factor authentication enabled',
                'totp_disabled': 'Two-factor authentication disabled',
                'totp_verified': 'Two-factor authentication verified',
                'totp_failed': 'Two-factor authentication failed',
                
                # Admin/Security actions
                'user_invited': 'User invited to system',
                'user_role_changed': 'User role changed',
                'superuser_access_granted': 'Superuser access granted',
                'superuser_access_revoked': 'Superuser access revoked',
                
                # System actions
                'system_backup': 'System backup performed',
                'system_restore': 'System restore performed',
                'system_maintenance': 'System maintenance performed',
                'data_export': 'Data exported',
                'data_import': 'Data imported'
            }
            return action_defaults.get(action, f"{action.replace('_', ' ').title()}")
        
        return description

    # Format response
    result = []
    for log in logs:
        result.append({
            "id": log.id,
            "timestamp": log.created_at.isoformat(),
            "action": log.action,
            "action_display": log.action_display,
            "user_id": log.user_id,
            "user_email": log.user.email if log.user else None,
            "user_name": f"{log.user.first_name} {log.user.last_name}" if log.user and log.user.first_name and log.user.last_name else log.user.email if log.user else "System",
            "office_id": log.office_id,
            "office_name": log.office.name if log.office else None,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "success": log.success == "True",
            "description": clean_description(log.description, log.action),
            "details": log.details,
            "error_message": log.error_message,
            "is_security_event": log.is_security_event
        })
    
    return {
        "logs": result,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": (offset + limit) < total_count
    }

@router.get("/users/locked")
async def list_locked_users(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all locked or suspended users"""
    
    require_admin_access(current_user)
    
    # Query locked/suspended users
    if current_user.is_superuser:
        locked_users = db.query(User).filter(
            User.status.in_([UserStatus.LOCKED, UserStatus.SUSPENDED])
        ).all()
    else:
        locked_users = db.query(User).filter(
            User.status.in_([UserStatus.LOCKED, UserStatus.SUSPENDED]),
            User.office_id == current_user.office_id
        ).all()
    
    result = []
    for user in locked_users:
        lockout_time = None
        if user.locked_until:
            lockout_time = get_lockout_remaining_time(user.locked_until)
        
        result.append({
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "role": user.role.value,
            "status": user.status.value,
            "office_id": user.office_id,
            "office_name": user.office.name if user.office else None,
            "failed_login_attempts": user.failed_login_attempts,
            "locked_until": user.locked_until.isoformat() if user.locked_until else None,
            "lockout_remaining_minutes": lockout_time,
            "last_login": user.last_login.isoformat() if user.last_login else None,
            "created_at": user.created_at.isoformat()
        })
    
    return result

# TODO: Add more admin endpoints for:
# - User management (suspend, activate, delete)
# - Case management (assign, change status)
# - File downloads
# - Audit log viewing
# - System configuration
