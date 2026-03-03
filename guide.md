# Synapse AI — The Engineering Manual 🏛️💎🛡️

This guide provides a deep-dive into the technical philosophy and architectural decisions that make Synapse AI a benchmark for AI Engineering.

---

## 🏛️ 1. Stateless Authentication (The "Mongo-Duo" Pattern)

**Objective**: Enable 100% horizontal scaling and cloud portability.

### The Architecture:

Synapse uses a custom `MongoAuthBackend` that treats MongoDB Atlas as the "Source of Truth" for user identity.

- **Backend Role (Logic)**: Validates credentials against salted PBKDF2 hashes in the `users` collection.
- **State Management**: On every successful login, the system performs a **"Shadow Sync"** to a local SQLite database.
- **Why?**: This allows Django's native Admin UI to function perfectly (which requires relational meta-data) while keeping the actual user accounts stateless and surviving any cloud pod restart.

---

## 📎 2. Multimodal Intelligence & Silk Scrolling

**Objective**: Provide a visual, immersive coding experience.

### Technical Implementation:

- **File Uploads**: When you click the paperclip icon (Frontend UI), `chat.js` captures the file and converts it to a Base64 stream.
- **Real-Time Pipeline**: This data is sent via an asynchronous WebSocket frame (Django Channels).
- **Security Audit (2026)**: Conducted an audit for LangChain SSRF (CVE-2026-26013). Synapse is **immune** because it utilizes `langchain-google-genai` for vision, bypassing the vulnerable OpenAI token-counting logic.
- **Asset Processing**: The AI Engine (Backend Logic) uses LangChain's Gemini SDK to process image parts as `inline_data`.
- **The "Silk" Effect**: We implemented a custom `scroll-behavior: smooth` logic that waits for the `HTMLImageElement.decode()` event. This prevents the "jumping" effect seen in lesser chat apps when large images load.

---

## 🛡️ 3. Security Hardening (The "No-Leak" Policy)

**Objective**: Protect primary API keys and frontend integrity.

### Hardening Layers:

1. **HMAC-SHA256**: Unlike standard SHA256, HMAC uses your random `SECRET_KEY` as a cryptographic key for hashing Gemini API keys. This means even with a database dump, the hashes are useless to an attacker.
2. **Subresource Integrity (SRI)**: Every external CDN script (Marked.js, Highlight.js) is pinned to a specific cryptographic hash.
   - **Purpose**: If a hacker compromises the CDN and changes the JS file, your browser will detect the hash mismatch and block the code from running.
3. **Git Scrubbing**: We use `git-filter-repo` to ensure the repository profile is always clean and secrets are never "remembered" by the Git history.

---

## 🎨 4. Design System (Neon Cyan Tokens)

**Objective**: A high-impact, professional workspace.

- **Frontend Role (UI)**: Built with Vanilla CSS Variables (`--accent-cyan`, `--bg-darker`, `--radius-xl`).
- **Uniqueness**: The UI uses dynamic mesh-gradients and obsidian surfaces to reduce eye strain during long engineering sessions while maintaining a high-contrast, premium aesthetic.

---

**You are now equipped with the architectural map of Synapse AI. Build with confidence.** 🚀💎🛡️
