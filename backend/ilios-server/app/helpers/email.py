import json
import logging
from datetime import datetime, timezone
from typing import Annotated

import requests as requests
from fastapi import HTTPException, status

from app.models.user import UserInvitation, UserPasswordRecovery
from app.settings import settings

logger = logging.getLogger(__name__)


class EmailUtility:
    """
    Implements mailgun email sending
    Docs: https://documentation.mailgun.com/en/latest/api-sending.html
    """

    # maintain constants at one place
    EMAIL_TEMPLATE_USERNAME_VAR_NAME = "username"

    INVITATION_EMAIL_SUBJECT = "You're invited"
    RESEND_INVITATION_EMAIL_SUBJECT = f"Reminder: {INVITATION_EMAIL_SUBJECT}"
    INVITATION_EMAIL_TEMPLATE = "Invitation email"
    INVITATION_EMAIL_TEMPLATE_URL_VAR_NAME = "invitation_url"
    INVITATION_EMAIL_TEMPLATE_EXP_VAR_NAME = "expiration_days"

    RESET_PASSWORD_EMAIL_SUBJECT = "Reset password"
    RESET_PASSWORD_EMAIL_TEMPLATE = "Reset password"
    RESET_PASSWORD_TEMPLATE_URL_VAR_NAME = "reset_password_url"
    RESET_PASSWORD_TEMPLATE_EXP_VAR_NAME = "expiration_minutes"

    EMAIL_UPDATE_TEMPLATE = "email address update notification"
    EMAIL_UPDATE_SUBJECT = "Email changed successfully"
    EMAIL_UPDATE_TEMPLATE_USER_EMAIL_VAR_NAME = "user_email"
    EMAIL_UPDATE_TEMPLATE_URL_VAR_NAME = "login_url"
    EMAIL_UPDATE_TEMPLATE_SUPPORT_EMAIL_VAR_NAME = "support_email"

    def __init__(self, raise_exception=False):
        self.api_key = settings.mailgun_api_key
        self.domain_name = settings.mailgun_domain_name
        self.email_sender = settings.default_email_sender
        self.url = f"https://{settings.mailgun_rest_api_endpoint}/v3"
        self.raise_exception = raise_exception

    @staticmethod
    def _handle_response(response):  # noqa: FNE008
        if not response.ok:
            logger.error(response.text)
            response.raise_for_status()

    def _handle_response_wrapper(self, response):
        """Depending on the class setup, raise exception or handle it silently"""
        if self.raise_exception:
            return self._handle_response(response)

        error = None
        try:
            self._handle_response(response)
        except Exception as exc:
            logger.warning(f"An error occurred during email sending: {str(exc)}")
            error = True
        return error

    def _send_email(self, recipients, subject, text=None, template_settings=None):
        request_url = f"{self.url}/{self.domain_name}/messages"
        payload = {
            "from": self.email_sender,
            "to": recipients,
            "subject": subject,
        }
        if text:
            payload["text"] = text
        if template_settings:
            payload.update(template_settings)
        return self._handle_response_wrapper(requests.post(request_url, auth=("api", self.api_key), data=payload))

    @staticmethod
    def _build_link_to_follow(url, token, email):
        return f"{url}?token={token}&email={email}"

    def send_invitation_email(self, recipient, token, subject=None):
        # by default, use invitation email subject
        subject = subject or self.INVITATION_EMAIL_SUBJECT
        template_settings = {
            "template": self.INVITATION_EMAIL_TEMPLATE,
            "h:X-Mailgun-Variables": json.dumps(
                {
                    self.EMAIL_TEMPLATE_USERNAME_VAR_NAME: recipient.first_name,
                    self.INVITATION_EMAIL_TEMPLATE_URL_VAR_NAME: self._build_link_to_follow(
                        settings.invitation_url, token, recipient.email
                    ),
                    self.INVITATION_EMAIL_TEMPLATE_EXP_VAR_NAME: settings.invitation_link_expire_days,
                }
            ),
        }
        return self._send_email(recipients=[recipient.email], subject=subject, template_settings=template_settings)

    def send_invitation_reminder_email(self, recipient, token):
        return self.send_invitation_email(recipient=recipient, token=token, subject=self.RESEND_INVITATION_EMAIL_SUBJECT)

    def send_password_recovery_email(self, recipient, token):
        template_settings = {
            "template": self.RESET_PASSWORD_EMAIL_TEMPLATE,
            "h:X-Mailgun-Variables": json.dumps(
                {
                    self.EMAIL_TEMPLATE_USERNAME_VAR_NAME: recipient.first_name,
                    self.RESET_PASSWORD_TEMPLATE_URL_VAR_NAME: self._build_link_to_follow(
                        settings.password_reset_url, token, recipient.email
                    ),
                    self.RESET_PASSWORD_TEMPLATE_EXP_VAR_NAME: settings.reset_password_expires_minutes,
                }
            ),
        }
        return self._send_email(
            recipients=[recipient.email], subject=self.RESET_PASSWORD_EMAIL_SUBJECT, template_settings=template_settings
        )

    def send_email_change_notification(self, username, old_user_email, user_email):
        template_settings = {
            "template": self.EMAIL_UPDATE_TEMPLATE,
            "h:X-Mailgun-Variables": json.dumps(
                {
                    self.EMAIL_TEMPLATE_USERNAME_VAR_NAME: username,
                    self.EMAIL_UPDATE_TEMPLATE_USER_EMAIL_VAR_NAME: user_email,
                    self.EMAIL_UPDATE_TEMPLATE_URL_VAR_NAME: settings.login_url,
                    self.EMAIL_UPDATE_TEMPLATE_SUPPORT_EMAIL_VAR_NAME: settings.support_email,
                }
            ),
        }
        return self._send_email(
            recipients=[old_user_email, user_email],
            subject=self.EMAIL_UPDATE_SUBJECT,
            template_settings=template_settings,
        )


class EmailTokenValidator:

    @staticmethod
    def validate(email: str, token: str, user_password_deeplink: Annotated[UserInvitation | UserPasswordRecovery, None]):
        """Util to raise Fastapi's HTTPException if provided token and user does not meet requirements."""
        if user_password_deeplink is None:
            logger.error(f"There's no such token in the database: {token}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The link is not active anymore, please, contact the admin")
        if user_password_deeplink.user.email != email:
            logger.error(f"Email in the query params doesn't match the email of the user associated with token {token}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "The link is not active anymore, please, contact the admin")
        if user_password_deeplink.expires_at.astimezone(timezone.utc) < datetime.now(timezone.utc):
            logger.error(f"Invitation for the token is expired: {token}")
            raise HTTPException(status.HTTP_410_GONE, "The link has expired, please, contact the admin")
