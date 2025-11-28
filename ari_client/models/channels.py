from pydantic import BaseModel, Field, field_validator, PrivateAttr
from typing import Optional, Callable, Awaitable
from datetime import datetime
import re


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
        obj: dict
    ) -> "Channel":
        channel = cls.model_validate(obj)
        channel.__answer_handler = answer_handler
        channel.__stop_handler = stop_handler
        return channel
    
    def add_handlers(
        self,
        answer_handler: Callable[[str], Awaitable[None]],
        stop_handler: Callable[[str], Awaitable[None]]
    ):
        """Add handlers to the channel for performing actions"""
        self.__answer_handler = answer_handler
        self.__stop_handler = stop_handler
    
    async def answer(self):
        if self.__answer_handler is None:
            raise ValueError("Answer handler not set")
        await self.__answer_handler(self.id)
    
    async def stop(self):
        if self.__stop_handler is None:
            raise ValueError("Stop handler not set")
        await self.__stop_handler(self.id)
