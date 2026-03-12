from __future__ import annotations
from pydantic import BaseModel, Field, field_validator, PrivateAttr
from typing import TYPE_CHECKING, Optional, Callable, Awaitable, Literal
from datetime import datetime
import re

if TYPE_CHECKING:
    from .recording import LiveRecording


class CallerID(BaseModel):
    name: str = Field(default="", description="Caller name")
    number: str = Field(default="", description="Caller number")


class DialplanCEP(BaseModel):
    context: str = Field(..., description="Context in the dialplan")
    exten: str = Field(..., description="Extension in the dialplan")
    priority: int = Field(..., description="Priority in the dialplan")
    app_name: Optional[str] = Field(default=None, description="Name of current dialplan application")
    app_data: Optional[str] = Field(default=None, description="Parameter of current dialplan application")


class Channel(BaseModel):
    id: str = Field(..., description="Unique identifier of the channel. This is the same as the Uniqueid field in AMI.")
    protocol_id: str = Field(default="", description="Protocol id from underlying channel driver (i.e. Call-ID for chan_pjsip; will be empty if not applicable or not implemented by driver).")
    name: str = Field(..., description="Name of the channel (i.e. SIP/foo-0000a7e3)")
    state: str = Field(..., description="Channel state")
    caller: CallerID = Field(..., description="Caller information")
    connected: CallerID = Field(..., description="Connected party information")
    accountcode: str = Field(default="", description="Account code")
    dialplan: DialplanCEP = Field(..., description="Current location in the dialplan")
    creationtime: str | datetime = Field(..., description="Timestamp when channel was created")
    language: Optional[str] = Field(default=None, description="The default spoken language")
    channelvars: Optional[dict] = Field(default=None, description="Channel variables")
    caller_rdnis: Optional[str] = Field(default=None, description="The Caller ID RDNIS")
    tenantid: Optional[str] = Field(default=None, description="The Tenant ID for the channel")

    __answer_handler: Optional[Callable[[str], Awaitable[None]]] = PrivateAttr(default=None)
    __stop_handler: Optional[Callable[[str], Awaitable[None]]] = PrivateAttr(default=None)
    __dial_handler: Optional[Callable[[str, Optional[str], Optional[int]], Awaitable["Channel"]]] = PrivateAttr(default=None)
    __record_handler: Optional[Callable[..., Awaitable["LiveRecording"]]] = PrivateAttr(default=None)
    __snoop_handler: Optional[Callable[..., Awaitable["Channel"]]] = PrivateAttr(default=None)
    __send_dtmf_handler: Optional[Callable[..., Awaitable[None]]] = PrivateAttr(default=None)
    __redirect_handler: Optional[Callable[..., Awaitable[None]]] = PrivateAttr(default=None)
    __move_handler: Optional[Callable[..., Awaitable[None]]] = PrivateAttr(default=None)

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
        answer_handler: Callable[[str], Awaitable[None]],
        stop_handler: Callable[[str], Awaitable[None]],
        dial_handler: Callable[[str, Optional[str], Optional[int]], Awaitable["Channel"]],
        record_handler: Callable[..., Awaitable["LiveRecording"]],
        snoop_handler: Callable[..., Awaitable["Channel"]],
        send_dtmf_handler: Callable[..., Awaitable[None]],
        redirect_handler: Callable[..., Awaitable[None]],
        move_handler: Callable[..., Awaitable[None]],
        obj: dict
    ) -> "Channel":
        channel = cls.model_validate(obj)
        channel.__answer_handler = answer_handler
        channel.__stop_handler = stop_handler
        channel.__dial_handler = dial_handler
        channel.__record_handler = record_handler
        channel.__snoop_handler = snoop_handler
        channel.__send_dtmf_handler = send_dtmf_handler
        channel.__redirect_handler = redirect_handler
        channel.__move_handler = move_handler
        return channel
    
    def add_handlers(
        self,
        answer_handler: Callable[[str], Awaitable[None]],
        stop_handler: Callable[[str], Awaitable[None]],
        dial_handler: Callable[[str, Optional[str], Optional[int]], Awaitable["Channel"]],
        record_handler: Callable[..., Awaitable["LiveRecording"]],
        snoop_handler: Callable[..., Awaitable["Channel"]],
        send_dtmf_handler: Callable[..., Awaitable[None]],
        redirect_handler: Callable[..., Awaitable[None]],
        move_handler: Callable[..., Awaitable[None]],
    ):
        """Add handlers to the channel for performing actions"""
        self.__answer_handler = answer_handler
        self.__stop_handler = stop_handler
        self.__dial_handler = dial_handler
        self.__record_handler = record_handler
        self.__snoop_handler = snoop_handler
        self.__send_dtmf_handler = send_dtmf_handler
        self.__redirect_handler = redirect_handler
        self.__move_handler = move_handler

    async def answer(self):
        if self.__answer_handler is None:
            raise ValueError("Answer handler not set")
        await self.__answer_handler(self.id)
    
    async def stop(self):
        if self.__stop_handler is None:
            raise ValueError("Stop handler not set")
        await self.__stop_handler(self.id)
    
    async def dial(self, caller: Optional[str] = None, timeout: Optional[int] = None) -> None:
        """
        Dial this channel from another channel or start the dial process.
        
        Args:
            caller: Channel ID of the calling channel
            timeout: Dial timeout in seconds
            
        Returns:
            Channel object (may be updated channel state)
        """
        if self.__dial_handler is None:
            raise ValueError("Dial handler not set")
        return await self.__dial_handler(self.id, caller, timeout)

    async def record(
        self,
        name: str,
        format: str,
        max_duration_seconds: Optional[int] = None,
        max_silence_seconds: Optional[int] = None,
        if_exists: Optional[Literal["fail", "overwrite", "append"]] = None,
        beep: Optional[bool] = None,
        terminate_on: Optional[Literal["none", "any", "*", "#"]] = None,
    ) -> "LiveRecording":
        """
        Start a recording on this channel.

        Record audio from this channel. Note that this will not capture audio
        sent to the channel. The bridge itself has a record feature if that's
        what you want.

        Args:
            name: Recording's filename (required)
            format: Format to encode audio in (required)
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
            channel_id=self.id,
            name=name,
            format=format,
            max_duration_seconds=max_duration_seconds,
            max_silence_seconds=max_silence_seconds,
            if_exists=if_exists,
            beep=beep,
            terminate_on=terminate_on,
        )

    async def snoop(
        self,
        spy: Optional[Literal["none", "both", "out", "in"]] = None,
        whisper: Optional[Literal["none", "both", "out", "in"]] = None,
        app_args: Optional[str] = None,
        snoop_id: Optional[str] = None,
    ) -> "Channel":
        """
        Start snooping (spy/whisper) on this channel.

        Creates a new snooping channel that can spy on and/or whisper into
        this channel's audio.

        Args:
            spy: Direction of audio to spy on (default: none).
                 "none" - No spying. "both" - Both directions.
                 "out" - Audio sent out. "in" - Audio coming in.
            whisper: Direction of audio to whisper into (default: none).
                     "none" - No whispering. "both" - Both directions.
                     "out" - Audio sent out. "in" - Audio coming in.
            app_args: The application arguments to pass to the Stasis application
            snoop_id: Unique ID to assign to the snooping channel

        Returns:
            Channel: The newly created snooping channel
        """
        if self.__snoop_handler is None:
            raise ValueError("Snoop handler not set")
        return await self.__snoop_handler(
            channel_id=self.id,
            spy=spy,
            whisper=whisper,
            app_args=app_args,
            snoop_id=snoop_id,
        )

    async def send_dtmf(
        self,
        dtmf: Optional[str] = None,
        before: Optional[int] = None,
        between: Optional[int] = None,
        duration: Optional[int] = None,
        after: Optional[int] = None,
    ) -> None:
        """
        Send DTMF to this channel.

        Args:
            dtmf: DTMF to send
            before: Amount of time to wait before DTMF digits (ms) start
            between: Amount of time in between DTMF digits (ms). Default: 100
            duration: Length of each DTMF digit (ms). Default: 100
            after: Amount of time to wait after DTMF digits (ms) end
        """
        if self.__send_dtmf_handler is None:
            raise ValueError("Send DTMF handler not set")
        await self.__send_dtmf_handler(
            channel_id=self.id,
            dtmf=dtmf,
            before=before,
            between=between,
            duration=duration,
            after=after,
        )

    async def redirect(self, endpoint: str) -> None:
        """
        Redirect this channel to a different location.

        Args:
            endpoint: The endpoint to redirect the channel to (required)
        """
        if self.__redirect_handler is None:
            raise ValueError("Redirect handler not set")
        await self.__redirect_handler(
            channel_id=self.id,
            endpoint=endpoint,
        )

    async def move(self, app: str, app_args: Optional[str] = None) -> None:
        """
        Move this channel from one Stasis application to another.

        Args:
            app: The Stasis application to move the channel to (required)
            app_args: Application arguments to pass to the target Stasis application
        """
        if self.__move_handler is None:
            raise ValueError("Move handler not set")
        await self.__move_handler(
            channel_id=self.id,
            app=app,
            app_args=app_args,
        )
