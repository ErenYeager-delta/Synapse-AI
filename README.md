# Synapse AI — Professional Coding Assistant

Synapse is a high-performance, expert-level AI coding assistant built for developers. It utilizes **Google Gemini 2.5-Flash** (with seamless 2.5-Flash-Lite failover) and a robust **Django + MongoDB** backend to provide real-time, token-streamed coding solutions, now wrapped in a stunning **Neon Cyan** brand identity.

---

## 🏛️ System Architecture

Synapse follows a modern, decoupled architecture designed for high availability and seamless developer experience.

### 1. High-Level Diagram (ASCII)

```text
[ USER BROWSER ] <---- WebSockets (Streaming) ----> [ DAPHNE / CHANNELS ]
      |                                                   |
      |--- HTTP (Auth/Registration) ----> [ DJANGO VIEWS ] <--- [ CUSTOM AUTH BACKEND ]
                                                   |                    |
                                            [ MONGODB ATLAS ] <---------|
                                                   |
                                            [ AI ENGINE ] <--- [ 4x GEMINI API KEYS ]
                                                   |
                                            [ REDIS CACHE ]
```

### 2. Core Components

- **Custom MongoDB Auth**: A bespoke authentication backend that stores users directly in MongoDB, bypassing the need for local SQLite databases in production.
- **Dual-Stage AI Rotation**: An intelligent engine that prioritizes the latest Gemini 2.5-Flash but automatically rolls back to 2.5-Flash-Lite across a pool of 4 API keys if quotas are reached.
- **Real-Time Streaming**: Powered by Django Channels and WebSockets to deliver "typewriter-style" responses as the AI generates them.
- **Live System Monitor**: A real-time monitoring system in the sidebar that tracks the health and capacity of the entire API key pool, ensuring transparency for all users.
- **Hybrid "Staff Engineer" Persona**: Synapse now combines the logical rigor and technical depth of Claude 3.5 Sonnet with the professional polish of Google Gemini.
- **Neon Cyan Design System**: A unified, high-contrast UI/UX built with a custom obsidian teal and electric blue palette.
- **Stateless Persistence**: Optimized session management designed to survive deployments on free, ephemeral cloud platforms like Railway.

---

## 🛠️ Technical Stack

| General Name           | Technical Component / Library        | Version                 |
| :--------------------- | :----------------------------------- | :---------------------- |
| **Core Runtime**       | Python (Interpreter Engine)          | 3.12+                   |
| **Web Framework**      | Django (MTV Architecture)            | 4.2.28                  |
| **Asynchronous Layer** | Django Channels (WebSocket Consumer) | 4.1.0                   |
| **Primary Database**   | MongoDB Atlas (Document Store)       | 4.7.3 (PyMongo)         |
| **AI Orchestration**   | LangChain (LLM Framework)            | 0.3.27                  |
| **Security Scanning**  | CodeQL & git-filter-repo             | 2026 Ready              |
| **Styling**            | Vanilla CSS (Design Tokens)          | Custom Neon Cyan System |

---

## 🚀 Deployment Guide (Production)

### ⚠️ IMPORTANT: API Key Security

To prevent **API Key Leakage**, we have implemented **Git History Scrubbing**.

1.  **Git Scrubbing**: Use `git-filter-repo` to permanently remove accidental secret commits.
2.  **Env Masking**: API keys are automatically masked in all server logs (e.g., `AIza...8Bjk`).
3.  **SRI Protection**: All external CDN scripts use Subresource Integrity (SRI) hashes to prevent man-in-the-middle attacks.

### 1. Railway Deployment (Recommended)

1.  **Connect Repo**: Link your GitHub repo to Railway.
2.  **Add MongoDB**: Provision a MongoDB service in your project.
3.  **Variables**: Add all `.env` keys (GEMINI_API_KEYS, MONGO_URI, etc.).
4.  **Start Command**: `daphne -b 0.0.0.0 -p $PORT synapse_project.asgi:application`

---

## 💻 Local Setup

1. `pip install -r requirements.txt`
2. Configure `.env` with your GEMINI keys.
3. `python manage.py runserver`
4. Visit `http://127.0.0.1:8000`

---

## 🛠️ Management & Maintenance

### Promoting an Administrator (Cloud/Local)

To access the `/admin` panel on Railway or locally:

1.  **Promotion Script**: Run the following locally (after setting your Cloud Mongo URI):
    ```powershell
    python promote_user.py <username>
    ```
2.  **Access**: Log in at [synapse-ai-production.up.railway.app/admin/](https://synapse-ai-production-3002.up.railway.app/admin/)

---

**Synapse AI is mission-ready. The code is clean, the history is scrubbed, and the design is electric.** 🚀💎🛡️
