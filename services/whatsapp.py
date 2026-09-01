"""Apex AI — SMS Sender via Twilio (works immediately, no templates needed)"""
import os
import httpx
from models import WhatsAppLog


class WhatsAppSender:
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.sms_from = os.environ.get("TWILIO_SMS_FROM", "+18335462728")
        self.api_url = "https://api.twilio.com/2010-04-01"

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token)

    async def send_message(self, to: str, message: str, client_id: str = "", msg_type: str = "summary") -> bool:
        """Send an SMS message via Twilio."""
        if not self.is_configured:
            WhatsAppLog(
                client_id=client_id, type=msg_type,
                message=message, recipient=to, status="not_configured",
                error="Twilio not configured"
            ).save()
            return False

        # Format phone number
        phone = to.replace("+", "").replace(" ", "").replace("-", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone
        phone = "+" + phone

        payload = {
            "To": phone,
            "From": self.sms_from,
            "Body": message
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.api_url}/Accounts/{self.account_sid}/Messages.json",
                    data=payload,
                    auth=(self.account_sid, self.auth_token),
                    timeout=30.0
                )

                success = resp.status_code == 201
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
        return await self.send_message(to, summary_text, client_id, msg_type="call_summary")

    async def send_payment_reminder(self, to: str, reminder_text: str, client_id: str = "") -> bool:
        return await self.send_message(to, reminder_text, client_id, msg_type="payment_reminder")

    async def send_daily_report(self, to: str, report_text: str, client_id: str = "") -> bool:
        return await self.send_message(to, report_text, client_id, msg_type="daily_report")


# Singleton
whatsapp_sender = WhatsAppSender()
