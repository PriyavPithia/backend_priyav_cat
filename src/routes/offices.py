from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, EmailStr

from ..config.database import get_db
from ..models.office import Office
from ..models.user import User, UserRole, UserStatus
from ..models.case import Case
from .auth import get_current_user

router = APIRouter()

# Pydantic models for office management
class OfficeCreate(BaseModel):
    name: str
    code: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None

class OfficeUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    contact_email: Optional[EmailStr] = None
    contact_phone: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None

class OfficeTransferRequest(BaseModel):
    target_office_id: str
    transfer_users: bool = True
    transfer_cases: bool = True
    transfer_audit_logs: bool = True

class OfficeTransferResponse(BaseModel):
    message: str
    transferred_users: int
    transferred_cases: int
    transferred_audit_logs: int
    source_office_name: str
    target_office_name: str

class OfficeResponse(BaseModel):
    id: str
    name: str
    code: Optional[str]
    contact_email: Optional[str]
    contact_phone: Optional[str]
    address: Optional[str]
    is_active: bool
    is_default: bool
    created_at: str
    user_count: int
    active_user_count: int
    client_count: int
    adviser_count: int
    superuser_count: int

class UserCreateInOffice(BaseModel):
    email: EmailStr
    first_name: str
    last_name: str
    phone: Optional[str] = None
    role: UserRole
    ca_client_number: Optional[str] = None  # For clients only
    is_office_admin: Optional[bool] = False

class UserResponse(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    phone: Optional[str]
    role: UserRole
    status: UserStatus
    ca_client_number: Optional[str]
    office_id: str
    office_name: Optional[str]
    is_office_admin: Optional[bool] = False
    created_at: str
    last_login: Optional[str]
    # Contact details
    title: Optional[str] = None
    home_phone: Optional[str] = None
    home_address: Optional[str] = None
    postcode: Optional[str] = None
    date_of_birth: Optional[str] = None
    gender: Optional[str] = None

def require_superuser(current_user: User = Depends(get_current_user)):
    """Require superuser role for office management"""
    if current_user.role != UserRole.SUPERUSER:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only superusers can manage offices"
        )
    return current_user

def require_office_admin(current_user: User = Depends(get_current_user)):
    """Require admin role (adviser or superuser) for user management"""
    if current_user.role not in [UserRole.ADVISER, UserRole.SUPERUSER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can manage users"
        )
    return current_user

@router.get("/office-management", response_model=List[OfficeResponse])
async def list_offices(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List offices visible to the current user.
    
    - Superusers: all offices
    - Advisers: only their own office
    """
    
    # Superusers can see all offices, advisers can only see their own
    if current_user.role == UserRole.SUPERUSER:
        offices = db.query(Office).all()
    else:
        # Advisers can only see their own office
        offices = db.query(Office).filter(Office.id == current_user.office_id).all()
    
    result = []
    for office in offices:
        # Only count non-superuser users (superusers are system-wide, not office-specific)
        user_count = db.query(User).filter(
            User.office_id == office.id,
            User.role != UserRole.SUPERUSER
        ).count()
        active_user_count = db.query(User).filter(
            User.office_id == office.id,
            User.status == UserStatus.ACTIVE,
            User.role != UserRole.SUPERUSER
        ).count()
        client_count = db.query(User).filter(
            User.office_id == office.id,
            User.role == UserRole.CLIENT
        ).count()
        adviser_count = db.query(User).filter(
            User.office_id == office.id,
            User.role == UserRole.ADVISER
        ).count()
        # Superusers are no longer tied to offices
        superuser_count = 0
        
        result.append(OfficeResponse(
            id=office.id,
            name=office.name,
            code=office.code,
            contact_email=office.contact_email,
            contact_phone=office.contact_phone,
            address=office.address,
            is_active=office.is_active,
            is_default=office.is_default,
            created_at=office.created_at.isoformat(),
            user_count=user_count,
            active_user_count=active_user_count,
            client_count=client_count,
            adviser_count=adviser_count,
            superuser_count=superuser_count
        ))
    
    return result

@router.post("/office-management", response_model=OfficeResponse)
async def create_office(
    office_data: OfficeCreate,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Create a new office (superuser only)"""
    
    # Check if office code already exists
    if office_data.code:
        existing_office = db.query(Office).filter(Office.code == office_data.code).first()
        if existing_office:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Office code already exists"
            )
    
    # Check if this is the first office (should be set as default)
    existing_offices = db.query(Office).count()
    is_first_office = existing_offices == 0
    
    # Create new office
    office = Office(
        name=office_data.name,
        code=office_data.code,
        contact_email=office_data.contact_email,
        contact_phone=office_data.contact_phone,
        address=office_data.address,
        is_active=True,
        is_default=is_first_office  # Set as default if it's the first office
    )
    
    db.add(office)
    db.commit()
    db.refresh(office)
    
    return OfficeResponse(
        id=office.id,
        name=office.name,
        code=office.code,
        contact_email=office.contact_email,
        contact_phone=office.contact_phone,
        address=office.address,
        is_active=office.is_active,
        is_default=office.is_default,
        created_at=office.created_at.isoformat(),
        user_count=0,
        active_user_count=0,
        client_count=0,
        adviser_count=0,
        superuser_count=0
    )

@router.get("/office-management/{office_id}", response_model=OfficeResponse)
async def get_office(
    office_id: str,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Get office details (superuser only)"""
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    # Only count non-superuser users (superusers are system-wide, not office-specific)
    user_count = db.query(User).filter(
        User.office_id == office.id,
        User.role != UserRole.SUPERUSER
    ).count()
    active_user_count = db.query(User).filter(
        User.office_id == office.id,
        User.status == UserStatus.ACTIVE,
        User.role != UserRole.SUPERUSER
    ).count()
    client_count = db.query(User).filter(
        User.office_id == office.id,
        User.role == UserRole.CLIENT
    ).count()
    adviser_count = db.query(User).filter(
        User.office_id == office.id,
        User.role == UserRole.ADVISER
    ).count()
    # Superusers are no longer tied to offices
    superuser_count = 0
    
    return OfficeResponse(
        id=office.id,
        name=office.name,
        code=office.code,
        contact_email=office.contact_email,
        contact_phone=office.contact_phone,
        address=office.address,
        is_active=office.is_active,
        is_default=office.is_default,
        created_at=office.created_at.isoformat(),
        user_count=user_count,
        active_user_count=active_user_count,
        client_count=client_count,
        adviser_count=adviser_count,
        superuser_count=superuser_count
    )

@router.put("/office-management/{office_id}", response_model=OfficeResponse)
async def update_office(
    office_id: str,
    office_data: OfficeUpdate,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Update office (superuser only)"""
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    # Check if office code already exists (if being updated)
    if office_data.code and office_data.code != office.code:
        existing_office = db.query(Office).filter(Office.code == office_data.code).first()
        if existing_office:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Office code already exists"
            )
    
    # Update fields
    update_data = office_data.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(office, field, value)
    
    db.commit()
    db.refresh(office)
    
    user_count = db.query(User).filter(User.office_id == office.id).count()
    active_user_count = db.query(User).filter(
        User.office_id == office.id,
        User.status == UserStatus.ACTIVE
    ).count()
    client_count = db.query(User).filter(
        User.office_id == office.id,
        User.role == UserRole.CLIENT
    ).count()
    adviser_count = db.query(User).filter(
        User.office_id == office.id,
        User.role == UserRole.ADVISER
    ).count()
    superuser_count = db.query(User).filter(
        User.office_id == office.id,
        User.role == UserRole.SUPERUSER
    ).count()
    
    return OfficeResponse(
        id=office.id,
        name=office.name,
        code=office.code,
        contact_email=office.contact_email,
        contact_phone=office.contact_phone,
        address=office.address,
        is_active=office.is_active,
        is_default=office.is_default,
        created_at=office.created_at.isoformat(),
        user_count=user_count,
        active_user_count=active_user_count,
        client_count=client_count,
        adviser_count=adviser_count,
        superuser_count=superuser_count
    )

@router.get("/office-management/{office_id}/users", response_model=List[UserResponse])
async def list_office_users(
    office_id: str,
    current_user: User = Depends(require_office_admin),
    db: Session = Depends(get_db)
):
    """List users in office (office admins and superusers)"""
    
    # Superusers can see all offices, advisers can only see their own office
    if current_user.role == UserRole.ADVISER and current_user.office_id != office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only view users in your own office"
        )
    
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    users = db.query(User).filter(User.office_id == office_id).all()
    
    return [UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        role=user.role,
        status=user.status,
        ca_client_number=user.ca_client_number,
        office_id=user.office_id,
        office_name=user.office.name if user.office else None,
        is_office_admin=user.is_office_admin,
        created_at=user.created_at.isoformat(),
        last_login=user.last_login.isoformat() if user.last_login else None,
        # Contact details
        title=user.title,
        home_phone=user.home_phone,
        home_address=user.home_address,
        postcode=user.postcode,
        date_of_birth=user.date_of_birth,
        gender=user.gender
    ) for user in users]

@router.post("/office-management/{office_id}/users", response_model=UserResponse)
async def create_user_in_office(
    office_id: str,
    user_data: UserCreateInOffice,
    current_user: User = Depends(require_office_admin),
    db: Session = Depends(get_db)
):
    """Create user in office (office admins and superusers)"""
    from ..utils.auth import hash_password
    import secrets
    import string
    
    # Superusers can create users in any office, advisers can only create in their own office
    if current_user.role == UserRole.ADVISER and current_user.office_id != office_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create users in your own office"
        )
    
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists"
        )
    
    # Generate temporary password
    temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(12))
    
    # Create user
    user = User(
        email=user_data.email,
        password_hash=hash_password(temp_password),
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        role=user_data.role,
        ca_client_number=user_data.ca_client_number,
        office_id=office_id,
        is_office_admin=user_data.is_office_admin,
        status=UserStatus.PENDING_VERIFICATION
    )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    # TODO: Send invitation email with temporary password
    # For now, we'll return the temporary password in the response
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        phone=user.phone,
        role=user.role,
        status=user.status,
        ca_client_number=user.ca_client_number,
        office_id=user.office_id,
        office_name=user.office.name if user.office else None,
        is_office_admin=user.is_office_admin,
        created_at=user.created_at.isoformat(),
        last_login=None
    )

@router.get("/code/{office_code}")
async def get_office_by_code(
    office_code: str,
    db: Session = Depends(get_db)
):
    """Get office information by office code (public endpoint for registration)"""
    print(f"🔍 Looking up office with code: {office_code}")
    
    office = db.query(Office).filter(Office.code == office_code).first()
    print(f"🔍 Office found: {office is not None}")
    if office:
        print(f"🔍 Office name: {office.name}")
        print(f"🔍 Office code: {office.code}")
    
    if not office:
        print(f"❌ No office found with code: {office_code}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    return {
        "id": office.id,
        "name": office.name,
        "code": office.code,
        "contact_email": office.contact_email,
        "contact_phone": office.contact_phone,
        "address": office.address,
        "is_active": office.is_active
    }

@router.post("/office-management/{office_id}/transfer", response_model=OfficeTransferResponse)
async def transfer_office_data(
    office_id: str,
    transfer_request: OfficeTransferRequest,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Transfer all data from one office to another before deletion (superuser only)"""
    
    # Validate source office
    source_office = db.query(Office).filter(Office.id == office_id).first()
    if not source_office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Source office not found"
        )
    
    # Validate target office
    target_office = db.query(Office).filter(Office.id == transfer_request.target_office_id).first()
    if not target_office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target office not found"
        )
    
    # Prevent transferring to the same office
    if office_id == transfer_request.target_office_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot transfer to the same office"
        )
    
    transferred_users = 0
    transferred_cases = 0
    transferred_audit_logs = 0
    
    try:
        # Transfer users
        if transfer_request.transfer_users:
            users_to_transfer = db.query(User).filter(User.office_id == office_id).all()
            for user in users_to_transfer:
                user.office_id = transfer_request.target_office_id
            transferred_users = len(users_to_transfer)
            print(f"🔍 Transferred {transferred_users} users from {source_office.name} to {target_office.name}")
        
        # Transfer cases
        if transfer_request.transfer_cases:
            cases_to_transfer = db.query(Case).filter(Case.office_id == office_id).all()
            for case in cases_to_transfer:
                case.office_id = transfer_request.target_office_id
            transferred_cases = len(cases_to_transfer)
            print(f"🔍 Transferred {transferred_cases} cases from {source_office.name} to {target_office.name}")
        
        # Transfer audit logs
        if transfer_request.transfer_audit_logs:
            from ..models.audit_log import AuditLog
            audit_logs_to_transfer = db.query(AuditLog).filter(AuditLog.office_id == office_id).all()
            for audit_log in audit_logs_to_transfer:
                audit_log.office_id = transfer_request.target_office_id
            transferred_audit_logs = len(audit_logs_to_transfer)
            print(f"🔍 Transferred {transferred_audit_logs} audit logs from {source_office.name} to {target_office.name}")
        
        db.commit()
        
        return OfficeTransferResponse(
            message=f"Successfully transferred data from {source_office.name} to {target_office.name}",
            transferred_users=transferred_users,
            transferred_cases=transferred_cases,
            transferred_audit_logs=transferred_audit_logs,
            source_office_name=source_office.name,
            target_office_name=target_office.name
        )
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error transferring office data: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to transfer office data: {str(e)}"
        )

@router.delete("/office-management/{office_id}")
async def delete_office(
    office_id: str,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Delete office (superuser only) - WARNING: This will delete all associated data"""
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    # Check if office has non-superuser users (superusers don't prevent office deletion)
    non_superuser_count = db.query(User).filter(
        User.office_id == office_id,
        User.role != UserRole.SUPERUSER
    ).count()
    if non_superuser_count > 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot delete office with {non_superuser_count} non-superuser users. Please transfer data first using the transfer endpoint."
        )
    
    # Superusers are no longer tied to offices, so no need to handle them in office deletion
    
    db.delete(office)
    db.commit()
    
    return {"message": f"Office {office.name} deleted successfully"}

@router.post("/office-management/{office_id}/set-default")
async def set_default_office(
    office_id: str,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Set an office as the default office (superuser only)"""
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    if not office.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot set inactive office as default"
        )
    
    try:
        # Remove default flag from all other offices
        db.query(Office).update({Office.is_default: False})
        
        # Set this office as default
        office.is_default = True
        db.commit()
        
        return {"message": f"Office '{office.name}' set as default office"}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error setting default office: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set default office: {str(e)}"
        )

@router.post("/office-management/{office_id}/unset-default")
async def unset_default_office(
    office_id: str,
    current_user: User = Depends(require_superuser),
    db: Session = Depends(get_db)
):
    """Unset an office as the default office (superuser only)"""
    office = db.query(Office).filter(Office.id == office_id).first()
    if not office:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Office not found"
        )
    
    if not office.is_default:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This office is not currently set as default"
        )
    
    try:
        # Unset this office as default
        office.is_default = False
        db.commit()
        
        return {"message": f"Office '{office.name}' is no longer the default office"}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Error unsetting default office: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to unset default office: {str(e)}"
        )
