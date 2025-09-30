"""
Email Service for CA Tadley Debt Tool

This module provides email functionality using AWS SES SMTP.
Supports HTML templates, retry logic, and comprehensive error handling.
"""

import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import List, Optional, Dict, Any
import logging
from pathlib import Path
import jinja2
from datetime import datetime
import asyncio
from functools import wraps
import time

try:
    from ..config.settings import settings
except ImportError:
    # Fallback for when running as script
    from config.settings import settings

# Setup logging
logger = logging.getLogger(__name__)


class EmailServiceError(Exception):
    """Custom exception for email service errors"""
    pass


class EmailTemplate:
    """Email template handler using Jinja2"""

    def __init__(self, template_dir: str = None):
        if template_dir is None:
            # Default to backend/templates/emails directory
            # __file__ = backend/src/services/email_service.py
            # parents[0]=services, [1]=src, [2]=backend → backend/templates/emails
            template_dir = Path(__file__).parents[2] / "templates" / "emails"

        self.template_dir = Path(template_dir)
        if self.template_dir.exists():
            self.env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(str(self.template_dir)),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
        else:
            logger.warning(
                f"Template directory {self.template_dir} not found. Using string templates.")
            self.env = None

    def render(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render email template with context"""
        if self.env:
            try:
                template = self.env.get_template(template_name)
                return template.render(**context)
            except jinja2.TemplateNotFound:
                logger.error(f"Template {template_name} not found")
                return self._get_fallback_template(template_name, context)
        else:
            return self._get_fallback_template(template_name, context)

    def _get_fallback_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Fallback templates when template files are not available"""
        
        # Base styles matching our brand
        base_styles = """
        <style>
        body { font-family: 'Open Sans', Arial, sans-serif; line-height: 1.6; color: #4b5563; margin: 0; padding: 20px; background-color: #f3f4f6; }
        .container { max-width: 600px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
        .header { background: linear-gradient(135deg, #004b88 0%, #0066cc 100%); color: white; padding: 30px 20px; text-align: center; }
        .header h1 { margin: 0; font-size: 24px; font-weight: 600; }
        .logo { font-size: 18px; font-weight: 700; margin-bottom: 5px; letter-spacing: 0.5px; }
        .content { padding: 40px 30px; }
        .button { display: inline-block; background: linear-gradient(135deg, #004b88 0%, #0066cc 100%); color: white !important; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: 600; font-size: 16px; }
        .button-success { background: linear-gradient(135deg, #16a34a 0%, #22c55e 100%); }
        .code { background: linear-gradient(135deg, #004b88 0%, #0066cc 100%); color: white; font-size: 24px; font-weight: bold; letter-spacing: 4px; text-align: center; padding: 20px; border-radius: 8px; margin: 20px 0; font-family: monospace; }
        .footer { background: #f8fafc; padding: 20px; text-align: center; font-size: 14px; color: #6b7280; border-top: 1px solid #e5e7eb; }
        .company-name { font-weight: 600; color: #004b88; font-size: 16px; }
        </style>
        """
        
        fallback_templates = {
            "password_reset.html": f"""
            <html><head>{base_styles}</head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">Citizens Advice Tadley</div>
                        <h1>Password Reset Request</h1>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{{{{user_name}}}}</strong>,</p>
                        <p>You have requested to reset your password for your CA Tadley Debt Advice Tool account.</p>
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{{{{reset_url}}}}" class="button">Reset My Password</a>
                        </p>
                        <p><strong>Important:</strong> This link will expire in {{{{expire_hours}}}} hours for your security.</p>
                        <p>If you didn't request this password reset, please ignore this email.</p>
                    </div>
                    <div class="footer">
                        <p class="company-name">Citizens Advice Tadley</p>
                        <p>📞 0800 144 8848 | ✉️ admin@catadley.com</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "invitation.html": f"""
            <html><head>{base_styles}</head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">Citizens Advice Tadley</div>
                        <h1>Welcome to Our Team!</h1>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{{{{user_name}}}}</strong>,</p>
                        <p>You have been invited to join CA Tadley Debt Advice Tool as <strong>{{{{role}}}}</strong>.</p>
                        <p><strong>Office:</strong> {{{{office_name}}}}</p>
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{{{{invitation_url}}}}" class="button button-success">Accept Invitation</a>
                        </p>
                        <p><strong>Important:</strong> This invitation will expire on {{{{expires_at}}}}.</p>
                    </div>
                    <div class="footer">
                        <p class="company-name">Citizens Advice Tadley</p>
                        <p>📞 0800 144 8848 | ✉️ admin@catadley.com</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "verification_code.html": f"""
            <html><head>{base_styles}</head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">Citizens Advice Tadley</div>
                        <h1>Two-Factor Authentication</h1>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{{{{user_name}}}}</strong>,</p>
                        <p>Your verification code for CA Tadley Debt Advice Tool is:</p>
                        <div class="code">{{{{verification_code}}}}</div>
                        <p><strong>Important:</strong> This code will expire in {{{{expire_minutes}}}} minutes.</p>
                        <p>If you didn't request this code, please contact support immediately.</p>
                    </div>
                    <div class="footer">
                        <p class="company-name">Citizens Advice Tadley</p>
                        <p>📞 0800 144 8848 | ✉️ admin@catadley.com</p>
                    </div>
                </div>
            </body>
            </html>
            """,
            "reminder.html": f"""
            <html><head>{base_styles}</head>
            <body>
                <div class="container">
                    <div class="header">
                        <div class="logo">Citizens Advice Tadley</div>
                        <h1>Account Setup Reminder</h1>
                    </div>
                    <div class="content">
                        <p>Hello <strong>{{{{user_name}}}}</strong>,</p>
                        <p>This is a reminder that your CA Tadley Debt Advice Tool account is still pending setup.</p>
                        <p style="text-align: center; margin: 30px 0;">
                            <a href="{{{{setup_url}}}}" class="button">Complete Setup</a>
                        </p>
                        <p>If you need assistance, please contact your administrator.</p>
                    </div>
                    <div class="footer">
                        <p class="company-name">Citizens Advice Tadley</p>
                        <p>📞 0800 144 8848 | ✉️ admin@catadley.com</p>
                    </div>
                </div>
            </body>
            </html>
            """
        }

        template_content = fallback_templates.get(
            template_name, f"<p>Email content for {template_name}</p>")
        template = jinja2.Template(template_content)
        return template.render(**context)


def retry_on_failure(max_retries: int = 3, delay: float = 1.0):
    """Decorator to retry email operations on failure"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"Email attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
                        # Exponential backoff
                        time.sleep(delay * (2 ** attempt))
                    else:
                        logger.error(
                            f"All {max_retries} email attempts failed")
            raise last_exception
        return wrapper
    return decorator


class EmailService:
    """AWS SES SMTP Email Service"""

    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.smtp_use_tls = settings.smtp_use_tls
        self.from_email = settings.from_email or "dev@sattva-ai.com"
        self.template_handler = EmailTemplate()

        # Validate configuration
        self._validate_config()

    def _validate_config(self):
        """Validate email configuration"""
        required_settings = [
            ('smtp_server', self.smtp_server),
            ('smtp_port', self.smtp_port),
            ('smtp_username', self.smtp_username),
            ('smtp_password', self.smtp_password),
        ]

        missing = [name for name, value in required_settings if not value]
        if missing:
            raise EmailServiceError(
                f"Missing required email settings: {', '.join(missing)}")

        logger.info(
            f"Email service configured with server: {self.smtp_server}:{self.smtp_port}")

    @retry_on_failure(max_retries=3)
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body_html: str,
        body_text: str = None,
        attachments: List[Dict[str, Any]] = None
    ) -> bool:
        """
        Send email via AWS SES SMTP

        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body_html: HTML email body
            body_text: Plain text email body (optional)
            attachments: List of attachments (optional)

        Returns:
            bool: True if sent successfully

        Raises:
            EmailServiceError: If email sending fails
        """
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)

            # Add text parts
            if body_text:
                part1 = MIMEText(body_text, 'plain')
                msg.attach(part1)

            part2 = MIMEText(body_html, 'html')
            msg.attach(part2)

            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    self._add_attachment(msg, attachment)

            # Create SMTP connection
            context = ssl.create_default_context()

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls(context=context)

                server.login(self.smtp_username, self.smtp_password)
                server.sendmail(self.from_email, to_emails, msg.as_string())

            logger.info(f"Email sent successfully to {', '.join(to_emails)}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise EmailServiceError(f"Failed to send email: {e}")

    def _add_attachment(self, msg: MIMEMultipart, attachment: Dict[str, Any]):
        """Add attachment to email message"""
        try:
            with open(attachment['path'], 'rb') as f:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(f.read())

            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {attachment.get("filename", "attachment")}'
            )
            msg.attach(part)
        except Exception as e:
            logger.error(
                f"Failed to add attachment {attachment.get('path', 'unknown')}: {e}")

    def send_template_email(
        self,
        to_emails: List[str],
        template_name: str,
        context: Dict[str, Any],
        subject: str = None
    ) -> bool:
        """
        Send email using template

        Args:
            to_emails: List of recipient email addresses
            template_name: Template filename (e.g., 'password_reset.html')
            context: Template context variables
            subject: Email subject (if not in context)

        Returns:
            bool: True if sent successfully
        """
        try:
            # Render template
            body_html = self.template_handler.render(template_name, context)

            # Get subject from context or parameter
            email_subject = subject or context.get(
                'subject', 'CA Tadley Debt Tool Notification')

            return self.send_email(to_emails, email_subject, body_html)

        except Exception as e:
            logger.error(f"Failed to send template email {template_name}: {e}")
            raise EmailServiceError(f"Failed to send template email: {e}")

    # Specific email methods for common use cases

    def send_password_reset_email(self, email: str, reset_token: str, user_name: str = None) -> bool:
        """Send password reset email"""
        reset_url = f"{settings.frontend_url}/reset-password?token={reset_token}"

        context = {
            'user_name': user_name or email.split('@')[0],
            'reset_url': reset_url,
            'reset_token': reset_token,
            'expire_hours': settings.password_reset_expire_hours,
            'subject': 'Password Reset Request - CA Tadley'
        }

        return self.send_template_email([email], 'password_reset.html', context)

    def send_invitation_email(
        self,
        email: str,
        invitation_token: str,
        user_name: str,
        role: str,
        office_name: str,
        expires_at: datetime,
        invited_by_name: str = None,
        invited_by_role: str = None,
        ca_client_number: str = None,
        office_code: str = None
    ) -> bool:
        """Send user invitation email"""
        # Build register URL (include office code when provided)
        if office_code:
            invitation_url = f"{settings.frontend_url}/register?officecode={office_code}&invite={invitation_token}"
        else:
            invitation_url = f"{settings.frontend_url}/register?invite={invitation_token}"

        # Choose template based on role
        role_lower = role.lower() if isinstance(role, str) else str(role).lower()
        is_client = role_lower == "client"
        is_adviser = role_lower in ("adviser", "advisor")

        if is_client:
            template_name = "1.CLIENT INVITATION.html"
        elif is_adviser:
            # Use the capitalized adviser invitation template from the templates folder
            template_name = "6. ADVISER INVITATION EMAIL.html"
        else:
            template_name = "invitation.html"

        subject = (
            f'Welcome to CA Tadley Debt Advice Service' if is_client
            else f'Invitation to CA Tadley Debt Tool - {role.title()}'
        )

        context = {
            'user_name': user_name,
            'user_email': email,
            'invitation_url': invitation_url,
            'invitation_token': invitation_token,
            'role': role.title(),
            'office_name': office_name,
            'expires_at': expires_at.strftime('%B %d, %Y at %I:%M %p'),
            'subject': subject
        }

        # Additional keys required by the client template (1.CLIENT INVITATION.html)
        if is_client:
            context['registration_link'] = invitation_url
            context['ca_office'] = office_name
            if ca_client_number is not None:
                context['ca_client_number'] = ca_client_number

        # Additional keys required by the capitalized adviser template
        if is_adviser:
            context['registration_link'] = invitation_url
            context['adviser_role'] = role.title()
            if invited_by_name:
                context['invited_by_name'] = invited_by_name
            if invited_by_role:
                context['invited_by_role'] = invited_by_role.title()

        return self.send_template_email([email], template_name, context)

    def send_verification_code_email(
        self,
        email: str,
        code: str,
        user_name: str = None,
        login_time: str = None,
        ip_address: str = None,
        purpose: str = "login"
    ) -> bool:
        """Send 2FA verification/OTP email using production template"""
        from datetime import datetime
        is_registration = (purpose or "").lower() in ("register", "registration", "signup")
        page_title = "Registration Verification Code - Citizens Advice Tadley" if is_registration else "Login Verification Code - Citizens Advice Tadley"
        heading_title = "Registration Verification" if is_registration else "Login Verification"
        intro_text = (
            "You're creating your Citizens Advice Tadley account. Use the verification code below to complete your registration."
            if is_registration
            else "You requested to log in to your Citizens Advice Tadley account. Use the verification code below to complete your login."
        )
        subject = page_title
        context = {
            'user_name': user_name or email.split('@')[0],
            'verification_code': code,
            'expire_minutes': 10,
            'login_time': login_time or datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC'),
            'ip_address': ip_address or 'unknown',
            'subject': subject,
            'page_title': page_title,
            'heading_title': heading_title,
            'intro_text': intro_text
        }

        # Use the branded template file under templates/emails
        return self.send_template_email([email], '3. CLIENT 2FA EMAIL (LOGIN).html', context)

    def send_reminder_email(self, email: str, setup_url: str, user_name: str = None) -> bool:
        """Send account setup reminder email"""
        context = {
            'user_name': user_name or email.split('@')[0],
            'setup_url': setup_url,
            'subject': 'Account Setup Reminder - CA Tadley'
        }

        return self.send_template_email([email], 'reminder.html', context)

    def send_user_created_email(
        self,
        email: str,
        user_name: str,
        role: str,
        office_name: str,
        temp_password: str,
        created_by: str,
        client_number: str,
        office_code: str,
        invite_url: str
    ) -> bool:
        """Send user creation notification email with temporary password"""
        login_url = f"{settings.frontend_url}/login"

        # Choose template and subject based on role
        template_name = "user_created.html"
        subject = f'Your CA Tadley Account Has Been Created - {role.title()}'

        context = {
            'user_name': user_name,
            'user_email': email,
            'role': role.title(),
            'office_name': office_name,
            'temp_password': temp_password,
            'login_url': login_url,
            'created_by': created_by,
            'subject': subject,
            'password_change_required': True,
            'client_number':client_number,
            'office_code':office_code,
            'invite_url':invite_url
        }

        return self.send_template_email([email], template_name, context)

    def send_registration_notice_to_office(
        self,
        office_name: str,
        ca_client_number: Optional[str],
        registration_date: datetime,
        to_email: Optional[str] = None,
        admin_dashboard_link: Optional[str] = None,
        role: Optional[str] = None,
        user_email: Optional[str] = None
    ) -> bool:
        """Notify office that a user registered (client or adviser)"""
        recipient = to_email or self.from_email
        # Choose dashboard link based on role
        default_link = f"{settings.frontend_url}/office/clients" if (role or '').lower() == 'client' else f"{settings.frontend_url}/office/advisers"
        dashboard_link = admin_dashboard_link or default_link

        context = {
            'ca_office': office_name,
            'ca_client_number': ca_client_number or 'None',
            'registration_date': registration_date.strftime('%B %d, %Y at %I:%M %p'),
            'admin_dashboard_link': dashboard_link,
            'subject': 'New Registration Notification - CA Tadley',
            'registration_title': f"New {'Client' if (role or '').lower() == 'client' else 'Adviser'} Registration",
            'account_created_heading': f"{'Client' if (role or '').lower() == 'client' else 'Adviser'} Account Created",
            'details_title': f"{'Client' if (role or '').lower() == 'client' else 'User'} Details:",
            'dashboard_button_text': f"View {'Client' if (role or '').lower() == 'client' else 'Adviser'} Dashboard",
            'role_title': (role or 'User').title(),
            'user_email': user_email
        }

        return self.send_template_email([recipient], '2.NEW REGISTRATION NOTICE TO CA OFFICE.html', context)

    def send_submission_notification_to_office(
        self,
        office_name: str,
        ca_client_number: Optional[str],
        submission_date: datetime,
        to_email: Optional[str] = None,
        case_review_link: Optional[str] = None
    ) -> bool:
        """Notify office that a client submitted their assessment"""
        recipient = to_email or self.from_email
        review_link = case_review_link or f"{settings.frontend_url}/office/clients"

        context = {
            'ca_office': office_name,
            'ca_client_number': ca_client_number or 'None',
            'ca_client_office': office_name,
            'submission_date': submission_date.strftime('%B %d, %Y at %I:%M %p'),
            'case_review_link': review_link,
            'subject': 'Client Submission Notification - CA Tadley'
        }

        return self.send_template_email([recipient], '5. SUBMISSION NOTIFICATION TO CA OFFICE.html', context)

    def test_connection(self) -> bool:
        """Test SMTP connection"""
        try:
            context = ssl.create_default_context()
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                if self.smtp_use_tls:
                    server.starttls(context=context)
                server.login(self.smtp_username, self.smtp_password)

            logger.info("SMTP connection test successful")
            return True

        except Exception as e:
            logger.error(f"SMTP connection test failed: {e}")
            return False


# Global email service instance - only create when needed
email_service = None

def get_email_service():
    """Get email service instance, creating it lazily"""
    global email_service
    if email_service is None:
        email_service = EmailService()
    return email_service

# Convenience functions for easy import


def send_password_reset_email(email: str, reset_token: str, user_name: str = None) -> bool:
    """Convenience function to send password reset email"""
    return get_email_service().send_password_reset_email(email, reset_token, user_name)


def send_invitation_email(
    email: str,
    invitation_token: str,
    user_name: str,
    role: str,
    office_name: str,
    expires_at: datetime,
    invited_by_name: str = None,
    invited_by_role: str = None,
    ca_client_number: str = None,
    office_code: str = None
) -> bool:
    """Convenience function to send invitation email"""
    return get_email_service().send_invitation_email(
        email=email,
        invitation_token=invitation_token,
        user_name=user_name,
        role=role,
        office_name=office_name,
        expires_at=expires_at,
        invited_by_name=invited_by_name,
        invited_by_role=invited_by_role,
        ca_client_number=ca_client_number,
        office_code=office_code
    )


def send_verification_code_email(email: str, code: str, user_name: str = None) -> bool:
    """Backward-compatible wrapper: prefer using extended args via keyword-only."""
    return get_email_service().send_verification_code_email(email=email, code=code, user_name=user_name)

def send_verification_code_email_extended(
    email: str,
    code: str,
    user_name: str = None,
    login_time: str = None,
    ip_address: str = None,
    purpose: str = None
) -> bool:
    """Convenience function to send 2FA/registration OTP with extended context"""
    return get_email_service().send_verification_code_email(
        email=email,
        code=code,
        user_name=user_name,
        login_time=login_time,
        ip_address=ip_address,
        purpose=purpose or "login"
    )


def send_reminder_email(email: str, setup_url: str, user_name: str = None) -> bool:
    """Convenience function to send reminder email"""
    return get_email_service().send_reminder_email(email, setup_url, user_name)


def send_user_created_email(
    email: str,
    user_name: str,
    role: str,
    office_name: str,
    temp_password: str,
    created_by: str,
    client_number:str,
    office_code: str,
    invite_url: str
) -> bool:
    """Convenience function to send user creation email"""
    return get_email_service().send_user_created_email(
        email, user_name, role, office_name, temp_password, created_by,client_number, office_code, invite_url
    )


def send_registration_notice_to_office(
    office_name: str,
    ca_client_number: Optional[str],
    registration_date: datetime,
    to_email: Optional[str] = None,
    admin_dashboard_link: Optional[str] = None,
    role: Optional[str] = None,
    user_email: Optional[str] = None
) -> bool:
    """Convenience wrapper to notify office of a new registration"""
    return get_email_service().send_registration_notice_to_office(
        office_name=office_name,
        ca_client_number=ca_client_number,
        registration_date=registration_date,
        to_email=to_email,
        admin_dashboard_link=admin_dashboard_link,
        role=role,
        user_email=user_email
    )


def send_submission_notification_to_office(
    office_name: str,
    ca_client_number: Optional[str],
    submission_date: datetime,
    to_email: Optional[str] = None,
    case_review_link: Optional[str] = None
) -> bool:
    """Convenience wrapper to notify office of a client submission"""
    return get_email_service().send_submission_notification_to_office(
        office_name=office_name,
        ca_client_number=ca_client_number,
        submission_date=submission_date,
        to_email=to_email,
        case_review_link=case_review_link
    )
