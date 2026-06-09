# Structura AI

**AI-powered UML diagram generator** — describe your system, pick a diagram type and visual theme, and get a professional PlantUML diagram in seconds.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/Flask-3.0-000000?style=flat&logo=flask&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_AI-Free-F55036?style=flat)
![PlantUML](https://img.shields.io/badge/PlantUML-Renderer-orange?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)

---

## What It Does

Structura AI takes a project name and diagram type, sends it to Groq's free LLM API, parses the PlantUML syntax the AI returns, renders it to a PNG via the public PlantUML server, and displays it with download and copy options. Every diagram is saved to history.

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Backend | Python 3.10+ · Flask 3.0 | Lightweight, production-ready web framework |
| AI Engine | Groq API — Llama 3.3 70B | Free tier, fastest inference, OpenAI-compatible |
| Diagram Renderer | PlantUML public server (direct HTTP) | No local Java dependency |
| Auth | Flask sessions · bcrypt | Secure password hashing, server-signed sessions |
| Frontend | Jinja2 · Tailwind CSS CDN · Vanilla JS | No build step, responsive, dark UI |
| Deployment | Gunicorn | Production WSGI server |
| Config | python-dotenv | 12-factor app environment management |

---

## Features

- **10 UML diagram types** — Sequence, Use Case, Class, Object, Activity, Component, Deployment, State, Timing, ER
- **8 visual themes** — fully custom skinparam palettes, each unique and high-contrast (no `!theme` directives)
- **Groq AI fallback chain** — tries `llama-3.3-70b-versatile` → `llama-3.1-8b-instant` → `gemma2-9b-it`
- **Diagram history** — every generation saved as PNG + PlantUML syntax; browse, download, delete
- **One-click export** — download PNG or copy raw PlantUML syntax
- **Secure auth** — bcrypt-hashed passwords, protected routes, session management
- **Health endpoint** — `/health` for uptime monitoring and deployment checks

---

## Quick Start

### 1. Clone
```bash
git clone https://github.com/your-username/structura-ai.git
cd structura-ai
```

### 2. Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Mac / Linux
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Get a free Groq API key
1. Go to **console.groq.com** and sign up (free, no credit card)
2. Navigate to **API Keys** → **Create API Key**
3. Copy the key — it starts with `gsk_`

### 5. Configure environment
```bash
cp .env.example .env
```
Open `.env` and fill in your values:
```env
GROQ_API_KEY=gsk_your_key_here
SECRET_KEY=any-random-string-you-choose
FLASK_ENV=development
PORT=5000
```

### 6. (Optional) Test your API key
```bash
python test_groq.py
```
You should see `✓ SUCCESS with model: llama-3.3-70b-versatile`.

### 7. Run
```bash
python app.py
```
Open **http://localhost:5000** in your browser.

---

## Project Structure

```
structura_ai/
├── app.py                  # Flask app, routes, Groq AI, PlantUML renderer
├── requirements.txt        # Python dependencies
├── test_groq.py            # Standalone key + model tester
├── .env.example            # Environment variable template
├── .gitignore
├── users.json              # Auto-created on first signup (bcrypt hashed)
├── history.json            # Auto-created on first generation
├── static/
│   ├── com_logo.png
│   └── diagrams/           # Generated PNG files saved here
└── templates/
    ├── base.html           # Shared layout: navbar, particles, toast, footer
    ├── index.html          # Landing page
    ├── login.html          # Login with show/hide password
    ├── signup.html         # Signup with password strength meter
    ├── generate.html       # Main generator UI with theme swatches
    └── history.html        # Saved diagrams browser with modal viewer
```

---

## API Reference

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/` | — | Landing page |
| `GET` | `POST` `/login` | — | Login form |
| `GET` | `POST` `/signup` | — | Registration form |
| `GET` | `/logout` | — | Clear session and redirect |
| `GET` | `/try` | ✅ | Generator UI |
| `GET` | `/history` | ✅ | Saved diagrams page |
| `POST` | `/generate` | ✅ | Generate diagram → returns `{diagram, syntax, entry_id}` |
| `GET` | `/api/history` | ✅ | List user's history as JSON |
| `DELETE` | `/api/history/<id>` | ✅ | Delete a history entry + PNG file |
| `GET` | `/health` | — | `{"status": "ok", "timestamp": "..."}` |

### `POST /generate`

**Form fields:**

| Field | Required | Description |
|---|---|---|
| `project_name` | Yes | Your project title, e.g. `E-commerce Platform` |
| `diagram_type` | Yes | One of the 10 supported types |
| `theme` | No | One of the 8 theme names, or empty for default |

**Response:**
```json
{
  "diagram": "<base64 PNG>",
  "syntax": "@startuml\n...\n@enduml",
  "entry_id": "uuid"
}
```

---

## Diagram Types

| # | Type | Best For |
|---|---|---|
| 1 | Sequence Diagram | API flows, user interactions, message passing |
| 2 | Use Case Diagram | Feature scope, actor-system relationships |
| 3 | Class Diagram | OOP architecture, data models |
| 4 | Object Diagram | Runtime state snapshots |
| 5 | Activity Diagram | Workflows, business processes |
| 6 | Component Diagram | Microservices, system architecture |
| 7 | Deployment Diagram | Infrastructure, cloud topology |
| 8 | State Diagram | Lifecycle management, FSMs |
| 9 | Timing Diagram | Time-based system behavior |
| 10 | ER Diagram | Database schema design |

---

## Visual Themes

All 8 themes use custom `skinparam` blocks — not `!theme` directives — so every element (background, text, borders, arrows) is explicitly styled with guaranteed contrast.

| Theme | Background | Accent | Style |
|---|---|---|---|
| Classic Blue | White | Navy | Clean professional |
| Dark Neon | Pitch black | Neon green | Developer / hacker |
| Sunset Orange | Warm cream | Deep orange | Energetic, warm |
| Forest Green | Pale green | Dark green | Natural, calm |
| Royal Purple | Lavender | Deep purple | Elegant, premium |
| Midnight Dark | Dark navy | Crimson red | Dramatic, bold |
| Ocean Teal | Light cyan | Dark teal | Fresh, modern |
| Rose Gold | Blush pink | Deep rose | Soft, elegant |

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GROQ_API_KEY` | ✅ | — | Free from console.groq.com — starts with `gsk_` |
| `SECRET_KEY` | ✅ | dev string | Flask session signing key — use a random string in production |
| `FLASK_ENV` | No | `development` | Set to `production` when deploying |
| `PORT` | No | `5000` | HTTP port |

---

## Deployment

### Render / Railway / Fly.io

1. Push to GitHub
2. Connect repo in your platform
3. Set environment variables: `GROQ_API_KEY`, `SECRET_KEY`, `FLASK_ENV=production`
4. Start command:
```bash
gunicorn -w 2 -b 0.0.0.0:$PORT app:app
```

### Docker (optional)
```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["gunicorn", "-w", "2", "-b", "0.0.0.0:5000", "app:app"]
```

---

## How It Works

```
User Input
    │
    ▼
Groq API (Llama 3.3 70B)
    │  generates PlantUML syntax
    ▼
clean_syntax()
    │  strips markdown fences
    │  removes !theme directives
    │  converts {{ }} → { }   ← fixes HTTP 400 errors
    │  injects skinparam theme block
    ▼
PlantUML Public Server
    │  renders syntax → PNG
    ▼
Base64 encode → browser
    │
    ▼
Save PNG to disk + history.json
```

---

## Known Limitations

- Diagram quality depends on Groq model output — complex domains may need prompt refinement
- PlantUML rendering requires internet access to `plantuml.com`
- `users.json` and `history.json` are flat files — swap for a database (SQLite/PostgreSQL) for multi-user production use
- Free Groq tier has rate limits (~30 requests/minute)

---

## License

MIT — free to use, modify, and distribute.

---

*Built with Flask · Groq AI · PlantUML · Tailwind CSS*
