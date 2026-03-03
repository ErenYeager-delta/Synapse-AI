const SynapseChat = (() => {
  let ws = null;
  let currentSessionId = window.SYNAPSE ? window.SYNAPSE.currentSessionId : null;
  let isStreaming = false;
  let streamBuffer = "";
  const DEBOUNCE_MS = 300;
  let lastSendTime = 0;
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  function init() { connectWebSocket(); updateUsageDisplay(); }

  async function updateUsageDisplay() {
    try {
      const r = await fetch("/api/usage/");
      const data = await r.json();
      if (data.status === "success") {
        const monitor = $("#system-monitor");
        const list = $("#key-pool-list");
        const text = $("#usage-text");
        if (monitor && list && text) {
          const totalRemaining = data.remaining;
          const totalCapacity = data.total;
          const percent = (totalRemaining / totalCapacity) * 100;

          // Update Global Text
          text.innerText = `Global: ${totalRemaining.toLocaleString()} / ${totalCapacity.toLocaleString()} left`;
          
          // Clear and Render Key List
          list.innerHTML = "";
          data.key_stats.forEach(key => {
              const kItem = document.createElement("div");
              kItem.className = "key-pool-item";
              const kColor = key.percent < 20 ? "var(--accent-rose)" : "var(--accent-cyan)";
              kItem.innerHTML = `
                <div class="key-pool-label">
                    <span>${key.label}</span>
                    <span>${key.percent}%</span>
                </div>
                <div class="usage-bar-container">
                    <div class="usage-bar" style="width: ${key.percent}%; background: ${kColor}; box-shadow: 0 0 8px ${kColor}44;"></div>
                </div>
              `;
              list.appendChild(kItem);
          });

          monitor.style.display = "flex";
          
          // Update global pulse color
          const dot = $(".status-dot");
          if (dot) dot.style.background = percent < 15 ? "var(--accent-rose)" : "var(--accent-cyan)";
        }
      }
    } catch (e) {
      console.error("Error updating usage:", e);
    }
  }

  function connectWebSocket() {
    const url = currentSessionId
      ? `${window.SYNAPSE.wsUrl}${currentSessionId}/`
      : window.SYNAPSE.wsUrl;
    if (ws) ws.close();
    ws = new WebSocket(url);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "status" && data.session_id) {
        if (!currentSessionId || currentSessionId !== data.session_id) {
            currentSessionId = data.session_id;
            refreshSidebarHighlights();
        }
      }
      handleWSMessage(data);
    };
    ws.onclose = () => setTimeout(connectWebSocket, 3000);
    ws.onerror = (err) => console.error("WebSocket error:", err);
  }

  function handleWSMessage(data) {
    switch (data.type) {
      case "status":     if (data.content === "thinking") showThinking(); break;
      case "stream_start": hideThinking(); startStreamMessage(); break;
      case "stream":     appendToStream(data.content); break;
      case "stream_end": finalizeStream(); break;
      case "error":      hideThinking(); showError(data.content); break;
      case "title_update": updateSidebarTitle(data.session_id, data.title); break;
    }
  }

  function updateSidebarTitle(sessionId, title) {
    // Update sidebar item
    const item = $(`.session-item[data-session-id="${sessionId}"] .session-title`);
    if (item) item.textContent = title;
    
    // Also update current active header if it's the same session
    if (currentSessionId === sessionId) {
      const headerTitle = $("#chat-title");
      if (headerTitle) headerTitle.textContent = title;
      refreshSidebarHighlights();
    }
  }

  function refreshSidebarHighlights() {
    $$(".session-item").forEach(el => {
        el.classList.toggle("active", el.dataset.sessionId === currentSessionId);
    });
  }

  function addUserMessage(text) {
    hideWelcome();
    const container = $("#messages-container");
    container.insertAdjacentHTML("beforeend",
      `<div class="message-user"><div class="message-bubble">${escapeHtml(text)}</div></div>`
    );
    scrollToBottom();
  }

  function showThinking() {
    hideThinking();
    $("#messages-container").insertAdjacentHTML("beforeend",
      `<div class="message-ai thinking-msg" id="thinking-msg">
         <div class="message-bubble">&#9679;&#9679;&#9679; Thinking...</div>
       </div>`
    );
    scrollToBottom();
  }
  function hideThinking() { const el = $("#thinking-msg"); if (el) el.remove(); }

  function startStreamMessage() {
    isStreaming = true; streamBuffer = "";
    $("#messages-container").insertAdjacentHTML("beforeend",
      `<div class="message-ai stream-msg">
         <div class="message-bubble"><div id="stream-content"></div></div>
       </div>`
    );
    scrollToBottom();
  }

  function appendToStream(chunk) {
    streamBuffer += chunk;
    const el = $("#stream-content");
    if (el) { el.innerHTML = renderMarkdown(streamBuffer); scrollToBottom(); }
  }

  function finalizeStream() {
    isStreaming = false;
    const el = $("#stream-content");
    if (el) {
      el.innerHTML = renderMarkdown(streamBuffer);
      el.querySelectorAll("pre code").forEach(hljs.highlightElement);
      addCopyButtons(el);
    }
    $("#btn-send").disabled = false;
    $("#message-input").disabled = false;
    streamBuffer = "";
    updateUsageDisplay();
    scrollToBottom();
  }

  function showError(text) {
    isStreaming = false;
    $("#messages-container").insertAdjacentHTML("beforeend",
      `<div class="message-ai error-msg"><div class="message-bubble">&#9888; ${escapeHtml(text)}</div></div>`
    );
    $("#btn-send").disabled = false;
    $("#message-input").disabled = false;
  }

  function sendMessage() {
    const now = Date.now();
    if (now - lastSendTime < DEBOUNCE_MS) return;
    const input = $("#message-input");
    const message = input.value.trim();
    if (!message || isStreaming) return;
    lastSendTime = now;
    addUserMessage(message);
    input.value = ""; input.style.height = "auto";
    $("#btn-send").disabled = true; input.disabled = true;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ message, session_id: currentSessionId }));
    } else {
      showError("Connection lost. Reconnecting...");
      connectWebSocket();
    }
  }

  function loadSession(sessionId) {
    currentSessionId = sessionId;
    $$(".session-item").forEach(el => el.classList.remove("active"));
    const active = $(`.session-item[data-session-id="${sessionId}"]`);
    if (active) active.classList.add("active");
    connectWebSocket();
    fetch(`/api/sessions/${sessionId}/messages/`)
      .then(r => r.json())
      .then(data => {
        if (data.status === "success") {
          const container = $("#messages-container");
          container.innerHTML = "";
          $("#chat-title").textContent = data.title || "Chat";
          if (data.messages.length === 0) showWelcome();
          else {
            hideWelcome();
            data.messages.forEach(msg => {
              if (msg.role === "user") addUserMessage(msg.content);
              else showAIMessage(msg.content);
            });
          }
        }
      });
  }

  function showAIMessage(text) {
    const container = $("#messages-container");
    container.insertAdjacentHTML("beforeend",
      `<div class="message-ai"><div class="message-bubble">${renderMarkdown(text)}</div></div>`
    );
    container.lastElementChild.querySelectorAll("pre code").forEach(hljs.highlightElement);
    addCopyButtons(container.lastElementChild);
    scrollToBottom();
  }

  async function newChat() {
    const r = await fetch("/api/sessions/new/", { headers: { "X-CSRFToken": window.SYNAPSE.csrfToken } });
    const data = await r.json();
    if (data.status === "success") location.reload();
  }

  async function deleteSession(sessionId) {
    if (!confirm("Delete this conversation?")) return;
    await fetch(`/api/sessions/${sessionId}/delete/`, { headers: { "X-CSRFToken": window.SYNAPSE.csrfToken } });
    $(`.session-item[data-session-id="${sessionId}"]`)?.remove();
    if (currentSessionId === sessionId) newChat();
  }

  function renderMarkdown(text) { return window.marked ? marked.parse(text) : escapeHtml(text); }

  function addCopyButtons(container) {
    container.querySelectorAll("pre").forEach(pre => {
      const btn = document.createElement("button");
      btn.className = "btn-copy"; btn.innerText = "Copy";
      btn.onclick = () => {
        navigator.clipboard.writeText(pre.innerText).then(() => {
          btn.innerText = "Copied!"; setTimeout(() => btn.innerText = "Copy", 2000);
        });
      };
      pre.appendChild(btn);
    });
  }

  function escapeHtml(text) { const d = document.createElement("div"); d.textContent = text; return d.innerHTML; }
  function scrollToBottom() {
    const c = $("#messages-container");
    if (!c) return;
    const threshold = 150; // pixels from bottom to trigger auto-scroll
    const isAtBottom = c.scrollHeight - c.scrollTop - c.clientHeight <= threshold;
    
    // Always scroll if it's the first few messages or if user is already near bottom
    if (isAtBottom || c.childNodes.length < 2) {
      requestAnimationFrame(() => {
        c.scrollTo({ top: c.scrollHeight, behavior: "smooth" });
      });
    }
  }
  function hideWelcome()     { $("#welcome-screen")?.remove(); }
  function showWelcome()     { location.reload(); }

  async function openSettings() {
    const modal = $("#settings-modal"); modal.style.display = "flex";
    const r = await fetch("/api/settings/");
    const data = await r.json();
    if (data.status === "success") {
      $("#setting-language").value = data.settings.preferred_language || "Python";
      $("#setting-api-key").value  = data.settings.personal_api_key   || "";
      
      // Populate Admin Stats if they exist
      if (data.admin_stats) {
          const uEl = $("#admin-total-users");
          const sEl = $("#admin-total-sessions");
          if (uEl) uEl.innerText = data.admin_stats.total_users;
          if (sEl) sEl.innerText = data.admin_stats.active_sessions;
      }
    }
  }
  function closeSettings() { $("#settings-modal").style.display = "none"; }

  async function saveSettings() {
    const btn = $("#btn-save-settings");
    btn.disabled = true; btn.innerText = "Saving...";
    const r = await fetch("/api/settings/update/", {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": window.SYNAPSE.csrfToken },
      body: JSON.stringify({ preferred_language: $("#setting-language").value, personal_api_key: $("#setting-api-key").value })
    });
    if (r.ok) { btn.innerText = "Saved!"; setTimeout(() => { closeSettings(); btn.disabled = false; btn.innerText = "Save Changes"; }, 1000); }
    else { alert("Error saving settings."); btn.disabled = false; btn.innerText = "Save Changes"; }
  }

  return { init, sendMessage, loadSession, newChat, deleteSession, openSettings, closeSettings, saveSettings };
})();

window.SynapseChat = SynapseChat;
document.addEventListener("DOMContentLoaded", SynapseChat.init);

function sendMessage()         { SynapseChat.sendMessage(); }
function loadSession(id)       { SynapseChat.loadSession(id); }
function newChat()             { SynapseChat.newChat(); }
function deleteSession(id)     { SynapseChat.deleteSession(id); }
function openSettings()        { SynapseChat.openSettings(); }
function closeSettings()       { SynapseChat.closeSettings(); }
function saveSettings()        { SynapseChat.saveSettings(); }
function quickPrompt(text)     { document.querySelector("#message-input").value = text; SynapseChat.sendMessage(); }
function handleKeyDown(event)  { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); SynapseChat.sendMessage(); } }
function autoResize(textarea)  { textarea.style.height = "auto"; textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px"; }
function toggleSidebar()       { document.getElementById("sidebar").classList.toggle("open"); document.getElementById("sidebar-overlay").classList.toggle("show"); }
function closeSidebarMobile()  { document.getElementById("sidebar").classList.remove("open"); document.getElementById("sidebar-overlay").classList.remove("show"); }
