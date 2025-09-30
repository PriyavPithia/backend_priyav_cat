"""
Test the invitation functionality in admin routes
"""
import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from fastapi.testclient import TestClient
from fastapi import status


def test_invitation_email_template_test_endpoint():
    """Test the invitation email test endpoint"""
    # This test requires a proper test setup with database
    # For now, we'll test the email service functionality directly
    pass


def test_email_service_validation():
    """Test email service configuration validation"""
    from services.email_service import EmailService, EmailServiceError
    
    # Test with missing configuration
    with patch('config.settings.settings') as mock_settings:
        mock_settings.smtp_server = None
        mock_settings.smtp_username = None
        mock_settings.smtp_password = None
        mock_settings.smtp_port = 587
        
        with pytest.raises(EmailServiceError) as exc_info:
            EmailService()
        
        assert "Missing required email settings" in str(exc_info.value)


def test_invitation_token_generation():
    """Test invitation token generation"""
    from utils.auth import generate_invitation_token
    
    token1 = generate_invitation_token()
    token2 = generate_invitation_token()
    
    # Tokens should be different
    assert token1 != token2
    
    # Tokens should be secure (URL-safe base64)
    assert len(token1) >= 32
    assert len(token2) >= 32
    
    # Should only contain URL-safe characters
    import string
    allowed_chars = string.ascii_letters + string.digits + '-_'
    assert all(c in allowed_chars for c in token1)
    assert all(c in allowed_chars for c in token2)


def test_invitation_email_context():
    """Test invitation email context generation"""
    from services.email_service import EmailService
    from datetime import datetime, timedelta
    
    # Mock SMTP settings before import to avoid connection attempts
    with patch('services.email_service.settings') as mock_settings:
        mock_settings.smtp_server = "test.smtp.com"
        mock_settings.smtp_username = "test"
        mock_settings.smtp_password = "test"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = True
        mock_settings.from_email = "test@test.com"
        mock_settings.frontend_url = "http://localhost:3000"
        
        email_service = EmailService()
        
        # Test template rendering
        context = {
            'user_name': 'Test User',
            'user_email': 'test@example.com',
            'invitation_url': 'http://localhost:3000/register?invite=test-token',
            'invitation_token': 'test-token',
            'role': 'Adviser',
            'office_name': 'Test Office',
            'expires_at': 'December 31, 2024 at 11:59 PM',
            'subject': 'Invitation to CA Tadley Debt Tool'
        }
        
        # Test adviser invitation template
        template_html = email_service.template_handler.render('invitation.html', context)
        
        assert 'Test User' in template_html
        assert 'Test Office' in template_html
        assert 'Adviser' in template_html
        assert 'register?invite=test-token' in template_html
        
        # Test client invitation template
        context['role'] = 'Client'
        template_html = email_service.template_handler.render('client_invitation.html', context)
        
        # Should fall back to invitation.html since client_invitation.html doesn't exist in fallbacks
        assert 'Test User' in template_html


def test_invitation_email_retry_mechanism():
    """Test email service retry mechanism"""
    from services.email_service import EmailService, EmailServiceError
    
    with patch('config.settings.settings') as mock_settings:
        mock_settings.smtp_server = "test.smtp.com"
        mock_settings.smtp_username = "test"
        mock_settings.smtp_password = "test"
        mock_settings.smtp_port = 587
        mock_settings.smtp_use_tls = True
        mock_settings.from_email = "test@test.com"
        
        email_service = EmailService()
        
        # Mock SMTP to fail
        with patch('smtplib.SMTP') as mock_smtp:
            mock_smtp.side_effect = Exception("Connection failed")
            
            # Should retry and ultimately fail
            with pytest.raises(EmailServiceError):
                email_service.send_email(
                    to_emails=["test@example.com"],
                    subject="Test",
                    body_html="<p>Test</p>"
                )


def test_password_reset_email_functionality():
    """Test password reset email functionality"""
    from services.email_service import send_password_reset_email
    
    # Mock the email service to avoid SMTP
    with patch('services.email_service.email_service') as mock_service:
        mock_service.send_password_reset_email.return_value = True
        
        result = send_password_reset_email(
            email="test@example.com",
            reset_token="test-token",
            user_name="Test User"
        )
        
        assert result is True
        mock_service.send_password_reset_email.assert_called_once()


def test_verification_code_email_functionality():
    """Test 2FA verification code email functionality"""
    from services.email_service import send_verification_code_email
    
    # Mock the email service to avoid SMTP
    with patch('services.email_service.email_service') as mock_service:
        mock_service.send_verification_code_email.return_value = True
        
        result = send_verification_code_email(
            email="test@example.com",
            code="123456",
            user_name="Test User"
        )
        
        assert result is True
        mock_service.send_verification_code_email.assert_called_once()


if __name__ == "__main__":
    # Add path for standalone execution
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
    
    # Run specific tests
    test_invitation_token_generation()
    print("✅ Invitation token generation test passed")
    
    test_invitation_email_context()
    print("✅ Invitation email context test passed")
    
    print("🎉 All manual tests passed!")