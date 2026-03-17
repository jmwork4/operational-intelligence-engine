"""Outbound notification dispatchers for the OIE integrations framework."""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

# Severity -> Slack sidebar colour
_SEVERITY_COLORS: dict[str, str] = {
    "critical": "#FF0000",
    "high": "#FF6600",
    "medium": "#FFCC00",
    "low": "#36A64F",
    "info": "#439FE0",
}


class NotificationDispatcher:
    """Routes alert payloads to one or more notification channels."""

    def __init__(self, http_timeout: float = 30.0) -> None:
        self._timeout = http_timeout

    # -----------------------------------------------------------------
    # Slack
    # -----------------------------------------------------------------

    async def send_slack(self, webhook_url: str, alert: dict[str, Any]) -> bool:
        """Send an alert formatted as a Slack Block Kit message.

        Parameters
        ----------
        webhook_url:
            Slack incoming-webhook URL.
        alert:
            Dict with keys ``severity``, ``entity``, ``message``, and
            optionally ``actions`` (list of ``{"text": ..., "url": ...}``).
        """
        severity = alert.get("severity", "info")
        color = _SEVERITY_COLORS.get(severity, _SEVERITY_COLORS["info"])
        entity = alert.get("entity", "Unknown")
        message = alert.get("message", "No message provided")

        blocks: list[dict[str, Any]] = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"OIE Alert — {severity.upper()}",
                },
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Entity:*\n{entity}"},
                    {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": message},
            },
        ]

        # Optional action buttons
        actions_list = alert.get("actions", [])
        if actions_list:
            elements = [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": a["text"]},
                    "url": a["url"],
                }
                for a in actions_list
                if "text" in a and "url" in a
            ]
            if elements:
                blocks.append({"type": "actions", "elements": elements})

        payload = {
            "attachments": [{"color": color, "blocks": blocks}],
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(webhook_url, json=payload)
                resp.raise_for_status()
            logger.info("Slack notification sent", extra={"entity": entity})
            return True
        except httpx.HTTPError:
            logger.exception("Failed to send Slack notification")
            return False

    # -----------------------------------------------------------------
    # Email (SMTP via aiosmtplib pattern)
    # -----------------------------------------------------------------

    async def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        smtp_config: dict[str, Any],
    ) -> bool:
        """Send a plain-text email using *aiosmtplib*.

        Parameters
        ----------
        smtp_config:
            Keys: ``host``, ``port``, ``username``, ``password``,
            ``from_addr``, ``use_tls`` (bool, default ``True``).
        """
        try:
            import aiosmtplib
            from email.message import EmailMessage

            msg = EmailMessage()
            msg["From"] = smtp_config.get("from_addr", smtp_config.get("username", ""))
            msg["To"] = to
            msg["Subject"] = subject
            msg.set_content(body)

            await aiosmtplib.send(
                msg,
                hostname=smtp_config["host"],
                port=smtp_config.get("port", 587),
                username=smtp_config.get("username"),
                password=smtp_config.get("password"),
                use_tls=smtp_config.get("use_tls", True),
            )
            logger.info("Email sent", extra={"to": to, "subject": subject})
            return True
        except Exception:
            logger.exception("Failed to send email")
            return False

    # -----------------------------------------------------------------
    # SMS (Twilio)
    # -----------------------------------------------------------------

    async def send_sms(
        self,
        to: str,
        message: str,
        twilio_config: dict[str, Any],
    ) -> bool:
        """Send an SMS via the Twilio REST API using *httpx*.

        Parameters
        ----------
        twilio_config:
            Keys: ``account_sid``, ``auth_token``, ``from_number``.
        """
        account_sid = twilio_config["account_sid"]
        auth_token = twilio_config["auth_token"]
        from_number = twilio_config["from_number"]

        url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    url,
                    data={"To": to, "From": from_number, "Body": message},
                    auth=(account_sid, auth_token),
                )
                resp.raise_for_status()
            logger.info("SMS sent", extra={"to": to})
            return True
        except httpx.HTTPError:
            logger.exception("Failed to send SMS")
            return False

    # -----------------------------------------------------------------
    # PagerDuty (Events API v2)
    # -----------------------------------------------------------------

    async def send_pagerduty(
        self,
        routing_key: str,
        alert: dict[str, Any],
    ) -> bool:
        """Create a PagerDuty incident via the Events API v2."""
        severity_map: dict[str, str] = {
            "critical": "critical",
            "high": "error",
            "medium": "warning",
            "low": "info",
            "info": "info",
        }
        severity = severity_map.get(alert.get("severity", "info"), "info")

        payload = {
            "routing_key": routing_key,
            "event_action": "trigger",
            "payload": {
                "summary": alert.get("message", "OIE Alert"),
                "severity": severity,
                "source": alert.get("entity", "oie"),
                "component": "operational-intelligence-engine",
                "custom_details": alert,
            },
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    "https://events.pagerduty.com/v2/enqueue",
                    json=payload,
                )
                resp.raise_for_status()
            logger.info("PagerDuty event created")
            return True
        except httpx.HTTPError:
            logger.exception("Failed to create PagerDuty event")
            return False

    # -----------------------------------------------------------------
    # Microsoft Teams (Adaptive Cards)
    # -----------------------------------------------------------------

    async def send_teams(
        self,
        webhook_url: str,
        alert: dict[str, Any],
    ) -> bool:
        """Send an alert formatted as a Microsoft Teams Adaptive Card."""
        severity = alert.get("severity", "info")
        entity = alert.get("entity", "Unknown")
        message = alert.get("message", "No message provided")

        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": [
                            {
                                "type": "TextBlock",
                                "size": "Large",
                                "weight": "Bolder",
                                "text": f"OIE Alert — {severity.upper()}",
                            },
                            {
                                "type": "FactSet",
                                "facts": [
                                    {"title": "Entity", "value": entity},
                                    {"title": "Severity", "value": severity},
                                ],
                            },
                            {
                                "type": "TextBlock",
                                "text": message,
                                "wrap": True,
                            },
                        ],
                    },
                }
            ],
        }

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(webhook_url, json=card)
                resp.raise_for_status()
            logger.info("Teams notification sent", extra={"entity": entity})
            return True
        except httpx.HTTPError:
            logger.exception("Failed to send Teams notification")
            return False

    # -----------------------------------------------------------------
    # Multi-channel dispatch
    # -----------------------------------------------------------------

    async def dispatch(
        self,
        channels: list[dict[str, Any]],
        alert: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Route *alert* to every channel in *channels*.

        Each channel dict must contain a ``"type"`` key (one of ``slack``,
        ``email``, ``sms``, ``pagerduty``, ``teams``) plus the parameters
        required by the corresponding ``send_*`` method.

        Returns a list of result dicts, one per channel, each containing
        ``type``, ``success``, and optionally ``error``.
        """
        results: list[dict[str, Any]] = []

        for ch in channels:
            ch_type = ch.get("type", "unknown")
            success = False
            error: str | None = None

            try:
                if ch_type == "slack":
                    success = await self.send_slack(ch["webhook_url"], alert)
                elif ch_type == "email":
                    success = await self.send_email(
                        to=ch["to"],
                        subject=ch.get("subject", "OIE Alert"),
                        body=alert.get("message", ""),
                        smtp_config=ch["smtp_config"],
                    )
                elif ch_type == "sms":
                    success = await self.send_sms(
                        to=ch["to"],
                        message=alert.get("message", ""),
                        twilio_config=ch["twilio_config"],
                    )
                elif ch_type == "pagerduty":
                    success = await self.send_pagerduty(ch["routing_key"], alert)
                elif ch_type == "teams":
                    success = await self.send_teams(ch["webhook_url"], alert)
                else:
                    error = f"Unknown channel type: {ch_type}"
            except Exception as exc:
                error = str(exc)

            results.append(
                {"type": ch_type, "success": success, **({"error": error} if error else {})}
            )

        return results
