/* ═══════════════════════════════════════════════════════════
   SYNAPSE AI — Premium Interactive Chat Client
   Live limits · Type-based WS routing · Toast notifications
═══════════════════════════════════════════════════════════ */

const SynapseChat = (() => {
  let ws = null;
  let currentSessionId = window.SYNAPSE ? window.SYNAPSE.currentSessionId : null;
  let isStreaming = false;
  let streamBuffer = "";
  const DEBOUNCE_MS = 300;
  let lastSendTime = 0;

  // Live limit state
  let chatStats = { daily_count: 0, daily_limit: 50, total_chats: 0 };

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ─── Initialization ──────────────────────────────────
  function init() {
    connectWebSocket();
    fetchChatStats();          // Load stats on page load
  }

  // ─── WebSocket Connection ────────────────────────────
  function connectWebSocket() {
    const url = currentSessionId
      ? window.SYNAPSE.wsUrl + currentSessionId + "/"
      : window.SYNAPSE.wsUrl;
    if (ws) ws.close();
    ws = new WebSocket(url);
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "status" && data.session_id) currentSessionId = data.session_id;
      handleWSMessage(data);
    };
    ws.onclose = () => setTimeout(connectWebSocket, 3000);
    ws.onerror = (err) => console.error("WebSocket error:", err);
  }

  // ─── WS Message Router ───────────────────────────────
  function handleWSMessage(data) {
    switch (data.type) {
      // --- Chat flow ---
      case "status":
        if (data.content === "thinking") showThinking();
        break;
      case "stream_start":
        hideThinking();
        startStreamMessage();
        break;
      case "stream":
        appendToStream(data.content);
        break;
      case "stream_end":
        finalizeStream();
        break;
      case "error":
        hideThinking();
        showError(data.content);
        break;

      // --- Live limit updates ---
      case "chat_stats":
        updateChatStats(data);
        break;
      case "limit_reached":
        hideThinking();
        handleLimitReached(data);
        break;

      // --- Session / message operations ---
      case "rename_success":
        handleRenameSuccess(data);
        break;
      case "delete_message_success":
        showToast("Message deleted", "success");
        break;
      case "delete_session_success":
        handleDeleteSessionSuccess(data);
        break;
    }
  }

  // ═══════════════════════════════════════════════════════
  //  LIVE LIMIT SYSTEM
  // ═══════════════════════════════════════════════════════

  function fetchChatStats() {
    fetch("/api/chat/stats/")
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.status === "success") updateChatStats(data);
      })
      .catch(function() { /* silent */ });
  }

  function updateChatStats(data) {
    chatStats.daily_count = data.daily_count || 0;
    chatStats.daily_limit = data.daily_limit || 50;
    chatStats.total_chats = data.total_chats || 0;
    renderLimitUI();
  }

  function renderLimitUI() {
    var used  = chatStats.daily_count;
    var limit = chatStats.daily_limit;
    var pct   = limit > 0 ? Math.min((used / limit) * 100, 100) : 0;

    // Determine severity
    var severity = "";
    if (pct >= 90) severity = "critical";
    else if (pct >= 70) severity = "warn";

    // --- Sidebar widget ---
    var currentEl = $("#limit-current");
    var totalEl   = $("#limit-total");
    var barFill   = $("#limit-bar-fill");
    var hintEl    = $("#limit-hint");

    if (currentEl) {
      // Animate the number change
      animateNumber(currentEl, used);
      totalEl.textContent = limit;

      barFill.style.width = pct + "%";
      barFill.className = "limit-bar-fill" + (severity ? " " + severity : "");

      if (severity === "critical") {
        hintEl.textContent = "Almost at limit! " + (limit - used) + " remaining";
        hintEl.className = "limit-hint critical";
      } else if (severity === "warn") {
        hintEl.textContent = (limit - used) + " chats remaining today";
        hintEl.className = "limit-hint warn";
      } else {
        hintEl.textContent = "Resets daily at midnight UTC";
        hintEl.className = "limit-hint";
      }
    }

    // --- Header badge ---
    var badge     = $("#header-limit-badge");
    var badgeText = $("#header-limit-text");
    if (badge) {
      badgeText.textContent = used + " / " + limit;
      badge.className = "header-limit-badge" + (severity ? " " + severity : "");
    }
  }

  function animateNumber(el, target) {
    var current = parseInt(el.textContent) || 0;
    if (current === target) return;
    var step = current < target ? 1 : -1;
    var delay = Math.max(30, 200 / Math.abs(target - current));
    var interval = setInterval(function() {
      current += step;
      el.textContent = current;
      if (current === target) clearInterval(interval);
    }, delay);
  }

  function handleLimitReached(data) {
    // Update stats to show 0 remaining
    chatStats.daily_count = data.daily_limit || 50;
    chatStats.daily_limit = data.daily_limit || 50;
    renderLimitUI();

    // Show limit message in chat
    var container = $("#messages-container");
    container.insertAdjacentHTML("beforeend",
      '<div class="message-ai">' +
        '<div class="message-bubble" style="border-left:3px solid var(--accent-rose); background:rgba(255,77,106,0.06);">' +
          '<strong style="color:var(--accent-rose);">&#9888; Daily Limit Reached</strong><br>' +
          '<span style="color:var(--text-secondary);">' + escapeHtml(data.content) + '</span>' +
        '</div>' +
      '</div>'
    );
    scrollToBottom();

    // Re-enable input
    $("#btn-send").disabled = false;
    $("#message-input").disabled = false;

    // Show toast
    showToast("Daily chat limit reached", "error");
  }

  // ═══════════════════════════════════════════════════════
  //  TOAST NOTIFICATIONS
  // ═══════════════════════════════════════════════════════

  function showToast(message, type) {
    type = type || "info";
    var container = $("#toast-container");
    if (!container) return;
    var toast = document.createElement("div");
    toast.className = "toast " + type;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(function() { toast.remove(); }, 3000);
  }

  // ═══════════════════════════════════════════════════════
  //  CHAT MESSAGES
  // ═══════════════════════════════════════════════════════

  function addUserMessage(text) {
    hideWelcome();
    var container = $("#messages-container");
    container.insertAdjacentHTML("beforeend",
      '<div class="message-user"><div class="message-bubble">' + escapeHtml(text) + '</div></div>'
    );
    scrollToBottom();
  }

  function showThinking() {
    hideThinking();
    $("#messages-container").insertAdjacentHTML("beforeend",
      '<div class="message-ai thinking-msg" id="thinking-msg">' +
        '<div class="message-bubble">&#9679;&#9679;&#9679; Thinking...</div>' +
      '</div>'
    );
    scrollToBottom();
  }

  function hideThinking() {
    var el = $("#thinking-msg");
    if (el) el.remove();
  }

  function startStreamMessage() {
    isStreaming = true;
    streamBuffer = "";
    $("#messages-container").insertAdjacentHTML("beforeend",
      '<div class="message-ai stream-msg">' +
        '<div class="message-bubble"><div id="stream-content"></div></div>' +
      '</div>'
    );
    scrollToBottom();
  }

  function appendToStream(chunk) {
    streamBuffer += chunk;
    var el = $("#stream-content");
    if (el) {
      el.innerHTML = renderMarkdown(streamBuffer);
      scrollToBottom();
    }
  }

  function finalizeStream() {
    isStreaming = false;
    var el = $("#stream-content");
    if (el) {
      el.innerHTML = renderMarkdown(streamBuffer);
      el.querySelectorAll("pre code").forEach(hljs.highlightElement);
      addCopyButtons(el);
    }
    $("#btn-send").disabled = false;
    $("#message-input").disabled = false;
    streamBuffer = "";
    scrollToBottom();
  }

  function showError(text) {
    var container = $("#messages-container");
    container.insertAdjacentHTML("beforeend",
      '<div class="message-ai error-msg">' +
        '<div class="message-bubble">&#9888; ' + escapeHtml(text) + '</div>' +
      '</div>'
    );
    $("#btn-send").disabled = false;
    $("#message-input").disabled = false;
    scrollToBottom();
  }

  function showAIMessage(text) {
    var container = $("#messages-container");
    container.insertAdjacentHTML("beforeend",
      '<div class="message-ai"><div class="message-bubble">' + renderMarkdown(text) + '</div></div>'
    );
    container.lastElementChild.querySelectorAll("pre code").forEach(hljs.highlightElement);
    addCopyButtons(container.lastElementChild);
    scrollToBottom();
  }

  // ═══════════════════════════════════════════════════════
  //  SEND MESSAGE (type: "chat")
  // ═══════════════════════════════════════════════════════

  function sendMessage() {
    var now = Date.now();
    if (now - lastSendTime < DEBOUNCE_MS) return;
    var input = $("#message-input");
    var message = input.value.trim();
    if (!message || isStreaming) return;
    lastSendTime = now;
    addUserMessage(message);
    input.value = "";
    input.style.height = "auto";
    $("#btn-send").disabled = true;
    input.disabled = true;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "chat",
        message: message,
        session_id: currentSessionId
      }));
    }
  }

  // ═══════════════════════════════════════════════════════
  //  SESSION MANAGEMENT
  // ═══════════════════════════════════════════════════════

  function loadSession(sessionId) {
    currentSessionId = sessionId;
    $$(".session-item").forEach(function(el) { el.classList.remove("active"); });
    var active = $(".session-item[data-session-id=\"" + sessionId + "\"]");
    if (active) active.classList.add("active");
    connectWebSocket();
    fetch("/api/sessions/" + sessionId + "/messages/")
      .then(function(r) { return r.json(); })
      .then(function(data) {
        if (data.status === "success") {
          var container = $("#messages-container");
          container.innerHTML = "";
          $("#chat-title").textContent = data.title || "Chat";
          if (data.messages.length === 0) {
            showWelcome();
          } else {
            hideWelcome();
            data.messages.forEach(function(msg) {
              if (msg.role === "user") addUserMessage(msg.content);
              else showAIMessage(msg.content);
            });
          }
        }
      });
  }

  async function newChat() {
    var r = await fetch("/api/sessions/new/", {
      headers: { "X-CSRFToken": window.SYNAPSE.csrfToken }
    });
    var data = await r.json();
    if (data.status === "success") location.reload();
  }

  // ─── Rename Session (via WebSocket) ──────────────────
  function renameSession(sessionId) {
    var item = $(".session-item[data-session-id=\"" + sessionId + "\"]");
    if (!item) return;
    var titleEl = item.querySelector(".session-title");
    var oldTitle = titleEl.textContent.trim();

    // Replace title with inline input
    var input = document.createElement("input");
    input.type = "text";
    input.className = "session-rename-input";
    input.value = oldTitle;
    titleEl.replaceWith(input);
    input.focus();
    input.select();

    function commitRename() {
      var newTitle = input.value.trim();
      if (!newTitle) newTitle = oldTitle;

      // Restore the span
      var span = document.createElement("span");
      span.className = "session-title";
      span.textContent = newTitle;
      input.replaceWith(span);

      // Send rename via WebSocket
      if (newTitle !== oldTitle && ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
          type: "rename_session",
          session_id: sessionId,
          title: newTitle
        }));
      }
    }

    input.addEventListener("blur", commitRename);
    input.addEventListener("keydown", function(e) {
      if (e.key === "Enter") { e.preventDefault(); input.blur(); }
      if (e.key === "Escape") { input.value = oldTitle; input.blur(); }
    });
  }

  function handleRenameSuccess(data) {
    // Update sidebar title
    var item = $(".session-item[data-session-id=\"" + data.session_id + "\"]");
    if (item) {
      var titleEl = item.querySelector(".session-title");
      if (titleEl) titleEl.textContent = data.title;
    }
    // Update header if it's the current session
    if (data.session_id === currentSessionId) {
      $("#chat-title").textContent = data.title;
    }
    showToast("Session renamed", "success");
  }

  // ─── Delete Session (via WebSocket) ──────────────────
  function deleteSession(sessionId) {
    if (!confirm("Delete this conversation?")) return;

    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({
        type: "delete_session",
        session_id: sessionId
      }));
    }
  }

  function handleDeleteSessionSuccess(data) {
    var item = $(".session-item[data-session-id=\"" + data.session_id + "\"]");
    if (item) {
      item.style.transition = "all 0.3s ease";
      item.style.opacity = "0";
      item.style.transform = "translateX(-20px)";
      setTimeout(function() { item.remove(); }, 300);
    }
    if (currentSessionId === data.session_id) {
      // Load the next available session or create new chat
      var next = $(".session-item");
      if (next) {
        loadSession(next.dataset.sessionId);
      } else {
        newChat();
      }
    }
    showToast("Conversation deleted", "success");
  }

  // ═══════════════════════════════════════════════════════
  //  SETTINGS
  // ═══════════════════════════════════════════════════════

  async function openSettings() {
    var modal = $("#settings-modal");
    modal.style.display = "flex";
    var r = await fetch("/api/settings/");
    var data = await r.json();
    if (data.status === "success") {
      $("#setting-language").value = data.settings.preferred_language || "Python";
      $("#setting-api-key").value  = data.settings.personal_api_key   || "";
    }
  }

  function closeSettings() {
    $("#settings-modal").style.display = "none";
  }

  async function saveSettings() {
    var btn = $("#btn-save-settings");
    btn.disabled = true;
    btn.innerText = "Saving...";
    var r = await fetch("/api/settings/update/", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": window.SYNAPSE.csrfToken
      },
      body: JSON.stringify({
        preferred_language: $("#setting-language").value,
        personal_api_key: $("#setting-api-key").value
      })
    });
    if (r.ok) {
      btn.innerText = "Saved!";
      showToast("Settings saved", "success");
      setTimeout(function() {
        closeSettings();
        btn.disabled = false;
        btn.innerText = "Save Changes";
      }, 1000);
    } else {
      showToast("Error saving settings", "error");
      btn.disabled = false;
      btn.innerText = "Save Changes";
    }
  }

  // ═══════════════════════════════════════════════════════
  //  UTILITIES
  // ═══════════════════════════════════════════════════════

  function renderMarkdown(text) {
    return window.marked ? marked.parse(text) : escapeHtml(text);
  }

  function addCopyButtons(container) {
    container.querySelectorAll("pre").forEach(function(pre) {
      var btn = document.createElement("button");
      btn.className = "btn-copy";
      btn.innerText = "Copy";
      btn.onclick = function() {
        navigator.clipboard.writeText(pre.innerText).then(function() {
          btn.innerText = "Copied!";
          setTimeout(function() { btn.innerText = "Copy"; }, 2000);
        });
      };
      pre.appendChild(btn);
    });
  }

  function escapeHtml(text) {
    var d = document.createElement("div");
    d.textContent = text;
    return d.innerHTML;
  }

  function scrollToBottom() {
    var c = $("#messages-container");
    requestAnimationFrame(function() { c.scrollTop = c.scrollHeight; });
  }

  function hideWelcome() {
    var el = $("#welcome-screen");
    if (el) el.remove();
  }

  function showWelcome() {
    location.reload();
  }

  // ─── Public API ──────────────────────────────────────
  return {
    init: init,
    sendMessage: sendMessage,
    loadSession: loadSession,
    newChat: newChat,
    deleteSession: deleteSession,
    renameSession: renameSession,
    openSettings: openSettings,
    closeSettings: closeSettings,
    saveSettings: saveSettings,
    showToast: showToast
  };
})();

window.SynapseChat = SynapseChat;
document.addEventListener("DOMContentLoaded", SynapseChat.init);

// ─── Global helpers (called from HTML onclick) ────────
function sendMessage()         { SynapseChat.sendMessage(); }
function loadSession(id)       { SynapseChat.loadSession(id); }
function newChat()             { SynapseChat.newChat(); }
function deleteSession(id)     { SynapseChat.deleteSession(id); }
function renameSession(id)     { SynapseChat.renameSession(id); }
function openSettings()        { SynapseChat.openSettings(); }
function closeSettings()       { SynapseChat.closeSettings(); }
function saveSettings()        { SynapseChat.saveSettings(); }
function quickPrompt(text)     { document.querySelector("#message-input").value = text; SynapseChat.sendMessage(); }
function handleKeyDown(event)  { if (event.key === "Enter" && !event.shiftKey) { event.preventDefault(); SynapseChat.sendMessage(); } }
function autoResize(textarea)  { textarea.style.height = "auto"; textarea.style.height = Math.min(textarea.scrollHeight, 150) + "px"; }
function toggleSidebar()       { document.getElementById("sidebar").classList.toggle("open"); document.getElementById("sidebar-overlay").classList.toggle("show"); }
function closeSidebarMobile()  { document.getElementById("sidebar").classList.remove("open"); document.getElementById("sidebar-overlay").classList.remove("show"); }