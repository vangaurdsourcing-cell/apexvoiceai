# Apex AI — Deployment Guide

## How to Deploy (Step by Step)

### Option 1: Render (Recommended — Free Tier)

#### Step 1: Push to GitHub
```bash
# Create a new repo on github.com, then:
cd voice-agent
git init
git add .
git commit -m "Apex AI Platform v1.0"
git remote add origin https://github.com/YOUR_USERNAME/apex-ai-platform.git
git push -u origin main
```

#### Step 2: Deploy on Render
1. Go to [render.com](https://render.com) → Sign up free
2. Click **New** → **Web Service**
3. Connect your GitHub repo
4. Settings:
   - **Name**: `apex-ai-platform`
   - **Runtime**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `cd voice-agent && python app.py`
   - **Port**: `8766`

#### Step 3: Set Environment Variables
In Render dashboard → Environment tab, add:
```
SARVAM_API_KEY=your_sarvam_api_key
BRAND_NAME=Apex AI
WHATSAPP_PHONE_NUMBER_ID=your_phone_id
WHATSAPP_ACCESS_TOKEN=your_token
```

#### Step 4: Run Seed Script (First Time Only)
After first deploy, go to Shell tab in Render and run:
```bash
cd voice-agent && python seed_clients.py
```

Your platform is now live at: `https://apex-ai-platform.onrender.com`

---

### Option 2: Railway ($5/month, better performance)

1. Go to [railway.app](https://railway.app)
2. New Project → Deploy from GitHub
3. Same env vars as above
4. Custom domain available

---

### Option 3: Local Development
```bash
cd voice-agent
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python seed_clients.py  # First time only
python app.py
# Open http://localhost:8766
```

---

## How to Connect Sarvam AI Voice Agents

### Step 1: Create Voice Agent on Sarvam AI
1. Go to [sarvam.ai](https://sarvam.ai) → Dashboard → Voice Agents
2. Create new agent for each hospital
3. Configure the conversation script (greeting, booking flow, etc.)

### Step 2: Set Webhook URL
In your Sarvam AI agent settings:
- **Webhook URL**: `https://your-server.com/webhook/sarvam`
- **Events**: `call_ended`

### Step 3: Add client_api_key to Webhook
The webhook payload must include the client's API key:
```json
{
  "event": "call_ended",
  "call_id": "sarvam_xxx",
  "client_api_key": "apx_63e3541d0eaa4d35add2fd94aa5398dd",
  "caller_phone": "+919876543210",
  "language": "hi",
  "duration_seconds": 180,
  "transcript": [...]
}
```

### Step 4: Test
```bash
curl -X POST https://your-server.com/webhook/sarvam \
  -H "Content-Type: application/json" \
  -d '{"event":"call_ended","client_api_key":"YOUR_KEY","caller_phone":"+919876543210","language":"hi","duration_seconds":120,"transcript":[{"role":"agent","text":"Namaste!"},{"role":"user","text":"Mera naam Test hai"}]}'
```

---

## How to Set Up WhatsApp Business API

1. Go to [business.facebook.com](https://business.facebook.com)
2. Create a Business account
3. Go to WhatsApp → Getting Started
4. Create a WhatsApp Business account
5. Get your **Phone Number ID** and **Access Token**
6. Add them as environment variables on your hosting platform

---

## Client API Keys (Pre-configured)

| Hospital | Plan | API Key |
|----------|------|---------|
| V Care Hospital | Pro (Rs 2,999/mo) | `apx_63e3541d...` |
| Ayaansh Hospital | Pro (Rs 2,999/mo) | `apx_ace6f5a2...` |
| Apollo Hospital Delhi | Basic (Rs 999/mo) | `apx_6f1f225d...` |
| Max Healthcare | Enterprise (Rs 9,999/mo) | `apx_ca040a87...` |
| Fortis Hospital | Pro (Rs 2,999/mo) | `apx_13cfb6ea...` |

Each hospital's voice agent should include their API key in the webhook payload so calls are automatically routed and summarized.

---

## What Happens When a Call Ends

```
Patient calls hospital's voice agent (Sarvam AI)
          ↓
Call ends → Sarvam sends webhook to your server
          ↓
Server looks up client by API key
          ↓
Generates summary (patient name, dept, date, sentiment)
          ↓
Saves call record to database
          ↓
Sends WhatsApp summary to hospital admin
          ↓
Dashboard updates in real-time
```

The hospital admin receives a WhatsApp message like:
```
Apex AI — Call Summary
----------------------------
Patient: Rajesh Kumar
Department: Cardiology
Date: Tomorrow
Time: Morning
Sentiment: Positive

Summary: Patient called to book appointment
in Cardiology. Booking confirmed.

Status: Confirmed
Hospital: V Care Hospital
----------------------------
Powered by Apex AI
```
