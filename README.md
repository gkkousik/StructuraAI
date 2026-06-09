# Structura AI 🏗️

**AI-powered UML diagram generator** built with Flask, Claude 3.5, and PlantUML.

Enter a project title, pick a diagram type and theme — Structura AI uses Anthropic's Claude API to generate syntactically correct PlantUML, renders it into a PNG, and lets you download or copy the syntax.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.10+ · Flask 3.x |
| AI Engine | Anthropic Claude 3.5 Haiku (Messages API) |
| Diagram Renderer | PlantUML (public server) |
| Auth | Flask sessions · bcrypt password hashing |
| Frontend | Jinja2 templates · Tailwind CSS (CDN) · Vanilla JS |
| Server | Gunicorn (production) |
| Config | python-dotenv (.env) |

---

## Features

- ✦ **12 UML diagram types** — Class, Sequence, Use Case, Activity, Component, Deployment, State, Object, Timing, ER, Network, Mind Map  
- 🎨 **44 PlantUML themes** — blueprint, cyberpunk, cloudscape and more  
- 🔒 **Secure auth** — bcrypt-hashed passwords, server-signed sessions, login required on generator  
- 💾 **Diagram history** — every generation saved as PNG + syntax; browse, view, re-download, delete  
- 📋 **One-click export** — download PNG or copy PlantUML syntax  
- ⚡ **Clean architecture** — no g4f, no plaintext passwords, proper .env config  

---

## Quick Start

### 1. Clone and enter
```bash
git clone <your-repo>
cd structura_ai
```

### 2. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env and add your ANTHROPIC_API_KEY
```

### 5. Run
```bash
python app.py
# or production:
# gunicorn -w 2 -b 0.0.0.0:5000 app:app
```

Visit **http://localhost:5000**

---

## Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | ✅ Yes | — | Your Anthropic API key |
| `SECRET_KEY` | Recommended | dev string | Flask session signing key |
| `FLASK_ENV` | No | `development` | `development` or `production` |
| `PORT` | No | `5000` | HTTP port |

---

## Project Structure

```
structura_ai/
├── app.py                  # Flask application & routes
├── requirements.txt
├── .env.example
├── .gitignore
├── users.json              # Created automatically on first signup
├── history.json            # Created automatically on first generation
├── static/
│   ├── com_logo.png
│   ├── image.png
│   └── diagrams/           # Generated PNGs saved here
└── templates/
    ├── base.html           # Shared layout, navbar, particles, toast
    ├── index.html          # Landing page
    ├── login.html
    ├── signup.html
    ├── generate.html       # UML generator UI
    └── history.html        # Saved diagrams browser
```

---

## API Endpoints

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/` | — | Landing page |
| `GET/POST` | `/login` | — | Login |
| `GET/POST` | `/signup` | — | Register |
| `GET` | `/logout` | — | Logout |
| `GET` | `/try` | ✅ | Generator UI |
| `GET` | `/history` | ✅ | History page |
| `POST` | `/generate` | ✅ | Generate diagram (returns JSON) |
| `GET` | `/api/history` | ✅ | List user history (JSON) |
| `DELETE` | `/api/history/<id>` | ✅ | Delete history entry |
| `GET` | `/health` | — | Health check |

---

## Deployment (Render / Railway / Fly.io)

```bash
# Procfile (already gunicorn in requirements.txt)
web: gunicorn -w 2 -b 0.0.0.0:$PORT app:app
```

Set `ANTHROPIC_API_KEY`, `SECRET_KEY`, and `FLASK_ENV=production` in your platform's environment.

---

## License

MIT
