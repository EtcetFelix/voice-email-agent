# 🎙️ Voice Email Agent

An **AI-powered email assistant** built with [Pipecat](https://github.com/pipecat-ai/pipecat), OpenAI, and ElevenLabs. It can **fetch**, **search**, and **send** emails — via voice or text.

---

## 🚀 Overview

**Alice** (the assistant) can:

* Retrieve your latest emails (via Nylas)
* Search your inbox by topic, sender, or content
* Compose and send emails
* Speak replies with ElevenLabs TTS
* Understand your speech with ElevenLabs STT

Core pieces:

* 🧠 OpenAI (GPT‑4o) — conversational reasoning + tool use
* 🔊 ElevenLabs — STT/TTS
* 💌 Nylas — email fetch + send
* 🗂️ SQLite + Chroma — storage + semantic search
* 🧩 Pipecat — orchestrates VAD → STT → LLM → TTS pipeline

---

## 🧰 Tech Stack

| Layer     | Technology                             | Purpose                          |
| --------- | -------------------------------------- | -------------------------------- |
| Audio I/O | Pipecat, Silero VAD, LocalSmartTurn    | real‑time mic and speaking turns |
| STT/TTS   | ElevenLabs                             | speech ↔ text                    |
| LLM       | OpenAI                                 | reasoning + tool orchestration   |
| Email     | Nylas                                  | fetch + send                     |
| Storage   | SQLite (structured), Chroma (semantic) | persistence + search             |
| ETL       | EmailETLService                        | fetch → transform → load         |

---

## 🧪 Development Setup

### 1) Clone & install

```bash
git clone https://github.com/<your-username>/voice-email-agent.git
cd voice-email-agent
pip install -r requirements.txt
```

### 2) Environment variables (`.env`)

Add your keys (placeholders shown):

```ini
ELEVENLABS_API_KEY=sk_...
OPENAI_API_KEY=sk-...
NYLAS_API_KEY=nyk_...
NYLAS_EMAIL_ACCOUNT_GRANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
```

> These are loaded via Pydantic Settings; missing keys raise on startup.

---

## 💌 Email Sending Modes

### Default: **Mailpit** (safe/local)

The project ships with **Mailpit** as the default SMTP sink so you can test sends without emailing real people.

Start Mailpit:

```bash
docker-compose up -d
```

View sent mail: [http://localhost:8025](http://localhost:8025)
Stop Mailpit:

```bash
docker-compose down
```

### Real sending: **Nylas** (production)

If you want to send **real emails**, switch the transport from Mailpit to Nylas:

1. **Uncomment** `voice_agent/email_services/transports/nylas_transport.py` (the Nylas transport implementation).
2. Update the transport wiring in `bot.py` to use **NylasTransport** (via `SimpleTransportManager`) instead of the Mailpit transport, e.g.

   ```python
   transport_manager = SimpleTransportManager(
       nylas_api_key=settings.NYLAS_API_KEY,
       nylas_grant_id=settings.NYLAS_EMAIL_ACCOUNT_GRANT_ID
   )
   ```
3. Ensure your Nylas grant/API key has send permissions.

> ⚠️ Once you switch to Nylas, all outgoing emails are **real**.

---

## 📬 Email Fetching & Search (ETL)

On startup, the **EmailETLService** pulls recent messages from Nylas and indexes them into SQLite (metadata/body) and Chroma (embeddings) for semantic search.

**Defaults** (see `voice_agent/email_fetcher.py`):

* `MAX_EMAILS = 10` (total to fetch)
* `EMAILS_PER_PAGE = 5` (page size per API call)

To fetch **more than 10** emails, either:

* Edit the defaults in `NylasEmailFetcher`:

  ```python
  self.MAX_EMAILS = 50
  self.EMAILS_PER_PAGE = 25
  ```
* Or call `fetch_emails(grant_id, max_emails=100, emails_per_page=20)` from your own entrypoint.

ETL status is logged; the vector store deduplicates by message id.

---

## 🧩 Pipeline Flow

```
🎤 User speaks
 ↓
ElevenLabs STT
 ↓
Pipecat LLM (OpenAI) + tools
   ↳ search_emails / search_emails_by_sender / get_recent_emails / send_email
 ↓
ElevenLabs TTS
 ↓
🎧 Audio reply
```

**Registered tools** (via Pipecat function calling):

* `search_emails`
* `search_emails_by_sender`
* `get_recent_emails`
* `send_email`

---

## 🏗️ Directory Structure

```
voice-email-agent/
├── bot.py                          # main entrypoint
├── docker-compose.yml              # Mailpit
├── voice_agent/
│   ├── config.py                   # Pydantic settings loader
│   ├── database_service.py         # SQLite wrapper
│   ├── embeddings/
│   │   └── vector_store.py         # Chroma store
│   ├── email_fetcher.py            # Nylas fetcher
│   ├── etl_service.py              # ETL (fetch → transform → load)
│   ├── email_services/
│   │   ├── email_service.py        # unified email sending interface
│   │   ├── transport_manager.py    # chooses Mailpit vs Nylas
│   │   └── transports/
│   │       └── nylas_transport.py  # real sender (commented by default)
│   ├── tools/
│   │   ├── email_tools.py          # search tools
│   │   └── email_send_tool.py      # send tool
│   └── models.py                   # Pydantic models
└── README.md
```

---

## ▶️ Running the Agent

```bash
python bot.py
```

You should see logs like:

```
🚀 PRE-INITIALIZATION STARTING
📦 Initializing database...
🔄 Running ETL to fetch and index emails...
✅ All email services fully initialized!
✅ Bot ready to accept connections!
```

---

## 🛠️ Troubleshooting

* **Settings validation fails** → confirm `.env` keys exist and match your Nylas grant region.
* **No emails fetched** → check `NYLAS_EMAIL_ACCOUNT_GRANT_ID` and that the grant has messages; try raising `MAX_EMAILS`.
* **Vectors not growing** → ensure message ids are unique; duplicates are skipped on ingest.
* **No audio output** → confirm your output device + ElevenLabs TTS key; look for rate‑limit or 4xx/5xx in logs.

---

## 🧯 Known Issues

* **TTS may stop after an email search.** Occasionally, right after invoking an inbox search tool, the ElevenLabs **TTS stops speaking** even though the agent continues to process input and respond in text. If you speak again, the agent **keeps working silently** (no TTS output).

  **Workarounds**

  * Say something again to trigger a new turn.
  * Restart the process if audio doesn’t come back. Try asking the agent to use different tools before retrying the search tool.

  **Notes for debugging**

  * Check logs around the tool call for any TTS enqueue/send errors or dropped audio frames.
  * Watch for ElevenLabs rate limits or transient 5xx; consider simple retry with backoff on TTS send.




---

## 👤 Author

Built by **Alan Bohannon** for rapid prototyping of voice‑driven email agents.
