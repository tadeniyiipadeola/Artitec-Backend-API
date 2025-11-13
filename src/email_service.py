# src/email_service.py
"""
Email service for sending password reset and other emails.
Supports both SMTP and console logging for development.
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails."""

    def __init__(self):
        """Initialize email service with environment configuration."""
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_user = os.getenv("SMTP_USER", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.from_email = os.getenv("FROM_EMAIL", self.smtp_user)
        self.from_name = os.getenv("FROM_NAME", "Artitec")
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        # Use console mode if SMTP credentials not configured
        self.console_mode = not (self.smtp_user and self.smtp_password)

        if self.console_mode:
            logger.info("📧 Email service running in CONSOLE MODE (no SMTP configured)")
        else:
            logger.info(f"📧 Email service configured: {self.smtp_host}:{self.smtp_port}")

    def send_email(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None
    ) -> bool:
        """
        Send an email.

        Args:
            to_email: Recipient email address
            subject: Email subject
            html_body: HTML email body
            plain_body: Plain text email body (optional, generated from HTML if not provided)

        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if self.console_mode:
                return self._send_console(to_email, subject, html_body)
            else:
                return self._send_smtp(to_email, subject, html_body, plain_body)
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    def _send_console(self, to_email: str, subject: str, html_body: str) -> bool:
        """Print email to console (for development)."""
        print("\n" + "="*80)
        print("📧 EMAIL (Console Mode)")
        print("="*80)
        print(f"To: {to_email}")
        print(f"From: {self.from_name} <{self.from_email}>")
        print(f"Subject: {subject}")
        print(f"Time: {datetime.utcnow().isoformat()}")
        print("-"*80)
        print(html_body)
        print("="*80 + "\n")
        return True

    def _send_smtp(
        self,
        to_email: str,
        subject: str,
        html_body: str,
        plain_body: Optional[str] = None
    ) -> bool:
        """Send email via SMTP."""
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = f"{self.from_name} <{self.from_email}>"
        msg['To'] = to_email

        # Add plain text version if not provided
        if not plain_body:
            # Simple HTML to text conversion
            plain_body = html_body.replace('<br>', '\n').replace('<br/>', '\n')
            plain_body = plain_body.replace('</p>', '\n\n')
            # Remove HTML tags
            import re
            plain_body = re.sub(r'<[^>]+>', '', plain_body)

        # Attach both plain and HTML versions
        part1 = MIMEText(plain_body, 'plain')
        part2 = MIMEText(html_body, 'html')

        msg.attach(part1)
        msg.attach(part2)

        # Send email
        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)

        logger.info(f"✉️ Email sent to {to_email}: {subject}")
        return True

    def send_password_reset_email(
        self,
        to_email: str,
        reset_token: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send password reset email.

        Args:
            to_email: User's email address
            reset_token: Password reset token
            user_name: User's name (optional, for personalization)

        Returns:
            True if sent successfully, False otherwise
        """
        reset_url = f"{self.frontend_url}/reset-password?token={reset_token}"

        greeting = f"Hi {user_name}," if user_name else "Hello,"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #D4AF37 0%, #C5A028 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background: #ffffff;
                    padding: 30px;
                    border: 1px solid #e1e1e1;
                    border-top: none;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 28px;
                    background: linear-gradient(135deg, #D4AF37 0%, #C5A028 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .button:hover {{
                    background: linear-gradient(135deg, #C5A028 0%, #B69020 100%);
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                    border-radius: 0 0 8px 8px;
                    border: 1px solid #e1e1e1;
                    border-top: none;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 12px;
                    margin: 20px 0;
                }}
                .code {{
                    background: #f5f5f5;
                    padding: 12px;
                    border-radius: 4px;
                    font-family: 'Courier New', monospace;
                    word-break: break-all;
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0;">🔐 Password Reset Request</h1>
            </div>
            <div class="content">
                <p>{greeting}</p>
                <p>We received a request to reset your password for your Artitec account.</p>
                <p>Click the button below to reset your password:</p>

                <div style="text-align: center;">
                    <a href="{reset_url}" class="button">Reset Password</a>
                </div>

                <p>Or copy and paste this link into your browser:</p>
                <div class="code">{reset_url}</div>

                <div class="warning">
                    <strong>⏰ This link will expire in 1 hour.</strong>
                </div>

                <p><strong>Didn't request this?</strong><br>
                If you didn't request a password reset, you can safely ignore this email. Your password will remain unchanged.</p>

                <p>For security reasons:</p>
                <ul>
                    <li>Never share this link with anyone</li>
                    <li>This link can only be used once</li>
                    <li>We will never ask for your password via email</li>
                </ul>
            </div>
            <div class="footer">
                <p><strong>Artitec</strong> - Modern Real Estate Platform</p>
                <p>This is an automated email. Please do not reply.</p>
                <p>© {datetime.utcnow().year} Artitec Technology. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        return self.send_email(
            to_email=to_email,
            subject="Reset Your Artitec Password",
            html_body=html_body
        )

    def send_password_changed_notification(
        self,
        to_email: str,
        user_name: Optional[str] = None
    ) -> bool:
        """
        Send notification that password was changed.

        Args:
            to_email: User's email address
            user_name: User's name (optional)

        Returns:
            True if sent successfully, False otherwise
        """
        greeting = f"Hi {user_name}," if user_name else "Hello,"

        html_body = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                    line-height: 1.6;
                    color: #333;
                    max-width: 600px;
                    margin: 0 auto;
                    padding: 20px;
                }}
                .header {{
                    background: linear-gradient(135deg, #28a745 0%, #20873a 100%);
                    color: white;
                    padding: 30px;
                    text-align: center;
                    border-radius: 8px 8px 0 0;
                }}
                .content {{
                    background: #ffffff;
                    padding: 30px;
                    border: 1px solid #e1e1e1;
                }}
                .alert {{
                    background: #d1ecf1;
                    border-left: 4px solid #17a2b8;
                    padding: 12px;
                    margin: 20px 0;
                }}
                .footer {{
                    background: #f8f9fa;
                    padding: 20px;
                    text-align: center;
                    font-size: 12px;
                    color: #666;
                    border-radius: 0 0 8px 8px;
                    border: 1px solid #e1e1e1;
                    border-top: none;
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1 style="margin: 0;">✅ Password Changed Successfully</h1>
            </div>
            <div class="content">
                <p>{greeting}</p>
                <p>Your Artitec account password was successfully changed.</p>

                <div class="alert">
                    <strong>🕐 Changed at:</strong> {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}
                </div>

                <p><strong>Didn't make this change?</strong></p>
                <p>If you did not change your password, please contact our support team immediately at <a href="mailto:support@artitec.com">support@artitec.com</a>.</p>

                <p>For your security, we recommend:</p>
                <ul>
                    <li>Using a unique password for your Artitec account</li>
                    <li>Enabling two-factor authentication (coming soon)</li>
                    <li>Never sharing your password with anyone</li>
                </ul>
            </div>
            <div class="footer">
                <p><strong>Artitec</strong> - Modern Real Estate Platform</p>
                <p>© {datetime.utcnow().year} Artitec Technology. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        return self.send_email(
            to_email=to_email,
            subject="Your Artitec Password Was Changed",
            html_body=html_body
        )


# Singleton instance
_email_service = None


def get_email_service() -> EmailService:
    """Get or create email service singleton."""
    global _email_service
    if _email_service is None:
        _email_service = EmailService()
    return _email_service


__all__ = ["EmailService", "get_email_service"]
