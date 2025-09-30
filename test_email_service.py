#!/usr/bin/env python3
"""
Email Service Testing Script for CA Tadley Debt Tool

This script tests the SMTP server configuration and email sending functionality.
"""
import os
import sys
import asyncio
from datetime import datetime, timedelta

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Load test environment
from dotenv import load_dotenv
load_dotenv('.env.test')

from config.settings import settings
from services.email_service import EmailService, EmailServiceError


def print_header(title: str):
    """Print a formatted header"""
    print("\n" + "=" * 60)
    print(f" {title}")
    print("=" * 60)


def print_config():
    """Print current email configuration"""
    print_header("EMAIL CONFIGURATION")
    print(f"SMTP Server: {settings.smtp_server}")
    print(f"SMTP Port: {settings.smtp_port}")
    print(f"SMTP Username: {settings.smtp_username}")
    print(f"SMTP Password: {'*' * len(settings.smtp_password) if settings.smtp_password else 'None'}")
    print(f"Use TLS: {settings.smtp_use_tls}")
    print(f"From Email: {settings.from_email}")
    print(f"Frontend URL: {settings.frontend_url}")


def test_smtp_connection():
    """Test SMTP server connection"""
    print_header("SMTP CONNECTION TEST")
    
    if not all([settings.smtp_server, settings.smtp_username, settings.smtp_password]):
        print("❌ SMTP configuration incomplete!")
        print("Please set SMTP_SERVER, SMTP_USERNAME, and SMTP_PASSWORD in .env.test")
        return False
    
    try:
        email_service = EmailService()
        result = email_service.test_connection()
        
        if result:
            print("✅ SMTP connection successful!")
            return True
        else:
            print("❌ SMTP connection failed!")
            return False
            
    except EmailServiceError as e:
        print(f"❌ SMTP connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False


def test_email_service_instantiation():
    """Test email service can be instantiated"""
    print_header("EMAIL SERVICE INSTANTIATION TEST")
    
    try:
        email_service = EmailService()
        print("✅ EmailService instantiated successfully!")
        return email_service
    except EmailServiceError as e:
        print(f"❌ EmailService instantiation failed: {e}")
        return None
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return None


def test_email_templates():
    """Test email template rendering"""
    print_header("EMAIL TEMPLATE TEST")
    
    try:
        email_service = EmailService()
        
        # Test password reset template
        context = {
            'user_name': 'Test User',
            'reset_url': 'http://localhost:3000/reset-password?token=test-token',
            'reset_token': 'test-token',
            'expire_hours': 24,
            'subject': 'Password Reset Test'
        }
        
        template_html = email_service.template_handler.render('password_reset.html', context)
        
        if 'Test User' in template_html and 'reset-password' in template_html:
            print("✅ Password reset template rendered successfully!")
        else:
            print("❌ Password reset template rendering failed!")
            
        # Test invitation template
        context = {
            'user_name': 'Test Adviser',
            'user_email': 'test@example.com',
            'invitation_url': 'http://localhost:3000/register?invite=test-token',
            'role': 'Adviser',
            'office_name': 'Test Office',
            'expires_at': 'December 31, 2024 at 11:59 PM'
        }
        
        template_html = email_service.template_handler.render('invitation.html', context)
        
        if 'Test Adviser' in template_html and 'Test Office' in template_html:
            print("✅ Invitation template rendered successfully!")
        else:
            print("❌ Invitation template rendering failed!")
            
        return True
        
    except Exception as e:
        print(f"❌ Template test error: {e}")
        return False


def test_invitation_email_sending(test_email: str = None):
    """Test sending invitation email"""
    print_header("INVITATION EMAIL SENDING TEST")
    
    if not test_email:
        print("⚠️  Skipping email sending test - no test email provided")
        print("   To test email sending, provide an email address")
        return False
    
    try:
        email_service = EmailService()
        
        # Test invitation email
        expires_at = datetime.utcnow() + timedelta(days=7)
        
        result = email_service.send_invitation_email(
            email=test_email,
            invitation_token="test-invitation-token-123",
            user_name="Test User",
            role="adviser",
            office_name="Test Office",
            expires_at=expires_at
        )
        
        if result:
            print(f"✅ Invitation email sent successfully to {test_email}!")
            return True
        else:
            print(f"❌ Failed to send invitation email to {test_email}")
            return False
            
    except Exception as e:
        print(f"❌ Invitation email sending error: {e}")
        return False


def test_password_reset_email_sending(test_email: str = None):
    """Test sending password reset email"""
    print_header("PASSWORD RESET EMAIL SENDING TEST")
    
    if not test_email:
        print("⚠️  Skipping email sending test - no test email provided")
        return False
    
    try:
        email_service = EmailService()
        
        result = email_service.send_password_reset_email(
            email=test_email,
            reset_token="test-reset-token-123",
            user_name="Test User"
        )
        
        if result:
            print(f"✅ Password reset email sent successfully to {test_email}!")
            return True
        else:
            print(f"❌ Failed to send password reset email to {test_email}")
            return False
            
    except Exception as e:
        print(f"❌ Password reset email sending error: {e}")
        return False


def test_verification_code_email_sending(test_email: str = None):
    """Test sending 2FA verification code email"""
    print_header("2FA VERIFICATION EMAIL SENDING TEST")
    
    if not test_email:
        print("⚠️  Skipping email sending test - no test email provided")
        return False
    
    try:
        email_service = EmailService()
        
        result = email_service.send_verification_code_email(
            email=test_email,
            code="123456",
            user_name="Test User"
        )
        
        if result:
            print(f"✅ 2FA verification email sent successfully to {test_email}!")
            return True
        else:
            print(f"❌ Failed to send 2FA verification email to {test_email}")
            return False
            
    except Exception as e:
        print(f"❌ 2FA verification email sending error: {e}")
        return False


def main():
    """Main testing function"""
    print_header("CA TADLEY DEBT TOOL - EMAIL SERVICE TEST")
    print("This script tests the SMTP server and email functionality")
    
    # Get test email from user
    test_email = input("\n📧 Enter test email address (or press Enter to skip email sending tests): ").strip()
    if not test_email:
        test_email = None
    
    print_config()
    
    # Run tests
    tests_passed = 0
    total_tests = 0
    
    # Test 1: Email Service Instantiation
    total_tests += 1
    if test_email_service_instantiation():
        tests_passed += 1
    
    # Test 2: SMTP Connection
    total_tests += 1
    smtp_works = test_smtp_connection()
    if smtp_works:
        tests_passed += 1
    
    # Test 3: Template Rendering
    total_tests += 1
    if test_email_templates():
        tests_passed += 1
    
    # Only run email sending tests if SMTP works and test email provided
    if smtp_works and test_email:
        # Test 4: Invitation Email
        total_tests += 1
        if test_invitation_email_sending(test_email):
            tests_passed += 1
        
        # Test 5: Password Reset Email
        total_tests += 1
        if test_password_reset_email_sending(test_email):
            tests_passed += 1
        
        # Test 6: 2FA Verification Email
        total_tests += 1
        if test_verification_code_email_sending(test_email):
            tests_passed += 1
    
    # Summary
    print_header("TEST SUMMARY")
    print(f"Tests passed: {tests_passed}/{total_tests}")
    
    if tests_passed == total_tests:
        print("🎉 All tests passed! Email service is working correctly.")
        return True
    else:
        print("⚠️  Some tests failed. Please check the configuration and fix issues.")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)