# Synapse AI — Professional Coding Assistant

Synapse is a high-performance, expert-level AI coding assistant built for developers. It utilizes **Google Gemini 2.5-Flash** (with seamless 2.5-Flash-Lite failover) and a robust **Django + MongoDB** backend to provide real-time, token-streamed coding solutions.

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
- **Intelligent Titling**: Automated summarization that renames "New Chat" sessions based on the actual conversation context.

---

## �️ Technical Stack

| General Name | Technical Component / Library | Version |
| :----------- | :---------------------------- | :------ |

## 🛠️ Technical Stack

| General Name           | Technical Component / Library        | Version                     |
| :--------------------- | :----------------------------------- | :-------------------------- |
| **Core Runtime**       | Python (Interpreter Engine)          | 3.12+                       |
| **Web Framework**      | Django (MTV Architecture)            | 4.2.28                      |
| **Asynchronous Layer** | Django Channels (WebSocket Consumer) | 4.1.0                       |
| **ASGI Server**        | Daphne (HTTP/WS Interface)           | 4.1.2                       |
| **Primary Database**   | MongoDB Atlas (Document Store)       | 4.7.3 (PyMongo)             |
| **AI Orchestration**   | LangChain (LLM Framework)            | 0.3.27                      |
| **Gemini Interface**   | LangChain Google GenAI (SDK)         | 2.1.2 (google-genai >= 1.0) |
| **Caching/Messaging**  | Redis (In-Memory Key-Value)          | 5.0.8                       |
| **Environment**        | Python-Dotenv (Config Loader)        | 1.2.2                       |

---

## 📁 Project Structure

```text
Synapse/
├── chat/
│   ├── static/chat/       # CSS/JS (Glassmorphic UI + Marked.js)
│   ├── templates/chat/    # Django HTML Templates
│   ├── ai_engine.py       # LLM Rotation, Titling, & Prompting
│   ├── mongo_store.py     # Centralized Pymongo CRUD
│   ├── mongo_auth.py      # MongoDB User Auth Backend
│   ├── consumers.py       # WebSocket streaming logic
│   └── views.py           # Registration, OTP, & Settings
├── synapse_project/       # Project Configuration
│   ├── settings.py        # Optimized Prod/Dev settings
│   └── asgi.py            # Async gateway for WebSockets
├── requirements.txt       # Audited production dependencies
└── manage.py              # Entry point
```

---

## 🚀 Deployment Guide (Production)

### ⚠️ IMPORTANT: API Key Security

To prevent **API Key Leakage**, never commit your `.env` file to GitHub.

1.  Ensure `.env` is listed in your `.gitignore`.
2.  Use **Environment Variables** in your hosting dashboard (Railway/Render) to inject keys safely.

### 1. Railway Deployment (Recommended)

1.  **Connect Repo**: Link your GitHub repo to Railway.
2.  **Add MongoDB**: Provision a MongoDB service in your project.
3.  **Variables**: Add all `.env` keys (GEMINI_API_KEYS, MONGO_URI, etc.).
4.  **Start Command**: `daphne -b 0.0.0.0 -p $PORT synapse_project.asgi:application`

### 2. Render Deployment

1.  **Web Service**: Create a new Web Service from your repo.
2.  **Environment**: Select Python.
3.  **Build Command**: `pip install langchain==0.3.27 langchain-google-genai==2.1.2 langchain-community==0.3.31 duckduckgo-search==8.1.1 google-genai>=1.0.0 && python manage.py collectstatic --noinput`
4.  **Start Command**: `daphne -b 0.0.0.0 -p $PORT synapse_project.asgi:application`
5.  **Redis**: Render requires a separate Redis instance for WebSockets to work.

---

## 🛡️ Leakage Protection Guide

- **Env Masking**: Synapse automatically masks API keys in server logs (e.g., `AIza...8Bjk`).
- **No Client Keys**: API keys are handled strictly on the server; the frontend never sees them.
- **Hashed PWDs**: User passwords are encrypted using Django's PBKDF2 algorithm before being saved to MongoDB.

---

## 💻 Local Setup

1. `pip install -r requirements.txt`
2. Configure `.env` with your GEMINI keys.
3. `python manage.py runserver`
4. Visit `http://127.0.0.1:8000`

---

## 💎 100% Verified Integration

This project has undergone a complete system-wide audit to ensure flawless performance:

- **Connected Logic**: Authentication, AI Rotation, and MongoDB storage are seamlessly linked.
- **Environment Agnostic**: Tested for zero-error performance on Windows (Local) and Linux (Railway/Render).
- **Scalable Baseline**: Optimized for Python 3.12+ and the 2026 Gemini API roadmap.

**Synapse AI is mission-ready.**

---

## 🛠️ Management & Maintenance

### Promoting an Administrator

To access the `/admin` panel and see all user chats/data:

1.  **Standard Command**: Run the following in your terminal:
    ```powershell
    python manage.py createsuperuser
    ```
2.  **Auto-Sync**: The system will automatically sync this admin account to MongoDB.
3.  **Access**: Log in at `http://127.0.0.1:8000/admin`.
