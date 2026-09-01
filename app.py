"""Apex AI Platform — Main Server"""
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")

from fastapi import FastAPI, HTTPException, Request, Query
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from models import Client, Call, Payment, WhatsAppLog, get_db
from services.summary import (
    generate_call_summary, format_summary_for_whatsapp,
    format_payment_reminder, format_daily_report
)
from services.whatsapp import whatsapp_sender
from services.sarvam_webhook import handle_sarvam_webhook

app = FastAPI(title="Apex AI Platform", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve static files
STATIC_DIR = Path(__file__).parent / "static"
STATIC_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# ─── Dashboard ────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root():
    return FileResponse(STATIC_DIR / "dashboard.html")


@app.get("/api/dashboard")
async def dashboard_stats():
    """Get overview stats for the dashboard."""
    clients = Client.list_all()
    calls = Call.list_all(1000)
    payments = Payment.list_all(1000)
    pending_payments = [p for p in payments if p.status == "pending"]

    total_revenue = sum(p.amount for p in payments if p.status == "paid")
    pending_amount = sum(p.amount for p in pending_payments)

    # This month's stats
    now = datetime.now()
    month_start = now.replace(day=1, hour=0, minute=0, second=0).isoformat()
    month_calls = [c for c in calls if c.created_at >= month_start]

    return {
        "total_clients": len(clients),
        "active_clients": len([c for c in clients if c.status == "active"]),
        "total_calls": len(calls),
        "month_calls": len(month_calls),
        "total_revenue": total_revenue,
        "pending_amount": pending_amount,
        "pending_payments": len(pending_payments),
        "total_duration_minutes": round(sum(c.duration_seconds for c in calls) / 60, 1),
    }


# ─── Client Management ───────────────────────────────────────

@app.get("/api/clients")
async def list_clients():
    clients = Client.list_all()
    result = []
    for c in clients:
        d = c.to_dict()
        d["total_calls"] = Call.count_by_client(c.id)
        d["total_duration"] = round(Call.total_duration_by_client(c.id) / 60, 1)
        result.append(d)
    return {"clients": result}


@app.post("/api/clients")
async def create_client(request: Request):
    data = await request.json()
    if not data.get("name"):
        raise HTTPException(400, "Name is required")

    client = Client(
        name=data["name"],
        phone=data.get("phone", ""),
        email=data.get("email", ""),
        plan=data.get("plan", "basic"),
        price_per_month=data.get("price_per_month", 999),
        whatsapp_number=data.get("whatsapp_number", ""),
        sarvam_agent_id=data.get("sarvam_agent_id", ""),
    )
    client.save()

    # Create first payment record
    due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    Payment(
        client_id=client.id,
        amount=client.price_per_month,
        due_date=due,
        calls_included=100 if client.plan == "basic" else 500,
    ).save()

    return {"client": client.to_dict()}


@app.get("/api/clients/{client_id}")
async def get_client(client_id: str):
    client = Client.get(client_id)
    if not client:
        raise HTTPException(404, "Client not found")
    d = client.to_dict()
    d["total_calls"] = Call.count_by_client(client.id)
    d["total_duration"] = round(Call.total_duration_by_client(client.id) / 60, 1)
    d["calls"] = [c.to_dict() for c in Call.list_by_client(client.id, 20)]
    d["payments"] = [p.to_dict() for p in Payment.list_by_client(client.id)]
    return {"client": d}


@app.put("/api/clients/{client_id}")
async def update_client(client_id: str, request: Request):
    client = Client.get(client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    data = await request.json()
    for key in ["name", "phone", "email", "plan", "price_per_month",
                "status", "whatsapp_number", "sarvam_agent_id"]:
        if key in data:
            setattr(client, key, data[key])
    client.save()
    return {"client": client.to_dict()}


@app.delete("/api/clients/{client_id}")
async def delete_client(client_id: str):
    client = Client.get(client_id)
    if not client:
        raise HTTPException(404, "Client not found")
    client.delete()
    return {"status": "deleted"}


# ─── Call Management ──────────────────────────────────────────

@app.get("/api/calls")
async def list_calls(client_id: str = Query(None), limit: int = Query(100)):
    if client_id:
        calls = Call.list_by_client(client_id, limit)
    else:
        calls = Call.list_all(limit)
    return {"calls": [c.to_dict() for c in calls]}


@app.get("/api/calls/{call_id}")
async def get_call(call_id: str):
    call = Call.get(call_id)
    if not call:
        raise HTTPException(404, "Call not found")
    return {"call": call.to_dict()}


@app.get("/api/calls/{call_id}/summary")
async def get_call_summary(call_id: str):
    call = Call.get(call_id)
    if not call:
        raise HTTPException(404, "Call not found")

    client = Client.get(call.client_id)
    client_name = client.name if client else "Apex Hospital"

    summary = {
        "text": call.summary,
        "sentiment": call.sentiment,
        "booking_data": None,
    }
    try:
        summary["booking_data"] = json.loads(call.booking_data) if call.booking_data else None
    except (json.JSONDecodeError, TypeError):
        pass

    formatted = format_summary_for_whatsapp(summary, client_name)
    return {"summary": summary, "formatted": formatted}


# ─── Payment Management ──────────────────────────────────────

@app.get("/api/payments")
async def list_payments(client_id: str = Query(None), status: str = Query(None)):
    if client_id:
        payments = Payment.list_by_client(client_id)
    else:
        payments = Payment.list_all()
    if status:
        payments = [p for p in payments if p.status == status]
    return {"payments": [p.to_dict() for p in payments]}


@app.post("/api/payments")
async def create_payment(request: Request):
    data = await request.json()
    if not data.get("client_id") or not data.get("amount"):
        raise HTTPException(400, "client_id and amount required")

    payment = Payment(
        client_id=data["client_id"],
        amount=data["amount"],
        due_date=data.get("due_date", (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")),
        calls_included=data.get("calls_included", 100),
    )
    payment.save()
    return {"payment": payment.to_dict()}


@app.put("/api/payments/{payment_id}/mark-paid")
async def mark_payment_paid(payment_id: str):
    payment = Payment.get(payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    payment.status = "paid"
    payment.paid_at = datetime.now().isoformat()
    payment.save()
    return {"payment": payment.to_dict()}


@app.post("/api/payments/{payment_id}/remind")
async def send_payment_reminder(payment_id: str):
    payment = Payment.get(payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")

    client = Client.get(payment.client_id)
    if not client:
        raise HTTPException(404, "Client not found")

    if not client.whatsapp_number:
        raise HTTPException(400, "Client has no WhatsApp number")

    msg = format_payment_reminder(client.name, payment.amount, payment.due_date, payment.calls_used)
    sent = await whatsapp_sender.send_payment_reminder(
        to=client.whatsapp_number,
        reminder_text=msg,
        client_id=client.id
    )

    return {"status": "sent" if sent else "failed", "message": msg}


@app.post("/api/payments/generate-monthly")
async def generate_monthly_payments():
    """Generate payment records for all active clients."""
    clients = Client.list_all()
    created = []
    now = datetime.now()
    due = (now + timedelta(days=30)).strftime("%Y-%m-%d")

    for client in clients:
        if client.status != "active":
            continue
        # Check if already has pending payment for this month
        existing = [p for p in Payment.list_by_client(client.id)
                    if p.status == "pending" and p.due_date >= now.strftime("%Y-%m-%d")]
        if existing:
            continue

        payment = Payment(
            client_id=client.id,
            amount=client.price_per_month,
            due_date=due,
            calls_used=Call.count_by_client(client.id),
            calls_included=100 if client.plan == "basic" else 500,
        )
        payment.save()
        created.append(payment.to_dict())

    return {"created": len(created), "payments": created}


# ─── WhatsApp Logs ───────────────────────────────────────────

@app.get("/api/whatsapp-logs")
async def list_whatsapp_logs(client_id: str = Query(None), limit: int = Query(50)):
    if client_id:
        logs = WhatsAppLog.list_by_client(client_id, limit)
    else:
        conn = get_db()
        rows = conn.execute("SELECT * FROM whatsapp_logs ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        logs = [WhatsAppLog(**dict(r)) for r in rows]
    return {"logs": [l.to_dict() for l in logs]}


# ─── Sarvam AI Webhook ───────────────────────────────────────

@app.post("/webhook/sarvam")
async def sarvam_webhook(request: Request):
    """Receive call data from Sarvam AI Voice Agent."""
    payload = await request.json()
    result = await handle_sarvam_webhook(payload)
    return result


@app.get("/webhook/sarvam")
async def sarvam_webhook_verify(request: Request):
    """Sarvam AI webhook verification."""
    return {"status": "ok", "message": "Apex AI webhook is live"}


# ─── Analytics ───────────────────────────────────────────────

@app.get("/api/analytics/calls-by-day")
async def calls_by_day():
    """Get call counts for the last 7 days."""
    conn = get_db()
    days = []
    now = datetime.now()
    for i in range(6, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        label = (now - timedelta(days=i)).strftime("%a")
        row = conn.execute("SELECT COUNT(*) as cnt FROM calls WHERE date(created_at) = ?", (day,)).fetchone()
        days.append({"label": label, "value": row["cnt"] if row else 0, "date": day})
    conn.close()
    return {"days": days}


@app.get("/api/analytics/sentiment")
async def sentiment_distribution():
    """Get sentiment breakdown."""
    conn = get_db()
    rows = conn.execute("SELECT sentiment, COUNT(*) as cnt FROM calls GROUP BY sentiment").fetchall()
    conn.close()
    result = {"Positive": 0, "Neutral": 0, "Needs Follow-up": 0}
    for r in rows:
        s = r["sentiment"] or "Neutral"
        result[s] = r["cnt"]
    return result


@app.get("/api/analytics/hourly")
async def hourly_distribution():
    """Get call distribution by hour."""
    conn = get_db()
    rows = conn.execute("SELECT strftime('%H', created_at) as hour, COUNT(*) as cnt FROM calls GROUP BY hour ORDER BY hour").fetchall()
    conn.close()
    hours = [{"hour": int(r["hour"]), "count": r["cnt"]} for r in rows]
    return {"hours": hours}


@app.get("/api/analytics/client-health")
async def client_api_health():
    """Check webhook connectivity for each client."""
    clients = Client.list_all()
    result = []
    for c in clients:
        has_key = bool(c.api_key)
        has_webhook = bool(c.sarvam_agent_id)
        total_calls = Call.count_by_client(c.id)
        result.append({
            "client_id": c.id,
            "name": c.name,
            "api_key_valid": has_key,
            "api_key": c.api_key[:12] + "..." if c.api_key else "",
            "webhook_configured": has_webhook,
            "has_received_calls": total_calls > 0,
            "total_calls": total_calls,
            "status": "active" if total_calls > 0 else "pending",
        })
    return {"clients": result}


# ─── Push Notifications ──────────────────────────────────────
# Store recent notifications in memory (last 50)
notifications = []

def push_notification(ntype, title, message, call_id=""):
    import uuid
    notif = {
        "id": str(uuid.uuid4().hex[:8]),
        "type": ntype,
        "title": title,
        "message": message,
        "call_id": call_id,
        "read": False,
        "created_at": datetime.now().isoformat(),
    }
    notifications.insert(0, notif)
    if len(notifications) > 50:
        notifications.pop()
    return notif


@app.get("/api/notifications")
async def list_notifications(limit: int = Query(20)):
    return {"notifications": notifications[:limit]}


@app.get("/api/notifications/unread-count")
async def unread_count():
    return {"count": len([n for n in notifications if not n["read"]])}


@app.post("/api/notifications/mark-read")
async def mark_all_read():
    for n in notifications:
        n["read"] = True
    return {"status": "ok"}


# ─── Health Check ─────────────────────────────────────────────

@app.get("/health")
async def health():
    return {
        "status": "running",
        "platform": "Apex AI",
        "whatsapp": whatsapp_sender.is_configured,
        "version": "1.0.0",
    }


# ─── Auto-seed clients on startup if empty ─────────────────
@app.on_event("startup")
async def seed_clients():
    clients = Client.list_all()
    if len(clients) == 0:
        import uuid
        default_clients = [
            {"name": "V Care Hospital", "phone": "+911122334455", "plan": "pro", "price_per_month": 2999, "whatsapp_number": "+917996700712"},
            {"name": "Ayaansh Hospital", "phone": "+911122334466", "plan": "pro", "price_per_month": 2999, "whatsapp_number": "+917996700712"},
            {"name": "Apollo Hospital Delhi", "phone": "+911122334477", "plan": "basic", "price_per_month": 999, "whatsapp_number": "+917996700712"},
            {"name": "Max Healthcare", "phone": "+911122334488", "plan": "enterprise", "price_per_month": 9999, "whatsapp_number": "+917996700712"},
            {"name": "Fortis Hospital", "phone": "+911122334499", "plan": "pro", "price_per_month": 2999, "whatsapp_number": "+917996700712"},
        ]
        for c in default_clients:
            client = Client(
                name=c["name"],
                phone=c["phone"],
                plan=c["plan"],
                price_per_month=c["price_per_month"],
                whatsapp_number=c["whatsapp_number"],
            )
            client.save()
        print(f"Seeded {len(default_clients)} default clients")


if __name__ == "__main__":
    import uvicorn
    print("Apex AI Platform v1.0.0")
    print("Dashboard: http://localhost:8766")
    print("WhatsApp: " + ("Configured" if whatsapp_sender.is_configured else "Not configured"))
    uvicorn.run(app, host="0.0.0.0", port=8766)
