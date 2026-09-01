"""Apex AI — WhatsApp Business API Sender"""
import os
import httpx
from typing import Optional
from models import WhatsAppLog


class WhatsAppSender:
    def __init__(self):
        self.phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self.access_token = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
        self.api_url = "https://graph.facebook.com/v18.0"

    @property
    def is_configured(self) -> bool:
        return bool(self.phone_number_id and self.access_token)

    async def send_message(self, to: str, message: str, client_id: str = "", msg_type: str = "summary") -> bool:
        """Send a WhatsApp message."""
        if not self.is_configured:
            # Log as not sent
            WhatsAppLog(
                client_id=client_id, type=msg_type,
                message=message, recipient=to, status="not_configured",
                error="WhatsApp not configured"
            ).save()
            return False

        # Format phone number
        phone = to.replace("+", "").replace(" ", "").replace("-", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone

        payload = {
            "messaging_product": "whatsapp",
            "to": phone,
            "type": "text",
            "text": {"body": message}
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.api_url}/{self.phone_number_id}/messages",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.access_token}",
                        "Content-Type": "application/json"
                    },
                    timeout=30.0
                )

                success = resp.status_code == 200
                error_msg = "" if success else resp.text

                WhatsAppLog(
                    client_id=client_id, type=msg_type,
                    message=message, recipient=phone,
                    status="sent" if success else "failed",
                    error=error_msg
                ).save()

                return success

        except Exception as e:
            WhatsAppLog(
                client_id=client_id, type=msg_type,
                message=message, recipient=phone,
                status="failed", error=str(e)
            ).save()
            return False

    async def send_call_summary(self, to: str, summary_text: str, call_id: str, client_id: str = "") -> bool:
        """Send a call summary via WhatsApp."""
        return await self.send_message(to, summary_text, client_id, msg_type="call_summary")

    async def send_payment_reminder(self, to: str, reminder_text: str, client_id: str = "") -> bool:
        """Send a payment reminder via WhatsApp."""
        return await self.send_message(to, reminder_text, client_id, msg_type="payment_reminder")

    async def send_daily_report(self, to: str, report_text: str, client_id: str = "") -> bool:
        """Send a daily report via WhatsApp."""
        return await self.send_message(to, report_text, client_id, msg_type="daily_report")


# Singleton
whatsapp_sender = WhatsAppSender()
