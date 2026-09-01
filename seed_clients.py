"""Seed existing hospital clients into the Apex AI platform."""
import sys
sys.path.insert(0, '.')

from models import Client, Payment, init_db
from datetime import datetime, timedelta

# Initialize database
init_db()

# Existing voice agent clients
CLIENTS = [
    {
        "name": "V Care Hospital",
        "phone": "+91 98765 43210",
        "email": "admin@vcarehospital.com",
        "whatsapp_number": "9876543210",
        "plan": "pro",
        "price_per_month": 2999,
        "sarvam_agent_id": "vcare_agent_001",
    },
    {
        "name": "Ayaansh Hospital",
        "phone": "+91 91234 56789",
        "email": "admin@ayaanshhospital.com",
        "whatsapp_number": "9123456789",
        "plan": "pro",
        "price_per_month": 2999,
        "sarvam_agent_id": "ayaansh_agent_001",
    },
    {
        "name": "Apollo Hospital Delhi",
        "phone": "+91 98765 43210",
        "email": "admin@apollo.com",
        "whatsapp_number": "9876543210",
        "plan": "basic",
        "price_per_month": 999,
        "sarvam_agent_id": "apollo_agent_001",
    },
    {
        "name": "Max Healthcare",
        "phone": "+91 99887 76655",
        "email": "admin@maxhealthcare.com",
        "whatsapp_number": "9988776655",
        "plan": "enterprise",
        "price_per_month": 9999,
        "sarvam_agent_id": "max_agent_001",
    },
    {
        "name": "Fortis Hospital",
        "phone": "+91 88776 65544",
        "email": "admin@fortis.com",
        "whatsapp_number": "8877665544",
        "plan": "pro",
        "price_per_month": 2999,
        "sarvam_agent_id": "fortis_agent_001",
    },
]

created = 0
for cdata in CLIENTS:
    # Check if client already exists
    existing = [c for c in Client.list_all() if c.name == cdata["name"]]
    if existing:
        print(f"  [SKIP] {cdata['name']} already exists")
        continue

    client = Client(**cdata)
    client.save()

    # Create payment record
    due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
    Payment(
        client_id=client.id,
        amount=cdata["price_per_month"],
        due_date=due,
        calls_included=100 if cdata["plan"] == "basic" else 500 if cdata["plan"] == "pro" else 9999,
    ).save()

    print(f"  [OK] {cdata['name']} ({cdata['plan']}) — API Key: {client.api_key}")
    created += 1

print(f"\nDone! Created {created} new clients.")
