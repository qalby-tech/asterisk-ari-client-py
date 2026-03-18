from __future__ import annotations
from pydantic import BaseModel, Field, PrivateAttr
from typing import Optional, Callable, Awaitable


class Playback(BaseModel):
    id: str = Field(..., description="ID for this playback operation")
    media_uri: str = Field(..., description="The URI for the media to play")
    next_media_uri: Optional[str] = Field(default=None, description="Next media URI to be played back if a list is being played")
    target_uri: str = Field(..., description="URI for the channel or bridge being played to")
    language: Optional[str] = Field(default=None, description="Language requested for playback")
    state: str = Field(..., description="Current state of playback (queued, playing, continuing, done, failed)")

    __stop_handler: Optional[Callable[[str], Awaitable[None]]] = PrivateAttr(default=None)
    __control_handler: Optional[Callable[[str, str], Awaitable[None]]] = PrivateAttr(default=None)

    @classmethod
    def create_with_handlers(
        cls,
        stop_handler: Callable[[str], Awaitable[None]],
        control_handler: Callable[[str, str], Awaitable[None]],
        obj: dict,
    ) -> Playback:
        playback = cls.model_validate(obj)
        playback.__stop_handler = stop_handler
        playback.__control_handler = control_handler
        return playback

    def add_handlers(
        self,
        stop_handler: Callable[[str], Awaitable[None]],
        control_handler: Callable[[str, str], Awaitable[None]],
    ):
        self.__stop_handler = stop_handler
        self.__control_handler = control_handler

    async def stop(self):
        """Stop this playback."""
        if self.__stop_handler is None:
            raise ValueError("Stop handler not set")
        await self.__stop_handler(self.id)

    async def control(self, operation: str):
        """
        Control this playback.

        Args:
            operation: One of restart, pause, unpause, reverse, forward
        """
        if self.__control_handler is None:
            raise ValueError("Control handler not set")
        await self.__control_handler(self.id, operation)
