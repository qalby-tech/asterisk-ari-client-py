from httpx import AsyncClient
from typing import Optional, Literal
from .models.bridge import Bridge
from .models.channels import Channel

class AriClientController:

    def __init__(self, client: AsyncClient, app: str):
        self.client = client
        self.app = app

    async def create_channel(
        self, 
        endpoint: str,  
        app_args: Optional[str] = None,
        channel_id: Optional[str] = None,
        originator: Optional[str] = None, 
        other_channel_id: Optional[str] = None,
        formats: Optional[str] = None,
        variables: Optional[dict[str, str]] = None,
        ) -> Channel:
        payload = {
            "endpoint": endpoint,
            "app": self.app,
        }
        if app_args:
            payload["app_args"] = app_args
        if channel_id:
            payload["channel_id"] = channel_id
        if originator:
            payload["originator"] = originator
        if other_channel_id:
            payload["other_channel_id"] = other_channel_id
        if formats:
            payload["formats"] = formats
        if variables:
            payload["variables"] = variables
        response = await self.client.post(f"/channels/create", json=payload)
        if response.status_code >= 300:
            raise Exception(f"Failed to create channel: {response.status_code} {response.text}")
        return Channel.create_with_handlers(
            answer_handler=self.answer_channel,
            stop_handler=self.stop_channel,
            dial_handler=self.dial,
            obj=response.json()
        )
    
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
    
    async def create_bridge(self, type: Optional[str] = None, bridge_id: Optional[str] = None, name: Optional[str] = None) -> Bridge:
        payload = {}
        if type:
            payload["type"] = type
        if bridge_id:
            payload["bridge_id"] = bridge_id
        if name:
            payload["name"] = name
        response = await self.client.post(f"/bridges", json=payload)
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
            dial_handler=self.dial,
            obj=response.json()
        )
    
    async def originate(
        self,
        endpoint: str,
        channel_id: Optional[str] = None,
        extension: Optional[str] = None,
        context: Optional[str] = None,
        priority: Optional[int] = None,
        formats: Optional[str] = None,
        label: Optional[str] = None,
        app_args: Optional[str] = None,
        caller_id: Optional[str] = None,
        timeout: Optional[int] = None,
        variables: Optional[dict[str, str]] = None,
        originator: Optional[str] = None,
        other_channel_id: Optional[str] = None
    ) -> Channel:
        """
        Originate a new channel (POST /channels)
        
        Args:
            endpoint: Endpoint to call (required)
            channel_id: The unique id to assign the channel on creation
            extension: The extension to dial after the endpoint answers
            context: The context to dial after the endpoint answers
            priority: The priority to dial after the endpoint answers
            formats: Format capability list (e.g. "ulaw,slin16")
            label: The label to dial after the endpoint answers
            app_args: Application arguments to pass to the Stasis application
            caller_id: CallerID to use when dialing
            timeout: Timeout in seconds before giving up dialing
            variables: Variable key/value pairs to set on the channel
            originator: The unique id of the channel which is originating this one
            other_channel_id: The unique id for the second channel when using local channels
            
        Returns:
            Channel: The originated channel object
        """
        payload = {
            "app": self.app,
            "endpoint": endpoint
        }
        
        # Add optional parameters to payload
        if channel_id:
            payload["channelId"] = channel_id
        if extension:
            payload["extension"] = extension
        if context:
            payload["context"] = context
        if priority is not None:
            payload["priority"] = priority
        if formats:
            payload["formats"] = formats
        if label:
            payload["label"] = label
        if app_args:
            payload["appArgs"] = app_args
        if caller_id:
            payload["callerId"] = caller_id
        if timeout is not None:
            payload["timeout"] = timeout
        if variables:
            payload["variables"] = variables
        if originator:
            payload["originator"] = originator
        if other_channel_id:
            payload["otherChannelId"] = other_channel_id
        
        # Make the API request
        response = await self.client.post("/channels", json=payload)
        response.raise_for_status()
        
        # Return the channel with handlers
        return Channel.create_with_handlers(
            answer_handler=self.answer_channel,
            stop_handler=self.stop_channel,
            dial_handler=self.dial,
            obj=response.json()
        )
    
    async def originate_with_id(
        self,
        channel_id: str,
        endpoint: str,
        extension: Optional[str] = None,
        context: Optional[str] = None,
        priority: Optional[int] = None,
        formats: Optional[str] = None,
        label: Optional[str] = None,
        app_args: Optional[str] = None,
        caller_id: Optional[str] = None,
        timeout: Optional[int] = None,
        variables: Optional[dict[str, str]] = None,
        originator: Optional[str] = None,
        other_channel_id: Optional[str] = None
    ) -> Channel:
        """
        Originate a new channel with a specific channel ID (POST /channels/{channelId})
        
        Args:
            channel_id: The unique id to assign the channel on creation (required)
            endpoint: Endpoint to call (required)
            extension: The extension to dial after the endpoint answers
            context: The context to dial after the endpoint answers
            priority: The priority to dial after the endpoint answers
            formats: Format capability list (e.g. "ulaw,slin16")
            label: The label to dial after the endpoint answers
            app_args: Application arguments to pass to the Stasis application
            caller_id: CallerID to use when dialing
            timeout: Timeout in seconds before giving up dialing
            variables: Variable key/value pairs to set on the channel
            originator: The unique id of the channel which is originating this one
            other_channel_id: The unique id for the second channel when using local channels
            
        Returns:
            Channel: The originated channel object with the specified ID
        """
        payload = {
            "app": self.app,
            "endpoint": endpoint
        }
        
        # Add optional parameters to payload
        if extension:
            payload["extension"] = extension
        if context:
            payload["context"] = context
        if priority is not None:
            payload["priority"] = priority
        if formats:
            payload["formats"] = formats
        if label:
            payload["label"] = label
        if app_args:
            payload["appArgs"] = app_args
        if caller_id:
            payload["callerId"] = caller_id
        if timeout is not None:
            payload["timeout"] = timeout
        if variables:
            payload["variables"] = variables
        if originator:
            payload["originator"] = originator
        if other_channel_id:
            payload["otherChannelId"] = other_channel_id
        
        # Make the API request with channel_id in the path
        response = await self.client.post(f"/channels/{channel_id}", json=payload)
        response.raise_for_status()
        
        # Return the channel with handlers
        return Channel.create_with_handlers(
            answer_handler=self.answer_channel,
            stop_handler=self.stop_channel,
            dial_handler=self.dial,
            obj=response.json()
        )
    

    async def dial(self, channel_id: str, caller: Optional[str] = None, timeout: Optional[int] = None):
        payload = {}
        if caller:
            payload["caller"] = caller
        if timeout:
            payload["timeout"] = timeout
        response = await self.client.post(f"/channels/{channel_id}/dial", json=payload)
        if response.status_code >= 300:
            raise Exception(f"Failed to dial channel: {response.status_code} {response.text}")
        return None
    
    async def continue_in_dialplan(
        self, 
        channel_id: str, 
        context: Optional[str] = None,
        extension: Optional[str] = None,
        priority: Optional[int] = None,
        label: Optional[str] = None,
        ):
        payload = {}
        if context:
            payload["context"] = context
        if extension:
            payload["extension"] = extension
        if priority:
            payload["priority"] = priority
        if label:
            payload["label"] = label
        response = await self.client.post(f"/channels/{channel_id}/continue", json=payload)
        response.raise_for_status()
        return None