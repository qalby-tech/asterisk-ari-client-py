from httpx import AsyncClient
from typing import Optional, Literal
from .models.bridge import Bridge
from .models.channels import Channel
from .models.recording import LiveRecording

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
            payload["appArgs"] = app_args
        if channel_id:
            payload["channelId"] = channel_id
        if originator:
            payload["originator"] = originator
        if other_channel_id:
            payload["otherChannelId"] = other_channel_id
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
            record_handler=self.record_channel,
            snoop_handler=self.snoop_channel,
            send_dtmf_handler=self.send_dtmf,
            redirect_handler=self.redirect_channel,
            move_handler=self.move_channel,
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
            record_handler=self.record_bridge,
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
            payload["channelId"] = channel_id
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
            record_handler=self.record_channel,
            snoop_handler=self.snoop_channel,
            send_dtmf_handler=self.send_dtmf,
            redirect_handler=self.redirect_channel,
            move_handler=self.move_channel,
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
            record_handler=self.record_channel,
            snoop_handler=self.snoop_channel,
            send_dtmf_handler=self.send_dtmf,
            redirect_handler=self.redirect_channel,
            move_handler=self.move_channel,
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
            record_handler=self.record_channel,
            snoop_handler=self.snoop_channel,
            send_dtmf_handler=self.send_dtmf,
            redirect_handler=self.redirect_channel,
            move_handler=self.move_channel,
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

    async def record_bridge(
        self,
        bridge_id: str,
        name: str,
        format: str,
        recorder_format: Optional[str] = None,
        max_duration_seconds: Optional[int] = None,
        max_silence_seconds: Optional[int] = None,
        if_exists: Optional[Literal["fail", "overwrite", "append"]] = None,
        beep: Optional[bool] = None,
        terminate_on: Optional[Literal["none", "any", "*", "#"]] = None,
    ) -> LiveRecording:
        """
        Start a recording on a bridge (POST /bridges/{bridgeId}/record).

        Records the mixed audio from all channels participating in the bridge.

        Args:
            bridge_id: Bridge's id (required)
            name: Recording's filename (required)
            format: Format to encode audio in (required)
            recorder_format: Format of the 'Recorder' channel attached to the bridge
            max_duration_seconds: Maximum duration of the recording, in seconds. 0 for no limit
            max_silence_seconds: Maximum duration of silence, in seconds. 0 for no limit
            if_exists: Action to take if a recording with the same name already exists (default: fail)
            beep: Play beep when recording begins
            terminate_on: DTMF input to terminate recording (default: none)

        Returns:
            LiveRecording: The live recording object
        """
        params: dict = {
            "name": name,
            "format": format,
        }
        if recorder_format is not None:
            params["recorderFormat"] = recorder_format
        if max_duration_seconds is not None:
            params["maxDurationSeconds"] = max_duration_seconds
        if max_silence_seconds is not None:
            params["maxSilenceSeconds"] = max_silence_seconds
        if if_exists is not None:
            params["ifExists"] = if_exists
        if beep is not None:
            params["beep"] = beep
        if terminate_on is not None:
            params["terminateOn"] = terminate_on

        response = await self.client.post(f"/bridges/{bridge_id}/record", params=params)
        if response.status_code >= 300:
            raise Exception(f"Failed to record bridge: {response.status_code} {response.text}")
        return LiveRecording.create_with_handlers(
            stop_handler=self.stop_recording,
            download_handler=self.download_recording,
            obj=response.json()
        )

    async def record_channel(
        self,
        channel_id: str,
        name: str,
        format: str,
        max_duration_seconds: Optional[int] = None,
        max_silence_seconds: Optional[int] = None,
        if_exists: Optional[Literal["fail", "overwrite", "append"]] = None,
        beep: Optional[bool] = None,
        terminate_on: Optional[Literal["none", "any", "*", "#"]] = None,
    ) -> LiveRecording:
        """
        Start a recording on a channel (POST /channels/{channelId}/record).

        Record audio from a channel. Note that this will not capture audio sent
        to the channel. The bridge itself has a record feature if that's what you want.

        Args:
            channel_id: Channel's id (required)
            name: Recording's filename (required)
            format: Format to encode audio in (required)
            max_duration_seconds: Maximum duration of the recording, in seconds. 0 for no limit
            max_silence_seconds: Maximum duration of silence, in seconds. 0 for no limit
            if_exists: Action to take if a recording with the same name already exists (default: fail)
            beep: Play beep when recording begins
            terminate_on: DTMF input to terminate recording (default: none)

        Returns:
            LiveRecording: The live recording object
        """
        params: dict = {
            "name": name,
            "format": format,
        }
        if max_duration_seconds is not None:
            params["maxDurationSeconds"] = max_duration_seconds
        if max_silence_seconds is not None:
            params["maxSilenceSeconds"] = max_silence_seconds
        if if_exists is not None:
            params["ifExists"] = if_exists
        if beep is not None:
            params["beep"] = beep
        if terminate_on is not None:
            params["terminateOn"] = terminate_on

        response = await self.client.post(f"/channels/{channel_id}/record", params=params)
        if response.status_code >= 300:
            raise Exception(f"Failed to record channel: {response.status_code} {response.text}")
        return LiveRecording.create_with_handlers(
            stop_handler=self.stop_recording,
            download_handler=self.download_recording,
            obj=response.json()
        )

    async def snoop_channel(
        self,
        channel_id: str,
        spy: Optional[Literal["none", "both", "out", "in"]] = None,
        whisper: Optional[Literal["none", "both", "out", "in"]] = None,
        app_args: Optional[str] = None,
        snoop_id: Optional[str] = None,
    ) -> Channel:
        """
        Start snooping on a channel (POST /channels/{channelId}/snoop).

        Snoop (spy/whisper) on a specific channel.

        Args:
            channel_id: Channel's id (required)
            spy: Direction of audio to spy on (default: none)
            whisper: Direction of audio to whisper into (default: none)
            app_args: The application arguments to pass to the Stasis application
            snoop_id: Unique ID to assign to snooping channel

        Returns:
            Channel: The snooping channel object
        """
        params: dict = {
            "app": self.app,
        }
        if spy is not None:
            params["spy"] = spy
        if whisper is not None:
            params["whisper"] = whisper
        if app_args is not None:
            params["appArgs"] = app_args
        if snoop_id is not None:
            params["snoopId"] = snoop_id

        response = await self.client.post(f"/channels/{channel_id}/snoop", params=params)
        if response.status_code >= 300:
            raise Exception(f"Failed to snoop channel: {response.status_code} {response.text}")
        return Channel.create_with_handlers(
            answer_handler=self.answer_channel,
            stop_handler=self.stop_channel,
            dial_handler=self.dial,
            record_handler=self.record_channel,
            snoop_handler=self.snoop_channel,
            send_dtmf_handler=self.send_dtmf,
            redirect_handler=self.redirect_channel,
            move_handler=self.move_channel,
            obj=response.json()
        )

    async def send_dtmf(
        self,
        channel_id: str,
        dtmf: Optional[str] = None,
        before: Optional[int] = None,
        between: Optional[int] = None,
        duration: Optional[int] = None,
        after: Optional[int] = None,
    ) -> None:
        """
        Send provided DTMF to a given channel (POST /channels/{channelId}/dtmf).

        Args:
            channel_id: Channel's id (required)
            dtmf: DTMF to send
            before: Amount of time to wait before DTMF digits (specified in milliseconds) start
            between: Amount of time in between DTMF digits (specified in milliseconds). Default: 100
            duration: Length of each DTMF digit (specified in milliseconds). Default: 100
            after: Amount of time to wait after DTMF digits (specified in milliseconds) end
        """
        params: dict = {}
        if dtmf is not None:
            params["dtmf"] = dtmf
        if before is not None:
            params["before"] = before
        if between is not None:
            params["between"] = between
        if duration is not None:
            params["duration"] = duration
        if after is not None:
            params["after"] = after

        response = await self.client.post(f"/channels/{channel_id}/dtmf", params=params)
        if response.status_code >= 300:
            raise Exception(f"Failed to send DTMF to channel: {response.status_code} {response.text}")
        return None

    async def redirect_channel(
        self,
        channel_id: str,
        endpoint: str,
    ) -> None:
        """
        Redirect the channel to a different location (POST /channels/{channelId}/redirect).

        Args:
            channel_id: Channel's id (required)
            endpoint: The endpoint to redirect the channel to (required)
        """
        params: dict = {
            "endpoint": endpoint,
        }

        response = await self.client.post(f"/channels/{channel_id}/redirect", params=params)
        if response.status_code >= 300:
            raise Exception(f"Failed to redirect channel: {response.status_code} {response.text}")
        return None

    async def move_channel(
        self,
        channel_id: str,
        app: str,
        app_args: Optional[str] = None,
    ) -> None:
        """
        Move the channel from one Stasis application to another
        (POST /channels/{channelId}/move).

        Args:
            channel_id: Channel's id (required)
            app: The channel will be passed to this Stasis application (required)
            app_args: The application arguments to pass to the Stasis application provided by 'app'
        """
        params: dict = {
            "app": app,
        }
        if app_args is not None:
            params["appArgs"] = app_args

        response = await self.client.post(f"/channels/{channel_id}/move", params=params)
        if response.status_code >= 300:
            raise Exception(f"Failed to move channel: {response.status_code} {response.text}")
        return None

    async def stop_recording(self, recording_name: str):
        """
        Stop a live recording and store it (POST /recordings/live/{recordingName}/stop).

        Args:
            recording_name: The name of the recording (required)
        """
        response = await self.client.post(f"/recordings/live/{recording_name}/stop")
        if response.status_code != 204:
            raise Exception(f"Failed to stop recording: {response.status_code} {response.text}")
        return None

    async def download_recording(self, recording_name: str) -> bytes:
        """
        Download the file associated with a stored recording
        (GET /recordings/stored/{recordingName}/file).

        Args:
            recording_name: The name of the recording (required)

        Returns:
            bytes: The raw audio file content (e.g. WAV)
        """
        response = await self.client.get(f"/recordings/stored/{recording_name}/file")
        if response.status_code == 403:
            raise Exception(f"Recording file could not be opened: {recording_name}")
        if response.status_code == 404:
            raise Exception(f"Recording not found: {recording_name}")
        if response.status_code >= 300:
            raise Exception(f"Failed to download recording: {response.status_code} {response.text}")
        return response.content