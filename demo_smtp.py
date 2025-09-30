#!/usr/bin/env python3
"""
Demo script to test SMTP with Gmail (requires real Gmail credentials)
"""
import os
import sys
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from dotenv import load_dotenv

def test_with_gmail():
    """Test with Gmail SMTP - requires user to provide credentials"""
    print("=== GMAIL SMTP TEST ===")
    print("This test requires a Gmail account with 2FA enabled and an App Password.")
    print("Setup instructions:")
    print("1. Enable 2-Factor Authentication on your Gmail account")
    print("2. Go to https://myaccount.google.com/apppasswords")
    print("3. Generate an App Password for 'Mail'")
    print("4. Use that 16-character password below")
    print()
    
    gmail_email = input("Enter your Gmail email address (or press Enter to skip): ").strip()
    if not gmail_email:
        print("⏭️ Skipping Gmail test")
        return False
        
    gmail_password = input("Enter your Gmail App Password (16 characters): ").strip()
    if not gmail_password:
        print("⏭️ Skipping Gmail test - no password provided")
        return False
    
    test_email = input("Enter email address to send test to (or press Enter to use your Gmail): ").strip()
    if not test_email:
        test_email = gmail_email
    
    # Set environment variables for Gmail
    os.environ['SMTP_SERVER'] = 'smtp.gmail.com'
    os.environ['SMTP_PORT'] = '587'
    os.environ['SMTP_USERNAME'] = gmail_email
    os.environ['SMTP_PASSWORD'] = gmail_password
    os.environ['SMTP_USE_TLS'] = 'true'
    os.environ['FROM_EMAIL'] = gmail_email
    
    # Import after setting environment
    from config.settings import Settings
    from services.email_service import EmailService
    
    # Create new settings with Gmail config
    settings = Settings()
    
    try:
        print(f"\n🔄 Testing SMTP connection to {settings.smtp_server}...")
        email_service = EmailService()
        
        # Test connection
        if email_service.test_connection():
            print("✅ SMTP connection successful!")
            
            # Test invitation email
            print(f"\n📧 Sending test invitation email to {test_email}...")
            expires_at = datetime.now() + timedelta(days=7)
            
            result = email_service.send_invitation_email(
                email=test_email,
                invitation_token="demo-invitation-token-123",
                user_name="Test User",
                role="adviser",
                office_name="Citizens Advice Tadley (Demo)",
                expires_at=expires_at
            )
            
            if result:
                print("✅ Invitation email sent successfully!")
                print(f"📬 Check your inbox at {test_email}")
                
                # Test password reset email
                print(f"\n📧 Sending test password reset email to {test_email}...")
                
                result2 = email_service.send_password_reset_email(
                    email=test_email,
                    reset_token="demo-reset-token-456",
                    user_name="Test User"
                )
                
                if result2:
                    print("✅ Password reset email sent successfully!")
                    print("🎉 Gmail SMTP test completed successfully!")
                    return True
                else:
                    print("❌ Password reset email failed")
                    return False
            else:
                print("❌ Invitation email failed")
                return False
        else:
            print("❌ SMTP connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Gmail SMTP test failed: {e}")
        return False


def test_with_mailtrap():
    """Test with Mailtrap - requires user to provide credentials"""
    print("\n=== MAILTRAP SMTP TEST ===")
    print("This test requires a Mailtrap account (free at https://mailtrap.io/)")
    print("Setup instructions:")
    print("1. Sign up at https://mailtrap.io/")
    print("2. Go to your inbox settings")
    print("3. Get your SMTP credentials")
    print()
    
    mailtrap_user = input("Enter your Mailtrap username (or press Enter to skip): ").strip()
    if not mailtrap_user:
        print("⏭️ Skipping Mailtrap test")
        return False
        
    mailtrap_password = input("Enter your Mailtrap password: ").strip()
    if not mailtrap_password:
        print("⏭️ Skipping Mailtrap test - no password provided")
        return False
    
    # Set environment variables for Mailtrap
    os.environ['SMTP_SERVER'] = 'sandbox.smtp.mailtrap.io'
    os.environ['SMTP_PORT'] = '2525'
    os.environ['SMTP_USERNAME'] = mailtrap_user
    os.environ['SMTP_PASSWORD'] = mailtrap_password
    os.environ['SMTP_USE_TLS'] = 'true'
    os.environ['FROM_EMAIL'] = 'test@citizensadvicetadley.org.uk'
    
    # Import after setting environment
    from config.settings import Settings
    from services.email_service import EmailService
    
    # Create new settings with Mailtrap config
    settings = Settings()
    
    try:
        print(f"\n🔄 Testing SMTP connection to {settings.smtp_server}...")
        email_service = EmailService()
        
        # Test connection
        if email_service.test_connection():
            print("✅ SMTP connection successful!")
            
            # Test invitation email
            print(f"\n📧 Sending test invitation email...")
            expires_at = datetime.now() + timedelta(days=7)
            
            result = email_service.send_invitation_email(
                email="test@example.com",
                invitation_token="demo-invitation-token-123",
                user_name="Test User",
                role="adviser",
                office_name="Citizens Advice Tadley (Demo)",
                expires_at=expires_at
            )
            
            if result:
                print("✅ Invitation email sent successfully!")
                print("📬 Check your Mailtrap inbox")
                
                # Test 2FA code email
                print(f"\n📧 Sending test 2FA verification email...")
                
                result2 = email_service.send_verification_code_email(
                    email="test@example.com",
                    code="123456",
                    user_name="Test User"
                )
                
                if result2:
                    print("✅ 2FA verification email sent successfully!")
                    print("🎉 Mailtrap SMTP test completed successfully!")
                    return True
                else:
                    print("❌ 2FA verification email failed")
                    return False
            else:
                print("❌ Invitation email failed")
                return False
        else:
            print("❌ SMTP connection failed")
            return False
            
    except Exception as e:
        print(f"❌ Mailtrap SMTP test failed: {e}")
        return False


def main():
    """Main function"""
    print("🌟 CA TADLEY DEBT TOOL - SMTP DEMO")
    print("=" * 60)
    print("This demo tests email sending with real SMTP providers.")
    print("Choose an option to test with real email delivery.")
    print()
    
    success = False
    
    while True:
        print("Options:")
        print("1. Test with Gmail SMTP (real email delivery)")
        print("2. Test with Mailtrap (testing service)")
        print("3. Exit")
        
        choice = input("\nEnter your choice (1-3): ").strip()
        
        if choice == "1":
            success = test_with_gmail()
            break
        elif choice == "2":
            success = test_with_mailtrap()
            break
        elif choice == "3":
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice. Please enter 1, 2, or 3.")
    
    if success:
        print("\n🎉 SMTP testing completed successfully!")
        print("✅ Email service is working correctly with real SMTP provider")
        print("✅ Invitation emails can be sent")
        print("✅ Templates are rendering properly")
    else:
        print("\n⚠️  SMTP testing was skipped or failed")
        print("💡 To enable email functionality, configure SMTP settings in .env")


if __name__ == "__main__":
    main()