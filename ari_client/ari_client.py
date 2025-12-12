import asyncio
import websockets
from .models.events import Event, EventType
from .models.events import StasisStartEvent, StasisEndEvent
from .controller import AriClientController
import logging
from typing import Callable, Awaitable, Optional, Type
from httpx import AsyncClient
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

    
class AriClient:
    def __init__(self, host: str, port: int, ari_user: str, ari_password: str, tls_enabled: bool = False):
        self.host = host
        self.port = port
        self.ari_user = ari_user
        self.ari_password = ari_password
        self.tls_enabled = tls_enabled

        # internal variables
        self.controller = None
        self.app = None
        self.ws = None
        self.event_listener = None

        # event handlers
        self.stasis_start_handler = None
        self.stasis_end_handler = None
    
    
    @property
    def ari(self) -> AriClientController:
        if self.controller is None:
            raise ValueError("Not connected to Asterisk")
        return self.controller
    
    async def connect(self, app: str, subscribe_to_all: bool = False):
        self.app = app
        self.controller = AriClientController(
            AsyncClient(
                base_url=f"{'https' if self.tls_enabled else 'http'}://{self.host}:{self.port}/ari",
                auth=(self.ari_user, self.ari_password),
                timeout=10
            ),
            app
        )
        
        url = f"{'wss' if self.tls_enabled else 'ws'}://{self.host}:{self.port}/ari/events?api_key={self.ari_user}:{self.ari_password}&app={self.app}&subscribeAll={str(subscribe_to_all).lower()}"
        self.ws = await websockets.connect(url)
        self.event_listener = asyncio.create_task(self.__listen_events())

    
    async def __dispatch(self, message: str,  event_schema: Type[Event], handler: Callable[[BaseModel], Awaitable[None]]) -> Type[Event]:
        event = event_schema.model_validate_json(message)
        if handler:
            task = asyncio.create_task(handler(event))
            task.add_done_callback(self._handle_task_exception)
        return event
    
    async def __listen_events(self):
        try:
            while True:
                try:
                    message = await self.ws.recv()
                    event = Event.model_validate_json(message)
                    if event.type == EventType.STASIS_START:
                        stasis_start_event: StasisStartEvent = await self.__dispatch(message, StasisStartEvent, self.stasis_start_handler)
                        if self.controller:
                            stasis_start_event.channel.add_handlers(
                                answer_handler=self.controller.answer_channel,
                                stop_handler=self.controller.stop_channel,
                                dial_handler=self.controller.dial
                            )
                    elif event.type == EventType.STASIS_END:
                        stasis_end_event: StasisEndEvent = await self.__dispatch(message, StasisEndEvent, self.stasis_end_handler)
                        if self.controller:
                            stasis_end_event.channel.add_handlers(
                                answer_handler=self.controller.answer_channel,
                                stop_handler=self.controller.stop_channel,
                                dial_handler=self.controller.dial
                            )
                    else:
                        logger.debug(f"Received unknown event: {event}")
                except Exception as e:
                    # Log but continue processing events
                    logger.error(f"Error processing event: {e}", exc_info=True)
                    continue
        except websockets.exceptions.WebSocketException as e:
            logger.error(f"WebSocket exception: {e}")
            raise e
        except asyncio.CancelledError:
            logger.info("Event listener cancelled")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in event listener: {e}", exc_info=True)
            raise e
    
    def _handle_task_exception(self, task: asyncio.Task):
        """Handle exceptions in event handler tasks"""
        try:
            task.result()  # This will raise if the task had an exception
        except Exception as e:
            logger.error(f"Error in event handler: {e}", exc_info=True)
    
    def on_stasis_start(self, handler: Optional[Callable[[StasisStartEvent], Awaitable[None]]] = None):
        """
        Register an async handler for StasisStart events.
        Can be used as a decorator: @client.on_stasis_start
        Or as a method call: client.on_stasis_start(handler)
        
        The handler will be called when a StasisStart event is received.
        The handler will be passed the StasisStartEvent object.
        """
        def decorator(func: Callable[[StasisStartEvent], Awaitable[None]]):
            self.stasis_start_handler = func
            return func
        
        if handler is None:
            # Called as @client.on_stasis_start
            return decorator
        else:
            # Called as client.on_stasis_start(handler)
            self.stasis_start_handler = handler
            return handler
    
    def on_stasis_end(self, handler: Optional[Callable[[StasisEndEvent], Awaitable[None]]] = None):
        """
        Register an async handler for StasisEnd events.
        Can be used as a decorator: @client.on_stasis_end
        Or as a method call: client.on_stasis_end(handler)
        
        The handler will be called when a StasisEnd event is received.
        The handler will be passed the StasisEndEvent object.
        """
        def decorator(func: Callable[[StasisEndEvent], Awaitable[None]]):
            self.stasis_end_handler = func
            return func
        
        if handler is None:
            # Called as @client.on_stasis_end
            return decorator
        else:
            # Called as client.on_stasis_end(handler)
            self.stasis_end_handler = handler
            return handler
    
    async def disconnect(self):
        if self.event_listener:
            self.event_listener.cancel()
        await self.ws.close()

