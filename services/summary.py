"""Apex AI — Call Summary Generator (v2)"""
import re
from typing import Optional


def generate_call_summary(transcript: str, language: str = "hi", client_name: str = "") -> dict:
    """Generate a structured summary from call transcript."""
    lines = [l.strip() for l in transcript.strip().split("\n") if l.strip()]

    patient_name = ""
    department = ""
    date = ""
    time_slot = ""
    sentiment = "Neutral"
    booking_confirmed = False

    for line in lines:
        lower = line.lower()

        # --- Extract patient name ---
        # Look for user lines with name patterns
        if "customer:" in lower or "patient:" in lower or "user:" in lower:
            text = line.split(":", 1)[-1].strip() if ":" in line else ""
            if not text:
                continue

            # Pattern: "mera naam X hai" or "my name is X"
            m = re.search(r"mera naam\s+(.+?)\s+hai", text, re.IGNORECASE)
            if m:
                patient_name = m.group(1).strip().title()
                continue

            m = re.search(r"naam\s+(.+?)\s+hai", text, re.IGNORECASE)
            if m:
                patient_name = m.group(1).strip().title()
                continue

            m = re.search(r"my name is\s+(.+?)(?:\.|$)", text, re.IGNORECASE)
            if m:
                patient_name = m.group(1).strip().title()
                continue

            # Fallback: short user responses that look like names (2-3 words, no digits)
            words = text.split()
            if 1 < len(words) <= 3 and not any(c.isdigit() for c in text):
                skip_words = {"haan", "ji", "ok", "theek", "subah", "shaam", "kal",
                              "parso", "yes", "no", "haanji", "accha", "acha",
                              "nahi", "thik", "bilkul", "ji haan", "ok ji",
                              "haan ji", "done", "confirm", "done ji"}
                if text.lower().strip() not in skip_words and not patient_name:
                    patient_name = text.title()

        # --- Detect department ---
        if not department:
            dept_map = [
                ("cardiology", "Cardiology"), ("cardio", "Cardiology"),
                ("heart", "Cardiology"), ("dil", "Cardiology"),
                ("chest", "Cardiology"),
                ("orthopedic", "Orthopedics"), ("ortho", "Orthopedics"),
                ("haddi", "Orthopedics"), ("bone", "Orthopedics"),
                ("joint", "Orthopedics"),
                ("neurology", "Neurology"), ("neuro", "Neurology"),
                ("brain", "Neurology"), ("head", "Neurology"),
                ("dermatology", "Dermatology"), ("skin", "Dermatology"),
                ("twacha", "Dermatology"),
                ("pediatrics", "Pediatrics"), ("pediatric", "Pediatrics"),
                ("child", "Pediatrics"), ("baby", "Pediatrics"),
                ("gynecology", "Gynecology"), ("gynae", "Gynecology"),
                ("women", "Gynecology"),
                ("dentistry", "Dentistry"), ("dental", "Dentistry"),
                ("daant", "Dentistry"), ("teeth", "Dentistry"), ("tooth", "Dentistry"),
                ("eye", "Eye"), ("ankh", "Eye"), ("nazar", "Eye"),
                ("vision", "Eye"),
                ("ent", "ENT"), ("kaan", "ENT"), ("naak", "ENT"),
                ("gala", "ENT"), ("throat", "ENT"), ("ear", "ENT"),
                ("general", "General Medicine"), ("samanya", "General Medicine"),
                ("fever", "General Medicine"), ("bukhar", "General Medicine"),
            ]
            for kw, dept_name in dept_map:
                # Use word boundary for short keywords to avoid 'ent' matching 'agent'
                if len(kw) <= 3:
                    import re as _re
                    if _re.search(r'' + kw + r'', lower):
                        department = dept_name
                        break
                elif kw in lower:
                    department = dept_name
                    break

        # --- Detect date ---
        if not date:
            if any(w in lower for w in ["kal", "tomorrow", "agle din"]):
                date = "Tomorrow"
            elif any(w in lower for w in ["parso", "day after"]):
                date = "Day After Tomorrow"
            elif any(w in lower for w in ["aaj", "today"]):
                date = "Today"
            else:
                m = re.search(r"\b(\d{1,2})\b", lower)
                if m:
                    from datetime import datetime
                    today = datetime.now()
                    day = int(m.group(1))
                    try:
                        date = datetime(today.year, today.month, day).strftime("%d %B")
                    except ValueError:
                        date = m.group(1) + "th"

        # --- Detect time ---
        if not time_slot:
            if any(w in lower for w in ["subah", "morning"]):
                time_slot = "Morning"
            elif any(w in lower for w in ["shaam", "evening"]):
                time_slot = "Evening"

        # --- Detect sentiment ---
        if any(w in lower for w in ["thank", "dhanyavaad", "achha", "great", "badiya", "perfect"]):
            sentiment = "Positive"
        elif any(w in lower for w in ["sorry", "nahi", "no", "problem", "dikkat", "pareshan"]):
            sentiment = "Needs Follow-up"

        # --- Detect booking confirmation ---
        if any(w in lower for w in ["confirm", "ho gayi", "done", "booked", "confirm ho"]):
            booking_confirmed = True

    # Build summary
    summary = {
        "patient_name": patient_name or "Unknown",
        "department": department or "Not specified",
        "preferred_date": date or "Not specified",
        "preferred_time": time_slot or "Not specified",
        "sentiment": sentiment,
        "booking_confirmed": booking_confirmed,
        "language": language,
        "total_turns": len(lines),
    }

    # Generate text summary
    if booking_confirmed:
        summary["text"] = (
            f"Patient {summary['patient_name']} called to book an appointment "
            f"in {department or 'the hospital'}. "
            f"{'Appointment confirmed for ' + date if date and date != 'Not specified' else 'Date to be confirmed'}. "
            f"Sentiment: {sentiment}."
        )
    else:
        summary["text"] = (
            f"Patient {summary['patient_name']} called regarding {department or 'general inquiry'}. "
            f"Booking pending. Sentiment: {sentiment}."
        )

    return summary


def format_summary_for_whatsapp(summary: dict, client_name: str = "Apex Hospital") -> str:
    """Format summary as a WhatsApp-friendly message."""
    status = "Confirmed" if summary.get("booking_confirmed") else "Pending"
    sentiment_emoji = {"Positive": "Smile", "Neutral": "Neutral", "Needs Follow-up": "Concern"}.get(
        summary.get("sentiment", ""), "Neutral"
    )

    msg = (
        f"Apex AI - Call Summary\n"
        f"----------------------------\n"
        f"Patient: {summary.get('patient_name', 'Unknown')}\n"
        f"Language: {summary.get('language', 'hi').upper()}\n"
        f"Date: {summary.get('preferred_date', 'Not specified')}\n"
        f"Time: {summary.get('preferred_time', 'Not specified')}\n"
        f"Department: {summary.get('department', 'Not specified')}\n\n"
        f"Summary:\n{summary.get('text', 'Call completed.')}\n\n"
        f"Status: {status}\n"
        f"Hospital: {client_name}\n"
        f"----------------------------\n"
        f"Powered by Apex AI - Intelligent Voice Agents"
    )

    return msg


def format_payment_reminder(client_name: str, amount: float, due_date: str, calls_used: int) -> str:
    """Format payment reminder for WhatsApp."""
    return (
        f"Apex AI - Payment Reminder\n"
        f"----------------------------\n"
        f"Hi {client_name}!\n\n"
        f"Your monthly subscription is due:\n"
        f"Amount: Rs {amount:,.0f}\n"
        f"Due Date: {due_date}\n"
        f"Calls this month: {calls_used}\n\n"
        f"Please make the payment to continue\n"
        f"enjoying uninterrupted AI voice agent service.\n\n"
        f"Pay via UPI/Bank Transfer\n"
        f"----------------------------\n"
        f"Powered by Apex AI"
    )


def format_daily_report(client_name: str, calls_today: int, bookings: int, total_duration: float) -> str:
    """Format daily report for WhatsApp."""
    mins = int(total_duration // 60)
    secs = int(total_duration % 60)
    return (
        f"Apex AI - Daily Report\n"
        f"----------------------------\n"
        f"Hi {client_name}! Here's today's summary:\n\n"
        f"Total Calls: {calls_today}\n"
        f"Bookings Made: {bookings}\n"
        f"Total Duration: {mins}m {secs}s\n\n"
        f"Keep growing with Apex AI!\n"
        f"----------------------------\n"
        f"Powered by Apex AI"
    )
