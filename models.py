"""Apex AI Platform — Database Models"""
import uuid
import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict

DB_PATH = Path(__file__).parent / "data" / "apex_ai.db"
DB_PATH.parent.mkdir(parents=True, exist_ok=True)


def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS clients (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            api_key TEXT UNIQUE NOT NULL,
            plan TEXT DEFAULT 'basic',
            price_per_month REAL DEFAULT 999.0,
            status TEXT DEFAULT 'active',
            sarvam_agent_id TEXT,
            whatsapp_number TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT
        );

        CREATE TABLE IF NOT EXISTS calls (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES clients(id),
            sarvam_call_id TEXT,
            patient_name TEXT,
            patient_phone TEXT,
            language TEXT DEFAULT 'hi',
            duration_seconds REAL DEFAULT 0,
            transcript TEXT DEFAULT '[]',
            summary TEXT,
            booking_data TEXT,
            sentiment TEXT,
            status TEXT DEFAULT 'completed',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS payments (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES clients(id),
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            due_date TEXT NOT NULL,
            paid_at TEXT,
            calls_used INTEGER DEFAULT 0,
            calls_included INTEGER DEFAULT 100,
            notes TEXT,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS whatsapp_logs (
            id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL REFERENCES clients(id),
            call_id TEXT,
            type TEXT NOT NULL,
            message TEXT NOT NULL,
            recipient TEXT,
            status TEXT DEFAULT 'sent',
            error TEXT,
            created_at TEXT NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_calls_client ON calls(client_id);
        CREATE INDEX IF NOT EXISTS idx_calls_created ON calls(created_at);
        CREATE INDEX IF NOT EXISTS idx_payments_client ON payments(client_id);
        CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status);
        CREATE INDEX IF NOT EXISTS idx_whatsapp_client ON whatsapp_logs(client_id);
    """)
    conn.commit()
    conn.close()


class Client:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", f"cli_{uuid.uuid4().hex[:8]}")
        self.name = kwargs.get("name", "")
        self.phone = kwargs.get("phone", "")
        self.email = kwargs.get("email", "")
        self.api_key = kwargs.get("api_key", f"apx_{uuid.uuid4().hex}")
        self.plan = kwargs.get("plan", "basic")
        self.price_per_month = kwargs.get("price_per_month", 999.0)
        self.status = kwargs.get("status", "active")
        self.sarvam_agent_id = kwargs.get("sarvam_agent_id", "")
        self.whatsapp_number = kwargs.get("whatsapp_number", "")
        self.created_at = kwargs.get("created_at", datetime.now().isoformat())
        self.updated_at = kwargs.get("updated_at", None)

    def save(self):
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO clients
            (id, name, phone, email, api_key, plan, price_per_month, status,
             sarvam_agent_id, whatsapp_number, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (self.id, self.name, self.phone, self.email, self.api_key,
              self.plan, self.price_per_month, self.status,
              self.sarvam_agent_id, self.whatsapp_number,
              self.created_at, datetime.now().isoformat()))
        conn.commit()
        conn.close()
        return self

    def delete(self):
        conn = get_db()
        conn.execute("DELETE FROM clients WHERE id = ?", (self.id,))
        conn.commit()
        conn.close()

    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "phone": self.phone,
            "email": self.email, "api_key": self.api_key, "plan": self.plan,
            "price_per_month": self.price_per_month, "status": self.status,
            "sarvam_agent_id": self.sarvam_agent_id,
            "whatsapp_number": self.whatsapp_number,
            "created_at": self.created_at, "updated_at": self.updated_at,
        }

    @staticmethod
    def get(client_id: str) -> Optional["Client"]:
        conn = get_db()
        row = conn.execute("SELECT * FROM clients WHERE id = ?", (client_id,)).fetchone()
        conn.close()
        return Client(**dict(row)) if row else None

    @staticmethod
    def get_by_api_key(api_key: str) -> Optional["Client"]:
        conn = get_db()
        row = conn.execute("SELECT * FROM clients WHERE api_key = ?", (api_key,)).fetchone()
        conn.close()
        return Client(**dict(row)) if row else None

    @staticmethod
    def list_all(limit: int = 100) -> List["Client"]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM clients ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [Client(**dict(r)) for r in rows]


class Call:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", f"call_{uuid.uuid4().hex[:8]}")
        self.client_id = kwargs.get("client_id", "")
        self.sarvam_call_id = kwargs.get("sarvam_call_id", "")
        self.patient_name = kwargs.get("patient_name", "")
        self.patient_phone = kwargs.get("patient_phone", "")
        self.language = kwargs.get("language", "hi")
        self.duration_seconds = kwargs.get("duration_seconds", 0)
        self.transcript = kwargs.get("transcript", "[]")
        self.summary = kwargs.get("summary", "")
        self.booking_data = kwargs.get("booking_data", "")
        self.sentiment = kwargs.get("sentiment", "")
        self.status = kwargs.get("status", "completed")
        self.created_at = kwargs.get("created_at", datetime.now().isoformat())

    def save(self):
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO calls
            (id, client_id, sarvam_call_id, patient_name, patient_phone,
             language, duration_seconds, transcript, summary, booking_data,
             sentiment, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (self.id, self.client_id, self.sarvam_call_id,
              self.patient_name, self.patient_phone, self.language,
              self.duration_seconds, self.transcript, self.summary,
              self.booking_data, self.sentiment, self.status, self.created_at))
        conn.commit()
        conn.close()
        return self

    def to_dict(self):
        d = {
            "id": self.id, "client_id": self.client_id,
            "sarvam_call_id": self.sarvam_call_id,
            "patient_name": self.patient_name,
            "patient_phone": self.patient_phone,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "summary": self.summary,
            "sentiment": self.sentiment,
            "status": self.status,
            "created_at": self.created_at,
        }
        try:
            d["transcript"] = json.loads(self.transcript) if self.transcript else []
        except (json.JSONDecodeError, TypeError):
            d["transcript"] = []
        try:
            d["booking_data"] = json.loads(self.booking_data) if self.booking_data else None
        except (json.JSONDecodeError, TypeError):
            d["booking_data"] = None
        return d

    @staticmethod
    def get(call_id: str) -> Optional["Call"]:
        conn = get_db()
        row = conn.execute("SELECT * FROM calls WHERE id = ?", (call_id,)).fetchone()
        conn.close()
        return Call(**dict(row)) if row else None

    @staticmethod
    def list_by_client(client_id: str, limit: int = 100) -> List["Call"]:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM calls WHERE client_id = ? ORDER BY created_at DESC LIMIT ?",
            (client_id, limit)
        ).fetchall()
        conn.close()
        return [Call(**dict(r)) for r in rows]

    @staticmethod
    def list_all(limit: int = 100) -> List["Call"]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM calls ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [Call(**dict(r)) for r in rows]

    @staticmethod
    def count_by_client(client_id: str) -> int:
        conn = get_db()
        row = conn.execute("SELECT COUNT(*) as cnt FROM calls WHERE client_id = ?", (client_id,)).fetchone()
        conn.close()
        return row["cnt"] if row else 0

    @staticmethod
    def total_duration_by_client(client_id: str) -> float:
        conn = get_db()
        row = conn.execute(
            "SELECT COALESCE(SUM(duration_seconds), 0) as total FROM calls WHERE client_id = ?",
            (client_id,)
        ).fetchone()
        conn.close()
        return row["total"] if row else 0


class Payment:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", f"pay_{uuid.uuid4().hex[:8]}")
        self.client_id = kwargs.get("client_id", "")
        self.amount = kwargs.get("amount", 0)
        self.status = kwargs.get("status", "pending")
        self.due_date = kwargs.get("due_date", "")
        self.paid_at = kwargs.get("paid_at", None)
        self.calls_used = kwargs.get("calls_used", 0)
        self.calls_included = kwargs.get("calls_included", 100)
        self.notes = kwargs.get("notes", "")
        self.created_at = kwargs.get("created_at", datetime.now().isoformat())

    def save(self):
        conn = get_db()
        conn.execute("""
            INSERT OR REPLACE INTO payments
            (id, client_id, amount, status, due_date, paid_at,
             calls_used, calls_included, notes, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (self.id, self.client_id, self.amount, self.status,
              self.due_date, self.paid_at, self.calls_used,
              self.calls_included, self.notes, self.created_at))
        conn.commit()
        conn.close()
        return self

    def to_dict(self):
        return {
            "id": self.id, "client_id": self.client_id,
            "amount": self.amount, "status": self.status,
            "due_date": self.due_date, "paid_at": self.paid_at,
            "calls_used": self.calls_used,
            "calls_included": self.calls_included,
            "notes": self.notes, "created_at": self.created_at,
        }

    @staticmethod
    def get(payment_id: str) -> Optional["Payment"]:
        conn = get_db()
        row = conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone()
        conn.close()
        return Payment(**dict(row)) if row else None

    @staticmethod
    def list_by_client(client_id: str) -> List["Payment"]:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM payments WHERE client_id = ? ORDER BY created_at DESC",
            (client_id,)
        ).fetchall()
        conn.close()
        return [Payment(**dict(r)) for r in rows]

    @staticmethod
    def list_pending() -> List["Payment"]:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM payments WHERE status = 'pending' ORDER BY due_date ASC"
        ).fetchall()
        conn.close()
        return [Payment(**dict(r)) for r in rows]

    @staticmethod
    def list_all(limit: int = 100) -> List["Payment"]:
        conn = get_db()
        rows = conn.execute("SELECT * FROM payments ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [Payment(**dict(r)) for r in rows]


class WhatsAppLog:
    def __init__(self, **kwargs):
        self.id = kwargs.get("id", f"wa_{uuid.uuid4().hex[:8]}")
        self.client_id = kwargs.get("client_id", "")
        self.call_id = kwargs.get("call_id", "")
        self.type = kwargs.get("type", "")
        self.message = kwargs.get("message", "")
        self.recipient = kwargs.get("recipient", "")
        self.status = kwargs.get("status", "sent")
        self.error = kwargs.get("error", "")
        self.created_at = kwargs.get("created_at", datetime.now().isoformat())

    def save(self):
        conn = get_db()
        conn.execute("""
            INSERT INTO whatsapp_logs
            (id, client_id, call_id, type, message, recipient, status, error, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (self.id, self.client_id, self.call_id, self.type,
              self.message, self.recipient, self.status, self.error,
              self.created_at))
        conn.commit()
        conn.close()
        return self

    def to_dict(self):
        return {
            "id": self.id, "client_id": self.client_id,
            "call_id": self.call_id, "type": self.type,
            "message": self.message, "recipient": self.recipient,
            "status": self.status, "error": self.error,
            "created_at": self.created_at,
        }

    @staticmethod
    def list_by_client(client_id: str, limit: int = 50) -> List["WhatsAppLog"]:
        conn = get_db()
        rows = conn.execute(
            "SELECT * FROM whatsapp_logs WHERE client_id = ? ORDER BY created_at DESC LIMIT ?",
            (client_id, limit)
        ).fetchall()
        conn.close()
        return [WhatsAppLog(**dict(r)) for r in rows]


# Initialize database on import
init_db()
