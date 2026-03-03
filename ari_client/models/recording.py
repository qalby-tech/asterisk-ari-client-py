from pydantic import BaseModel, Field, PrivateAttr
from typing import Optional, Callable, Awaitable


class LiveRecording(BaseModel):
    name: str = Field(..., description="Base name for the recording")
    format: str = Field(..., description="Recording format (wav, gsm, etc.)")
    state: Optional[str] = Field(default=None, description="The current state of the recording")
    target_uri: Optional[str] = Field(default=None, description="URI for the channel or bridge being recorded")
    cause: Optional[str] = Field(default=None, description="Cause for recording failure if failed")
    duration: Optional[int] = Field(default=None, description="Duration in seconds of the recording")
    talking_duration: Optional[int] = Field(default=None, description="Duration of talking, in seconds, detected in the recording")
    silence_duration: Optional[int] = Field(default=None, description="Duration of silence, in seconds, detected in the recording")

    __stop_handler: Optional[Callable[[str], Awaitable[None]]] = PrivateAttr(default=None)
    __download_handler: Optional[Callable[[str], Awaitable[bytes]]] = PrivateAttr(default=None)

    @classmethod
    def create_with_handlers(
        cls,
        stop_handler: Callable[[str], Awaitable[None]],
        download_handler: Callable[[str], Awaitable[bytes]],
        obj: dict
    ) -> "LiveRecording":
        recording = cls.model_validate(obj)
        recording.__stop_handler = stop_handler
        recording.__download_handler = download_handler
        return recording

    async def stop(self):
        """Stop this live recording and store it."""
        if self.__stop_handler is None:
            raise ValueError("Stop handler not set")
        await self.__stop_handler(self.name)

    async def download(self) -> bytes:
        """Download the stored recording file as bytes."""
        if self.__download_handler is None:
            raise ValueError("Download handler not set")
        return await self.__download_handler(self.name)
