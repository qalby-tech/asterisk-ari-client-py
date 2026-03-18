import asyncio
import websockets
from .models.events import (
    Event, EventType, EVENT_MODEL_MAP,
    StasisStartEvent, StasisEndEvent,
    BridgeAttendedTransferEvent, BridgeBlindTransferEvent,
    BridgeCreatedEvent, BridgeDestroyedEvent, BridgeMergedEvent,
    BridgeVideoSourceChangedEvent,
    ChannelCallerIdEvent, ChannelConnectedLineEvent,
    ChannelCreatedEvent, ChannelDestroyedEvent, ChannelDialplanEvent,
    ChannelDtmfReceivedEvent, ChannelEnteredBridgeEvent,
    ChannelHangupRequestEvent, ChannelHoldEvent, ChannelLeftBridgeEvent,
    ChannelStateChangeEvent, ChannelTalkingFinishedEvent,
    ChannelTalkingStartedEvent, ChannelToneDetectedEvent,
    ChannelUnholdEvent, ChannelUsereventEvent, ChannelVarsetEvent,
    DialEvent,
    PlaybackContinuingEvent, PlaybackFinishedEvent, PlaybackStartedEvent,
    RecordingFailedEvent, RecordingFinishedEvent, RecordingStartedEvent,
)
from .models.channels import Channel
from .models.bridge import Bridge
from .models.playback import Playback
from .models.recording import LiveRecording
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
        self.controller: Optional[AriClientController] = None
        self.app: Optional[str] = None
        self.ws = None
        self.event_listener = None

        # event handlers keyed by event type string (e.g. "StasisStart")
        self._event_handlers: dict[str, Callable[..., Awaitable[None]]] = {}
    
    
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

    # ------------------------------------------------------------------
    # Internal dispatch machinery
    # ------------------------------------------------------------------

    def _add_channel_handlers(self, channel: Channel) -> None:
        """Add controller handlers to a channel."""
        if self.controller:
            channel.add_handlers(
                answer_handler=self.controller.answer_channel,
                stop_handler=self.controller.stop_channel,
                dial_handler=self.controller.dial,
                record_handler=self.controller.record_channel,
                snoop_handler=self.controller.snoop_channel,
                send_dtmf_handler=self.controller.send_dtmf,
                redirect_handler=self.controller.redirect_channel,
                move_handler=self.controller.move_channel,
                play_handler=self.controller.play_channel,
            )

    def _add_bridge_handlers(self, bridge: Bridge) -> None:
        """Add controller handlers to a bridge."""
        if self.controller:
            bridge.add_handlers(
                stop_handler=self.controller.stop_bridge,
                add_channel_handler=self.controller.bridge_add_channel,
                record_handler=self.controller.record_bridge,
                play_handler=self.controller.play_bridge,
            )

    def _add_playback_handlers(self, playback: Playback) -> None:
        """Add controller handlers to a playback."""
        if self.controller:
            playback.add_handlers(
                stop_handler=self.controller.stop_playback,
                control_handler=self.controller.control_playback,
            )

    def _add_recording_handlers(self, recording: LiveRecording) -> None:
        """Add controller handlers to a recording."""
        if self.controller:
            recording.add_handlers(
                stop_handler=self.controller.stop_recording,
                download_handler=self.controller.download_recording,
            )

    def _enrich_event(self, event: Event) -> None:
        """Walk event fields and inject controller handlers into model instances."""
        if not self.controller:
            return
        for field_name in event.model_fields:
            value = getattr(event, field_name, None)
            if value is None:
                continue
            if isinstance(value, Channel):
                self._add_channel_handlers(value)
            elif isinstance(value, Bridge):
                self._add_bridge_handlers(value)
            elif isinstance(value, Playback):
                self._add_playback_handlers(value)
            elif isinstance(value, LiveRecording):
                self._add_recording_handlers(value)

    async def __listen_events(self):
        try:
            while True:
                try:
                    message = await self.ws.recv()
                    event = Event.model_validate_json(message)
                    event_type_str = event.type if isinstance(event.type, str) else event.type.value

                    handler = self._event_handlers.get(event_type_str)
                    model_class = EVENT_MODEL_MAP.get(event_type_str)

                    if handler and model_class:
                        parsed = model_class.model_validate_json(message)
                        self._enrich_event(parsed)
                        task = asyncio.create_task(handler(parsed))
                        task.add_done_callback(self._handle_task_exception)
                    elif handler:
                        task = asyncio.create_task(handler(event))
                        task.add_done_callback(self._handle_task_exception)
                    elif model_class is None:
                        logger.debug(f"Received unknown event type: {event_type_str}")
                except Exception as e:
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
            task.result()
        except Exception as e:
            logger.error(f"Error in event handler: {e}", exc_info=True)

    # ------------------------------------------------------------------
    # Generic handler registration
    # ------------------------------------------------------------------

    def on_event(self, event_type: str | EventType):
        """
        Register a handler for any event type.

        Can be used as a decorator::

            @client.on_event(EventType.CHANNEL_CREATED)
            async def handle(event: ChannelCreatedEvent):
                ...

        Or as a method call::

            client.on_event(EventType.CHANNEL_CREATED)(handler)
        """
        key = event_type.value if isinstance(event_type, EventType) else event_type
        def decorator(func: Callable[..., Awaitable[None]]):
            self._event_handlers[key] = func
            return func
        return decorator

    # ------------------------------------------------------------------
    # Convenience handler registration (typed decorators)
    # ------------------------------------------------------------------

    def _register_handler(self, event_type_str: str, handler: Optional[Callable] = None):
        """Internal helper used by all on_* convenience methods."""
        def decorator(func: Callable[..., Awaitable[None]]):
            self._event_handlers[event_type_str] = func
            return func
        if handler is None:
            return decorator
        self._event_handlers[event_type_str] = handler
        return handler

    # -- Stasis --

    def on_stasis_start(self, handler: Optional[Callable[[StasisStartEvent], Awaitable[None]]] = None):
        return self._register_handler("StasisStart", handler)

    def on_stasis_end(self, handler: Optional[Callable[[StasisEndEvent], Awaitable[None]]] = None):
        return self._register_handler("StasisEnd", handler)

    # -- Bridge --

    def on_bridge_attended_transfer(self, handler: Optional[Callable[[BridgeAttendedTransferEvent], Awaitable[None]]] = None):
        return self._register_handler("BridgeAttendedTransfer", handler)

    def on_bridge_blind_transfer(self, handler: Optional[Callable[[BridgeBlindTransferEvent], Awaitable[None]]] = None):
        return self._register_handler("BridgeBlindTransfer", handler)

    def on_bridge_created(self, handler: Optional[Callable[[BridgeCreatedEvent], Awaitable[None]]] = None):
        return self._register_handler("BridgeCreated", handler)

    def on_bridge_destroyed(self, handler: Optional[Callable[[BridgeDestroyedEvent], Awaitable[None]]] = None):
        return self._register_handler("BridgeDestroyed", handler)

    def on_bridge_merged(self, handler: Optional[Callable[[BridgeMergedEvent], Awaitable[None]]] = None):
        return self._register_handler("BridgeMerged", handler)

    def on_bridge_video_source_changed(self, handler: Optional[Callable[[BridgeVideoSourceChangedEvent], Awaitable[None]]] = None):
        return self._register_handler("BridgeVideoSourceChanged", handler)

    # -- Channel --

    def on_channel_caller_id(self, handler: Optional[Callable[[ChannelCallerIdEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelCallerId", handler)

    def on_channel_connected_line(self, handler: Optional[Callable[[ChannelConnectedLineEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelConnectedLine", handler)

    def on_channel_created(self, handler: Optional[Callable[[ChannelCreatedEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelCreated", handler)

    def on_channel_destroyed(self, handler: Optional[Callable[[ChannelDestroyedEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelDestroyed", handler)

    def on_channel_dialplan(self, handler: Optional[Callable[[ChannelDialplanEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelDialplan", handler)

    def on_channel_dtmf_received(self, handler: Optional[Callable[[ChannelDtmfReceivedEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelDtmfReceived", handler)

    def on_channel_entered_bridge(self, handler: Optional[Callable[[ChannelEnteredBridgeEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelEnteredBridge", handler)

    def on_channel_hangup_request(self, handler: Optional[Callable[[ChannelHangupRequestEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelHangupRequest", handler)

    def on_channel_hold(self, handler: Optional[Callable[[ChannelHoldEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelHold", handler)

    def on_channel_left_bridge(self, handler: Optional[Callable[[ChannelLeftBridgeEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelLeftBridge", handler)

    def on_channel_state_change(self, handler: Optional[Callable[[ChannelStateChangeEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelStateChange", handler)

    def on_channel_talking_finished(self, handler: Optional[Callable[[ChannelTalkingFinishedEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelTalkingFinished", handler)

    def on_channel_talking_started(self, handler: Optional[Callable[[ChannelTalkingStartedEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelTalkingStarted", handler)

    def on_channel_tone_detected(self, handler: Optional[Callable[[ChannelToneDetectedEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelToneDetected", handler)

    def on_channel_unhold(self, handler: Optional[Callable[[ChannelUnholdEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelUnhold", handler)

    def on_channel_userevent(self, handler: Optional[Callable[[ChannelUsereventEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelUserevent", handler)

    def on_channel_varset(self, handler: Optional[Callable[[ChannelVarsetEvent], Awaitable[None]]] = None):
        return self._register_handler("ChannelVarset", handler)

    # -- Dial --

    def on_dial(self, handler: Optional[Callable[[DialEvent], Awaitable[None]]] = None):
        return self._register_handler("Dial", handler)

    # -- Playback --

    def on_playback_continuing(self, handler: Optional[Callable[[PlaybackContinuingEvent], Awaitable[None]]] = None):
        return self._register_handler("PlaybackContinuing", handler)

    def on_playback_finished(self, handler: Optional[Callable[[PlaybackFinishedEvent], Awaitable[None]]] = None):
        return self._register_handler("PlaybackFinished", handler)

    def on_playback_started(self, handler: Optional[Callable[[PlaybackStartedEvent], Awaitable[None]]] = None):
        return self._register_handler("PlaybackStarted", handler)

    # -- Recording --

    def on_recording_failed(self, handler: Optional[Callable[[RecordingFailedEvent], Awaitable[None]]] = None):
        return self._register_handler("RecordingFailed", handler)

    def on_recording_finished(self, handler: Optional[Callable[[RecordingFinishedEvent], Awaitable[None]]] = None):
        return self._register_handler("RecordingFinished", handler)

    def on_recording_started(self, handler: Optional[Callable[[RecordingStartedEvent], Awaitable[None]]] = None):
        return self._register_handler("RecordingStarted", handler)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    
    async def disconnect(self):
        if self.event_listener:
            self.event_listener.cancel()
        await self.ws.close()
