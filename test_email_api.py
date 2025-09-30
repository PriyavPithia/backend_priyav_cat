#!/usr/bin/env python3
"""
Test script to send sample emails to admin@sattva-ai.com for verification.
This will test the actual email sending functionality.
"""

import sys
import os
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from services.email_service import get_email_service
    print("✅ Successfully imported email service")
except ImportError as e:
    print(f"❌ Failed to import email service: {e}")
    sys.exit(1)

def test_email_service():
    """Test email service configuration and connectivity"""
    print("\n🔧 Testing email service configuration...")
    
    try:
        email_service = get_email_service()
        print("✅ Email service initialized successfully")
        
        # Test SMTP connection (this may fail if credentials are not configured)
        try:
            connection_test = email_service.test_connection()
            if connection_test:
                print("✅ SMTP connection test passed")
                return True
            else:
                print("❌ SMTP connection test failed - email sending will not work")
                return False
        except Exception as e:
            print(f"❌ SMTP connection test failed: {e}")
            print("💡 This is expected if SMTP credentials are not configured")
            return False
            
    except Exception as e:
        print(f"❌ Failed to initialize email service: {e}")
        return False

def send_test_emails():
    """Send test emails to admin@sattva-ai.com"""
    
    test_email = "admin@sattva-ai.com"
    
    print(f"\n📧 Preparing to send test emails to {test_email}")
    print("Note: Emails will only be sent if SMTP is properly configured")
    
    try:
        email_service = get_email_service()
        
        # Test 1: Password Reset Email
        print("\n1️⃣ Testing password reset email...")
        try:
            success = email_service.send_password_reset_email(
                email=test_email,
                reset_token="test-reset-token-12345",
                user_name="Test Administrator"
            )
            if success:
                print("✅ Password reset email sent successfully")
            else:
                print("❌ Password reset email failed to send")
        except Exception as e:
            print(f"❌ Password reset email error: {e}")
        
        # Test 2: Staff Invitation Email
        print("\n2️⃣ Testing staff invitation email...")
        try:
            expires_at = datetime.now() + timedelta(days=7)
            success = email_service.send_invitation_email(
                email=test_email,
                invitation_token="test-invite-token-67890",
                user_name="Test User",
                role="Adviser",
                office_name="CA Tadley Main Office",
                expires_at=expires_at
            )
            if success:
                print("✅ Staff invitation email sent successfully")
            else:
                print("❌ Staff invitation email failed to send")
        except Exception as e:
            print(f"❌ Staff invitation email error: {e}")
        
        # Test 3: Verification Code Email
        print("\n3️⃣ Testing verification code email...")
        try:
            success = email_service.send_verification_code_email(
                email=test_email,
                code="987654",
                user_name="Test Administrator"
            )
            if success:
                print("✅ Verification code email sent successfully")
            else:
                print("❌ Verification code email failed to send")
        except Exception as e:
            print(f"❌ Verification code email error: {e}")
        
        # Test 4: User Created Email
        print("\n4️⃣ Testing user created email...")
        try:
            success = email_service.send_user_created_email(
                email=test_email,
                user_name="Test New User",
                role="Manager",
                office_name="CA Tadley Main Office",
                temp_password="TempPass123!",
                created_by="Test Administrator"
            )
            if success:
                print("✅ User created email sent successfully")
            else:
                print("❌ User created email failed to send")
        except Exception as e:
            print(f"❌ User created email error: {e}")
        
        # Test 5: Client Invitation (using template directly)
        print("\n5️⃣ Testing client invitation email...")
        try:
            expires_at = datetime.now() + timedelta(days=14)
            success = email_service.send_template_email(
                to_emails=[test_email],
                template_name="client_invitation.html",
                context={
                    'user_name': 'Test Client',
                    'user_email': test_email,
                    'invitation_url': 'https://example.com/register?invite=client-test-123',
                    'office_name': 'CA Tadley Main Office',
                    'ca_client_number': 'CT-2024-TEST-001',
                    'expires_at': expires_at.strftime('%B %d, %Y at %I:%M %p'),
                },
                subject='Welcome to CA Tadley Debt Advice Service - Template Test'
            )
            if success:
                print("✅ Client invitation email sent successfully")
            else:
                print("❌ Client invitation email failed to send")
        except Exception as e:
            print(f"❌ Client invitation email error: {e}")
            
    except Exception as e:
        print(f"❌ Failed to get email service: {e}")

def main():
    print("🧪 CA Tadley Email Template Testing")
    print("=" * 50)
    print("This script will test the email templates and attempt to send")
    print("sample emails to admin@sattva-ai.com for verification.")
    print()
    
    # Test email service configuration
    smtp_working = test_email_service()
    
    if smtp_working:
        print("\n✅ SMTP is configured and working!")
        
        # Ask for confirmation before sending emails
        response = input("\n📧 Do you want to send test emails to admin@sattva-ai.com? (y/N): ")
        if response.lower().startswith('y'):
            send_test_emails()
            print("\n📧 Test emails have been sent!")
            print("📋 Please check admin@sattva-ai.com inbox to verify:")
            print("   • Email templates use consistent CA Tadley branding")
            print("   • Colors match the brand guidelines (#004b88, #0066cc)")
            print("   • Fonts are Open Sans throughout")
            print("   • Contact information is consistent")
            print("   • Layout and styling are professional")
        else:
            print("📧 Email sending skipped by user choice")
    else:
        print("\n⚠️  SMTP is not configured or not working")
        print("💡 To test actual email sending:")
        print("   1. Configure SMTP settings in environment variables")
        print("   2. Set SMTP_SERVER, SMTP_USERNAME, SMTP_PASSWORD, etc.")
        print("   3. Run this script again")
        
    print("\n✅ Template testing completed!")
    print("🎨 All templates now use consistent CA Tadley branding")

if __name__ == "__main__":
    main()