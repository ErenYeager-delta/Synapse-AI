# Synapse AI — Terminal & Execution Guide 🚀

Use this guide as a quick reference for running your AI Coding Assistant in your IDE terminal (VS Code, PowerShell, etc.).

---

## 📂 1. Directory Setup

Before running any commands, ensure your terminal is in the correct directory:

```powershell
cd "c:\Users\VIGNESH\Downloads\Synapse"
```

---

## ⚡ 2. Execution Methods (Pros & Cons)

### Method A: Standard Development Server

**Command:**

```powershell
python manage.py runserver
```

| Pros ✅                                                        | Cons ❌                                                                    |
| :------------------------------------------------------------- | :------------------------------------------------------------------------- |
| **Auto-Reload**: Instantly updates when you save a file.       | **Slower WebSockets**: Can feel slightly laggy during AI "Thinking" state. |
| **Debugging**: Shows full error logs directly in the terminal. | **Single-Threaded**: Not built for high-concurrency production.            |
| **Simplicity**: No extra dependencies needed.                  |                                                                            |

---

### Method B: Professional Performance (DAPHNE)

**Recommended for the best Chat experience.**
**Command:**

```powershell
daphne -b 127.0.0.1 -p 8000 synapse_project.asgi:application
```

| Pros ✅                                                                 | Cons ❌                                                              |
| :---------------------------------------------------------------------- | :------------------------------------------------------------------- |
| **Ultra-Fast WebSockets**: No lag between User message and AI Response. | **No Auto-Reload**: You must restart it manually after editing code. |
| **Real Production Core**: This is how the app runs on Railway/Render.   | **Complex Logs**: Error logs are more condensed and harder to read.  |
| **Asynchronous**: Handles multiple chat strands simultaneously.         |                                                                      |

---

## 🛠️ 3. Essential Maintenance Commands

### Create Admin / Owner

Run this to give your user account full control over the system:

```powershell
python manage.py createsuperuser
```

### Update System Dependencies

If you add new libraries or sync from GitHub, run this:

```powershell
pip install -r requirements.txt
```

---

## 📅 4. Your Daily Workflow

1. **Open IDE** (VS Code).
2. **Open Terminal** (Ctrl + `).
3. **Move to Folder**: `cd "c:\Users\VIGNESH\Downloads\Synapse"`
4. **Run Server**: `python manage.py runserver`
5. **Start Chatting**: Visit [http://127.0.0.1:8000](http://127.0.0.1:8000)
