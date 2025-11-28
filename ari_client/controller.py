from httpx import AsyncClient
from typing import Optional, Literal
from .models.bridge import Bridge
from .models.channels import Channel
import uuid

class AriClientController:

    def __init__(self, client: AsyncClient, app: str):
        self.client = client
        self.app = app

    async def answer_channel(self, channel_id: str):
        response = await self.client.post(f"/channels/{channel_id}/answer")
        if response.status_code != 204:
            raise Exception(f"Failed to answer channel: {response.status_code} {response.text}")
        return None
    
    async def stop_channel(self, channel_id: str):
        response = await self.client.delete(f"/channels/{channel_id}")
        if response.status_code != 204:
            raise Exception(f"Failed to stop channel: {response.status_code} {response.text}")
        return None
    
    async def create_bridge(self, type: str, bridge_id: Optional[str] = None, name: Optional[str] = None) -> Bridge:
        if bridge_id is None:
            bridge_id = str(uuid.uuid4())
        if name is None:
            name = f"bridge_{bridge_id}"
        response = await self.client.post(f"/bridges", json={
            "type": type,
            "bridge_id": bridge_id,
            "name": name
        })
        if response.status_code != 200:
            raise Exception(f"Failed to create bridge: {response.status_code} {response.text}")
        return Bridge.create_with_handlers(
            stop_handler=self.stop_bridge,
            add_channel_handler=self.bridge_add_channel,
            obj=response.json()
        )
    
    async def bridge_add_channel(self, bridge_id: str, channel_id: str):
        response = await self.client.post(f"/bridges/{bridge_id}/addChannel", json={
            "channel": channel_id
        })
        if response.status_code != 204:
            raise Exception(f"Failed to add channel to bridge: {response.status_code} {response.text}")
        return None
    
    async def stop_bridge(self, bridge_id: str):
        response = await self.client.delete(f"/bridges/{bridge_id}")
        if response.status_code != 204:
            raise Exception(f"Failed to stop bridge: {response.status_code} {response.text}")
        return None
    
    async def stop_channel(self, channel_id: str):
        response = await self.client.delete(f"/channels/{channel_id}")
        if response.status_code != 204:
            raise Exception(f"Failed to stop channel: {response.status_code} {response.text}")
        return None
    
    async def create_external_media(
        self, 
        external_host: str, 
        format: str,
        encapsulation: Literal["rtp", "audiosocket"] = "rtp", 
        transport: Literal["tcp", "udp"] = "udp", 
        connection_type: str = "client", 
        direction: str = "both", 
        channel_id: Optional[str] = None, 
        variables: Optional[dict[str, str]] = None, 
        data: Optional[str] = None
    ) -> Channel:
        payload = {
            "app": self.app,
            "external_host": external_host,
            "format": format,
            "encapsulation": encapsulation,
            "transport": transport,
            "connection_type": connection_type,
            "direction": direction
        }
        if channel_id:
            payload["channel_id"] = channel_id
        if variables:
            payload["variables"] = variables
        if data:
            payload["data"] = data
        response = await self.client.post(f"/channels/externalMedia", json=payload)
        if response.status_code != 200:
            raise Exception(f"Failed to create external media: {response.status_code} {response.text}")
        return Channel.create_with_handlers(
            answer_handler=self.answer_channel,
            stop_handler=self.stop_channel,
            obj=response.json()
        )
    
    async def originate(self, endpoint: str, channel_id: Optional[str] = None, extension: Optional[str] = None, context: Optional[str] = None, priority: int = 1, formats: Optional[str] = None, label: Optional[str] = None, app_args: Optional[str] = None, caller_id: Optional[str] = None, timeout: int = 30, variables: Optional[dict[str, str]] = None, originator: Optional[str] = None, other_channel_id: Optional[str] = None) -> Channel:
        payload = {
            "endpoint": endpoint,
            "app": self.app,
        }
        if channel_id:
            payload["channelId"] = channel_id
        if extension:
            payload["extension"] = extension
        if context:
            payload["context"] = context
        if priority:
            payload["priority"] = priority
        if formats:
            payload["formats"] = formats
        if label:
            payload["label"] = label
        if app_args:
            payload["appArgs"] = app_args
        if caller_id:
            payload["callerId"] = caller_id
        if timeout:
            payload["timeout"] = timeout
        if variables:
            payload["variables"] = variables
        if originator:
            payload["originator"] = originator
        if other_channel_id:
            payload["otherChannelId"] = other_channel_id
        response = await self.client.post(f"/channels", json=payload)
        response.raise_for_status()
        return Channel.create_with_handlers(
            answer_handler=self.answer_channel,
            stop_handler=self.stop_channel,
            obj=response.json()
        )
