"""
Email Template Engine
Handles loading and rendering of HTML email templates with dynamic content
"""

import os
import logging
from typing import Dict, Any, Optional
from jinja2 import Environment, FileSystemLoader, Template
from datetime import datetime

logger = logging.getLogger(__name__)

class EmailTemplateEngine:
    """
    Email template engine using Jinja2 for rendering HTML email templates
    """
    
    def __init__(self):
        # Get the templates directory path
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(current_dir, 'email_templates')
        
        # Initialize Jinja2 environment
        try:
            self.env = Environment(
                loader=FileSystemLoader(self.templates_dir),
                autoescape=True  # Enable auto-escaping for security
            )
            logger.info(f"Email template engine initialized with templates from: {self.templates_dir}")
        except Exception as e:
            logger.error(f"Failed to initialize template engine: {str(e)}")
            self.env = None
    
    def render_template(self, template_name: str, context: Dict[str, Any]) -> Optional[str]:
        """
        Render an email template with the given context
        
        Args:
            template_name: Name of the template file (e.g., 'welcome_email.html')
            context: Dictionary of variables to substitute in the template
        
        Returns:
            Rendered HTML string or None if rendering failed
        """
        if not self.env:
            logger.error("Template engine not initialized")
            return None
        
        try:
            template = self.env.get_template(template_name)
            return template.render(context)
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {str(e)}")
            return None
    
    def render_welcome_email(
        self,
        user_name: str,
        reset_url: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Render welcome email template"""
        
        context = {
            'user_name': user_name,
            'reset_url': reset_url,
            'current_year': datetime.now().year,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        if additional_context:
            context.update(additional_context)
        
        return self.render_template('welcome_email.html', context)
    
    def render_password_reset_email(
        self,
        user_name: str,
        reset_url: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Render password reset email template"""
        
        context = {
            'user_name': user_name,
            'reset_url': reset_url,
            'current_year': datetime.now().year,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        if additional_context:
            context.update(additional_context)
        
        return self.render_template('password_reset.html', context)
    
    def render_invitation_email(
        self,
        inviter_name: str,
        invitation_url: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Render invitation email template"""
        
        context = {
            'inviter_name': inviter_name,
            'invitation_url': invitation_url,
            'registration_link': invitation_url,  # Alias for template compatibility
            'ca_office': additional_context.get('ca_office', 'CA Tadley') if additional_context else 'CA Tadley',
            'ca_client_number': additional_context.get('ca_client_number', 'TBD') if additional_context else 'TBD',
            'current_year': datetime.now().year,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        if additional_context:
            context.update(additional_context)
        
        return self.render_template('invitation.html', context)
    
    def render_2fa_code_email(
        self,
        user_name: str,
        code: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Render 2FA verification code email template"""
        
        context = {
            'user_name': user_name,
            'code': code,
            'current_year': datetime.now().year,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        if additional_context:
            context.update(additional_context)
        
        return self.render_template('2fa_code.html', context)
    
    def render_case_reminder_email(
        self,
        user_name: str,
        case_number: str,
        client_name: str,
        days_pending: int,
        case_url: str,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """Render case reminder email template (for future implementation)"""
        
        context = {
            'user_name': user_name,
            'case_number': case_number,
            'client_name': client_name,
            'days_pending': days_pending,
            'case_url': case_url,
            'current_year': datetime.now().year,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        if additional_context:
            context.update(additional_context)
        
        # For now, return a simple template - you can create case_reminder.html later
        template_content = """
        <h2>Case Reminder</h2>
        <p>Hello {{user_name}},</p>
        <p>Case {{case_number}} for client {{client_name}} has been pending for {{days_pending}} days.</p>
        <p><a href="{{case_url}}">View Case</a></p>
        """
        
        try:
            template = Template(template_content)
            return template.render(context)
        except Exception as e:
            logger.error(f"Failed to render case reminder template: {str(e)}")
            return None
    
    def list_available_templates(self) -> list:
        """List all available email templates"""
        if not os.path.exists(self.templates_dir):
            return []
        
        try:
            templates = [f for f in os.listdir(self.templates_dir) if f.endswith('.html')]
            return templates
        except Exception as e:
            logger.error(f"Failed to list templates: {str(e)}")
            return []
    
    def template_exists(self, template_name: str) -> bool:
        """Check if a template file exists"""
        template_path = os.path.join(self.templates_dir, template_name)
        return os.path.isfile(template_path)

# Global template engine instance
template_engine = EmailTemplateEngine()

# Convenience functions for common template rendering
def render_welcome_email(user_name: str, reset_url: str, **kwargs) -> Optional[str]:
    """Convenience function to render welcome email"""
    return template_engine.render_welcome_email(user_name, reset_url, kwargs)

def render_password_reset_email(user_name: str, reset_url: str, **kwargs) -> Optional[str]:
    """Convenience function to render password reset email"""
    return template_engine.render_password_reset_email(user_name, reset_url, kwargs)

def render_invitation_email(inviter_name: str, invitation_url: str, **kwargs) -> Optional[str]:
    """Convenience function to render invitation email"""
    return template_engine.render_invitation_email(inviter_name, invitation_url, kwargs)

def render_2fa_code_email(user_name: str, code: str, **kwargs) -> Optional[str]:
    """Convenience function to render 2FA code email"""
    return template_engine.render_2fa_code_email(user_name, code, kwargs)
