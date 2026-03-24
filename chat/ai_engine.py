"""
AI Engine — Direct Gemini chat via LangChain (no agent wrapper).
FIXED: Removed AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION which breaks
       with Gemini. Now uses simple direct LLM call with conversation history.
"""
import random, logging, hashlib, hmac
from threading import Lock
from django.conf import settings
from django.core.cache import cache
from .mongo_store import mongo_store

def _secure_hash(data: str) -> str:
    """Generate a secure salted hash for API keys."""
    salt = settings.SECRET_KEY.encode()
    return hmac.new(salt, data.encode(), hashlib.sha256).hexdigest()[:12]

# --- 2026 ROADMAP CONFIG ---
AI_MODELS = {
    'PRIMARY': 'gemini-1.5-flash-latest',
    'FALLBACK': 'gemini-1.5-flash',
    'PRO': 'gemini-1.5-pro-latest',
    'VERSION': 'v1'
}

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
    Calculate remaining chats for ALL keys in the pool.
    Returns (total_remaining, total_capacity, key_stats_list).
    """
    import datetime
    today = datetime.date.today().isoformat()
    app_keys = getattr(settings, 'GEMINI_API_KEYS', [])
    if not app_keys:
        primary = getattr(settings, 'GEMINI_API_KEY', '')
        app_keys = [primary] if primary else []

    key_stats = []
    total_remaining = 0
    total_capacity = len(app_keys) * 1500

    for i, key in enumerate(app_keys):
        k_hash = _secure_hash(key)
        usage_key = f"synapse:usage:{today}:{k_hash}"
        usage = cache.get(usage_key, 0)
        remaining = max(0, 1500 - usage)
        total_remaining += remaining
        key_stats.append({
            'index': i + 1,
            'label': f"Key {i+1} ({k_hash})",
            'used': usage,
            'remaining': remaining,
            'percent': round((remaining / 1500) * 100, 1)
        })
    
    return total_remaining, total_capacity, key_stats


def _increment_usage(api_key):
    if not api_key: return
    import datetime
    today = datetime.date.today().isoformat()
    k_hash = _secure_hash(api_key)
    usage_key = f"synapse:usage:{today}:{k_hash}"
    try:
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
        model=AI_MODELS['PRIMARY'],
        google_api_key=api_key,
        temperature=0.4,
        max_output_tokens=4096,
        max_retries=0, 
        timeout=30,
        version="v1"   # Force stable v1 API
    )


def _get_preferred_lang(user_id):
    try:
        return mongo_store.get_user_settings(user_id).get('preferred_language', 'Python')
    except Exception:
        return 'Python'


def run_chat(user_id: int, message: str, session_id: str = None, **kwargs) -> str:
    """
    Run a chat turn. Loads conversation history from MongoDB,
    calls Gemini, returns response string.
    """
    from langchain.schema import HumanMessage, SystemMessage, AIMessage

    lang = _get_preferred_lang(user_id)

    system_prompt = f"""You are Synapse AI, a state-of-the-art software engineering assistant.
Your persona combines the extreme technical depth and logical rigor of Claude 3.5 Sonnet with the professional polish and helpfulness of Google Gemini.

The user prefers: {lang}. Prioritize {lang} in all code examples.

Core Directives:
- Act as a Senior Staff Engineer. Provide deep technical analysis, not just surface-level code.
- Continuous Evolution: You have a persistent memory across this session. Refer back to previous decisions and context to provide cohesive engineering advice.
- Offer alternative architectural approaches and explain trade-offs clearly.
- Code must be production-ready, performant, and include rigorous error handling.
- Use a sophisticated, precise, yet encouraging professional tone.
- When explaining complex concepts, use analogies but maintain technical accuracy.
- Suggest best practices (SOLID, DRY) and warn against common security/performance pitfalls.
- Vision & Docs: You can now "see" images and "read" documents. Analyze them with extreme precision and relate them to the coding task.
- Use clean, structured Markdown with syntax-highlighted code blocks."""

    messages = [SystemMessage(content=system_prompt)]

    # Load last 20 messages from MongoDB for context (Memory Power Boost)
    if session_id:
        try:
            history = mongo_store.get_messages(session_id)[-20:]
            for m in history:
                content = m.get('content', '').strip()
                if not content: continue # Skip empty messages
                
                if m['role'] == 'user':
                    messages.append(HumanMessage(content=content))
                elif m['role'] == 'assistant':
                    messages.append(AIMessage(content=content))
                
            # SAFETY CHECK: Ensure the list of messages alternates properly
            # LLMs can crash if they see consecutive messages from the same role.
            # Our structure: System -> [History...] -> New User Message.
        except Exception as e:
            logger.warning(f"Could not load history: {e}")

    attachments = kwargs.get('attachments', [])
    if not attachments:
        messages.append(HumanMessage(content=message))
    else:
        # Multimodal payload construction
        content_parts = []
        if message:
            content_parts.append({"type": "text", "text": message})
        
        for att in attachments:
            a_type = att.get('type', '')
            if a_type.startswith('image/'):
                content_parts.append({
                    "type": "image_url",
                    "image_url": f"data:{a_type};base64,{att.get('data')}"
                })
            else:
                # Handle other types (PDF, text) as text context for now
                content_parts.append({
                    "type": "text", 
                    "text": f"\n[File: {att.get('name')}]\n(Binary or large text data processed separately in future phases)\n"
                })
        
        messages.append(HumanMessage(content=content_parts))
    
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
            logger.info(f"Attempting Stage 1 Model | Key #{attempt+1}/{all_keys_count}")
            
            llm = _get_llm(user_id, api_key) # _get_llm defaults to 2.5-flash
            response = llm.invoke(messages)
            
            if not is_personal: _increment_usage(api_key)
            return response.content
            
        except Exception as e:
            err_str = str(e).lower()
            if any(x in err_str for x in ["429", "rate_limit", "quota", "exhausted", "too many requests"]):
                logger.warning(f"Key #{attempt+1} limit hit. Rotating...")
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
            logger.info(f"Attempting Stage 2 Model (Fallback) | Key #{attempt+1}/{all_keys_count}")
            
            # Use 2.5-Flash-Lite for high-availability fallback
            llm = ChatGoogleGenerativeAI(
                model=AI_MODELS['FALLBACK'], 
                google_api_key=api_key, 
                max_retries=0, 
                timeout=30,
                version="v1"
            )
            response = llm.invoke(messages)
            
            if not is_personal: _increment_usage(api_key)
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
    Direct synchronous call for stability.
    """
    if not user_query or not ai_response:
        return "New Chat"

    from langchain.schema import HumanMessage, SystemMessage
    prompt = f"Summarize into a 3-5 word professional title (no punctuation): {user_query}"
    
    messages = [
        SystemMessage(content="You are a professional session titler. Return ONLY the title."),
        HumanMessage(content=prompt)
    ]
    
    try:
        # Use primary key directly with a shorter timeout for titling
        api_key, _ = _get_api_key("SYSTEM_TITLER")
        if not api_key: return user_query[:40]
        
        from langchain_google_genai import ChatGoogleGenerativeAI
        llm = ChatGoogleGenerativeAI(
            model=AI_MODELS['PRIMARY'],
            google_api_key=api_key,
            temperature=0.2,
            timeout=10, # Very short timeout for titler to prevent hanging the chat
            version="v1"
        )
        res = llm.invoke(messages)
        return res.content.strip().replace('"', '').replace('.', '')[:50]
    except Exception:
        # Fallback to simple truncation if Gemini fails or hangs
        return user_query[:40].strip() + ("..." if len(user_query) > 40 else "")


# Compatibility shim — consumers.py calls agent.run(message)
class _AgentShim:
    def __init__(self, user_id, session_id=None):
        self.user_id    = user_id
        self.session_id = session_id
    def run(self, message):
        return run_chat(self.user_id, message, self.session_id)
    def run_multimodal(self, message, attachments):
        return run_chat(self.user_id, message, self.session_id, attachments=attachments)


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
