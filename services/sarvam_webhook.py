"""Apex AI — Sarvam AI Webhook Handler

Supports two payload formats:
1. Sarvam native — interaction_transcript + final_agent_variables + metadata
2. Legacy mock — event/transcript/client_api_key (for testing)
"""
import os
import json
import hashlib
import hmac
from typing import Optional, Dict
from models import Client, Call
from services.summary import generate_call_summary, format_summary_for_whatsapp
from services.whatsapp import whatsapp_sender

# Import notification system from app
try:
    from app import push_notification
except ImportError:
    def push_notification(ntype, title, message, call_id=""):
        pass


async def handle_sarvam_webhook(payload: dict) -> dict:
    """
    Detect payload format and route to the right handler.

    Sarvam native format (campaigns / instant outbound):
        Has 'interaction_transcript' and 'final_agent_variables'
        Client identified via metadata.client_api_key

    Legacy format (testing):
        Has 'event' and 'transcript'
        Client identified via client_api_key
    """
    # Sarvam native: campaigns or instant outbound
    if "interaction_transcript" in payload or "attempt_id" in payload:
        return await handle_sarvam_native(payload)

    # Legacy mock format
    event = payload.get("event", "")
    if event == "call_ended":
        return await handle_legacy(payload)
    elif event == "call_started":
        return {"status": "ok", "message": "Call started"}
    else:
        return {"status": "ok", "message": f"Event {event} received"}


# ─── Sarvam Native Handler ─────────────────────────────────

async def handle_sarvam_native(payload: dict) -> dict:
    """Handle real Sarvam AI webhook (campaigns or instant outbound)."""

    # Identify client from metadata or webhook_config
    client = None
    meta = payload.get("metadata") or {}
    webhook_meta = (payload.get("webhook_config") or {}).get("metadata") or {}
    client_api_key = meta.get("client_api_key") or webhook_meta.get("client_api_key") or ""

    if client_api_key:
        client = Client.get_by_api_key(client_api_key)

    # Fallback: match by agent_phone_number or app_id
    if not client:
        agent_phone = payload.get("agent_phone_number") or (
            payload.get("channel_info") or {}).get("agent_phone_number", "")
        app_id = payload.get("app_id", "")
        if agent_phone or app_id:
            clients = Client.list_all()
            for c in clients:
                if c.sarvam_agent_id and c.sarvam_agent_id == app_id:
                    client = c
                    break

    if not client:
        # Default to first active client if only one exists
        clients = Client.list_all()
        active = [c for c in clients if c.status == "active"]
        if len(active) == 1:
            client = active[0]

    if not client:
        return {"status": "error", "message": "Could not identify client from webhook payload"}

    # Extract fields
    status = payload.get("status") or payload.get("completion_status", "")
    duration = payload.get("duration") or 0
    phone = payload.get("user_phone_number", "")
    attempt_id = payload.get("attempt_id", "")
    interaction_id = payload.get("interaction_id", "")
    campaign_id = payload.get("campaign_id", "")

    # Parse transcript: Sarvam uses {role, en_text}
    raw_transcript = payload.get("interaction_transcript") or []
    transcript_list = []
    transcript_text_lines = []
    for turn in raw_transcript:
        role = turn.get("role", "user")
        text = turn.get("en_text") or turn.get("text", "")
        transcript_list.append({"role": role, "text": text})
        label = "Agent" if role == "agent" else "Customer"
        transcript_text_lines.append(f"{label}: {text}")
    transcript_text = "\n".join(transcript_text_lines)

    # Extract agent variables (patient name, sentiment, etc.)
    agent_vars = payload.get("final_agent_variables") or {}
    patient_name = agent_vars.get("customer_name") or agent_vars.get("patient_name") or ""
    sentiment = agent_vars.get("sentiment", "Neutral")

    # Generate summary from transcript
    summary = generate_call_summary(transcript_text, "en", client.name)

    # Use agent-extracted name if available, else fall back to summary
    if patient_name:
        summary["patient_name"] = patient_name
    if sentiment != "Neutral":
        summary["sentiment"] = sentiment

    # Save call
    call = Call(
        client_id=client.id,
        sarvam_call_id=attempt_id or interaction_id,
        patient_name=summary.get("patient_name", ""),
        patient_phone=phone,
        language="en",  # Sarvam translates to en_text
        duration_seconds=duration,
        transcript=json.dumps(transcript_list, ensure_ascii=False),
        summary=summary.get("text", ""),
        booking_data="",
        sentiment=summary.get("sentiment", "Neutral"),
    )
    call.save()

    # Send WhatsApp summary to hospital admin
    whatsapp_sent = False
    if client.whatsapp_number:
        summary_msg = format_summary_for_whatsapp(summary, client.name)
        whatsapp_sent = await whatsapp_sender.send_call_summary(
            to=client.whatsapp_number,
            summary_text=summary_msg,
            call_id=call.id,
            client_id=client.id
        )

    # Push notification
    push_notification(
        "call",
        f"New Call: {summary.get('patient_name', 'Unknown')}",
        f"{client.name} — {summary.get('sentiment', 'Neutral')} — {int(duration)}s",
        call.id
    )

    return {
        "status": "ok",
        "call_id": call.id,
        "patient_name": summary.get("patient_name", ""),
        "sentiment": summary.get("sentiment", ""),
        "summary": summary.get("text", ""),
        "whatsapp_sent": whatsapp_sent,
        "campaign_id": campaign_id,
    }


# ─── Legacy Handler (for testing) ──────────────────────────

async def handle_legacy(payload: dict) -> dict:
    """Handle legacy mock format for testing."""
    client_api_key = payload.get("client_api_key", "")
    sarvam_call_id = payload.get("call_id", "")

    client = Client.get_by_api_key(client_api_key)
    if not client:
        return {"status": "error", "message": "Invalid API key"}

    transcript_list = payload.get("transcript", [])
    transcript_text = "\n".join(
        f"{'Agent' if t.get('role') == 'agent' else 'Customer'}: {t.get('text', '')}"
        for t in transcript_list
    )

    summary = generate_call_summary(transcript_text, payload.get("language", "hi"), client.name)
    patient_name = summary.get("patient_name", "")
    patient_phone = payload.get("caller_phone", "")

    booking_data = None
    if summary.get("booking_confirmed"):
        booking_data = {
            "patient_name": patient_name,
            "department": summary.get("department", ""),
            "date": summary.get("preferred_date", ""),
            "time": summary.get("preferred_time", ""),
            "hospital": client.name,
        }

    call = Call(
        client_id=client.id,
        sarvam_call_id=sarvam_call_id,
        patient_name=patient_name,
        patient_phone=patient_phone,
        language=payload.get("language", "hi"),
        duration_seconds=payload.get("duration_seconds", 0),
        transcript=json.dumps(transcript_list, ensure_ascii=False),
        summary=summary.get("text", ""),
        booking_data=json.dumps(booking_data, ensure_ascii=False) if booking_data else "",
        sentiment=summary.get("sentiment", "Neutral"),
    )
    call.save()

    if client.whatsapp_number:
        summary_msg = format_summary_for_whatsapp(summary, client.name)
        await whatsapp_sender.send_call_summary(
            to=client.whatsapp_number,
            summary_text=summary_msg,
            call_id=call.id,
            client_id=client.id
        )

    return {
        "status": "ok",
        "call_id": call.id,
        "summary": summary,
        "whatsapp_sent": bool(client.whatsapp_number),
    }


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify that the webhook is from Sarvam AI."""
    if not secret:
        return True
    expected = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)
