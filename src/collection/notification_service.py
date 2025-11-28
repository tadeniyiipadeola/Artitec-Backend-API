"""
Property Approval Notification Service

Sends notifications when properties are:
- Auto-approved
- Require manual review
- Auto-denied

Supports both email and webhook notifications.
"""
import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime
import requests
from sqlalchemy.orm import Session

from model.property.property import Property
from model.collection import CollectionChange
from model.profiles.builder import BuilderProfile
from model.profiles.community import Community
from src.email_service import get_email_service

logger = logging.getLogger(__name__)


class PropertyApprovalNotificationService:
    """
    Service for sending property approval notifications via email and webhooks.

    Notification Types:
    - AUTO_APPROVED: Property was automatically approved
    - MANUAL_REVIEW: Property requires manual review
    - AUTO_DENIED: Property was automatically denied
    """

    def __init__(self, db: Session):
        self.db = db
        self.email_service = get_email_service()

        # Get admin notification emails from environment
        admin_emails_str = os.getenv("ADMIN_NOTIFICATION_EMAILS", "")
        self.admin_emails = [
            email.strip()
            for email in admin_emails_str.split(",")
            if email.strip()
        ]

        # Get webhook URL from environment
        self.webhook_url = os.getenv("PROPERTY_APPROVAL_WEBHOOK_URL", "")

        # Frontend URL for links
        self.frontend_url = os.getenv("FRONTEND_URL", "http://localhost:3000")

        if not self.admin_emails:
            logger.warning("⚠️  No admin notification emails configured (set ADMIN_NOTIFICATION_EMAILS)")
        else:
            logger.info(f"📧 Admin notifications enabled for {len(self.admin_emails)} email(s)")

        if not self.webhook_url:
            logger.info("🔗 No webhook URL configured (set PROPERTY_APPROVAL_WEBHOOK_URL)")
        else:
            logger.info(f"🔗 Webhook notifications enabled: {self.webhook_url[:50]}...")

    def notify_auto_approved(
        self,
        property: Property,
        change: CollectionChange,
        confidence: float
    ):
        """
        Send notification when a property is auto-approved.

        Args:
            property: The approved Property instance
            change: The CollectionChange that triggered approval
            confidence: The confidence score
        """
        try:
            # Get builder and community info
            builder = self.db.query(BuilderProfile).filter(
                BuilderProfile.id == property.builder_id
            ).first()

            community = self.db.query(Community).filter(
                Community.id == property.community_id
            ).first()

            builder_name = builder.name if builder else "Unknown Builder"
            community_name = community.name if community else "Unknown Community"

            # Send email notification
            if self.admin_emails:
                for admin_email in self.admin_emails:
                    self._send_auto_approved_email(
                        to_email=admin_email,
                        property=property,
                        builder_name=builder_name,
                        community_name=community_name,
                        confidence=confidence
                    )

            # Send webhook notification
            if self.webhook_url:
                self._send_webhook(
                    event_type="property.auto_approved",
                    data={
                        "property_id": property.id,
                        "address": property.address1,
                        "city": property.city,
                        "state": property.state,
                        "price": float(property.price) if property.price else None,
                        "bedrooms": property.bedrooms,
                        "bathrooms": float(property.bathrooms) if property.bathrooms else None,
                        "sqft": property.sqft,
                        "builder_name": builder_name,
                        "community_name": community_name,
                        "confidence": confidence,
                        "approved_at": property.approved_at.isoformat() if property.approved_at else None,
                        "change_id": change.id
                    }
                )

            logger.info(
                f"✅ Sent auto-approval notifications for property {property.id} "
                f"({property.address1}, {property.city})"
            )

        except Exception as e:
            logger.error(f"Failed to send auto-approval notifications: {e}", exc_info=True)

    def notify_manual_review_required(
        self,
        change: CollectionChange,
        property_data: Dict[str, Any],
        confidence: float,
        reason: str = "Property requires manual review"
    ):
        """
        Send notification when a property requires manual review.

        Args:
            change: The CollectionChange requiring review
            property_data: The proposed property data
            confidence: The confidence score
            reason: Reason for manual review
        """
        try:
            # Extract key info
            address = property_data.get("address1", "Unknown Address")
            city = property_data.get("city", "Unknown City")
            state = property_data.get("state", "Unknown State")
            price = property_data.get("price")
            bedrooms = property_data.get("bedrooms", 0)
            bathrooms = property_data.get("bathrooms", 0)

            # Send email notification
            if self.admin_emails:
                for admin_email in self.admin_emails:
                    self._send_manual_review_email(
                        to_email=admin_email,
                        change=change,
                        property_data=property_data,
                        confidence=confidence,
                        reason=reason
                    )

            # Send webhook notification
            if self.webhook_url:
                self._send_webhook(
                    event_type="property.manual_review_required",
                    data={
                        "change_id": change.id,
                        "address": address,
                        "city": city,
                        "state": state,
                        "price": float(price) if price else None,
                        "bedrooms": bedrooms,
                        "bathrooms": float(bathrooms) if bathrooms else None,
                        "confidence": confidence,
                        "reason": reason,
                        "created_at": change.created_at.isoformat() if change.created_at else None
                    }
                )

            logger.info(
                f"📋 Sent manual review notifications for change {change.id} "
                f"({address}, {city})"
            )

        except Exception as e:
            logger.error(f"Failed to send manual review notifications: {e}", exc_info=True)

    def notify_auto_denied(
        self,
        change: CollectionChange,
        property_data: Dict[str, Any],
        confidence: float,
        denial_reason: str
    ):
        """
        Send notification when a property is auto-denied.

        Args:
            change: The CollectionChange that was denied
            property_data: The proposed property data
            confidence: The confidence score
            denial_reason: Reason for denial
        """
        try:
            # Extract key info
            address = property_data.get("address1", "Unknown Address")
            city = property_data.get("city", "Unknown City")
            state = property_data.get("state", "Unknown State")
            price = property_data.get("price")
            bedrooms = property_data.get("bedrooms", 0)
            bathrooms = property_data.get("bathrooms", 0)

            # Send email notification
            if self.admin_emails:
                for admin_email in self.admin_emails:
                    self._send_auto_denied_email(
                        to_email=admin_email,
                        change=change,
                        property_data=property_data,
                        confidence=confidence,
                        denial_reason=denial_reason
                    )

            # Send webhook notification
            if self.webhook_url:
                self._send_webhook(
                    event_type="property.auto_denied",
                    data={
                        "change_id": change.id,
                        "address": address,
                        "city": city,
                        "state": state,
                        "price": float(price) if price else None,
                        "bedrooms": bedrooms,
                        "bathrooms": float(bathrooms) if bathrooms else None,
                        "confidence": confidence,
                        "denial_reason": denial_reason,
                        "denied_at": datetime.utcnow().isoformat()
                    }
                )

            logger.info(
                f"❌ Sent auto-denial notifications for change {change.id} "
                f"({address}, {city})"
            )

        except Exception as e:
            logger.error(f"Failed to send auto-denial notifications: {e}", exc_info=True)

    def _send_auto_approved_email(
        self,
        to_email: str,
        property: Property,
        builder_name: str,
        community_name: str,
        confidence: float
    ):
        """Send auto-approval email notification."""
        property_url = f"{self.frontend_url}/admin/properties/{property.id}"

        price_display = f"${property.price:,.0f}" if property.price else "N/A"
        sqft_display = f"{property.sqft:,}" if property.sqft else "N/A"

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
                    border-top: none;
                }}
                .property-card {{
                    background: #f8f9fa;
                    border-left: 4px solid #28a745;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .property-detail {{
                    margin: 8px 0;
                }}
                .label {{
                    font-weight: 600;
                    color: #666;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 28px;
                    background: linear-gradient(135deg, #28a745 0%, #20873a 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .confidence-badge {{
                    display: inline-block;
                    background: #d4edda;
                    color: #155724;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
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
                <h1 style="margin: 0;">✅ Property Auto-Approved</h1>
            </div>
            <div class="content">
                <p>A new property was automatically approved and added to the database.</p>

                <div class="property-card">
                    <h2 style="margin-top: 0; color: #28a745;">
                        {property.address1}
                    </h2>
                    <p style="font-size: 18px; color: #666; margin: 5px 0;">
                        {property.city}, {property.state} {property.postal_code}
                    </p>

                    <div class="property-detail">
                        <span class="label">Builder:</span> {builder_name}
                    </div>
                    <div class="property-detail">
                        <span class="label">Community:</span> {community_name}
                    </div>
                    <div class="property-detail">
                        <span class="label">Price:</span> {price_display}
                    </div>
                    <div class="property-detail">
                        <span class="label">Beds/Baths:</span> {property.bedrooms} bed / {property.bathrooms} bath
                    </div>
                    <div class="property-detail">
                        <span class="label">Square Feet:</span> {sqft_display}
                    </div>
                    <div class="property-detail" style="margin-top: 15px;">
                        <span class="label">Data Confidence:</span>
                        <span class="confidence-badge">{confidence:.0%}</span>
                    </div>
                </div>

                <p><strong>Auto-Approval Criteria Met:</strong></p>
                <ul>
                    <li>✅ Confidence score > 90% ({confidence:.0%})</li>
                    <li>✅ Valid bedrooms ({property.bedrooms})</li>
                    <li>✅ Valid bathrooms ({property.bathrooms})</li>
                </ul>

                <div style="text-align: center;">
                    <a href="{property_url}" class="button">View Property Details</a>
                </div>

                <p style="font-size: 12px; color: #666; margin-top: 20px;">
                    Property ID: {property.id}<br>
                    Approved: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}
                </p>
            </div>
            <div class="footer">
                <p><strong>Artitec</strong> - Property Collection System</p>
                <p>This is an automated notification. Please do not reply.</p>
                <p>© {datetime.utcnow().year} Artitec Technology. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        self.email_service.send_email(
            to_email=to_email,
            subject=f"✅ Property Auto-Approved: {property.address1}",
            html_body=html_body
        )

    def _send_manual_review_email(
        self,
        to_email: str,
        change: CollectionChange,
        property_data: Dict[str, Any],
        confidence: float,
        reason: str
    ):
        """Send manual review required email notification."""
        review_url = f"{self.frontend_url}/admin/collection/changes/{change.id}"

        address = property_data.get("address1", "Unknown Address")
        city = property_data.get("city", "Unknown City")
        state = property_data.get("state", "Unknown State")
        postal_code = property_data.get("postal_code", "")
        price = property_data.get("price")
        bedrooms = property_data.get("bedrooms", 0)
        bathrooms = property_data.get("bathrooms", 0)
        sqft = property_data.get("sqft")

        price_display = f"${price:,.0f}" if price else "N/A"
        sqft_display = f"{sqft:,}" if sqft else "N/A"

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
                    background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
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
                .property-card {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .property-detail {{
                    margin: 8px 0;
                }}
                .label {{
                    font-weight: 600;
                    color: #666;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 28px;
                    background: linear-gradient(135deg, #ffc107 0%, #ff9800 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .confidence-badge {{
                    display: inline-block;
                    background: #fff3cd;
                    color: #856404;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                }}
                .warning {{
                    background: #fff3cd;
                    border-left: 4px solid #ffc107;
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
                <h1 style="margin: 0;">📋 Manual Review Required</h1>
            </div>
            <div class="content">
                <p>A new property requires manual review before it can be added to the database.</p>

                <div class="property-card">
                    <h2 style="margin-top: 0; color: #856404;">
                        {address}
                    </h2>
                    <p style="font-size: 18px; color: #666; margin: 5px 0;">
                        {city}, {state} {postal_code}
                    </p>

                    <div class="property-detail">
                        <span class="label">Price:</span> {price_display}
                    </div>
                    <div class="property-detail">
                        <span class="label">Beds/Baths:</span> {bedrooms} bed / {bathrooms} bath
                    </div>
                    <div class="property-detail">
                        <span class="label">Square Feet:</span> {sqft_display}
                    </div>
                    <div class="property-detail" style="margin-top: 15px;">
                        <span class="label">Data Confidence:</span>
                        <span class="confidence-badge">{confidence:.0%}</span>
                    </div>
                </div>

                <div class="warning">
                    <strong>⚠️ Reason for Manual Review:</strong><br>
                    {reason}
                </div>

                <p><strong>What to check:</strong></p>
                <ul>
                    <li>Verify property details are accurate</li>
                    <li>Confirm pricing information</li>
                    <li>Check bed/bath counts</li>
                    <li>Review data confidence score</li>
                </ul>

                <div style="text-align: center;">
                    <a href="{review_url}" class="button">Review Property Now</a>
                </div>

                <p style="font-size: 12px; color: #666; margin-top: 20px;">
                    Change ID: {change.id}<br>
                    Created: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}
                </p>
            </div>
            <div class="footer">
                <p><strong>Artitec</strong> - Property Collection System</p>
                <p>This is an automated notification. Please do not reply.</p>
                <p>© {datetime.utcnow().year} Artitec Technology. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        self.email_service.send_email(
            to_email=to_email,
            subject=f"📋 Manual Review Required: {address}",
            html_body=html_body
        )

    def _send_auto_denied_email(
        self,
        to_email: str,
        change: CollectionChange,
        property_data: Dict[str, Any],
        confidence: float,
        denial_reason: str
    ):
        """Send auto-denial email notification."""
        change_url = f"{self.frontend_url}/admin/collection/changes/{change.id}"

        address = property_data.get("address1", "Unknown Address")
        city = property_data.get("city", "Unknown City")
        state = property_data.get("state", "Unknown State")
        postal_code = property_data.get("postal_code", "")
        price = property_data.get("price")
        bedrooms = property_data.get("bedrooms", 0)
        bathrooms = property_data.get("bathrooms", 0)
        sqft = property_data.get("sqft")

        price_display = f"${price:,.0f}" if price else "N/A"
        sqft_display = f"{sqft:,}" if sqft else "N/A"

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
                    background: linear-gradient(135deg, #dc3545 0%, #c82333 100%);
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
                .property-card {{
                    background: #f8d7da;
                    border-left: 4px solid #dc3545;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .property-detail {{
                    margin: 8px 0;
                }}
                .label {{
                    font-weight: 600;
                    color: #666;
                }}
                .button {{
                    display: inline-block;
                    padding: 14px 28px;
                    background: linear-gradient(135deg, #6c757d 0%, #5a6268 100%);
                    color: white !important;
                    text-decoration: none;
                    border-radius: 6px;
                    font-weight: 600;
                    margin: 20px 0;
                }}
                .confidence-badge {{
                    display: inline-block;
                    background: #f8d7da;
                    color: #721c24;
                    padding: 6px 12px;
                    border-radius: 20px;
                    font-weight: 600;
                    font-size: 14px;
                }}
                .alert {{
                    background: #f8d7da;
                    border-left: 4px solid #dc3545;
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
                <h1 style="margin: 0;">❌ Property Auto-Denied</h1>
            </div>
            <div class="content">
                <p>A property was automatically denied due to data quality issues.</p>

                <div class="property-card">
                    <h2 style="margin-top: 0; color: #721c24;">
                        {address}
                    </h2>
                    <p style="font-size: 18px; color: #666; margin: 5px 0;">
                        {city}, {state} {postal_code}
                    </p>

                    <div class="property-detail">
                        <span class="label">Price:</span> {price_display}
                    </div>
                    <div class="property-detail">
                        <span class="label">Beds/Baths:</span> {bedrooms} bed / {bathrooms} bath
                    </div>
                    <div class="property-detail">
                        <span class="label">Square Feet:</span> {sqft_display}
                    </div>
                    <div class="property-detail" style="margin-top: 15px;">
                        <span class="label">Data Confidence:</span>
                        <span class="confidence-badge">{confidence:.0%}</span>
                    </div>
                </div>

                <div class="alert">
                    <strong>❌ Denial Reason:</strong><br>
                    {denial_reason}
                </div>

                <p><strong>Common causes of auto-denial:</strong></p>
                <ul>
                    <li>Low data confidence score (< 75%)</li>
                    <li>Invalid or missing bedroom count</li>
                    <li>Invalid or missing bathroom count</li>
                    <li>Incomplete property information</li>
                </ul>

                <p><strong>Next steps:</strong></p>
                <ul>
                    <li>Review the data collection source</li>
                    <li>Check if auto-denial logic needs adjustment</li>
                    <li>Consider improving data collection quality</li>
                </ul>

                <div style="text-align: center;">
                    <a href="{change_url}" class="button">View Change Details</a>
                </div>

                <p style="font-size: 12px; color: #666; margin-top: 20px;">
                    Change ID: {change.id}<br>
                    Denied: {datetime.utcnow().strftime('%B %d, %Y at %I:%M %p UTC')}
                </p>
            </div>
            <div class="footer">
                <p><strong>Artitec</strong> - Property Collection System</p>
                <p>This is an automated notification. Please do not reply.</p>
                <p>© {datetime.utcnow().year} Artitec Technology. All rights reserved.</p>
            </div>
        </body>
        </html>
        """

        self.email_service.send_email(
            to_email=to_email,
            subject=f"❌ Property Auto-Denied: {address}",
            html_body=html_body
        )

    def _send_webhook(self, event_type: str, data: Dict[str, Any]):
        """
        Send webhook notification.

        Args:
            event_type: Type of event (e.g., "property.auto_approved")
            data: Event data payload
        """
        if not self.webhook_url:
            return

        try:
            payload = {
                "event": event_type,
                "timestamp": datetime.utcnow().isoformat(),
                "data": data
            }

            response = requests.post(
                self.webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=10
            )

            if response.status_code >= 200 and response.status_code < 300:
                logger.info(f"🔗 Webhook sent successfully: {event_type}")
            else:
                logger.warning(
                    f"⚠️  Webhook returned status {response.status_code}: {event_type}"
                )

        except requests.exceptions.Timeout:
            logger.error(f"⏱️  Webhook timeout: {event_type}")
        except Exception as e:
            logger.error(f"Failed to send webhook for {event_type}: {e}")


# Singleton instance
_notification_service = None


def get_notification_service(db: Session) -> PropertyApprovalNotificationService:
    """Get or create notification service instance."""
    return PropertyApprovalNotificationService(db)


__all__ = ["PropertyApprovalNotificationService", "get_notification_service"]
