from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from .channels import Channel
from .bridge import Bridge
from .playback import Playback
from .recording import LiveRecording
from datetime import datetime
from enum import Enum
import re


class EventType(str, Enum):
    # Stasis
    STASIS_START = "StasisStart"
    STASIS_END = "StasisEnd"

    # Bridge
    BRIDGE_ATTENDED_TRANSFER = "BridgeAttendedTransfer"
    BRIDGE_BLIND_TRANSFER = "BridgeBlindTransfer"
    BRIDGE_CREATED = "BridgeCreated"
    BRIDGE_DESTROYED = "BridgeDestroyed"
    BRIDGE_MERGED = "BridgeMerged"
    BRIDGE_VIDEO_SOURCE_CHANGED = "BridgeVideoSourceChanged"

    # Channel
    CHANNEL_CALLER_ID = "ChannelCallerId"
    CHANNEL_CONNECTED_LINE = "ChannelConnectedLine"
    CHANNEL_CREATED = "ChannelCreated"
    CHANNEL_DESTROYED = "ChannelDestroyed"
    CHANNEL_DIALPLAN = "ChannelDialplan"
    CHANNEL_DTMF_RECEIVED = "ChannelDtmfReceived"
    CHANNEL_ENTERED_BRIDGE = "ChannelEnteredBridge"
    CHANNEL_HANGUP_REQUEST = "ChannelHangupRequest"
    CHANNEL_HOLD = "ChannelHold"
    CHANNEL_LEFT_BRIDGE = "ChannelLeftBridge"
    CHANNEL_STATE_CHANGE = "ChannelStateChange"
    CHANNEL_TALKING_FINISHED = "ChannelTalkingFinished"
    CHANNEL_TALKING_STARTED = "ChannelTalkingStarted"
    CHANNEL_TONE_DETECTED = "ChannelToneDetected"
    CHANNEL_UNHOLD = "ChannelUnhold"
    CHANNEL_USEREVENT = "ChannelUserevent"
    CHANNEL_VARSET = "ChannelVarset"

    # Dial
    DIAL = "Dial"

    # Playback
    PLAYBACK_CONTINUING = "PlaybackContinuing"
    PLAYBACK_FINISHED = "PlaybackFinished"
    PLAYBACK_STARTED = "PlaybackStarted"

    # Recording
    RECORDING_FAILED = "RecordingFailed"
    RECORDING_FINISHED = "RecordingFinished"
    RECORDING_STARTED = "RecordingStarted"


def _parse_ari_timestamp(v: str | datetime | None) -> datetime | None:
    """Normalize ARI timestamp strings (timezone offset without colon) to datetime."""
    if v is None:
        return v
    if isinstance(v, str):
        v = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', v)
        return datetime.fromisoformat(v)
    return v


class Event(BaseModel):
    """Base event -- used for initial type detection and as parent for all events."""
    type: EventType | str = Field(..., description="The type of the event")
    timestamp: Optional[str | datetime] = Field(default=None)
    application: str = Field(default="")
    asterisk_id: str = Field(default="")

    @field_validator("timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, v: str | datetime | None) -> datetime | None:
        return _parse_ari_timestamp(v)


# ---------------------------------------------------------------------------
# Stasis events
# ---------------------------------------------------------------------------

class StasisStartEvent(Event):
    type: EventType = Field(default=EventType.STASIS_START)
    timestamp: str | datetime
    args: List[str] = Field(default_factory=list)
    channel: Channel


class StasisEndEvent(Event):
    type: EventType = Field(default=EventType.STASIS_END)
    timestamp: str | datetime
    channel: Channel


# ---------------------------------------------------------------------------
# Bridge events
# ---------------------------------------------------------------------------

class BridgeAttendedTransferEvent(Event):
    type: EventType = Field(default=EventType.BRIDGE_ATTENDED_TRANSFER)
    timestamp: str | datetime
    result: str = Field(..., description="Result of the transfer (e.g. success, fail)")
    transferer_first_leg: Channel
    transferer_second_leg: Channel
    replace_channel: Optional[Channel] = None
    transferee: Optional[Channel] = None
    transfer_target: Optional[Channel] = None
    transferer_first_leg_bridge: Optional[Bridge] = None
    transferer_second_leg_bridge: Optional[Bridge] = None
    destination_type: str = Field(..., description="How the transfer was accomplished (bridge, app, link, threeway)")
    destination_bridge: Optional[str] = None
    destination_application: Optional[str] = None
    destination_link_first_leg: Optional[Channel] = None
    destination_link_second_leg: Optional[Channel] = None
    destination_threeway_channel: Optional[Channel] = None
    destination_threeway_bridge: Optional[Bridge] = None
    is_external: bool = Field(..., description="Whether the transfer was external")


class BridgeBlindTransferEvent(Event):
    type: EventType = Field(default=EventType.BRIDGE_BLIND_TRANSFER)
    timestamp: str | datetime
    channel: Channel
    replace_channel: Optional[Channel] = None
    transferee: Optional[Channel] = None
    exten: str = Field(..., description="Extension transferred to")
    context: str = Field(..., description="Context transferred to")
    result: str = Field(..., description="Result of the transfer (e.g. success, fail)")
    is_external: bool = Field(..., description="Whether the transfer was external")
    bridge: Optional[Bridge] = None


class BridgeCreatedEvent(Event):
    type: EventType = Field(default=EventType.BRIDGE_CREATED)
    timestamp: str | datetime
    bridge: Bridge


class BridgeDestroyedEvent(Event):
    type: EventType = Field(default=EventType.BRIDGE_DESTROYED)
    timestamp: str | datetime
    bridge: Bridge


class BridgeMergedEvent(Event):
    type: EventType = Field(default=EventType.BRIDGE_MERGED)
    timestamp: str | datetime
    bridge: Bridge = Field(..., description="The resulting merged bridge")
    bridge_from: Bridge = Field(..., description="The bridge that was merged into the other")


class BridgeVideoSourceChangedEvent(Event):
    type: EventType = Field(default=EventType.BRIDGE_VIDEO_SOURCE_CHANGED)
    timestamp: str | datetime
    bridge: Bridge
    old_video_source_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Channel events
# ---------------------------------------------------------------------------

class ChannelCallerIdEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_CALLER_ID)
    timestamp: str | datetime
    caller_presentation: int = Field(..., description="The integer representation of the Caller Presentation value")
    caller_presentation_txt: str = Field(..., description="The text representation of the Caller Presentation value")
    channel: Channel


class ChannelConnectedLineEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_CONNECTED_LINE)
    timestamp: str | datetime
    channel: Channel


class ChannelCreatedEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_CREATED)
    timestamp: str | datetime
    channel: Channel


class ChannelDestroyedEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_DESTROYED)
    timestamp: str | datetime
    cause: int = Field(..., description="Integer representation of the cause of the hangup")
    cause_txt: str = Field(..., description="Text representation of the cause of the hangup")
    channel: Channel


class ChannelDialplanEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_DIALPLAN)
    timestamp: str | datetime
    channel: Channel
    dialplan_app: str = Field(..., description="The application about to be executed")
    dialplan_app_data: str = Field(..., description="The data to be passed to the application")


class ChannelDtmfReceivedEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_DTMF_RECEIVED)
    timestamp: str | datetime
    digit: str = Field(..., description="DTMF digit received (0-9, A-D, *, #)")
    duration_ms: int = Field(..., description="Number of milliseconds DTMF was received")
    channel: Channel


class ChannelEnteredBridgeEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_ENTERED_BRIDGE)
    timestamp: str | datetime
    bridge: Bridge
    channel: Channel


class ChannelHangupRequestEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_HANGUP_REQUEST)
    timestamp: str | datetime
    cause: Optional[int] = Field(default=None, description="Integer representation of the hangup cause")
    soft: Optional[bool] = Field(default=None, description="Whether the hangup request was a soft hangup request")
    channel: Channel


class ChannelHoldEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_HOLD)
    timestamp: str | datetime
    channel: Channel
    musicclass: Optional[str] = Field(default=None, description="The music on hold class that the initiator requested")


class ChannelLeftBridgeEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_LEFT_BRIDGE)
    timestamp: str | datetime
    bridge: Bridge
    channel: Channel


class ChannelStateChangeEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_STATE_CHANGE)
    timestamp: str | datetime
    channel: Channel


class ChannelTalkingFinishedEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_TALKING_FINISHED)
    timestamp: str | datetime
    channel: Channel
    duration: int = Field(..., description="The length of time, in milliseconds, that talking was detected on the channel")


class ChannelTalkingStartedEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_TALKING_STARTED)
    timestamp: str | datetime
    channel: Channel


class ChannelToneDetectedEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_TONE_DETECTED)
    timestamp: str | datetime
    channel: Channel


class ChannelUnholdEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_UNHOLD)
    timestamp: str | datetime
    channel: Channel


class ChannelUsereventEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_USEREVENT)
    timestamp: str | datetime
    eventname: str = Field(..., description="The name of the user event")
    userevent: Dict[str, Any] = Field(default_factory=dict, description="Custom data sent with the user event")
    channel: Optional[Channel] = None
    bridge: Optional[Bridge] = None


class ChannelVarsetEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_VARSET)
    timestamp: str | datetime
    variable: str = Field(..., description="The variable that changed")
    value: str = Field(..., description="The new value of the variable")
    channel: Optional[Channel] = Field(default=None, description="The channel on which the variable was set (None for global)")


# ---------------------------------------------------------------------------
# Dial event
# ---------------------------------------------------------------------------

class DialEvent(Event):
    type: EventType = Field(default=EventType.DIAL)
    timestamp: str | datetime
    caller: Optional[Channel] = Field(default=None, description="The calling channel")
    peer: Channel = Field(..., description="The dialed channel")
    forward: Optional[str] = Field(default=None, description="Forwarding target requested by the original dialed channel")
    forwarded: Optional[Channel] = Field(default=None, description="Channel that the caller has been forwarded to")
    dialstring: Optional[str] = Field(default=None, description="The dial string for calling the peer channel")
    dialstatus: str = Field(..., description="Current status of the dial attempt")
    resultcode: Optional[str] = Field(default=None, description="The result code of the dial operation")


# ---------------------------------------------------------------------------
# Playback events
# ---------------------------------------------------------------------------

class PlaybackContinuingEvent(Event):
    type: EventType = Field(default=EventType.PLAYBACK_CONTINUING)
    timestamp: str | datetime
    playback: Playback


class PlaybackFinishedEvent(Event):
    type: EventType = Field(default=EventType.PLAYBACK_FINISHED)
    timestamp: str | datetime
    playback: Playback


class PlaybackStartedEvent(Event):
    type: EventType = Field(default=EventType.PLAYBACK_STARTED)
    timestamp: str | datetime
    playback: Playback


# ---------------------------------------------------------------------------
# Recording events
# ---------------------------------------------------------------------------

class RecordingFailedEvent(Event):
    type: EventType = Field(default=EventType.RECORDING_FAILED)
    timestamp: str | datetime
    recording: LiveRecording


class RecordingFinishedEvent(Event):
    type: EventType = Field(default=EventType.RECORDING_FINISHED)
    timestamp: str | datetime
    recording: LiveRecording


class RecordingStartedEvent(Event):
    type: EventType = Field(default=EventType.RECORDING_STARTED)
    timestamp: str | datetime
    recording: LiveRecording


# ---------------------------------------------------------------------------
# Mapping from event type string -> model class (used by dispatcher)
# ---------------------------------------------------------------------------

EVENT_MODEL_MAP: dict[str, type[Event]] = {
    EventType.STASIS_START.value: StasisStartEvent,
    EventType.STASIS_END.value: StasisEndEvent,

    EventType.BRIDGE_ATTENDED_TRANSFER.value: BridgeAttendedTransferEvent,
    EventType.BRIDGE_BLIND_TRANSFER.value: BridgeBlindTransferEvent,
    EventType.BRIDGE_CREATED.value: BridgeCreatedEvent,
    EventType.BRIDGE_DESTROYED.value: BridgeDestroyedEvent,
    EventType.BRIDGE_MERGED.value: BridgeMergedEvent,
    EventType.BRIDGE_VIDEO_SOURCE_CHANGED.value: BridgeVideoSourceChangedEvent,

    EventType.CHANNEL_CALLER_ID.value: ChannelCallerIdEvent,
    EventType.CHANNEL_CONNECTED_LINE.value: ChannelConnectedLineEvent,
    EventType.CHANNEL_CREATED.value: ChannelCreatedEvent,
    EventType.CHANNEL_DESTROYED.value: ChannelDestroyedEvent,
    EventType.CHANNEL_DIALPLAN.value: ChannelDialplanEvent,
    EventType.CHANNEL_DTMF_RECEIVED.value: ChannelDtmfReceivedEvent,
    EventType.CHANNEL_ENTERED_BRIDGE.value: ChannelEnteredBridgeEvent,
    EventType.CHANNEL_HANGUP_REQUEST.value: ChannelHangupRequestEvent,
    EventType.CHANNEL_HOLD.value: ChannelHoldEvent,
    EventType.CHANNEL_LEFT_BRIDGE.value: ChannelLeftBridgeEvent,
    EventType.CHANNEL_STATE_CHANGE.value: ChannelStateChangeEvent,
    EventType.CHANNEL_TALKING_FINISHED.value: ChannelTalkingFinishedEvent,
    EventType.CHANNEL_TALKING_STARTED.value: ChannelTalkingStartedEvent,
    EventType.CHANNEL_TONE_DETECTED.value: ChannelToneDetectedEvent,
    EventType.CHANNEL_UNHOLD.value: ChannelUnholdEvent,
    EventType.CHANNEL_USEREVENT.value: ChannelUsereventEvent,
    EventType.CHANNEL_VARSET.value: ChannelVarsetEvent,

    EventType.DIAL.value: DialEvent,

    EventType.PLAYBACK_CONTINUING.value: PlaybackContinuingEvent,
    EventType.PLAYBACK_FINISHED.value: PlaybackFinishedEvent,
    EventType.PLAYBACK_STARTED.value: PlaybackStartedEvent,

    EventType.RECORDING_FAILED.value: RecordingFailedEvent,
    EventType.RECORDING_FINISHED.value: RecordingFinishedEvent,
    EventType.RECORDING_STARTED.value: RecordingStartedEvent,
}
