"""
AI Engine — Direct Gemini chat via LangChain (no agent wrapper).
FIXED: Removed AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION which breaks
       with Gemini. Now uses simple direct LLM call with conversation history.
"""
import random, logging, hashlib
from threading import Lock
from django.conf import settings
from django.core.cache import cache
from .mongo_store import mongo_store

logger = logging.getLogger(__name__)




def _get_api_key(user_id, exclude_keys=None):
    """
    Get API key: personal key > env keys (rotated).
    Returns (api_key, is_personal).
    """
    if exclude_keys is None:
        exclude_keys = set()
    
    # 1. Check Personal Key (BYOK)
    try:
        s = mongo_store.get_user_settings(user_id)
        k = s.get('personal_api_key', '').strip()
        if k and k not in exclude_keys:
            return k, True
    except Exception as e:
        logger.debug(f"BYOK Key check failed: {e}")
    
    # 2. Check App Rotation Pool
    app_keys = getattr(settings, 'GEMINI_API_KEYS', [])
    keys = [k for k in app_keys if k.strip() and k not in exclude_keys]
    if keys:
        return keys[0], False
    
    # 3. Fallback to Primary
    primary = getattr(settings, 'GEMINI_API_KEY', '').strip()
    if primary and primary not in exclude_keys:
        return primary, False
    
    return None, False


def get_remaining_chats():
    """
    Calculate remaining chats across all keys.
    Gemini Free tier is ~1500 RPD (Requests Per Day).
    We track usage in cache with a daily key.
    """
    import datetime
    today = datetime.date.today().isoformat()
    usage_key = f"synapse:usage:{today}"
    usage = cache.get(usage_key, 0)
    
    num_keys = len(getattr(settings, 'GEMINI_API_KEYS', []))
    if not num_keys: num_keys = 1
    
    # 1500 requests per key per day
    total_capacity = num_keys * 1500
    remaining = max(0, total_capacity - usage)
    return remaining, total_capacity


def _increment_usage():
    import datetime
    today = datetime.date.today().isoformat()
    usage_key = f"synapse:usage:{today}"
    try:
        # Increment global usage. 86400s = 1 day.
        cache.get_or_set(usage_key, 0, 86400)
        cache.incr(usage_key)
    except Exception:
        pass


def _get_llm(user_id, api_key=None):
    """Get or create LLM instance for user."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    if not api_key:
        api_key = _get_api_key(user_id)
    if not api_key:
        raise ValueError("No GEMINI_API_KEY available.")
    
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=api_key,
        temperature=0.4,
        max_output_tokens=4096,
        convert_system_message_to_human=True,
        max_retries=0, # Force immediate rotation by our logic
        timeout=30,    # Don't hang forever
        version="v1"   # Stable long-term version
    )


def _get_preferred_lang(user_id):
    try:
        return mongo_store.get_user_settings(user_id).get('preferred_language', 'Python')
    except Exception:
        return 'Python'


def run_chat(user_id: int, message: str, session_id: str = None) -> str:
    """
    Run a chat turn. Loads conversation history from MongoDB,
    calls Gemini, returns response string.
    """
    from langchain.schema import HumanMessage, SystemMessage, AIMessage

    lang = _get_preferred_lang(user_id)

    system_prompt = f"""You are Synapse, an expert AI coding assistant built for developers.

The user prefers: {lang}. Prioritize {lang} in all code examples.

Guidelines:
- Give clear, working, well-commented code.
- Explain the WHY behind the code, not just the HOW.
- For beginners, break down complex concepts step by step.
- Suggest best practices, mention common pitfalls.
- Keep responses focused and practical.
- Use markdown formatting for code blocks."""

    messages = [SystemMessage(content=system_prompt)]

    # Load last 10 messages from MongoDB for context
    if session_id:
        try:
            history = mongo_store.get_messages(session_id)[-10:]
            for m in history:
                if m['role'] == 'user':
                    messages.append(HumanMessage(content=m['content']))
                elif m['role'] == 'assistant':
                    messages.append(AIMessage(content=m['content']))
        except Exception as e:
            logger.warning(f"Could not load history: {e}")

    messages.append(HumanMessage(content=message))
    
    # NEW: Log query globally
    mongo_store.log_query(user_id, message)

    exclude_keys = set()
    last_error = None

    import time
    all_keys_count = len(getattr(settings, 'GEMINI_API_KEYS', []))
    
    # --- STAGE 1: Try all keys with Gemini 2.0-Flash ---
    for attempt in range(all_keys_count + 1):
        api_key, is_personal = _get_api_key(user_id, exclude_keys)
        if not api_key: break
        
        try:
            masked = f"{api_key[:4]}...{api_key[-4:]}"
            logger.info(f"Attempting 2.5-Flash | Key: {masked} | {attempt+1}/{all_keys_count}")
            
            llm = _get_llm(user_id, api_key) # _get_llm defaults to 2.5-flash
            response = llm.invoke(messages)
            
            if not is_personal: _increment_usage()
            return response.content
            
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["429", "rate_limit", "quota", "exhausted", "too many requests"]):
                logger.warning(f"Key {api_key[:6]} limit hit (2.5). Rotating...")
                exclude_keys.add(api_key)
                last_error = e
                time.sleep(1)
                continue
            raise e

    # --- STAGE 2: Try all keys with Gemini 2.5-Flash-Lite (Fallback) ---
    logger.info("Gemini 2.5-Flash exhausted for all keys. Falling back to 2.5-Flash-Lite pool.")
    exclude_keys.clear() # Reset for the 1.5 pool attempt
    from langchain_google_genai import ChatGoogleGenerativeAI

    for attempt in range(all_keys_count + 1):
        api_key, is_personal = _get_api_key(user_id, exclude_keys)
        if not api_key: break
        
        try:
            masked = f"{api_key[:4]}...{api_key[-4:]}"
            logger.info(f"Attempting 2.5-Flash-Lite | Key: {masked} | {attempt+1}/{all_keys_count}")
            
            # Use 2.5-Flash-Lite for high-availability fallback
            llm = ChatGoogleGenerativeAI(
                model="gemini-2.5-flash-lite", 
                google_api_key=api_key, 
                max_retries=0, 
                timeout=30,
                version="v1"
            )
            response = llm.invoke(messages)
            
            if not is_personal: _increment_usage()
            return response.content
        except Exception as e:
            exclude_keys.add(api_key)
            last_error = e
            continue

    if last_error:
        raise Exception(f"All models/keys exhausted. Final error: {last_error}")
    raise Exception("No active Gemini API keys found.")


def generate_title(user_query, ai_response):
    """
    Generate a professional 3-5 word title for a chat session.
    Internal use only — doesn't use cache or query logging.
    """
    from langchain.schema import HumanMessage, SystemMessage
    prompt = f"""Summarize the following interaction into a short, professional, 3-5 word title.
Do NOT use punctuation. Return ONLY the title.
USER: {user_query}
AI: {ai_response[:200]}"""
    
    messages = [
        SystemMessage(content="You are a professional session titler. Be extremely concise."),
        HumanMessage(content=prompt)
    ]
    
    # We use a simplified version of rotation here or just call the main engine
    # To keep it seamless, we'll use one of the keys directly or a simplified loop
    try:
        # Re-using the logic but with a dummy user_id to avoid usage tracking
        return get_ai_response(user_id="SYSTEM_TITLER", messages=messages)
    except Exception:
        # Fallback to simple truncation if Gemini fails to title
        return user_query[:40].strip() + ("..." if len(user_query) > 40 else "")


# Compatibility shim — consumers.py calls agent.run(message)
class _AgentShim:
    def __init__(self, user_id, session_id=None):
        self.user_id    = user_id
        self.session_id = session_id
    def run(self, message):
        return run_chat(self.user_id, message, self.session_id)


def get_or_create_agent(user_id: int, session_id: str = None):
    """Returns a shim that mimics the old agent.run() interface."""
    return _AgentShim(user_id, session_id)


def reset_agent(user_id: int):
    """Placeholder for backward compatibility."""
    pass


# ── Cache helpers ─────────────────────────────────────────────
def _cache_key(msg: str) -> str:
    return f"synapse:r:{hashlib.sha256(msg.strip().lower().encode()).hexdigest()}"

def get_cached_response(message: str):
    try:    return cache.get(_cache_key(message))
    except: return None

def set_cached_response(message: str, response: str, timeout=3600):
    try:    cache.set(_cache_key(message), response, timeout)
    except: pass


async def get_ai_response(user_id: int, message: str, session_id: str = None) -> str:
    cached = get_cached_response(message)
    if cached:
        return cached
    import asyncio
    response = await asyncio.to_thread(run_chat, user_id, message, session_id)
    set_cached_response(message, response)
    return response
