#!/usr/bin/env python3
"""
Migration script to update existing ClientDetails records with default communication preferences
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config.database import get_db
from src.models.client_details import ClientDetails
from sqlalchemy.orm import Session

def update_communication_preferences():
    """Update existing ClientDetails records with default communication preferences"""
    
    # Get database session
    db = next(get_db())
    
    try:
        # Find all ClientDetails records that have NULL or empty communication preferences
        client_details_list = db.query(ClientDetails).filter(
            (ClientDetails.happy_voicemail.is_(None)) |
            (ClientDetails.happy_text_messages.is_(None)) |
            (ClientDetails.preferred_contact_email.is_(None)) |
            (ClientDetails.preferred_contact_mobile.is_(None)) |
            (ClientDetails.preferred_contact_home_phone.is_(None)) |
            (ClientDetails.preferred_contact_address.is_(None)) |
            (ClientDetails.agree_to_feedback.is_(None))
        ).all()
        
        print(f"Found {len(client_details_list)} ClientDetails records to update")
        
        updated_count = 0
        for client_details in client_details_list:
            print(f"Updating client details for user: {client_details.user_id}")
            
            # Set default communication preferences
            client_details.happy_voicemail = True
            client_details.happy_text_messages = True
            client_details.preferred_contact_email = True
            client_details.preferred_contact_mobile = True
            client_details.preferred_contact_home_phone = False
            client_details.preferred_contact_address = False
            client_details.do_not_contact_methods = client_details.do_not_contact_methods or ""
            client_details.agree_to_feedback = True
            client_details.do_not_contact_feedback_methods = client_details.do_not_contact_feedback_methods or ""
            
            updated_count += 1
        
        # Commit all changes
        db.commit()
        print(f"✅ Successfully updated {updated_count} ClientDetails records")
        
        # Also create ClientDetails for users who don't have them
        from src.models.user import User
        users_without_client_details = db.query(User).outerjoin(ClientDetails).filter(
            ClientDetails.id.is_(None)
        ).all()
        
        print(f"Found {len(users_without_client_details)} users without ClientDetails")
        
        created_count = 0
        for user in users_without_client_details:
            print(f"Creating ClientDetails for user: {user.email}")
            
            client_details = ClientDetails(
                user_id=user.id,
                first_name=user.first_name or "",
                surname=user.last_name or "",
                home_address="",
                postcode="",
                date_of_birth=None,
                # Set default communication preferences
                happy_voicemail=True,
                happy_text_messages=True,
                preferred_contact_email=True,
                preferred_contact_mobile=True,
                preferred_contact_home_phone=False,
                preferred_contact_address=False,
                do_not_contact_methods="",
                agree_to_feedback=True,
                do_not_contact_feedback_methods=""
            )
            
            db.add(client_details)
            created_count += 1
        
        # Commit all new ClientDetails
        db.commit()
        print(f"✅ Successfully created {created_count} new ClientDetails records")
        
    except Exception as e:
        print(f"❌ Error updating communication preferences: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_communication_preferences()
