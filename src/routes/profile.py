from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from ..config.database import get_db
from ..models.user import User
from ..models import Case, AuditLog
from ..models.client_details import ClientDetails
from datetime import datetime
from .auth import get_current_user

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class ProfileUpdateRequest(BaseModel):
    first_name: str = None
    last_name: str = None
    email: EmailStr = None
    phone: str = None

class PasswordChangeRequest(BaseModel):
    current_password: str
    new_password: str

class ProfileResponse(BaseModel):
    id: str
    email: str
    first_name: str = None
    last_name: str = None
    phone: str = None
    role: str
    status: str
    ca_client_number: str | None = None
    office_id: str
    office_name: str = None
    is_office_admin: bool = False
    created_at: str = None
    last_login: str = None
    
    class Config:
        from_attributes = True

@router.put("/update")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user profile information"""
    
    # Check if email is already taken by another user
    if request.email and request.email != current_user.email:
        existing_user = db.query(User).filter(
            User.email == request.email,
            User.id != current_user.id
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email address is already in use"
            )
    
    # Update user fields
    if request.first_name is not None:
        current_user.first_name = request.first_name
    if request.last_name is not None:
        current_user.last_name = request.last_name
    if request.email is not None:
        current_user.email = request.email
    if request.phone is not None:
        current_user.phone = request.phone
    
    # Save changes
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Profile updated successfully"}

@router.put("/change-password")
async def change_password(
    request: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Change user password"""
    
    # Verify current password
    if not pwd_context.verify(request.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    
    # Hash and update password
    current_user.password_hash = pwd_context.hash(request.new_password)
    
    # Save changes
    db.commit()
    
    return {"message": "Password changed successfully"}

@router.get("/me")
async def get_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user profile"""
    
    # Get office name for response
    office_name = current_user.office.name if current_user.office else None
    
    return {
        "id": current_user.id,
        "email": current_user.email,
        "first_name": current_user.first_name,
        "last_name": current_user.last_name,
        "phone": current_user.phone,
        "role": current_user.role.value,
        "status": current_user.status.value,
        "ca_client_number": current_user.ca_client_number,
        "office_id": current_user.office_id,
        "office_name": office_name,
        "is_office_admin": current_user.is_office_admin,
        "created_at": current_user.created_at.isoformat() if current_user.created_at else None,
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
        # Optional information fields
        "ethnicity": current_user.ethnicity,
        "nationality": current_user.nationality,
        "preferred_language": current_user.preferred_language,
        "religion": current_user.religion,
        "gender_identity": current_user.gender_identity,
        "sexual_orientation": current_user.sexual_orientation,
        "disability_status": current_user.disability_status,
        "marital_status": current_user.marital_status,
        "household_type": current_user.household_type,
        "occupation": current_user.occupation,
        "housing_tenure": current_user.housing_tenure,
        "optional_info_completed": current_user.optional_info_completed,
        "optional_info_skipped": current_user.optional_info_skipped,
        "optional_info_never_show": current_user.optional_info_never_show
    }

# Optional Information Models
class OptionalInformationRequest(BaseModel):
    ethnicity: str = None
    nationality: str = None
    preferred_language: str = None
    religion: str = None
    gender_identity: str = None
    sexual_orientation: str = None
    disability_status: str = None
    marital_status: str = None
    household_type: str = None
    occupation: str = None
    housing_tenure: str = None

# Client Details Models
class ClientDetailsRequest(BaseModel):
    # Personal Information
    title: str = None
    first_name: str = None
    surname: str = None
    
    # Contact Details
    home_address: str = None
    postcode: str = None
    date_of_birth: str = None
    gender: str = None
    home_phone: str = None
    mobile_phone: str = None
    email: str = None
    
    # Communication Preferences
    happy_voicemail: bool = False
    happy_text_messages: bool = False
    preferred_contact_email: bool = False
    preferred_contact_mobile: bool = False
    preferred_contact_home_phone: bool = False
    preferred_contact_address: bool = False
    do_not_contact_methods: str = None
    
    # Research & Feedback
    agree_to_feedback: bool = False
    do_not_contact_feedback_methods: str = None

@router.post("/optional-info")
async def submit_optional_info(
    request: OptionalInformationRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit optional demographic information"""
    
    # Update user with optional information
    if request.ethnicity is not None:
        current_user.ethnicity = request.ethnicity
    if request.nationality is not None:
        current_user.nationality = request.nationality
    if request.preferred_language is not None:
        current_user.preferred_language = request.preferred_language
    if request.religion is not None:
        current_user.religion = request.religion
    if request.gender_identity is not None:
        current_user.gender_identity = request.gender_identity
    if request.sexual_orientation is not None:
        current_user.sexual_orientation = request.sexual_orientation
    if request.disability_status is not None:
        current_user.disability_status = request.disability_status
    if request.marital_status is not None:
        current_user.marital_status = request.marital_status
    if request.household_type is not None:
        current_user.household_type = request.household_type
    if request.occupation is not None:
        current_user.occupation = request.occupation
    if request.housing_tenure is not None:
        current_user.housing_tenure = request.housing_tenure
    
    # Mark that user has completed optional information
    current_user.optional_info_completed = True
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Optional information submitted successfully"}

@router.post("/optional-info-skip")
async def skip_optional_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Skip optional information collection"""
    
    # Mark that user has skipped optional information
    current_user.optional_info_skipped = True
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Optional information skipped"}

@router.post("/optional-info-never-show")
async def never_show_optional_info(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark to never show optional information prompt again"""
    
    # Mark that user has chosen to never show optional information
    current_user.optional_info_never_show = True
    
    db.commit()
    db.refresh(current_user)
    
    return {"message": "Optional information prompt disabled"}

@router.get("/client-details")
async def get_client_details(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get client details for current user"""
    
    print(f"🔍 Getting client details for user: {current_user.id}")
    
    # Get client details from the database with raw SQL to avoid enum validation issues
    try:
        # Try normal query first
        client_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    except Exception as e:
        print(f"🔍 Error with normal query: {e}")
        # If that fails, use raw SQL to get the data
        from sqlalchemy import text
        result = db.execute(
            text("SELECT * FROM client_details WHERE user_id = :user_id"),
            {"user_id": current_user.id}
        ).first()
        
        if result:
            # Create a mock object with the raw data
            class MockClientDetails:
                def __init__(self, data):
                    self.id = data.id
                    self.user_id = data.user_id
                    self.title = data.title  # Raw string value
                    self.first_name = data.first_name
                    self.surname = data.surname
                    self.home_address = data.home_address
                    self.postcode = data.postcode
                    self.date_of_birth = data.date_of_birth
                    self.gender = data.gender  # Raw string value
                    self.home_phone = data.home_phone
                    self.mobile_phone = data.mobile_phone
                    self.email = data.email
                    self.happy_voicemail = data.happy_voicemail
                    self.happy_text_messages = data.happy_text_messages
                    self.preferred_contact_email = data.preferred_contact_email
                    self.preferred_contact_mobile = data.preferred_contact_mobile
                    self.preferred_contact_home_phone = data.preferred_contact_home_phone
                    self.preferred_contact_address = data.preferred_contact_address
                    self.do_not_contact_methods = data.do_not_contact_methods
                    self.agree_to_feedback = data.agree_to_feedback
                    self.do_not_contact_feedback_methods = data.do_not_contact_feedback_methods
            
            client_details = MockClientDetails(result)
        else:
            client_details = None
    
    print(f"🔍 Client details found: {client_details is not None}")
    if client_details:
        print(f"🔍 Title: {client_details.title}")
        print(f"🔍 Gender: {client_details.gender}")
    
    if not client_details:
        return {
            "title": "",
            "first_name": "",
            "surname": "",
            "home_address": "",
            "postcode": "",
            "date_of_birth": "",
            "gender": "",
            "home_phone": "",
            "mobile_phone": "",
            "email": "",
            "happy_voicemail": False,
            "happy_text_messages": False,
            "preferred_contact_email": False,
            "preferred_contact_mobile": False,
            "preferred_contact_home_phone": False,
            "preferred_contact_address": False,
            "do_not_contact_methods": "",
            "agree_to_feedback": False,
            "do_not_contact_feedback_methods": ""
        }
    
    return {
        "title": client_details.title or "",
        "first_name": client_details.first_name or "",
        "surname": client_details.surname or "",
        "home_address": client_details.home_address or "",
        "postcode": client_details.postcode or "",
        "date_of_birth": client_details.date_of_birth.isoformat() if hasattr(client_details.date_of_birth, 'isoformat') else (client_details.date_of_birth or ""),
        "gender": client_details.gender or "",
        "home_phone": client_details.home_phone or "",
        "mobile_phone": client_details.mobile_phone or "",
        "email": client_details.email or "",
        "happy_voicemail": client_details.happy_voicemail or False,
        "happy_text_messages": client_details.happy_text_messages or False,
        "preferred_contact_email": client_details.preferred_contact_email or False,
        "preferred_contact_mobile": client_details.preferred_contact_mobile or False,
        "preferred_contact_home_phone": client_details.preferred_contact_home_phone or False,
        "preferred_contact_address": client_details.preferred_contact_address or False,
        "do_not_contact_methods": client_details.do_not_contact_methods or "",
        "agree_to_feedback": client_details.agree_to_feedback or False,
        "do_not_contact_feedback_methods": client_details.do_not_contact_feedback_methods or ""
    }

@router.put("/client-details")
async def update_client_details(
    request: ClientDetailsRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update client details for current user"""
    
    # Get or create client details
    client_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    
    if not client_details:
        # Create new client details
        client_details = ClientDetails(user_id=current_user.id)
        db.add(client_details)
    
    # Update fields
    if request.title is not None:
        client_details.title = request.title
    if request.first_name is not None:
        client_details.first_name = request.first_name
    if request.surname is not None:
        client_details.surname = request.surname
    if request.home_address is not None:
        client_details.home_address = request.home_address
    if request.postcode is not None:
        client_details.postcode = request.postcode
    if request.date_of_birth is not None:
        try:
            client_details.date_of_birth = datetime.strptime(request.date_of_birth, "%Y-%m-%d").date()
        except ValueError:
            pass  # Invalid date format
    if request.gender is not None:
        client_details.gender = request.gender
    if request.home_phone is not None:
        client_details.home_phone = request.home_phone
    if request.mobile_phone is not None:
        client_details.mobile_phone = request.mobile_phone
    if request.email is not None:
        client_details.email = request.email
    if request.happy_voicemail is not None:
        client_details.happy_voicemail = request.happy_voicemail
    if request.happy_text_messages is not None:
        client_details.happy_text_messages = request.happy_text_messages
    if request.preferred_contact_email is not None:
        client_details.preferred_contact_email = request.preferred_contact_email
    if request.preferred_contact_mobile is not None:
        client_details.preferred_contact_mobile = request.preferred_contact_mobile
    if request.preferred_contact_home_phone is not None:
        client_details.preferred_contact_home_phone = request.preferred_contact_home_phone
    if request.preferred_contact_address is not None:
        client_details.preferred_contact_address = request.preferred_contact_address
    if request.do_not_contact_methods is not None:
        client_details.do_not_contact_methods = request.do_not_contact_methods
    if request.agree_to_feedback is not None:
        client_details.agree_to_feedback = request.agree_to_feedback
    if request.do_not_contact_feedback_methods is not None:
        client_details.do_not_contact_feedback_methods = request.do_not_contact_feedback_methods
    
    # Also update user preferences in users table
    import json
    user_preferences = {
        # Communication Preferences
        "happy_voicemail": client_details.happy_voicemail,
        "happy_text_messages": client_details.happy_text_messages,
        
        # Preferred Contact Methods
        "preferred_contact_email": client_details.preferred_contact_email,
        "preferred_contact_mobile": client_details.preferred_contact_mobile,
        "preferred_contact_home_phone": client_details.preferred_contact_home_phone,
        "preferred_contact_address": client_details.preferred_contact_address,
        
        # Research & Feedback
        "agree_to_feedback": client_details.agree_to_feedback,
        
        # Do Not Contact Methods
        "do_not_contact_methods": client_details.do_not_contact_methods or "",
        "do_not_contact_feedback_methods": client_details.do_not_contact_feedback_methods or "",
        
        # Additional metadata
        "preferences_updated_at": datetime.utcnow().isoformat(),
        "preferences_source": "profile_update"
    }
    current_user.preferences = json.dumps(user_preferences)
    
    db.commit()
    db.refresh(client_details)
    
    print(f"🔍 PROFILE: Updated user preferences in users table")
    print(f"🔍 PROFILE: Preferences saved - happy_voicemail: {client_details.happy_voicemail}")
    print(f"🔍 PROFILE: Preferences saved - preferred_contact_email: {client_details.preferred_contact_email}")
    
    return {"message": "Client details updated successfully"}

@router.delete("/delete-case")
async def delete_my_case(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete the current client's case and all associated files."""
    # Only clients can delete their case
    if not getattr(current_user, "is_client", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can delete their case"
        )

    # Find case
    case = db.query(Case).filter(Case.client_id == current_user.id).first()
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No case found for this user"
        )

    # Cleanup files
    from ..utils.file_utils import delete_case_files
    file_cleanup_result = await delete_case_files(case.id, db)

    try:
        # Delete related financial records to avoid FK constraints and ensure full cleanup
        try:
            from ..models.debt import Debt
            from ..models.asset import Asset
            from ..models.income import Income
            from ..models.expenditure import Expenditure

            db.query(Debt).filter(Debt.case_id == case.id).delete()
            db.query(Asset).filter(Asset.case_id == case.id).delete()
            db.query(Income).filter(Income.case_id == case.id).delete()
            db.query(Expenditure).filter(Expenditure.case_id == case.id).delete()
            db.flush()
        except Exception:
            # If model-level deletes fail for any reason, continue with case delete; DB may have ON DELETE CASCADE
            pass

        # Delete the case record
        db.delete(case)
        db.commit()

        # Audit log
        try:
            audit_log = AuditLog(
                user_id=current_user.id,
                office_id=current_user.office_id,
                action="case_deleted",
                resource_type="case",
                resource_id=case.id,
                details=f"User deleted own case - Files: {file_cleanup_result.get('files_deleted', 0)} deleted, {file_cleanup_result.get('files_failed', 0)} failed"
            )
            db.add(audit_log)
            db.commit()
        except Exception:
            db.rollback()

        return {
            "message": "Case deleted successfully",
            "file_cleanup": file_cleanup_result
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete case: {str(e)}"
        )

@router.delete("/delete-account")
async def delete_my_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete the current user's account, including case, files, and client details."""
    # For safety, only allow clients to self-delete via this endpoint
    if not getattr(current_user, "is_client", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can delete their account"
        )

    # Delete user's case(s) and associated files
    from ..utils.file_utils import delete_case_files
    cases = db.query(Case).filter(Case.client_id == current_user.id).all()
    for case in cases:
        try:
            await delete_case_files(case.id, db)
            db.delete(case)
            db.commit()
        except Exception:
            db.rollback()

    # Delete client details (if any)
    try:
        client_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
        if client_details:
            db.delete(client_details)
            db.commit()
    except Exception:
        db.rollback()

    # Capture for response then delete user
    user_email = current_user.email
    user_id = current_user.id

    try:
        db.delete(current_user)
        db.commit()

        # Best-effort audit log (note: user_id reference preserved)
        try:
            audit_log = AuditLog(
                user_id=user_id,
                office_id=None if not hasattr(current_user, 'office_id') else current_user.office_id,
                action="account_deleted",
                resource_type="user",
                resource_id=user_id,
                details=f"User {user_email} deleted their account and all associated data"
            )
            db.add(audit_log)
            db.commit()
        except Exception:
            db.rollback()

        return {"message": "Account deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete account: {str(e)}"
        )
