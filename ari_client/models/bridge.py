from pydantic import BaseModel, Field, field_validator, PrivateAttr
from typing import List, Optional, Callable, Awaitable
from datetime import datetime
from enum import Enum
import re


class BridgeType(str, Enum):
    MIXING = "mixing"
    HOLDING = "holding"


class VideoMode(str, Enum):
    NONE = "none"
    TALKER = "talker"
    SFU = "sfu"
    SINGLE = "single"


class Bridge(BaseModel):
    id: str = Field(..., description="Unique identifier for this bridge")
    technology: str = Field(..., description="Name of the current bridging technology")
    bridge_type: BridgeType = Field(..., description="Type of bridge technology")
    bridge_class: str = Field(..., description="Bridging class")
    creator: str = Field(..., description="Entity that created the bridge")
    name: str = Field(..., description="Name the creator gave the bridge")
    channels: List[str] = Field(default_factory=list, description="Ids of channels participating in this bridge")
    video_mode: Optional[VideoMode] = Field(default=None, description="The video mode the bridge is using")
    video_source_id: Optional[str] = Field(default=None, description="The ID of the channel that is the source of video in this bridge, if one exists")
    creationtime: str | datetime = Field(..., description="Timestamp when bridge was created")

    __stop_handler: Optional[Callable[[str], Awaitable[None]]] = PrivateAttr(default=None)
    __add_channel_handler: Optional[Callable[[str, str], Awaitable[None]]] = PrivateAttr(default=None)

    @field_validator("creationtime", mode="after")
    @classmethod
    def validate_creationtime(cls, v: str | datetime) -> datetime:
        if isinstance(v, str):
            # Handle timezone offset without colon (e.g., +0300 -> +03:00)
            # Match timezone offset pattern like +0300 or -0500
            v = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', v)
            return datetime.fromisoformat(v)
        return v
    
    @classmethod
    def create_with_handlers(
        cls, 
        stop_handler: Callable[[str], Awaitable[None]],
        add_channel_handler: Callable[[str, str], Awaitable[None]],
        obj: dict
    ) -> "Bridge":
        bridge = cls.model_validate(obj)
        bridge.__stop_handler = stop_handler
        bridge.__add_channel_handler = add_channel_handler
        return bridge
    
    async def stop(self):
        if self.__stop_handler is None:
            raise ValueError("Stop handler not set")
        await self.__stop_handler(self.id)
    
    async def add_channel(self, channel_id: str):
        if self.__add_channel_handler is None:
            raise ValueError("Add channel handler not set")
        await self.__add_channel_handler(self.id, channel_id)

