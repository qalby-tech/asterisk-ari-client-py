from pydantic import BaseModel, Field, field_validator
from typing import List
from .channels import Channel
from datetime import datetime
from enum import Enum
import re


class EventType(str, Enum):
    STASIS_START = "StasisStart"
    STASIS_END = "StasisEnd"
    CHANNEL_DTMF_RECEIVED = "ChannelDtmfReceived"



class Event(BaseModel):
    type: EventType | str = Field(..., description="The type of the event")

class StasisStartEvent(Event):
    type: EventType = Field(default=EventType.STASIS_START, description="Event type")
    timestamp: str | datetime = Field(..., description="Event timestamp")
    args: List[str] = Field(default_factory=list, description="Event arguments")
    channel: "Channel" = Field(..., description="Channel information")
    asterisk_id: str = Field(..., description="Asterisk ID")
    application: str = Field(..., description="Application name")

    @field_validator("timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, v: str | datetime) -> datetime:
        if isinstance(v, str):
            # Handle timezone offset without colon (e.g., +0300 -> +03:00)
            # Match timezone offset pattern like +0300 or -0500
            v = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', v)
            return datetime.fromisoformat(v)
        return v


class StasisEndEvent(Event):
    type: EventType = Field(default=EventType.STASIS_END, description="Event type")
    timestamp: str | datetime = Field(..., description="Event timestamp")
    channel: "Channel" = Field(..., description="Channel information")
    application: str = Field(..., description="Application name")

    @field_validator("timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, v: str | datetime) -> datetime:
        if isinstance(v, str):
            # Handle timezone offset without colon (e.g., +0300 -> +03:00)
            # Match timezone offset pattern like +0300 or -0500
            v = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', v)
            return datetime.fromisoformat(v)
        return v


class ChannelDtmfReceivedEvent(Event):
    type: EventType = Field(default=EventType.CHANNEL_DTMF_RECEIVED, description="Event type")
    timestamp: str | datetime = Field(..., description="Event timestamp")
    digit: str = Field(..., description="DTMF digit received (0-9, A-D, *, #)")
    duration_ms: int = Field(..., description="Number of milliseconds DTMF was received")
    channel: "Channel" = Field(..., description="The channel on which DTMF was received")
    asterisk_id: str = Field(default="", description="Asterisk ID")
    application: str = Field(default="", description="Application name")

    @field_validator("timestamp", mode="after")
    @classmethod
    def validate_timestamp(cls, v: str | datetime) -> datetime:
        if isinstance(v, str):
            v = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', v)
            return datetime.fromisoformat(v)
        return v
