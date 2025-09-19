"""
AWS SES Email Service
Handles sending emails through Amazon Simple Email Service (SES)
"""

import boto3
import logging
from typing import List, Optional, Dict, Any
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from botocore.exceptions import ClientError, NoCredentialsError
import smtplib
from email.mime.text import MIMEText as SMTPMIMEText
from email.mime.multipart import MIMEMultipart as SMTPMIMEMultipart

from ..config.settings import settings
from .email_template_engine import (
    render_welcome_email, render_password_reset_email, 
    render_invitation_email, render_2fa_code_email
)

logger = logging.getLogger(__name__)

class EmailService:
    """
    Unified email service that can use either AWS SES or SMTP
    """
    
    def __init__(self):
        self.use_ses = settings.use_ses
        if self.use_ses:
            self._init_ses_client()
        else:
            logger.info("Using SMTP email service")
    
    def _init_ses_client(self):
        """Initialize AWS SES client"""
        try:
            self.ses_client = boto3.client(
                'ses',
                aws_access_key_id=settings.aws_access_key_id,
                aws_secret_access_key=settings.aws_secret_access_key,
                region_name=settings.aws_region
            )
            logger.info(f"SES client initialized for region: {settings.aws_region}")
        except NoCredentialsError:
            logger.error("AWS credentials not found. Falling back to SMTP.")
            self.use_ses = False
        except Exception as e:
            logger.error(f"Failed to initialize SES client: {str(e)}. Falling back to SMTP.")
            self.use_ses = False
    
    async def send_email(
        self,
        to_email: str | List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Send email using either SES or SMTP
        
        Args:
            to_email: Recipient email address(es)
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            reply_to: Reply-to email address
            attachments: List of attachments (for SMTP only)
            tags: Email tags for tracking (SES only)
        
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        
        # Normalize to_email to list
        if isinstance(to_email, str):
            to_email = [to_email]
        
        if self.use_ses:
            return await self._send_via_ses(
                to_email, subject, html_body, text_body, reply_to, tags
            )
        else:
            return await self._send_via_smtp(
                to_email, subject, html_body, text_body, reply_to, attachments
            )
    
    async def _send_via_ses(
        self,
        to_email: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        tags: Optional[Dict[str, str]] = None
    ) -> bool:
        """Send email via AWS SES"""
        
        try:
            # Prepare the email content
            destination = {'ToAddresses': to_email}
            
            message = {
                'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                'Body': {'Html': {'Data': html_body, 'Charset': 'UTF-8'}}
            }
            
            if text_body:
                message['Body']['Text'] = {'Data': text_body, 'Charset': 'UTF-8'}
            
            # Prepare send parameters
            send_params = {
                'Source': settings.ses_from_email,
                'Destination': destination,
                'Message': message
            }
            
            # Add reply-to if specified
            if reply_to or settings.ses_reply_to_email:
                send_params['ReplyToAddresses'] = [reply_to or settings.ses_reply_to_email]
            
            # Add configuration set if specified (for tracking)
            if settings.ses_configuration_set:
                send_params['ConfigurationSetName'] = settings.ses_configuration_set
            
            # Add tags if specified
            if tags:
                send_params['Tags'] = [{'Name': k, 'Value': v} for k, v in tags.items()]
            
            # Send the email
            response = self.ses_client.send_email(**send_params)
            
            message_id = response['MessageId']
            logger.info(f"Email sent successfully via SES. MessageId: {message_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES ClientError ({error_code}): {error_message}")
            
            if error_code == 'MessageRejected':
                logger.error("Email was rejected. Check if sender email is verified in SES.")
            elif error_code == 'SendingPausedException':
                logger.error("SES sending is paused for your account.")
            elif error_code == 'MailFromDomainNotVerifiedException':
                logger.error("The domain used in the 'From' address is not verified in SES.")
            
            return False
            
        except Exception as e:
            logger.error(f"Unexpected error sending email via SES: {str(e)}")
            return False
    
    async def _send_via_smtp(
        self,
        to_email: List[str],
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        reply_to: Optional[str] = None,
        attachments: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """Send email via SMTP (fallback)"""
        
        if not settings.smtp_server:
            logger.error("SMTP server not configured")
            return False
        
        try:
            # Create message
            msg = SMTPMIMEMultipart('alternative')
            msg['From'] = settings.from_email
            msg['To'] = ', '.join(to_email)
            msg['Subject'] = subject
            
            if reply_to:
                msg['Reply-To'] = reply_to
            
            # Add text part
            if text_body:
                text_part = SMTPMIMEText(text_body, 'plain', 'utf-8')
                msg.attach(text_part)
            
            # Add HTML part
            html_part = SMTPMIMEText(html_body, 'html', 'utf-8')
            msg.attach(html_part)
            
            # Add attachments if provided
            if attachments:
                for attachment in attachments:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment['content'])
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {attachment["filename"]}'
                    )
                    msg.attach(part)
            
            # Send email
            with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
                if settings.smtp_use_tls:
                    server.starttls()
                
                if settings.smtp_username and settings.smtp_password:
                    server.login(settings.smtp_username, settings.smtp_password)
                
                server.send_message(msg)
            
            logger.info(f"Email sent successfully via SMTP to {', '.join(to_email)}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email via SMTP: {str(e)}")
            return False
    
    async def verify_email_address(self, email: str) -> bool:
        """
        Verify an email address in SES (only works with SES)
        """
        if not self.use_ses:
            logger.warning("Email verification only available with SES")
            return False
        
        try:
            self.ses_client.verify_email_identity(EmailAddress=email)
            logger.info(f"Verification email sent to {email}")
            return True
        except ClientError as e:
            logger.error(f"Failed to verify email {email}: {e}")
            return False
    
    async def get_send_quota(self) -> Optional[Dict[str, float]]:
        """
        Get SES send quota information
        """
        if not self.use_ses:
            return None
        
        try:
            response = self.ses_client.get_send_quota()
            return {
                'max_24_hour': response['Max24HourSend'],
                'max_send_rate': response['MaxSendRate'],
                'sent_last_24_hours': response['SentLast24Hours']
            }
        except ClientError as e:
            logger.error(f"Failed to get send quota: {e}")
            return None
    
    async def get_verified_identities(self) -> List[str]:
        """
        Get list of verified email addresses and domains
        """
        if not self.use_ses:
            return []
        
        try:
            response = self.ses_client.list_verified_email_addresses()
            return response.get('VerifiedEmailAddresses', [])
        except ClientError as e:
            logger.error(f"Failed to get verified identities: {e}")
            return []

# Global email service instance
email_service = EmailService()

# Convenience functions
async def send_email(
    to_email: str | List[str],
    subject: str,
    html_body: str,
    text_body: Optional[str] = None,
    reply_to: Optional[str] = None,
    tags: Optional[Dict[str, str]] = None
) -> bool:
    """Convenience function to send email"""
    return await email_service.send_email(
        to_email, subject, html_body, text_body, reply_to, tags=tags
    )

async def send_password_reset_email(email: str, reset_token: str, user_name: str = "") -> bool:
    """Send password reset email using professional template"""
    subject = "Password Reset Request - CA Tadley Debt Advice Tool"
    
    # Create reset URL (you'll need to adjust this based on your frontend URL)
    reset_url = f"{settings.allowed_origins[0]}/reset-password?token={reset_token}"
    
    # Render HTML template
    html_body = render_password_reset_email(user_name, reset_url)
    
    # Fallback to simple template if rendering fails
    if not html_body:
        html_body = f"""
        <h2>Password Reset Request</h2>
        <p>Hello {user_name},</p>
        <p>You have requested to reset your password for the CA Tadley Debt Advice Tool.</p>
        <p><a href="{reset_url}">Reset Password</a></p>
        <p>This link will expire in 24 hours.</p>
        """
    
    # Plain text version
    text_body = f"""
    Password Reset Request
    
    Hello {user_name},
    
    You have requested to reset your password for the CA Tadley Debt Advice Tool.
    
    Please visit the following link to reset your password:
    {reset_url}
    
    This link will expire in 24 hours.
    
    If you did not request this password reset, please ignore this email.
    """
    
    return await send_email(
        email, 
        subject, 
        html_body, 
        text_body, 
        tags={'type': 'password_reset'}
    )

async def send_invitation_email(email: str, invitation_token: str, inviter_name: str = "") -> bool:
    """Send user invitation email using professional template"""
    subject = "Invitation to CA Tadley Debt Advice Tool"
    
    # Create invitation URL
    invitation_url = f"{settings.allowed_origins[0]}/register?token={invitation_token}"
    
    # Render HTML template
    html_body = render_invitation_email(inviter_name, invitation_url)
    
    # Fallback to simple template if rendering fails
    if not html_body:
        html_body = f"""
        <h2>You're Invited!</h2>
        <p>Hello,</p>
        <p>You have been invited by {inviter_name} to join the CA Tadley Debt Advice Tool.</p>
        <p><a href="{invitation_url}">Accept Invitation</a></p>
        <p>This invitation will expire in 7 days.</p>
        """
    
    # Plain text version
    text_body = f"""
    You're Invited to CA Tadley Debt Advice Tool
    
    Hello,
    
    You have been invited by {inviter_name} to join the CA Tadley Debt Advice Tool.
    
    Please visit the following link to accept your invitation and create your account:
    {invitation_url}
    
    This invitation will expire in 7 days.
    """
    
    return await send_email(
        email, 
        subject, 
        html_body, 
        text_body, 
        tags={'type': 'invitation'}
    )

async def send_2fa_code_email(email: str, code: str, user_name: str = "") -> bool:
    """Send 2FA verification code email using professional template"""
    subject = "Your 2FA Verification Code - CA Tadley Debt Advice Tool"
    
    # Render HTML template
    html_body = render_2fa_code_email(user_name, code)
    
    # Fallback to simple template if rendering fails
    if not html_body:
        html_body = f"""
        <h2>2FA Verification Code</h2>
        <p>Hello {user_name},</p>
        <p>Here is your two-factor authentication code:</p>
        <div style="text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 3px; padding: 20px; background-color: #f8f9fa; border-radius: 10px;">
            {code}
        </div>
        <p><strong>This code will expire in 10 minutes.</strong></p>
        """
    
    # Plain text version
    text_body = f"""
    2FA Verification Code
    
    Hello {user_name},
    
    Here is your two-factor authentication code: {code}
    
    This code will expire in 10 minutes.
    
    If you did not request this code, please contact support immediately.
    """
    
    return await send_email(
        email, 
        subject, 
        html_body, 
        text_body, 
        tags={'type': '2fa_code'}
    )
