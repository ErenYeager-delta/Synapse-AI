"""
AI Engine — Direct Gemini chat via LangChain (no agent wrapper).

Features:
  - Smart 4-key auto-rotation with quota failover & cooldown
  - Retry with exponential backoff for transient errors
  - Gemini 2.0 Flash for faster responses
  - Daily chat limit integration via MongoDB
  - Async streaming generator for WebSocket token-by-token delivery
"""
import logging
import hashlib
import time
from threading import Lock

from django.conf import settings
from django.core.cache import cache

try:
    import google.api_core.exceptions as google_exceptions
except ImportError:
    google_exceptions = None

logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────
MAX_MESSAGE_LENGTH = 10000       # Max characters allowed per user message
LLM_CACHE_TTL = 3600            # Seconds before a cached LLM instance expires (1 hour)
CONVERSATION_HISTORY_LIMIT = 20  # Max past messages loaded for context
KEY_COOLDOWN = 60                # Seconds before an exhausted key can be retried
MAX_RETRIES = 3                  # Max retry attempts for transient LLM errors

# ── LLM instance cache: {user_id: (llm_instance, created_timestamp)} ──
_user_llms: dict = {}
_llms_lock = Lock()

# ── Smart key rotation state ─────────────────────────────────
_key_index = 0                   # Current round-robin index into GEMINI_API_KEYS
_key_lock = Lock()
_exhausted_keys: dict = {}       # {key_index: timestamp} — tracks exhausted keys


# ── Internal helpers ──────────────────────────────────────────

def _get_pool_keys():
    """Return the list of pool API keys from Django settings."""
    return [k for k in getattr(settings, 'GEMINI_API_KEYS', []) if k.strip()]


def _mark_key_exhausted(idx: int):
    """Mark a pool key index as exhausted with the current timestamp."""
    with _key_lock:
        _exhausted_keys[idx] = time.time()
        logger.warning("Marked pool key index %d as exhausted.", idx)


def _get_api_key(user_id):
    """Resolve the Gemini API key for a user with smart rotation.

    Priority order:
      1. Personal API key stored in the user's MongoDB settings.
      2. Next available (non-exhausted) key from the GEMINI_API_KEYS pool,
         selected via round-robin with cooldown-aware skipping.
      3. Fallback to the single GEMINI_API_KEY in Django settings.

    Returns:
        tuple[str, int | None]: (api_key, pool_index_or_None).

    Raises:
        RuntimeError: If all pool keys are temporarily exhausted.
    """
    # Import at function level to avoid circular imports
    from .mongo_store import mongo_store

    # 1. Personal key — not subject to pool rotation
    try:
        s = mongo_store.get_user_settings(user_id)
        k = s.get('personal_api_key', '').strip()
        if k:
            return k, None
    except Exception as e:
        logger.warning("Could not fetch personal API key for user %s: %s", user_id, e)

    # 2. Pool keys with smart rotation
    keys = _get_pool_keys()
    if keys:
        global _key_index
        now = time.time()
        with _key_lock:
            # Clean up cooled-down keys
            cooled = [idx for idx, ts in _exhausted_keys.items() if now - ts >= KEY_COOLDOWN]
            for idx in cooled:
                del _exhausted_keys[idx]
                logger.info("Pool key index %d has cooled down, re-enabling.", idx)

            # Find the next available key (up to len(keys) attempts)
            for _ in range(len(keys)):
                candidate = _key_index % len(keys)
                _key_index = (_key_index + 1) % len(keys)
                if candidate not in _exhausted_keys:
                    logger.debug("Using pool key index %d.", candidate)
                    return keys[candidate], candidate

            # All pool keys exhausted
            raise RuntimeError(
                "All Gemini API keys are temporarily exhausted. "
                "Please wait ~60 seconds and try again."
            )

    # 3. Single fallback key
    fallback = getattr(settings, 'GEMINI_API_KEY', '').strip()
    return fallback, None


def _create_llm(api_key: str):
    """Create a fresh ChatGoogleGenerativeAI instance with the given key."""
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        google_api_key=api_key,
        temperature=0.7,
        max_output_tokens=2048,
        convert_system_message_to_human=True,
    )


def _get_llm(user_id):
    """Get or create a cached LLM instance for the given user.

    Instances are cached in ``_user_llms`` as ``(llm, key_index, timestamp)``
    tuples.  If the cached instance is older than ``LLM_CACHE_TTL`` seconds
    it is discarded and a fresh one is created.

    Returns:
        tuple[ChatGoogleGenerativeAI, int | None]: (llm, pool_key_index).

    Raises:
        ValueError: If no valid API key can be resolved.
        RuntimeError: If all pool keys are exhausted.
    """
    with _llms_lock:
        if user_id in _user_llms:
            llm, key_idx, created_at = _user_llms[user_id]
            if (time.time() - created_at) < LLM_CACHE_TTL:
                return llm, key_idx
            logger.info("LLM cache expired for user %s, recreating.", user_id)
            del _user_llms[user_id]

        api_key, key_idx = _get_api_key(user_id)
        if not api_key:
            raise ValueError("GEMINI_API_KEY not set in .env file.")

        llm = _create_llm(api_key)
        _user_llms[user_id] = (llm, key_idx, time.time())
        return llm, key_idx


def _get_preferred_lang(user_id):
    """Return the user's preferred programming language (default: Python)."""
    from .mongo_store import mongo_store
    try:
        return mongo_store.get_user_settings(user_id).get('preferred_language', 'Python')
    except Exception as e:
        logger.warning("Could not fetch preferred language for user %s: %s", user_id, e)
        return 'Python'


def _build_messages(user_id, message, session_id):
    """Build the full message list (system + history + user message).

    Returns:
        list: LangChain message objects ready for LLM invocation.
    """
    from langchain.schema import HumanMessage, SystemMessage, AIMessage
    from .mongo_store import mongo_store

    lang = _get_preferred_lang(user_id)

    system_prompt = (
        f"You are Synapse, an expert AI coding assistant. "
        f"User prefers {lang}. Prioritize {lang} in code examples.\n"
        f"Rules: Give clear, working, well-commented code. Explain WHY, not just HOW. "
        f"Break down complex concepts. Suggest best practices & common pitfalls. "
        f"Be concise and practical. Use markdown code blocks."
    )

    messages = [SystemMessage(content=system_prompt)]

    if session_id:
        try:
            history = mongo_store.get_messages(session_id)[-CONVERSATION_HISTORY_LIMIT:]
            for m in history:
                if m['role'] == 'user':
                    messages.append(HumanMessage(content=m['content']))
                elif m['role'] == 'assistant':
                    messages.append(AIMessage(content=m['content']))
        except Exception as e:
            logger.warning("Could not load history for session %s: %s", session_id, e)

    messages.append(HumanMessage(content=message))
    return messages


# ── Core chat logic ──────────────────────────────────────────

def run_chat(user_id: int, message: str, session_id: str = None) -> str:
    """Run a single chat turn against Gemini with retry & key failover.

    On ``ResourceExhausted`` (429) errors the current pool key is marked as
    exhausted and a new key is obtained automatically.  Other transient
    errors trigger exponential backoff (1 s, 2 s, 4 s).

    Args:
        user_id:    Numeric ID of the requesting user.
        message:    The user's latest message text.
        session_id: Optional chat-session identifier for history lookup.

    Returns:
        str: The assistant's response text.

    Raises:
        ValueError: If the message exceeds ``MAX_MESSAGE_LENGTH``.
        RuntimeError: If all API keys are exhausted.
    """
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message too long ({len(message)} chars). "
            f"Maximum allowed is {MAX_MESSAGE_LENGTH} characters."
        )

    messages = _build_messages(user_id, message, session_id)

    llm, key_idx = _get_llm(user_id)
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = llm.invoke(messages)
            return response.content

        except Exception as exc:
            last_exc = exc
            is_resource_exhausted = (
                google_exceptions is not None
                and isinstance(exc, google_exceptions.ResourceExhausted)
            )

            if is_resource_exhausted:
                # ── Key failover ──
                logger.warning(
                    "ResourceExhausted on attempt %d (key_idx=%s): %s",
                    attempt, key_idx, exc,
                )
                if key_idx is not None:
                    _mark_key_exhausted(key_idx)
                # Evict cached LLM so next call picks a fresh key
                with _llms_lock:
                    _user_llms.pop(user_id, None)
                try:
                    llm, key_idx = _get_llm(user_id)
                except RuntimeError:
                    raise  # All keys exhausted — propagate immediately
                continue  # retry with new key

            is_google_error = (
                google_exceptions is not None
                and isinstance(exc, google_exceptions.GoogleAPIError)
            )

            if is_google_error and attempt < MAX_RETRIES:
                backoff = 2 ** (attempt - 1)  # 1s, 2s, 4s
                logger.warning(
                    "Transient Google API error on attempt %d, retrying in %ds: %s",
                    attempt, backoff, exc,
                )
                time.sleep(backoff)
                continue

            # Non-retryable or final attempt — raise
            raise

    # Should not reach here, but just in case
    raise last_exc  # type: ignore[misc]


# ── Compatibility shim — consumers.py calls agent.run(message) ──

class _AgentShim:
    """Thin wrapper that exposes a ``.run()`` method so existing consumer
    code (``agent.run(message)``) keeps working without changes."""

    def __init__(self, user_id, session_id=None):
        self.user_id = user_id
        self.session_id = session_id

    def run(self, message):
        """Execute a chat turn and return the response string."""
        return run_chat(self.user_id, message, self.session_id)


def get_or_create_agent(user_id: int, session_id: str = None):
    """Return an ``_AgentShim`` that mimics the old ``agent.run()`` interface.

    Args:
        user_id:    Numeric user ID.
        session_id: Optional session identifier for conversation history.

    Returns:
        _AgentShim: An object with a ``.run(message)`` method.
    """
    return _AgentShim(user_id, session_id)


def reset_agent(user_id: int):
    """Evict the cached LLM instance for a user.

    Call this when the user changes their API key or settings so the
    next request creates a fresh LLM with the updated configuration.
    """
    with _llms_lock:
        _user_llms.pop(user_id, None)


# ── Cache helpers ─────────────────────────────────────────────

def _cache_key(msg: str) -> str:
    """Derive a deterministic Django-cache key from a message string."""
    return f"synapse:r:{hashlib.sha256(msg.strip().lower().encode()).hexdigest()}"


def get_cached_response(message: str):
    """Look up a previously cached AI response for *message*.

    Returns:
        str or None: The cached response text, or ``None`` on miss / error.
    """
    try:
        return cache.get(_cache_key(message))
    except Exception as e:
        logger.warning("Cache read failed: %s", e)
        return None


def set_cached_response(message: str, response: str, timeout: int = 3600):
    """Store an AI response in the Django cache.

    Args:
        message:  The original user message (used to derive the key).
        response: The AI-generated response text.
        timeout:  Cache TTL in seconds (default 3600 = 1 hour).
    """
    try:
        cache.set(_cache_key(message), response, timeout)
    except Exception as e:
        logger.warning("Cache write failed: %s", e)


# ── Async entry-point ────────────────────────────────────────

async def get_ai_response(user_id: int, message: str, session_id: str = None,
                          mongo_user_id: str = None) -> str:
    """High-level async helper used by WebSocket consumers.

    Checks daily chat limits, then the response cache; on a miss, runs
    the chat in a thread (via ``asyncio.to_thread``) and caches the result.

    Args:
        user_id:       Numeric user ID (Django auth).
        message:       The user's message text.
        session_id:    Optional session identifier.
        mongo_user_id: MongoDB ``_id`` string for chat-limit checks.
                       If ``None``, limit checking is skipped.

    Returns:
        str: The AI response (from cache or freshly generated).

    Raises:
        ValueError: If the message exceeds ``MAX_MESSAGE_LENGTH``.
    """
    import asyncio

    # ── Input validation (also checked inside run_chat, but fail fast) ──
    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message too long ({len(message)} chars). "
            f"Maximum allowed is {MAX_MESSAGE_LENGTH} characters."
        )

    # ── Chat limit check ──
    if mongo_user_id:
        try:
            from .mongo_store import mongo_store
            allowed, remaining = mongo_store.check_and_increment_chat_count(mongo_user_id)
            if not allowed:
                return "Daily chat limit reached. Please try again tomorrow."
            logger.debug("User %s chat limit OK, %d remaining.", mongo_user_id, remaining)
        except Exception as e:
            logger.warning("Chat limit check failed for user %s: %s", mongo_user_id, e)
            # Fail open — allow the chat if the limit check itself errors

    # ── Cache lookup ──
    cached = get_cached_response(message)
    if cached:
        return cached

    response = await asyncio.to_thread(run_chat, user_id, message, session_id)
    set_cached_response(message, response)
    return response


# ── Async streaming generator for WebSocket token delivery ───

async def async_stream_response(user_id: int, session_id: str, message: str,
                                mongo_user_id: str = None):
    """Async generator that yields response tokens for WebSocket streaming.

    Uses ``llm.stream()`` under the hood (run in a thread) and yields each
    chunk's text content as it arrives.  Handles key failover identically
    to ``run_chat``.

    Args:
        user_id:       Numeric user ID (Django auth).
        session_id:    Chat session identifier.
        message:       The user's message text.
        mongo_user_id: MongoDB ``_id`` for chat-limit checks (optional).

    Yields:
        str: Individual text tokens / chunks from the model.

    Raises:
        ValueError: If the message exceeds ``MAX_MESSAGE_LENGTH``.
        RuntimeError: If all API keys are exhausted.
    """
    import asyncio

    if len(message) > MAX_MESSAGE_LENGTH:
        raise ValueError(
            f"Message too long ({len(message)} chars). "
            f"Maximum allowed is {MAX_MESSAGE_LENGTH} characters."
        )

    # ── Chat limit check ──
    if mongo_user_id:
        try:
            from .mongo_store import mongo_store
            allowed, remaining = mongo_store.check_and_increment_chat_count(mongo_user_id)
            if not allowed:
                yield "Daily chat limit reached. Please try again tomorrow."
                return
        except Exception as e:
            logger.warning("Chat limit check failed for user %s: %s", mongo_user_id, e)

    messages = _build_messages(user_id, message, session_id)
    llm, key_idx = _get_llm(user_id)
    last_exc = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Run the blocking stream iterator in a thread and yield chunks
            chunks = await asyncio.to_thread(lambda: list(llm.stream(messages)))
            for chunk in chunks:
                text = chunk.content if hasattr(chunk, 'content') else str(chunk)
                if text:
                    yield text
            return  # success

        except Exception as exc:
            last_exc = exc
            is_resource_exhausted = (
                google_exceptions is not None
                and isinstance(exc, google_exceptions.ResourceExhausted)
            )

            if is_resource_exhausted:
                logger.warning(
                    "Stream ResourceExhausted attempt %d (key_idx=%s): %s",
                    attempt, key_idx, exc,
                )
                if key_idx is not None:
                    _mark_key_exhausted(key_idx)
                with _llms_lock:
                    _user_llms.pop(user_id, None)
                try:
                    llm, key_idx = _get_llm(user_id)
                except RuntimeError:
                    raise
                continue

            is_google_error = (
                google_exceptions is not None
                and isinstance(exc, google_exceptions.GoogleAPIError)
            )
            if is_google_error and attempt < MAX_RETRIES:
                backoff = 2 ** (attempt - 1)
                logger.warning(
                    "Stream transient error attempt %d, retrying in %ds: %s",
                    attempt, backoff, exc,
                )
                await asyncio.sleep(backoff)
                continue

            raise

    raise last_exc  # type: ignore[misc]