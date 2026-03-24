"""WebSocket consumer — streams AI responses token-by-token."""

import json
import asyncio
import logging
import traceback

from channels.generic.websocket import AsyncWebsocketConsumer
from .mongo_store import mongo_store
from .ai_engine import async_stream_response

logger = logging.getLogger(__name__)

# Maximum allowed message length (characters)
MAX_MESSAGE_LENGTH = 10_000

# TODO: Implement rate limiting for WebSocket messages.
# Consider using a per-user token-bucket or sliding-window counter
# (e.g., max 20 messages per minute) to prevent abuse and protect
# downstream AI resources.  A lightweight approach is to track
# timestamps in self._message_timestamps and reject when the window
# is exceeded.

# TODO: For production, implement WebSocket heartbeat / ping-pong
# to detect stale connections early.  Channels supports this via
# the server-level --ping-interval / --ping-timeout flags in Daphne
# or Uvicorn, but application-level keep-alive can also be added
# inside connect() with a periodic asyncio task.


class ChatConsumer(AsyncWebsocketConsumer):
    """Handles a single WebSocket connection for real-time chat."""

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------

    async def connect(self):
        """Accept the WebSocket only for authenticated users."""
        self.user = self.scope.get('user')
        self.session_id = None
        self._connected = False

        if not self.user or self.user.is_anonymous:
            logger.warning("WS rejected: unauthenticated user")
            await self.close()
            return

        self.session_id = self.scope['url_route']['kwargs'].get('session_id')

        try:
            # Connection timeout: if accept() hangs, bail out after 10 s
            await asyncio.wait_for(self.accept(), timeout=10.0)
            self._connected = True
            logger.info("WS connected: user=%s session=%s", self.user.username, self.session_id)
        except asyncio.TimeoutError:
            logger.error("WS accept timed out for user=%s", self.user.username)
            await self.close()
        except Exception as exc:
            logger.error("WS accept failed for user=%s: %s", self.user.username, exc)
            await self.close()

    async def disconnect(self, close_code):
        """Log disconnection and clean up resources."""
        username = getattr(self.user, 'username', 'unknown') if hasattr(self, 'user') else 'unknown'
        logger.info(
            "WS disconnected: user=%s session=%s code=%s",
            username,
            getattr(self, 'session_id', None),
            close_code,
        )
        self._connected = False

        # Clean up any per-connection resources (MongoDB cursors, caches, etc.)
        # Currently mongo_store uses a shared client, so nothing to close here,
        # but this is the right place if per-socket resources are added later.

    # ------------------------------------------------------------------
    # Incoming messages — type-based routing
    # ------------------------------------------------------------------

    async def receive(self, text_data):
        """Route incoming messages by their ``type`` field."""

        # --- Parse JSON safely -------------------------------------------
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self._safe_send({'type': 'error', 'content': 'Invalid message format.'})
            return

        # --- Ensure the user is authenticated ----------------------------
        if not self.user or self.user.is_anonymous:
            await self._safe_send({'type': 'error', 'content': 'Authentication required.'})
            return

        try:
            # Parse message type (default to "chat" for backward compat)
            message_type = data.get('type', 'chat')

            if message_type == 'chat':
                await self._handle_chat(data)
            elif message_type == 'rename_session':
                await self._handle_rename_session(data)
            elif message_type == 'delete_message':
                await self._handle_delete_message(data)
            elif message_type == 'delete_session':
                await self._handle_delete_session(data)
            else:
                await self._safe_send({
                    'type': 'error',
                    'content': f'Unknown message type: {message_type}',
                })

        except Exception as exc:
            logger.error("Consumer error: %s: %s", type(exc).__name__, exc)
            logger.error(traceback.format_exc())
            await self._safe_send({
                'type': 'error',
                'content': f'{type(exc).__name__}: {str(exc)[:300]}',
            })

    # ------------------------------------------------------------------
    # Handler: chat
    # ------------------------------------------------------------------

    async def _handle_chat(self, data):
        """Process a chat message and stream the AI response."""
        message    = data.get('message', '').strip()
        session_id = data.get('session_id') or self.session_id

        # --- Validate message --------------------------------------------
        if not message:
            await self._safe_send({'type': 'error', 'content': 'Empty message.'})
            return

        if len(message) > MAX_MESSAGE_LENGTH:
            await self._safe_send({
                'type': 'error',
                'content': f'Message too long ({len(message)} chars). '
                           f'Maximum is {MAX_MESSAGE_LENGTH} characters.',
            })
            return

        # --- Create session if needed ------------------------------------
        if not session_id:
            session_id = await asyncio.to_thread(
                mongo_store.create_session, self.user.id,
            )
            self.session_id = session_id

        # --- Save user message -------------------------------------------
        await asyncio.to_thread(mongo_store.add_message, session_id, 'user', message)

        # --- Send "thinking" indicator ------------------------------------
        await self._safe_send({
            'type': 'status', 'content': 'thinking', 'session_id': session_id,
        })

        # --- Check Gemini key --------------------------------------------
        from django.conf import settings
        api_keys = [k for k in getattr(settings, 'GEMINI_API_KEYS', []) if k.strip()]
        if not api_keys:
            await self._safe_send({
                'type': 'error',
                'content': 'Gemini API key missing! Add GEMINI_API_KEY=your_key to your .env file',
            })
            return

        # --- Check cache -------------------------------------------------
        from .ai_engine import get_cached_response, set_cached_response
        cached = get_cached_response(message)
        if cached:
            await self._stream_cached_response(cached, session_id)
            return

        # --- Resolve mongo_user_id for chat-limit checks -----------------
        mongo_user = await asyncio.to_thread(
            mongo_store.get_user_by_username, self.user.username,
        )
        mongo_user_id = mongo_user['id'] if mongo_user else None

        # --- Stream AI response using async generator --------------------
        try:
            await self._safe_send({'type': 'stream_start', 'content': ''})

            full_response = ""
            async for token in async_stream_response(
                user_id=self.user.id,
                session_id=session_id,
                message=message,
                mongo_user_id=mongo_user_id,
            ):
                # Handle daily-limit sentinel from ai_engine
                if token == "Daily chat limit reached. Please try again tomorrow.":
                    # Send remaining = 0 so the UI can update the live counter
                    await self._safe_send({
                        'type': 'limit_reached',
                        'content': token,
                        'remaining': 0,
                        'daily_limit': 50,
                    })
                    return

                full_response += token
                await self._safe_send({'type': 'stream', 'content': token})

            await self._safe_send({'type': 'stream_end', 'content': ''})

            # Cache and persist
            set_cached_response(message, full_response)
            await asyncio.to_thread(
                mongo_store.add_message, session_id, 'assistant', full_response,
            )

            # Send updated chat stats so the UI counter refreshes live
            await self._send_chat_stats()

            # Auto-title new sessions
            await self._auto_title_session(session_id, full_response)

        except RuntimeError as exc:
            if "All Gemini API keys are temporarily exhausted" in str(exc):
                await self._safe_send({
                    'type': 'error',
                    'content': 'All AI services are temporarily busy. '
                               'Please wait about 60 seconds and try again.',
                })
            else:
                raise
        except Exception as exc:
            err_type = type(exc).__name__
            err_msg  = str(exc)
            logger.error("AI error [%s]: %s", err_type, err_msg)
            logger.error(traceback.format_exc())

            if 'API_KEY' in err_msg.upper() or 'INVALID' in err_msg.upper():
                hint = 'Invalid Gemini API key. Get one free at https://aistudio.google.com'
            elif 'QUOTA' in err_msg.upper() or 'RESOURCE_EXHAUSTED' in err_msg.upper():
                hint = 'Gemini rate limit hit. Wait 60 seconds and try again.'
            elif 'not set' in err_msg:
                hint = err_msg
            else:
                hint = f'{err_type}: {err_msg[:300]}'

            await self._safe_send({'type': 'error', 'content': hint})

    # ------------------------------------------------------------------
    # Handler: rename_session
    # ------------------------------------------------------------------

    async def _handle_rename_session(self, data):
        """Rename a chat session."""
        session_id = data.get('session_id')
        title      = data.get('title', '').strip()

        if not session_id:
            await self._safe_send({'type': 'error', 'content': 'Session ID required for rename.'})
            return
        if not title:
            await self._safe_send({'type': 'error', 'content': 'Title required for rename.'})
            return

        try:
            await asyncio.to_thread(mongo_store.update_session_title, session_id, title)
            await self._safe_send({
                'type': 'rename_success',
                'content': 'Session renamed successfully.',
                'session_id': session_id,
                'title': title,
            })
        except Exception as exc:
            logger.error("Failed to rename session %s: %s", session_id, exc)
            await self._safe_send({'type': 'error', 'content': 'Failed to rename session.'})

    # ------------------------------------------------------------------
    # Handler: delete_message
    # ------------------------------------------------------------------

    async def _handle_delete_message(self, data):
        """Delete a single message."""
        message_id = data.get('message_id')

        if not message_id:
            await self._safe_send({'type': 'error', 'content': 'Message ID required for deletion.'})
            return

        try:
            success = await asyncio.to_thread(mongo_store.delete_message, message_id)
            if success:
                await self._safe_send({
                    'type': 'delete_message_success',
                    'content': 'Message deleted successfully.',
                    'message_id': message_id,
                })
            else:
                await self._safe_send({'type': 'error', 'content': 'Message not found or already deleted.'})
        except Exception as exc:
            logger.error("Failed to delete message %s: %s", message_id, exc)
            await self._safe_send({'type': 'error', 'content': 'Failed to delete message.'})

    # ------------------------------------------------------------------
    # Handler: delete_session
    # ------------------------------------------------------------------

    async def _handle_delete_session(self, data):
        """Delete an entire chat session."""
        session_id = data.get('session_id')

        if not session_id:
            await self._safe_send({'type': 'error', 'content': 'Session ID required for deletion.'})
            return

        try:
            success = await asyncio.to_thread(
                mongo_store.delete_session, session_id, self.user.id,
            )
            if success:
                await self._safe_send({
                    'type': 'delete_session_success',
                    'content': 'Session deleted successfully.',
                    'session_id': session_id,
                })
            else:
                await self._safe_send({'type': 'error', 'content': 'Session not found or access denied.'})
        except Exception as exc:
            logger.error("Failed to delete session %s: %s", session_id, exc)
            await self._safe_send({'type': 'error', 'content': 'Failed to delete session.'})

    # ------------------------------------------------------------------
    # Streaming helpers
    # ------------------------------------------------------------------

    async def _stream_cached_response(self, response: str, session_id: str):
        """Stream a *cached* response to the client token-by-token, then persist."""
        await self._safe_send({'type': 'stream_start', 'content': ''})

        chunk_size = 4
        for i in range(0, len(response), chunk_size):
            await self._safe_send({'type': 'stream', 'content': response[i:i + chunk_size]})
            await asyncio.sleep(0.01)

        await self._safe_send({'type': 'stream_end', 'content': ''})

        # Persist assistant message
        await asyncio.to_thread(mongo_store.add_message, session_id, 'assistant', response)

        # Send updated chat stats
        await self._send_chat_stats()

        # Auto-title new sessions
        await self._auto_title_session(session_id, response)

    async def _auto_title_session(self, session_id: str, response: str):
        """Auto-title new sessions based on response content."""
        try:
            session = await asyncio.to_thread(
                mongo_store.get_session, session_id, self.user.id,
            )
            if session and session.get('title') == 'New Chat':
                title = response[:50].strip() + ('...' if len(response) > 50 else '')
                await asyncio.to_thread(mongo_store.update_session_title, session_id, title)
        except Exception as exc:
            logger.error("Failed to update session title: %s", exc)

    async def _send_chat_stats(self):
        """Push current chat-limit stats to the client for live UI updates."""
        try:
            mongo_user = await asyncio.to_thread(
                mongo_store.get_user_by_username, self.user.username,
            )
            if mongo_user:
                stats = await asyncio.to_thread(
                    mongo_store.get_user_chat_stats, mongo_user['id'],
                )
                if stats:
                    await self._safe_send({
                        'type': 'chat_stats',
                        'daily_count': stats['daily_count'],
                        'daily_limit': stats['daily_limit'],
                        'total_chats': stats['total_chats'],
                    })
        except Exception as exc:
            logger.warning("Failed to send chat stats: %s", exc)

    # ------------------------------------------------------------------
    # Safe send — gracefully handles disconnected clients
    # ------------------------------------------------------------------

    async def _safe_send(self, payload: dict) -> bool:
        """Serialize *payload* to JSON and send it over the WebSocket.

        Returns ``True`` on success, ``False`` if the client has already
        disconnected or the send fails for any other reason.
        """
        try:
            await self.send(text_data=json.dumps(payload))
            return True
        except Exception as exc:
            logger.warning(
                "WS send failed (user=%s): %s",
                getattr(self.user, 'username', 'unknown') if hasattr(self, 'user') else 'unknown',
                exc,
            )
            return False