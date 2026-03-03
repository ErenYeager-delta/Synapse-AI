"""WebSocket consumer — streams AI responses token-by-token."""
import json, asyncio, logging, traceback
from channels.generic.websocket import AsyncWebsocketConsumer
from .mongo_store import mongo_store

logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        self.user = self.scope.get('user')
        if not self.user or self.user.is_anonymous:
            await self.close()
            return
        self.session_id = self.scope['url_route']['kwargs'].get('session_id')
        await self.accept()
        logger.info(f"WS connected: {self.user.username}")

    async def disconnect(self, close_code):
        logger.info(f"WS disconnected: {close_code}")

    async def receive(self, text_data):
        try:
            data       = json.loads(text_data)
            message    = data.get('message', '').strip()
            session_id = data.get('session_id')

            if not message:
                await self.send(text_data=json.dumps({'type': 'error', 'content': 'Empty message.'}))
                return

            # Create session if needed
            if not session_id:
                session_id = await asyncio.to_thread(mongo_store.create_session, self.user.username)

            # Save user message
            await asyncio.to_thread(mongo_store.add_message, session_id, 'user', message)

            # Send "thinking" indicator
            await self.send(text_data=json.dumps({
                'type': 'status', 'content': 'thinking', 'session_id': session_id
            }))

            # Thinking is sent, let ai_engine handle the rest
            from .ai_engine import get_cached_response, set_cached_response, get_or_create_agent
            
            # Check cache
            cached = get_cached_response(message)
            if cached:
                await self._stream_response(cached, session_id)
                return

            # Run AI — centralized rotation in ai_engine handles keys
            try:
                agent    = get_or_create_agent(self.user.username, session_id)
                response = await asyncio.to_thread(agent.run, message)
            except Exception as e:
                err_msg = str(e)
                logger.error(f"AI error: {err_msg}")
                # Show the actual error to the user to help them debug their keys
                await self.send(text_data=json.dumps({
                    'type': 'error', 
                    'content': f"AI Error: {err_msg}"
                }))
                return

            set_cached_response(message, response)
            await self._stream_response(response, session_id)

            # --- Professional AI Title Automation ---
            session = await asyncio.to_thread(mongo_store.get_session, session_id, self.user.username)
            if session and session.get('title') == 'New Chat':
                from .ai_engine import generate_title
                # Generate a smart title based on user intent
                title = await asyncio.to_thread(generate_title, message, response)
                await asyncio.to_thread(mongo_store.update_session_title, session_id, title)
                # Notify frontend to update sidebar
                await self.send(text_data=json.dumps({
                    'type': 'title_update', 
                    'session_id': session_id,
                    'title': title
                }))

        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'type': 'error', 'content': 'Invalid message format.'}))
        except Exception as e:
            logger.error(f"Consumer error: {type(e).__name__}: {e}")
            logger.error(traceback.format_exc())
            await self.send(text_data=json.dumps({
                'type': 'error',
                'content': f'{type(e).__name__}: {str(e)[:300]}'
            }))

    async def _stream_response(self, response: str, session_id: str):
        await self.send(text_data=json.dumps({'type': 'stream_start', 'content': ''}))
        chunk_size = 4
        for i in range(0, len(response), chunk_size):
            await self.send(text_data=json.dumps({'type': 'stream', 'content': response[i:i+chunk_size]}))
            await asyncio.sleep(0.01)
        await self.send(text_data=json.dumps({'type': 'stream_end', 'content': ''}))

        await asyncio.to_thread(mongo_store.add_message, session_id, 'assistant', response)
