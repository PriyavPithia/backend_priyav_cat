#!/usr/bin/env python3
"""
Test script to verify email templates are working correctly.
This will test template rendering without actually sending emails.
"""

import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

try:
    from services.email_service import EmailTemplate
    print("✅ Successfully imported EmailTemplate")
except ImportError as e:
    print(f"❌ Failed to import EmailTemplate: {e}")
    sys.exit(1)

def test_template_rendering():
    """Test that all email templates render correctly with sample data"""
    
    # Initialize template handler
    template_handler = EmailTemplate()
    print(f"📁 Template directory: {template_handler.template_dir}")
    print(f"📁 Template directory exists: {template_handler.template_dir.exists()}")
    
    # Test contexts for each template
    test_contexts = {
        'password_reset.html': {
            'user_name': 'John Doe',
            'reset_url': 'https://example.com/reset?token=abc123',
            'expire_hours': 24,
            'subject': 'Password Reset Request - CA Tadley'
        },
        'invitation.html': {
            'user_name': 'Jane Smith',
            'user_email': 'jane.smith@example.com',
            'invitation_url': 'https://example.com/register?invite=xyz789',
            'role': 'Adviser',
            'office_name': 'CA Tadley Main Office',
            'expires_at': 'December 31, 2024 at 11:59 PM',
            'subject': 'Invitation to CA Tadley Debt Tool'
        },
        'client_invitation.html': {
            'user_name': 'Bob Johnson',
            'user_email': 'bob.johnson@example.com',
            'invitation_url': 'https://example.com/register?invite=client123',
            'office_name': 'CA Tadley Main Office',
            'ca_client_number': 'CT-2024-001',
            'expires_at': 'December 31, 2024 at 11:59 PM',
            'subject': 'Welcome to CA Tadley Debt Advice Service'
        },
        'verification_code.html': {
            'user_name': 'Alice Brown',
            'verification_code': '123456',
            'expire_minutes': 10,
            'subject': 'Verification Code - CA Tadley'
        },
        'user_created.html': {
            'user_name': 'Mike Wilson',
            'user_email': 'mike.wilson@example.com',
            'role': 'Manager',
            'office_name': 'CA Tadley Main Office',
            'temp_password': 'TempPass123!',
            'login_url': 'https://example.com/login',
            'created_by': 'Admin User',
            'subject': 'Your CA Tadley Account Has Been Created'
        }
    }
    
    print("\n🧪 Testing template rendering...")
    
    success_count = 0
    total_templates = len(test_contexts)
    
    for template_name, context in test_contexts.items():
        try:
            print(f"\n📧 Testing {template_name}...")
            
            # Render the template
            rendered_html = template_handler.render(template_name, context)
            
            # Basic checks
            if not rendered_html:
                print(f"❌ {template_name}: Empty output")
                continue
                
            if len(rendered_html) < 100:
                print(f"❌ {template_name}: Output too short ({len(rendered_html)} chars)")
                continue
                
            # Check for key elements
            checks = []
            
            # All templates should have these elements
            checks.append(('Citizens Advice Tadley' in rendered_html, 'Contains CA Tadley branding'))
            checks.append(('ca-blue' in rendered_html or '#004b88' in rendered_html or '#0066cc' in rendered_html, 'Contains brand colors'))
            checks.append(('Open Sans' in rendered_html, 'Contains brand font'))
            
            # Template-specific checks
            if 'user_name' in context:
                checks.append((context['user_name'] in rendered_html, f'Contains user name: {context["user_name"]}'))
            
            if 'verification_code' in context:
                checks.append((context['verification_code'] in rendered_html, 'Contains verification code'))
                
            if 'temp_password' in context:
                checks.append((context['temp_password'] in rendered_html, 'Contains temporary password'))
                
            if 'office_name' in context:
                checks.append((context['office_name'] in rendered_html, 'Contains office name'))
            
            # Evaluate checks
            passed_checks = sum(1 for check, _ in checks if check)
            total_checks = len(checks)
            
            if passed_checks == total_checks:
                print(f"✅ {template_name}: All {total_checks} checks passed")
                success_count += 1
            else:
                print(f"⚠️  {template_name}: {passed_checks}/{total_checks} checks passed")
                for check, description in checks:
                    status = "✅" if check else "❌"
                    print(f"   {status} {description}")
            
            # Save rendered template for manual inspection
            output_dir = Path("/tmp/email_templates")
            output_dir.mkdir(exist_ok=True)
            output_file = output_dir / f"rendered_{template_name}"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(rendered_html)
            print(f"📁 Saved rendered template to: {output_file}")
            
        except Exception as e:
            print(f"❌ {template_name}: Error rendering - {e}")
    
    print(f"\n📊 Results: {success_count}/{total_templates} templates rendered successfully")
    
    if success_count == total_templates:
        print("🎉 All email templates are working correctly!")
        return True
    else:
        print("⚠️  Some templates had issues. Check the output above.")
        return False

def test_brand_consistency():
    """Test that all templates use consistent branding"""
    print("\n🎨 Testing brand consistency...")
    
    template_handler = EmailTemplate()
    
    # Sample context for testing
    context = {
        'user_name': 'Test User',
        'user_email': 'test@example.com',
        'role': 'Adviser',
        'office_name': 'Test Office',
        'expires_at': 'Test Date',
        'verification_code': '123456',
        'expire_minutes': 10,
        'temp_password': 'TempPass123',
        'login_url': 'https://example.com/login',
        'created_by': 'Admin',
        'reset_url': 'https://example.com/reset',
        'expire_hours': 24,
        'invitation_url': 'https://example.com/invite'
    }
    
    templates = ['password_reset.html', 'invitation.html', 'client_invitation.html', 
                'verification_code.html', 'user_created.html']
    
    brand_elements = {
        'Citizens Advice Tadley': 'Company name',
        '#004b88': 'Primary brand color',
        '#0066cc': 'Secondary brand color', 
        'Open Sans': 'Brand font',
        'admin@catadley.com': 'Contact email',
        '0800 144 8848': 'Phone number'
    }
    
    consistency_results = {}
    
    for template_name in templates:
        try:
            rendered = template_handler.render(template_name, context)
            consistency_results[template_name] = {}
            
            for element, description in brand_elements.items():
                consistency_results[template_name][element] = element in rendered
                
        except Exception as e:
            print(f"❌ Error testing {template_name}: {e}")
            consistency_results[template_name] = {}
    
    # Report results
    print("\n📋 Brand Consistency Report:")
    print("-" * 80)
    
    for element, description in brand_elements.items():
        print(f"\n🔍 {description} ({element}):")
        for template_name in templates:
            if template_name in consistency_results:
                status = "✅" if consistency_results[template_name].get(element, False) else "❌"
                print(f"   {status} {template_name}")
            else:
                print(f"   ❓ {template_name} (test failed)")
    
    return consistency_results

if __name__ == "__main__":
    print("🚀 Starting email template tests...")
    print("=" * 60)
    
    # Test template rendering
    rendering_success = test_template_rendering()
    
    # Test brand consistency  
    consistency_results = test_brand_consistency()
    
    print("\n" + "=" * 60)
    if rendering_success:
        print("✅ Email template testing completed successfully!")
        print("📧 All templates are using consistent CA Tadley branding")
        print("🎨 Check /tmp/email_templates/ for rendered template previews")
    else:
        print("❌ Some issues were found during testing")
        print("🔧 Please review the output above and fix any issues")
        sys.exit(1)