from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime, date

from ..config.database import get_db
from ..models import ClientDetails, User, UserRole
from ..schemas.client_details import ClientDetailsCreate, ClientDetailsResponse
from .auth import get_current_user

router = APIRouter(prefix="/client-details", tags=["Client Details"])

@router.post("/register", response_model=ClientDetailsResponse)
async def register_client_details(
    client_data: ClientDetailsCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Register or update client details for a new client"""
    
    print(f"🔍 CLIENT_DETAILS: Registration called for user: {current_user.id}")
    print(f"🔍 CLIENT_DETAILS: User email: {current_user.email}")
    print(f"🔍 CLIENT_DETAILS: User role: {current_user.role}")
    print(f"🔍 CLIENT_DETAILS: Client data received:")
    print(f"   - title: {client_data.title}")
    print(f"   - first_name: {client_data.first_name}")
    print(f"   - surname: {client_data.surname}")
    print(f"   - home_address: {client_data.home_address}")
    print(f"   - postcode: {client_data.postcode}")
    print(f"   - date_of_birth: {client_data.date_of_birth} (type: {type(client_data.date_of_birth)})")
    print(f"   - gender: {client_data.gender}")
    print(f"   - mobile_phone: {client_data.mobile_phone}")
    print(f"   - email: {client_data.email}")
    print(f"\n📞 COMMUNICATION PREFERENCES RECEIVED:")
    print(f"   - happy_voicemail: {client_data.happy_voicemail}")
    print(f"   - happy_text_messages: {client_data.happy_text_messages}")
    print(f"   - preferred_contact_email: {client_data.preferred_contact_email}")
    print(f"   - preferred_contact_mobile: {client_data.preferred_contact_mobile}")
    print(f"   - preferred_contact_home_phone: {client_data.preferred_contact_home_phone}")
    print(f"   - preferred_contact_address: {client_data.preferred_contact_address}")
    print(f"   - agree_to_feedback: {client_data.agree_to_feedback}")
    print(f"   - do_not_contact_methods: {client_data.do_not_contact_methods}")
    print(f"   - do_not_contact_feedback_methods: {client_data.do_not_contact_feedback_methods}")
    
    # Only clients can register details
    if not current_user.is_client:
        print(f"❌ CLIENT_DETAILS: User {current_user.id} is not a client")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only clients can register client details"
        )
    
    # Check if client details already exist
    existing_details = db.query(ClientDetails).filter(ClientDetails.user_id == current_user.id).first()
    print(f"🔍 Existing client details found: {existing_details is not None}")
    
    if existing_details:
        print(f"🔍 Updating existing client details for user: {current_user.id}")
        # Update existing record instead of creating new one
        existing_details.title = client_data.title
        existing_details.first_name = client_data.first_name
        existing_details.surname = client_data.surname
        existing_details.home_address = client_data.home_address
        existing_details.postcode = client_data.postcode
        # Convert string date to date object
        if client_data.date_of_birth:
            try:
                existing_details.date_of_birth = datetime.strptime(client_data.date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                # If date parsing fails, use a default date
                existing_details.date_of_birth = date(1900, 1, 1)
        else:
            existing_details.date_of_birth = date(1900, 1, 1)
        existing_details.gender = client_data.gender
        existing_details.home_phone = client_data.home_phone
        existing_details.mobile_phone = client_data.mobile_phone
        existing_details.email = client_data.email
        existing_details.happy_voicemail = client_data.happy_voicemail
        existing_details.happy_text_messages = client_data.happy_text_messages
        existing_details.preferred_contact_email = client_data.preferred_contact_email
        existing_details.preferred_contact_mobile = client_data.preferred_contact_mobile
        existing_details.preferred_contact_home_phone = client_data.preferred_contact_home_phone
        existing_details.preferred_contact_address = client_data.preferred_contact_address
        existing_details.do_not_contact_methods = json.dumps(client_data.do_not_contact_methods) if client_data.do_not_contact_methods else None
        existing_details.agree_to_feedback = client_data.agree_to_feedback
        existing_details.do_not_contact_feedback_methods = json.dumps(client_data.do_not_contact_feedback_methods) if client_data.do_not_contact_feedback_methods else None
        existing_details.ethnicity = client_data.ethnicity
        existing_details.ethnicity_other = client_data.ethnicity_other
        existing_details.nationality = client_data.nationality
        existing_details.nationality_other = client_data.nationality_other
        existing_details.preferred_language = client_data.preferred_language
        existing_details.preferred_language_other = client_data.preferred_language_other
        existing_details.religion = client_data.religion
        existing_details.religion_other = client_data.religion_other
        existing_details.gender_identity = client_data.gender_identity
        existing_details.gender_identity_other = client_data.gender_identity_other
        existing_details.sexual_orientation = client_data.sexual_orientation
        existing_details.sexual_orientation_other = client_data.sexual_orientation_other
        existing_details.disability_status = client_data.disability_status
        existing_details.disability_details = client_data.disability_details
        existing_details.marital_status = client_data.marital_status
        existing_details.marital_status_other = client_data.marital_status_other
        existing_details.household_type = client_data.household_type
        existing_details.household_type_other = client_data.household_type_other
        existing_details.occupation = client_data.occupation
        existing_details.occupation_other = client_data.occupation_other
        existing_details.housing_tenure = client_data.housing_tenure
        existing_details.housing_tenure_other = client_data.housing_tenure_other
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
            print(f"❌ Error updating client details: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update client details: {str(e)}"
            )
    
    # Create new client details
    print(f"🔍 Creating new client details for user: {current_user.id}")
    client_details = ClientDetails(
        user_id=current_user.id,
        title=client_data.title,
        first_name=client_data.first_name,
        surname=client_data.surname,
        home_address=client_data.home_address,
        postcode=client_data.postcode,
        # Convert string date to date object
        date_of_birth=datetime.strptime(client_data.date_of_birth, "%Y-%m-%d").date() if client_data.date_of_birth else date(1900, 1, 1),
        gender=client_data.gender,
        home_phone=client_data.home_phone,
        mobile_phone=client_data.mobile_phone,
        email=client_data.email,
        happy_voicemail=client_data.happy_voicemail,
        happy_text_messages=client_data.happy_text_messages,
        preferred_contact_email=client_data.preferred_contact_email,
        preferred_contact_mobile=client_data.preferred_contact_mobile,
        preferred_contact_home_phone=client_data.preferred_contact_home_phone,
        preferred_contact_address=client_data.preferred_contact_address,
        do_not_contact_methods=json.dumps(client_data.do_not_contact_methods) if client_data.do_not_contact_methods else None,
        agree_to_feedback=client_data.agree_to_feedback,
        do_not_contact_feedback_methods=json.dumps(client_data.do_not_contact_feedback_methods) if client_data.do_not_contact_feedback_methods else None,
        ethnicity=client_data.ethnicity,
        ethnicity_other=client_data.ethnicity_other,
        nationality=client_data.nationality,
        nationality_other=client_data.nationality_other,
        preferred_language=client_data.preferred_language,
        preferred_language_other=client_data.preferred_language_other,
        religion=client_data.religion,
        religion_other=client_data.religion_other,
        gender_identity=client_data.gender_identity,
        gender_identity_other=client_data.gender_identity_other,
        sexual_orientation=client_data.sexual_orientation,
        sexual_orientation_other=client_data.sexual_orientation_other,
        disability_status=client_data.disability_status,
        disability_details=client_data.disability_details,
        marital_status=client_data.marital_status,
        marital_status_other=client_data.marital_status_other,
        household_type=client_data.household_type,
        household_type_other=client_data.household_type_other,
        occupation=client_data.occupation,
        occupation_other=client_data.occupation_other,
        housing_tenure=client_data.housing_tenure,
        housing_tenure_other=client_data.housing_tenure_other
    )
    
    try:
        db.add(client_details)
        db.commit()
        db.refresh(client_details)
        
        # Update user status to active after registration
        current_user.status = "active"
        db.commit()
        
        print(f"\n✅ SUCCESS: New client details created for user: {current_user.id}")
        print(f"✅ SUCCESS: Communication preferences saved to client_details table:")
        print(f"   - happy_voicemail: {client_details.happy_voicemail}")
        print(f"   - happy_text_messages: {client_details.happy_text_messages}")
        print(f"   - preferred_contact_email: {client_details.preferred_contact_email}")
        print(f"   - preferred_contact_mobile: {client_details.preferred_contact_mobile}")
        print(f"   - preferred_contact_home_phone: {client_details.preferred_contact_home_phone}")
        print(f"   - preferred_contact_address: {client_details.preferred_contact_address}")
        print(f"   - agree_to_feedback: {client_details.agree_to_feedback}")
        print(f"   - do_not_contact_methods: {client_details.do_not_contact_methods}")
        print(f"   - do_not_contact_feedback_methods: {client_details.do_not_contact_feedback_methods}")
        print(f"✅ SUCCESS: Communication preferences also saved to users table")
        
        # Also save preferences to user table
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
            "do_not_contact_methods": client_details.do_not_contact_methods,
            "do_not_contact_feedback_methods": client_details.do_not_contact_feedback_methods,
            
            # Additional metadata
            "preferences_updated_at": datetime.utcnow().isoformat(),
            "preferences_source": "client_details_registration_new"
        }
        current_user.preferences = json.dumps(user_preferences)
        db.commit()
        print(f"✅ SUCCESS: User preferences also saved to users table")
        
        # Convert date to string for response
        if client_details.date_of_birth:
            client_details.date_of_birth = client_details.date_of_birth.isoformat()
        
        return client_details
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to register client details: {str(e)}"
        )

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
