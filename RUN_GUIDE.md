# Synapse AI — Terminal & Execution Guide 🚀

Use this guide as a quick reference for running and maintaining your AI Coding Assistant. Every command is optimized for the Synapse architecture.

---

## 📂 1. Core Execution Commands

### A. Development (With Auto-Reload)

**Purpose**: Best for active coding. Automatically restarts the server when you save changes.

```powershell
# Purpose: Launches the standard Django dev server.
# Why: Validates template logic and Python code changes instantly.
python manage.py runserver
```

### B. High-Performance (DAPHNE)

**Purpose**: Recommended for active chat sessions. Provides the most responsive WebSocket streaming.

```powershell
# Purpose: Runs the app using the ASGI (Asynchronous Server Gateway Interface).
# Why: Daphne is required for WebSockets to stream AI responses token-by-token without lag.
daphne -b 127.0.0.1 -p 8000 synapse_project.asgi:application
```

---

## ⚡ 2. Database & Auth Maintenance

### User Promotion (Cloud & Local)

**Purpose**: Grant administrative access to an account stored in MongoDB.

```powershell
# Purpose: Elevates a standard user to Staff/Superuser status.
# Why: Synapse uses a custom MongoDB Auth backend; this script syncs permissions to the SQLite shadow models for Admin UI access.
python promote_user.py <username>
```

### Shadow Sync (Mass Recovery)

**Purpose**: Ensure all MongoDB users are represented in the local SQLite "Shadow" database.

```powershell
# Purpose: Scans MongoDB and creates missing records in SQLite.
# Why: Django's Admin panel requires a local record to manage permissions; this keeps both databases perfectly aligned.
python mass_sync.py
```

---

## 🛡️ 3. Security & Environment Setup

### Environment Refresh

**Purpose**: Update your local configuration after changes to `.env.example`.

```powershell
# Purpose: Copies the template to a localized secret file.
# Why: Keeps your API keys and Mongo URIs safe from accidental Git commits.
cp .env.example .env
```

### Dependency Hardening

**Purpose**: Ensure your environment matches the production-locked requirements.

```powershell
# Purpose: Installs specific versions of PyMongo, LangChain, and Django Channels.
# Why: Prevents "version drift" errors and ensures that security patches (like SRI support) are active.
pip install -r requirements.txt
```

---

## 📅 4. Mission-Ready Workflow

1. **Verify Connection**: `ping mongodb-atlas-cluster` (Check cloud availability).
2. **Boot Engine**: `python manage.py runserver` (Start the core logic).
3. **Analyze**: Head to `http://127.0.0.1:8000` and start your multimodal engineering session.

**Synapse AI is mission-ready. The terminal is your cockpit.** 🚀💎🛡️
