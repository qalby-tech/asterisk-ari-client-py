from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, PrivateAttr
from typing import TYPE_CHECKING, List, Optional, Callable, Awaitable, Literal
from datetime import datetime
from enum import Enum
import re

if TYPE_CHECKING:
    from .recording import LiveRecording
    from .playback import Playback


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
    __record_handler: Optional[Callable[..., Awaitable["LiveRecording"]]] = PrivateAttr(default=None)
    __play_handler: Optional[Callable[..., Awaitable["Playback"]]] = PrivateAttr(default=None)

    @field_validator("creationtime", mode="after")
    @classmethod
    def validate_creationtime(cls, v: str | datetime) -> datetime:
        if isinstance(v, str):
            v = re.sub(r'([+-])(\d{2})(\d{2})$', r'\1\2:\3', v)
            return datetime.fromisoformat(v)
        return v
    
    @classmethod
    def create_with_handlers(
        cls, 
        stop_handler: Callable[[str], Awaitable[None]],
        add_channel_handler: Callable[[str, str], Awaitable[None]],
        record_handler: Callable[..., Awaitable["LiveRecording"]],
        play_handler: Callable[..., Awaitable["Playback"]],
        obj: dict
    ) -> "Bridge":
        bridge = cls.model_validate(obj)
        bridge.__stop_handler = stop_handler
        bridge.__add_channel_handler = add_channel_handler
        bridge.__record_handler = record_handler
        bridge.__play_handler = play_handler
        return bridge

    def add_handlers(
        self,
        stop_handler: Callable[[str], Awaitable[None]],
        add_channel_handler: Callable[[str, str], Awaitable[None]],
        record_handler: Callable[..., Awaitable["LiveRecording"]],
        play_handler: Callable[..., Awaitable["Playback"]],
    ):
        self.__stop_handler = stop_handler
        self.__add_channel_handler = add_channel_handler
        self.__record_handler = record_handler
        self.__play_handler = play_handler
    
    async def stop(self):
        if self.__stop_handler is None:
            raise ValueError("Stop handler not set")
        await self.__stop_handler(self.id)
    
    async def add_channel(self, channel_id: str):
        if self.__add_channel_handler is None:
            raise ValueError("Add channel handler not set")
        await self.__add_channel_handler(self.id, channel_id)

    async def play(
        self,
        media: str | list[str],
        lang: Optional[str] = None,
        offsetms: Optional[int] = None,
        skipms: Optional[int] = None,
        playback_id: Optional[str] = None,
        announcer_format: Optional[str] = None,
    ) -> "Playback":
        """
        Start playback of media on this bridge.

        Args:
            media: Media URIs to play (e.g. "sound:hello-world", "tone:ring")
            lang: For sounds, selects language for playback
            offsetms: Number of milliseconds to skip before playing
            skipms: Number of milliseconds to skip for forward/reverse operations
            playback_id: Playback ID to use for controlling this playback
            announcer_format: Format of the Announcer channel attached to the bridge.
                Defaults to the format of the channel in the bridge with the highest sample rate.

        Returns:
            Playback: The playback object
        """
        if self.__play_handler is None:
            raise ValueError("Play handler not set")
        return await self.__play_handler(
            bridge_id=self.id,
            media=media,
            lang=lang,
            offsetms=offsetms,
            skipms=skipms,
            playback_id=playback_id,
            announcer_format=announcer_format,
        )

    async def record(
        self,
        name: str,
        format: str,
        recorder_format: Optional[str] = None,
        max_duration_seconds: Optional[int] = None,
        max_silence_seconds: Optional[int] = None,
        if_exists: Optional[Literal["fail", "overwrite", "append"]] = None,
        beep: Optional[bool] = None,
        terminate_on: Optional[Literal["none", "any", "*", "#"]] = None,
    ) -> "LiveRecording":
        """
        Start a recording on this bridge.

        Records the mixed audio from all channels participating in this bridge.

        Args:
            name: Recording's filename (required)
            format: Format to encode audio in (required)
            recorder_format: Format of the 'Recorder' channel attached to the bridge
            max_duration_seconds: Maximum duration of the recording, in seconds. 0 for no limit
            max_silence_seconds: Maximum duration of silence, in seconds. 0 for no limit
            if_exists: Action to take if a recording with the same name already exists
            beep: Play beep when recording begins
            terminate_on: DTMF input to terminate recording

        Returns:
            LiveRecording: The live recording object
        """
        if self.__record_handler is None:
            raise ValueError("Record handler not set")
        return await self.__record_handler(
            bridge_id=self.id,
            name=name,
            format=format,
            recorder_format=recorder_format,
            max_duration_seconds=max_duration_seconds,
            max_silence_seconds=max_silence_seconds,
            if_exists=if_exists,
            beep=beep,
            terminate_on=terminate_on,
        )
