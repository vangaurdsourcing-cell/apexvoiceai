# Apex AI — Intelligent Voice Agent Platform

AI-powered voice agent for Indian businesses. Speaks 10+ languages, records calls, generates summaries, and sends them to clients via WhatsApp — all under your brand.

## Features

- **10 Indian Languages** — Hindi, Tamil, Telugu, Bengali, Marathi, Gujarati, Kannada, Malayalam, Punjabi, English
- **Sarvam AI TTS** — Natural Indian voices via Bulbul v3
- **Call Recording** — Every conversation turn saved with timestamps
- **AI Summaries** — Auto-generated call summaries after each conversation
- **WhatsApp Delivery** — Summaries sent to clients under Apex AI brand
- **Exotel Integration** — Real phone calls via Indian telephony
- **Cloud-Ready** — Deploy to Render in minutes

## Quick Start

### Local
```bash
cp .env.example .env          # Add your API keys
pip install -r requirements.txt
python server.py              # Open http://localhost:8766
```

### Deploy to Render (free tier)
1. Push this folder to GitHub
2. Go to [render.com](https://render.com) → New → Blueprint
3. Connect your repo — it auto-detects `render.yaml`
4. Add environment variables (SARVAM_API_KEY, etc.)
5. Done! Your agent is live on the internet

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Voice agent UI |
| `/health` | GET | Server status |
| `/ws` | WebSocket | Real-time conversation |
| `/tts?text=...&lang=hi` | GET | Text-to-speech (Sarvam AI) |
| `/stt` | POST | Speech-to-text (Sarvam AI) |
| `/api/calls` | GET | List recorded calls |
| `/api/calls/{id}` | GET | Get call + summary |
| `/api/stats` | GET | Dashboard stats |
| `/api/call` | POST | Initiate Exotel call |
| `/exotel/incoming` | POST | Exotel webhook |

## Environment Variables

```
BRAND_NAME=Apex AI
SARVAM_API_KEY=your_key        # TTS + STT + LLM summaries
OPENAI_API_KEY=sk-...          # Optional: smarter responses
WHATSAPP_PHONE_NUMBER_ID=...   # WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=...
EXOTEL_SID=...                 # Indian phone calls
EXOTEL_TOKEN=...
EXOTEL_CALLER_ID=+91XXXXXXXXXX
EXOTEL_WEBHOOK_URL=https://your-server.com
```

## How Call Recording Works

1. User opens the agent and starts chatting
2. Every message (user + agent) is saved with timestamps
3. When the call ends (WebSocket disconnects):
   - Call duration is calculated
   - AI summary is generated (sentiment, outcome, action items)
   - Summary is sent via WhatsApp (if configured)
4. All data stored in `data/calls/` as JSON files

## Architecture

```
User speaks -> Browser STT -> WebSocket -> Apex AI Server
                                              |
                                    +---------+---------+
                                    |                   |
                              Sarvam AI TTS       Call Recorder
                                    |                   |
                              Voice output        data/calls/
                                                      |
                                                Summary Generator
                                                      |
                                                WhatsApp API
                                                      |
                                              Client gets summary
```
