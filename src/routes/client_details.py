from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime, date

from ..config.database import get_db
from ..config.logging import get_logger
from ..models import ClientDetails, User, UserRole
from ..schemas.client_details import ClientDetailsCreate, ClientDetailsResponse
from .auth import get_current_user

router = APIRouter(prefix="/client-details", tags=["Client Details"])
logger = get_logger('client_details')

@router.post("/register", response_model=ClientDetailsResponse)
async def register_client_details(
    client_data: ClientDetailsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register or update client details for a new client"""
    
    logger.info("CLIENT_DETAILS register called", extra={
        'user_id': getattr(current_user, 'id', None),
        'email': getattr(current_user, 'email', None),
        'role': str(getattr(current_user, 'role', '')),
        'payload': {
            'title': client_data.title,
            'first_name': client_data.first_name,
            'surname': client_data.surname,
            'home_address': client_data.home_address,
            'postcode': client_data.postcode,
            'date_of_birth': client_data.date_of_birth,
            'gender': client_data.gender,
            'home_phone': client_data.home_phone,
            'mobile_phone': client_data.mobile_phone,
            'email': client_data.email,
            'happy_voicemail': client_data.happy_voicemail,
            'happy_text_messages': client_data.happy_text_messages,
            'preferred_contact_email': client_data.preferred_contact_email,
            'preferred_contact_mobile': client_data.preferred_contact_mobile,
            'preferred_contact_home_phone': client_data.preferred_contact_home_phone,
            'preferred_contact_address': client_data.preferred_contact_address,
        }
    })
    
    # Only clients can register details
    if not current_user.is_client:
        print(f"❌ CLIENT_DETAILS: User {current_user.id} is not a client")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can register client details"
        )
    
    # Check if client details already exist
    existing_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    logger.info(f"CLIENT_DETAILS existing row: {existing_details is not None}")
    
    # Helper to safely trim strings to column limits
    def _s(v, n=None):
        if v is None:
            return None
        v = str(v)
        return v[:n] if n else v

    # Normalize selected enum-like values to avoid DB constraint issues
    def _normalize_gender(v):
        allowed = {"Male", "Female", "Other", "Prefer not to say"}
        return v if v in allowed else None

    def _normalize_title(v):
        allowed = {"Mr", "Mrs", "Miss", "Ms", "Dr", "Prof", "Other"}
        return v if v in allowed else None

    if existing_details:
        print(f"🔍 Updating existing client details for user: {current_user.id}")
        # Update existing record instead of creating new one
        existing_details.title = _normalize_title(client_data.title)
        existing_details.first_name = _s(client_data.first_name, 100)
        existing_details.surname = _s(client_data.surname, 100)
        existing_details.home_address = _s(client_data.home_address)
        existing_details.postcode = _s((client_data.postcode or '').strip().upper(), 10)
        # Convert string date to date object
        if client_data.date_of_birth:
            try:
                parsed = datetime.strptime(client_data.date_of_birth, "%Y-%m-%d").date()
                if parsed > date.today():
                    parsed = date(1900, 1, 1)
                existing_details.date_of_birth = parsed
            except ValueError:
                # If date parsing fails, use a default date
                existing_details.date_of_birth = date(1900, 1, 1)
        else:
            existing_details.date_of_birth = date(1900, 1, 1)
        existing_details.gender = _normalize_gender(client_data.gender)
        existing_details.home_phone = _s(client_data.home_phone, 20)
        existing_details.mobile_phone = _s(client_data.mobile_phone, 20)
        existing_details.email = _s(client_data.email, 255)
        existing_details.happy_voicemail = client_data.happy_voicemail
        existing_details.happy_text_messages = client_data.happy_text_messages
        existing_details.preferred_contact_email = client_data.preferred_contact_email
        existing_details.preferred_contact_mobile = client_data.preferred_contact_mobile
        existing_details.preferred_contact_home_phone = client_data.preferred_contact_home_phone
        existing_details.preferred_contact_address = client_data.preferred_contact_address
        existing_details.do_not_contact_methods = json.dumps(client_data.do_not_contact_methods) if client_data.do_not_contact_methods else None
        existing_details.agree_to_feedback = client_data.agree_to_feedback
        existing_details.do_not_contact_feedback_methods = json.dumps(client_data.do_not_contact_feedback_methods) if client_data.do_not_contact_feedback_methods else None
        existing_details.ethnicity = _s(client_data.ethnicity, 31)
        existing_details.ethnicity_other = _s(client_data.ethnicity_other, 100)
        existing_details.nationality = _s(client_data.nationality, 100)
        existing_details.nationality_other = _s(client_data.nationality_other, 100)
        existing_details.preferred_language = _s(client_data.preferred_language, 100)
        existing_details.preferred_language_other = _s(client_data.preferred_language_other, 100)
        existing_details.religion = _s(client_data.religion, 100)
        existing_details.religion_other = _s(client_data.religion_other, 100)
        existing_details.gender_identity = _s(client_data.gender_identity, 100)
        existing_details.gender_identity_other = _s(client_data.gender_identity_other, 100)
        existing_details.sexual_orientation = _s(client_data.sexual_orientation, 100)
        existing_details.sexual_orientation_other = _s(client_data.sexual_orientation_other, 100)
        existing_details.disability_status = _s(client_data.disability_status, 26)
        existing_details.disability_details = client_data.disability_details
        existing_details.marital_status = _s(client_data.marital_status, 17)
        existing_details.marital_status_other = _s(client_data.marital_status_other, 100)
        existing_details.household_type = _s(client_data.household_type, 26)
        existing_details.household_type_other = _s(client_data.household_type_other, 100)
        existing_details.occupation = _s(client_data.occupation, 25)
        existing_details.occupation_other = _s(client_data.occupation_other, 100)
        existing_details.housing_tenure = _s(client_data.housing_tenure, 27)
        existing_details.housing_tenure_other = _s(client_data.housing_tenure_other, 100)
        existing_details.updated_at = datetime.utcnow()
        
        try:
            # Also update user preferences with all communication preferences
            user_preferences = {
                # Communication Preferences
                "happy_voicemail": client_data.happy_voicemail,
                "happy_text_messages": client_data.happy_text_messages,
                
                # Preferred Contact Methods
                "preferred_contact_email": client_data.preferred_contact_email,
                "preferred_contact_mobile": client_data.preferred_contact_mobile,
                "preferred_contact_home_phone": client_data.preferred_contact_home_phone,
                "preferred_contact_address": client_data.preferred_contact_address,
                
                # Research & Feedback
                "agree_to_feedback": client_data.agree_to_feedback,
                
                # Do Not Contact Methods
                "do_not_contact_methods": client_data.do_not_contact_methods or [],
                "do_not_contact_feedback_methods": client_data.do_not_contact_feedback_methods or [],
                
                # Additional metadata
                "preferences_updated_at": datetime.utcnow().isoformat(),
                "preferences_source": "client_details_registration"
            }
            current_user.preferences = json.dumps(user_preferences)
            
            print(f"\n💾 SAVING COMMUNICATION PREFERENCES TO USER TABLE:")
            print(f"   📞 Communication Preferences:")
            print(f"     - happy_voicemail: {client_data.happy_voicemail}")
            print(f"     - happy_text_messages: {client_data.happy_text_messages}")
            print(f"   📧 Preferred Contact Methods:")
            print(f"     - preferred_contact_email: {client_data.preferred_contact_email}")
            print(f"     - preferred_contact_mobile: {client_data.preferred_contact_mobile}")
            print(f"     - preferred_contact_home_phone: {client_data.preferred_contact_home_phone}")
            print(f"     - preferred_contact_address: {client_data.preferred_contact_address}")
            print(f"   📊 Research & Feedback:")
            print(f"     - agree_to_feedback: {client_data.agree_to_feedback}")
            print(f"   🚫 Do Not Contact Methods:")
            print(f"     - do_not_contact_methods: {client_data.do_not_contact_methods}")
            print(f"     - do_not_contact_feedback_methods: {client_data.do_not_contact_feedback_methods}")
            
            db.commit()
            db.refresh(existing_details)
            print(f"\n✅ SUCCESS: Client details updated for user: {current_user.id}")
            print(f"✅ SUCCESS: Communication preferences saved to client_details table:")
            print(f"   - happy_voicemail: {existing_details.happy_voicemail}")
            print(f"   - happy_text_messages: {existing_details.happy_text_messages}")
            print(f"   - preferred_contact_email: {existing_details.preferred_contact_email}")
            print(f"   - preferred_contact_mobile: {existing_details.preferred_contact_mobile}")
            print(f"   - preferred_contact_home_phone: {existing_details.preferred_contact_home_phone}")
            print(f"   - preferred_contact_address: {existing_details.preferred_contact_address}")
            print(f"   - agree_to_feedback: {existing_details.agree_to_feedback}")
            print(f"   - do_not_contact_methods: {existing_details.do_not_contact_methods}")
            print(f"   - do_not_contact_feedback_methods: {existing_details.do_not_contact_feedback_methods}")
            print(f"✅ SUCCESS: Communication preferences also saved to users table")
            
            # Convert date to string for response
            if existing_details.date_of_birth:
                existing_details.date_of_birth = existing_details.date_of_birth.isoformat()
            
            return existing_details
        except Exception as e:
            db.rollback()
            logger.exception("CLIENT_DETAILS update failed", extra={'user_id': current_user.id})
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update client details: {str(e)}"
            )
    
    # Create new client details
    print(f"🔍 Creating new client details for user: {current_user.id}")
    # Parse and clamp date_of_birth
    if client_data.date_of_birth:
        try:
            _dob = datetime.strptime(client_data.date_of_birth, "%Y-%m-%d").date()
            if _dob > date.today():
                _dob = date(1900, 1, 1)
        except ValueError:
            _dob = date(1900, 1, 1)
    else:
        _dob = date(1900, 1, 1)

    client_details = ClientDetails(
        user_id=current_user.id,
        title=_normalize_title(client_data.title),
        first_name=_s(client_data.first_name, 100),
        surname=_s(client_data.surname, 100),
        home_address=_s(client_data.home_address),
        postcode=_s((client_data.postcode or '').strip().upper(), 10),
        # Convert string date to date object (with future-date guard)
        date_of_birth=_dob,
        gender=_normalize_gender(client_data.gender),
        home_phone=_s(client_data.home_phone, 20),
        mobile_phone=_s(client_data.mobile_phone, 20),
        email=_s(client_data.email, 255),
        happy_voicemail=client_data.happy_voicemail,
        happy_text_messages=client_data.happy_text_messages,
        preferred_contact_email=client_data.preferred_contact_email,
        preferred_contact_mobile=client_data.preferred_contact_mobile,
        preferred_contact_home_phone=client_data.preferred_contact_home_phone,
        preferred_contact_address=client_data.preferred_contact_address,
        do_not_contact_methods=json.dumps(client_data.do_not_contact_methods) if client_data.do_not_contact_methods else None,
        agree_to_feedback=client_data.agree_to_feedback,
        do_not_contact_feedback_methods=json.dumps(client_data.do_not_contact_feedback_methods) if client_data.do_not_contact_feedback_methods else None,
        ethnicity=_s(client_data.ethnicity, 31),
        ethnicity_other=_s(client_data.ethnicity_other, 100),
        nationality=_s(client_data.nationality, 100),
        nationality_other=_s(client_data.nationality_other, 100),
        preferred_language=_s(client_data.preferred_language, 100),
        preferred_language_other=_s(client_data.preferred_language_other, 100),
        religion=_s(client_data.religion, 100),
        religion_other=_s(client_data.religion_other, 100),
        gender_identity=_s(client_data.gender_identity, 100),
        gender_identity_other=_s(client_data.gender_identity_other, 100),
        sexual_orientation=_s(client_data.sexual_orientation, 100),
        sexual_orientation_other=_s(client_data.sexual_orientation_other, 100),
        disability_status=_s(client_data.disability_status, 26),
        disability_details=client_data.disability_details,
        marital_status=_s(client_data.marital_status, 17),
        marital_status_other=_s(client_data.marital_status_other, 100),
        household_type=_s(client_data.household_type, 26),
        household_type_other=_s(client_data.household_type_other, 100),
        occupation=_s(client_data.occupation, 25),
        occupation_other=_s(client_data.occupation_other, 100),
        housing_tenure=_s(client_data.housing_tenure, 27),
        housing_tenure_other=_s(client_data.housing_tenure_other, 100)
    )

    # Log prepared fields
    logger.info("CLIENT_DETAILS prepared for insert", extra={
        'user_id': current_user.id,
        'prepared': {
            'title': client_details.title,
            'first_name': client_details.first_name,
            'surname': client_details.surname,
            'postcode': client_details.postcode,
            'date_of_birth': str(client_details.date_of_birth),
            'gender': client_details.gender,
            'mobile_phone': client_details.mobile_phone,
        }
    })

    # Commit with robust error logging
    try:
        db.add(client_details)
        db.commit()
        db.refresh(client_details)
    except Exception as e:
        db.rollback()
        logger.exception("CLIENT_DETAILS insert failed", extra={'user_id': current_user.id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register client details: {str(e)}"
        )

    # Update user preferences and finalize (separate try so we do not duplicate insert)
    try:
        # Update user status to active after registration
        try:
            current_user.status = "active"
            db.commit()
        except Exception:
            db.rollback()
        
        # Also save preferences to user table
        user_preferences = {
            "happy_voicemail": client_details.happy_voicemail,
            "happy_text_messages": client_details.happy_text_messages,
            "preferred_contact_email": client_details.preferred_contact_email,
            "preferred_contact_mobile": client_details.preferred_contact_mobile,
            "preferred_contact_home_phone": client_details.preferred_contact_home_phone,
            "preferred_contact_address": client_details.preferred_contact_address,
            "agree_to_feedback": client_details.agree_to_feedback,
            "do_not_contact_methods": client_details.do_not_contact_methods,
            "do_not_contact_feedback_methods": client_details.do_not_contact_feedback_methods,
            "preferences_updated_at": datetime.utcnow().isoformat(),
            "preferences_source": "client_details_registration_new"
        }
        current_user.preferences = json.dumps(user_preferences)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.exception("CLIENT_DETAILS finalize failed", extra={'user_id': current_user.id})
        # Do not fail the entire operation; preferences are optional

    # Convert date to string for response
    if client_details.date_of_birth:
        client_details.date_of_birth = client_details.date_of_birth.isoformat()
    return client_details

@router.get("/my-details", response_model=ClientDetailsResponse)
async def get_my_client_details(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get client details for the current user"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access client details"
        )
    
    client_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    
    if not client_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client details not found"
        )
    
    # Also log user preferences from users table
    user_preferences = current_user.get_preferences()
    print(f"🔍 CLIENT_DETAILS: User preferences from users table: {user_preferences}")
    
    return client_details

@router.get("/my-preferences")
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user preferences from both client_details and users table"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can access preferences"
        )
    
    # Get preferences from client_details table
    client_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    
    # Get preferences from users table
    user_preferences = current_user.get_preferences()
    
    print(f"🔍 PREFERENCES: Client details preferences: {client_details.get_preferences() if client_details else 'No client details'}")
    print(f"🔍 PREFERENCES: User table preferences: {user_preferences}")
    
    return {
        "client_details_preferences": {
            "happy_voicemail": client_details.happy_voicemail if client_details else None,
            "happy_text_messages": client_details.happy_text_messages if client_details else None,
            "preferred_contact_email": client_details.preferred_contact_email if client_details else None,
            "preferred_contact_mobile": client_details.preferred_contact_mobile if client_details else None,
            "preferred_contact_home_phone": client_details.preferred_contact_home_phone if client_details else None,
            "preferred_contact_address": client_details.preferred_contact_address if client_details else None,
            "agree_to_feedback": client_details.agree_to_feedback if client_details else None,
        } if client_details else None,
        "user_table_preferences": user_preferences,
        "user_id": current_user.id,
        "email": current_user.email
    }

@router.put("/update", response_model=ClientDetailsResponse)
async def update_client_details(
    client_data: ClientDetailsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update client details for the current user"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can update client details"
        )
    
    client_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    
    if not client_details:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client details not found"
        )
    
    # Update fields
    client_details.title = client_data.title
    client_details.first_name = client_data.first_name
    client_details.surname = client_data.surname
    client_details.home_address = client_data.home_address
    client_details.postcode = client_data.postcode
    client_details.date_of_birth = client_data.date_of_birth
    client_details.gender = client_data.gender
    client_details.home_phone = client_data.home_phone
    client_details.mobile_phone = client_data.mobile_phone
    client_details.email = client_data.email
    client_details.happy_voicemail = client_data.happy_voicemail
    client_details.happy_text_messages = client_data.happy_text_messages
    client_details.preferred_contact_email = client_data.preferred_contact_email
    client_details.preferred_contact_mobile = client_data.preferred_contact_mobile
    client_details.preferred_contact_home_phone = client_data.preferred_contact_home_phone
    client_details.preferred_contact_address = client_data.preferred_contact_address
    client_details.do_not_contact_methods = json.dumps(client_data.do_not_contact_methods) if client_data.do_not_contact_methods else None
    client_details.agree_to_feedback = client_data.agree_to_feedback
    client_details.do_not_contact_feedback_methods = json.dumps(client_data.do_not_contact_feedback_methods) if client_data.do_not_contact_feedback_methods else None
    client_details.ethnicity = client_data.ethnicity
    client_details.ethnicity_other = client_data.ethnicity_other
    client_details.nationality = client_data.nationality
    client_details.nationality_other = client_data.nationality_other
    client_details.preferred_language = client_data.preferred_language
    client_details.preferred_language_other = client_data.preferred_language_other
    client_details.religion = client_data.religion
    client_details.religion_other = client_data.religion_other
    client_details.gender_identity = client_data.gender_identity
    client_details.gender_identity_other = client_data.gender_identity_other
    client_details.sexual_orientation = client_data.sexual_orientation
    client_details.sexual_orientation_other = client_data.sexual_orientation_other
    client_details.disability_status = client_data.disability_status
    client_details.disability_details = client_data.disability_details
    client_details.marital_status = client_data.marital_status
    client_details.marital_status_other = client_data.marital_status_other
    client_details.household_type = client_data.household_type
    client_details.household_type_other = client_data.household_type_other
    client_details.occupation = client_data.occupation
    client_details.occupation_other = client_data.occupation_other
    client_details.housing_tenure = client_data.housing_tenure
    client_details.housing_tenure_other = client_data.housing_tenure_other
    client_details.updated_at = datetime.utcnow()
    
    try:
        db.commit()
        db.refresh(client_details)
        return client_details
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update client details: {str(e)}"
        )

@router.get("/check-registration")
async def check_registration_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if client has completed registration"""
    
    if not current_user.is_client:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can check registration status"
        )
    
    client_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    
    return {
        "is_registered": client_details is not None,
        "has_completed_registration": client_details is not None
    }
