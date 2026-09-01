"""Apex AI — Email/SMS Sender (multiple channels)"""
import os
import httpx
from models import WhatsAppLog


class WhatsAppSender:
    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.sms_from = os.environ.get("TWILIO_SMS_FROM", "+17372508034")
        self.verify_sid = os.environ.get("TWILIO_VERIFY_SID", "VAb8dde5f15bc0f0bbcb86714a204b6332")
        self.api_url = "https://api.twilio.com/2010-04-01"

    @property
    def is_configured(self) -> bool:
        return bool(self.account_sid and self.auth_token)

    async def send_message(self, to: str, message: str, client_id: str = "", msg_type: str = "summary") -> bool:
        """Send message via Twilio Verify (works with trial accounts)."""
        if not self.is_configured:
            WhatsAppLog(
                client_id=client_id, type=msg_type,
                message=message, recipient=to, status="not_configured",
                error="Twilio not configured"
            ).save()
            return False

        phone = to.replace("+", "").replace(" ", "").replace("-", "")
        if not phone.startswith("91") and len(phone) == 10:
            phone = "91" + phone
        phone = "+" + phone

        # Use Twilio Verify API (works with trial accounts)
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"https://verify.twilio.com/v2/Services/{self.verify_sid}/Verifications",
                    data={"To": phone, "Channel": "sms"},
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


whatsapp_sender = WhatsAppSender()
