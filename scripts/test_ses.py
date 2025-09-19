#!/usr/bin/env python3
"""
AWS SES Testing and Management Script
Test email functionality, verify domains, and manage SES configuration
"""

import os
import sys
import asyncio
import logging
from datetime import datetime

# Add the src directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from src.utils.ses_email_service import (
    email_service, send_password_reset_email, 
    send_invitation_email, send_2fa_code_email
)
from src.config.settings import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_ses_connection():
    """Test SES connection and configuration"""
    print("🔧 Testing SES Connection...")
    
    if not settings.use_ses:
        print("❌ SES is not enabled. Set USE_SES=true in your environment.")
        return False
    
    if not settings.aws_access_key_id or not settings.aws_secret_access_key:
        print("❌ AWS credentials not configured.")
        return False
    
    try:
        # Get send quota
        quota = await email_service.get_send_quota()
        if quota:
            print("✅ SES connection successful!")
            print(f"   📊 Send quota: {quota['max_24_hour']:.0f} emails/24h")
            print(f"   📈 Send rate: {quota['max_send_rate']:.1f} emails/second")
            print(f"   📮 Sent today: {quota['sent_last_24_hours']:.0f} emails")
            return True
        else:
            print("❌ Could not retrieve SES quota information")
            return False
    except Exception as e:
        print(f"❌ SES connection failed: {str(e)}")
        return False

async def check_verified_identities():
    """Check verified email addresses and domains"""
    print("\n📧 Checking Verified Identities...")
    
    try:
        identities = await email_service.get_verified_identities()
        if identities:
            print(f"✅ Found {len(identities)} verified identities:")
            for identity in identities:
                print(f"   ✉️  {identity}")
        else:
            print("⚠️  No verified email addresses found.")
            print("   You need to verify your 'from' email address in AWS SES console.")
        
        return identities
    except Exception as e:
        print(f"❌ Failed to check verified identities: {str(e)}")
        return []

async def send_test_email(to_email: str):
    """Send a test email"""
    print(f"\n📤 Sending test email to {to_email}...")
    
    try:
        success = await send_password_reset_email(
            to_email, 
            "test-token-123", 
            "Test User"
        )
        
        if success:
            print("✅ Test email sent successfully!")
        else:
            print("❌ Failed to send test email")
        
        return success
    except Exception as e:
        print(f"❌ Error sending test email: {str(e)}")
        return False

async def test_all_email_types(to_email: str):
    """Test all email template types"""
    print(f"\n🧪 Testing all email types to {to_email}...")
    
    tests = [
        ("Password Reset", lambda: send_password_reset_email(to_email, "test-reset-123", "Test User")),
        ("User Invitation", lambda: send_invitation_email(to_email, "test-invite-123", "Test Admin")),
        ("2FA Code", lambda: send_2fa_code_email(to_email, "123456", "Test User"))
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            print(f"   📧 Testing {test_name}...")
            success = await test_func()
            if success:
                print(f"   ✅ {test_name} sent successfully")
            else:
                print(f"   ❌ {test_name} failed")
            results.append((test_name, success))
        except Exception as e:
            print(f"   ❌ {test_name} error: {str(e)}")
            results.append((test_name, False))
    
    return results

def display_configuration():
    """Display current SES configuration"""
    print("\n⚙️  Current Configuration:")
    print(f"   USE_SES: {settings.use_ses}")
    print(f"   AWS_REGION: {settings.aws_region}")
    print(f"   SES_FROM_EMAIL: {settings.ses_from_email}")
    print(f"   SES_REPLY_TO_EMAIL: {settings.ses_reply_to_email or 'Not set'}")
    print(f"   SES_CONFIGURATION_SET: {settings.ses_configuration_set or 'Not set'}")
    print(f"   AWS_ACCESS_KEY_ID: {'✅ Set' if settings.aws_access_key_id else '❌ Not set'}")
    print(f"   AWS_SECRET_ACCESS_KEY: {'✅ Set' if settings.aws_secret_access_key else '❌ Not set'}")

async def verify_email_address(email: str):
    """Verify an email address in SES"""
    print(f"\n📧 Sending verification email to {email}...")
    
    try:
        success = await email_service.verify_email_address(email)
        if success:
            print("✅ Verification email sent!")
            print("   Check your email and click the verification link.")
        else:
            print("❌ Failed to send verification email")
        
        return success
    except Exception as e:
        print(f"❌ Error sending verification email: {str(e)}")
        return False

def print_setup_instructions():
    """Print SES setup instructions"""
    print("\n📋 AWS SES Setup Instructions:")
    print("=" * 50)
    print("1. 🔑 AWS Credentials:")
    print("   - Set AWS_ACCESS_KEY_ID in your environment")
    print("   - Set AWS_SECRET_ACCESS_KEY in your environment")
    print("   - Or use IAM roles if running on AWS")
    print()
    print("2. 📧 Email Verification:")
    print("   - Go to AWS SES Console")
    print("   - Navigate to 'Verified identities'")
    print(f"   - Verify your from email: {settings.ses_from_email}")
    print("   - Or verify your entire domain")
    print()
    print("3. 🚀 Production Access:")
    print("   - By default, SES is in sandbox mode")
    print("   - Request production access to send to any email")
    print("   - In sandbox mode, you can only send to verified emails")
    print()
    print("4. 🔧 Configuration:")
    print("   - Set USE_SES=true in your environment")
    print("   - Configure SES_FROM_EMAIL")
    print("   - Optionally set SES_REPLY_TO_EMAIL")
    print("   - Set AWS_REGION (default: eu-west-2)")

async def main():
    """Main function"""
    print("🚀 AWS SES Testing and Management Tool")
    print("=" * 50)
    
    # Display configuration
    display_configuration()
    
    if len(sys.argv) < 2:
        print("\nUsage:")
        print("  python test_ses.py <command> [options]")
        print("\nCommands:")
        print("  test-connection          - Test SES connection")
        print("  check-verified           - Check verified identities")
        print("  verify <email>           - Send verification email")
        print("  test-email <email>       - Send test password reset email")
        print("  test-all <email>         - Test all email types")
        print("  setup-help               - Show setup instructions")
        return
    
    command = sys.argv[1]
    
    if command == "test-connection":
        await test_ses_connection()
    
    elif command == "check-verified":
        await check_verified_identities()
    
    elif command == "verify":
        if len(sys.argv) < 3:
            print("❌ Please provide an email address to verify")
            return
        await verify_email_address(sys.argv[2])
    
    elif command == "test-email":
        if len(sys.argv) < 3:
            print("❌ Please provide a recipient email address")
            return
        
        # First check connection and verified identities
        connection_ok = await test_ses_connection()
        if connection_ok:
            identities = await check_verified_identities()
            if identities:
                await send_test_email(sys.argv[2])
            else:
                print("⚠️  No verified identities. Please verify your from email first.")
        
    elif command == "test-all":
        if len(sys.argv) < 3:
            print("❌ Please provide a recipient email address")
            return
        
        # First check connection and verified identities
        connection_ok = await test_ses_connection()
        if connection_ok:
            identities = await check_verified_identities()
            if identities:
                results = await test_all_email_types(sys.argv[2])
                print("\n📊 Test Results Summary:")
                for test_name, success in results:
                    status = "✅" if success else "❌"
                    print(f"   {status} {test_name}")
            else:
                print("⚠️  No verified identities. Please verify your from email first.")
    
    elif command == "setup-help":
        print_setup_instructions()
    
    else:
        print(f"❌ Unknown command: {command}")

if __name__ == "__main__":
    asyncio.run(main())
