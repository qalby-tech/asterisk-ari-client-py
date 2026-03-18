# ARI Client Library

A Python client library for Asterisk REST Interface (ARI) that provides an object-oriented approach to managing channels, bridges, playbacks, recordings, and events.

## Architecture

The library follows a clean architecture pattern with separation of concerns:

- **AriClient**: Main client class that handles WebSocket connections and event dispatching
- **AriClientController**: Separate controller class that handles all HTTP API operations
- **Model Objects**: Bridge, Channel, Playback, and LiveRecording objects that encapsulate state and provide methods for actions

### Key Design Principles

1. **All actions are performed via model objects** - Channel, Bridge, Playback, and LiveRecording objects carry their own action methods, keeping operations context-aware and type-safe
2. **Controller is separate from client** - The controller handles HTTP operations, while the client manages WebSocket connections
3. **Automatic handler injection** - When events arrive, all model instances inside them (channels, bridges, playbacks, recordings) are automatically enriched with controller handlers so you can call action methods immediately

## Installation

```bash
pip install asterisk-ari-client
# or using uv
uv add asterisk-ari-client
# or from source
uv sync
```

## Quick Start

```python
import asyncio
from ari_client import (
    AriClient,
    StasisStartEvent,
    StasisEndEvent,
    ChannelDtmfReceivedEvent,
    ChannelHangupRequestEvent,
    PlaybackFinishedEvent,
)
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AriClient(
    host="localhost",
    port=8088,
    ari_user="asterisk",
    ari_password="asterisk",
    tls_enabled=False
)

@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    logger.info(f"Channel entered Stasis: {event.channel.id}")
    await event.channel.answer()

    # Play a sound on the channel
    playback = await event.channel.play(media="sound:hello-world")
    logger.info(f"Playback started: {playback.id}")

    # Create a bridge and add the channel
    bridge = await client.ari.create_bridge(type="mixing")
    await bridge.add_channel(event.channel.id)

@client.on_stasis_end
async def on_stasis_end(event: StasisEndEvent):
    logger.info(f"Channel left Stasis: {event.channel.id}")

@client.on_channel_dtmf_received
async def on_dtmf(event: ChannelDtmfReceivedEvent):
    logger.info(f"DTMF received: digit={event.digit} on channel {event.channel.id}")

@client.on_playback_finished
async def on_playback_done(event: PlaybackFinishedEvent):
    logger.info(f"Playback {event.playback.id} finished with state: {event.playback.state}")

async def main():
    await client.connect(app="myapp", subscribe_to_all=True)

    try:
        await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Supported Events

All events below can be registered with typed decorator methods or the generic `on_event()` method.

### Stasis

| Event | Decorator | Description |
|-------|-----------|-------------|
| `StasisStartEvent` | `@client.on_stasis_start` | Channel entered your Stasis application |
| `StasisEndEvent` | `@client.on_stasis_end` | Channel left your Stasis application |

### Bridge

| Event | Decorator | Description |
|-------|-----------|-------------|
| `BridgeAttendedTransferEvent` | `@client.on_bridge_attended_transfer` | Attended transfer on a bridge |
| `BridgeBlindTransferEvent` | `@client.on_bridge_blind_transfer` | Blind transfer on a bridge |
| `BridgeCreatedEvent` | `@client.on_bridge_created` | A bridge was created |
| `BridgeDestroyedEvent` | `@client.on_bridge_destroyed` | A bridge was destroyed |
| `BridgeMergedEvent` | `@client.on_bridge_merged` | Two bridges were merged |
| `BridgeVideoSourceChangedEvent` | `@client.on_bridge_video_source_changed` | Video source changed on a bridge |

### Channel

| Event | Decorator | Description |
|-------|-----------|-------------|
| `ChannelCallerIdEvent` | `@client.on_channel_caller_id` | Caller ID changed on a channel |
| `ChannelConnectedLineEvent` | `@client.on_channel_connected_line` | Connected line information changed |
| `ChannelCreatedEvent` | `@client.on_channel_created` | A channel was created |
| `ChannelDestroyedEvent` | `@client.on_channel_destroyed` | A channel was destroyed |
| `ChannelDialplanEvent` | `@client.on_channel_dialplan` | Channel entered a new dialplan context |
| `ChannelDtmfReceivedEvent` | `@client.on_channel_dtmf_received` | DTMF digit received |
| `ChannelEnteredBridgeEvent` | `@client.on_channel_entered_bridge` | Channel joined a bridge |
| `ChannelHangupRequestEvent` | `@client.on_channel_hangup_request` | Hangup requested on a channel |
| `ChannelHoldEvent` | `@client.on_channel_hold` | Channel placed on hold |
| `ChannelLeftBridgeEvent` | `@client.on_channel_left_bridge` | Channel left a bridge |
| `ChannelStateChangeEvent` | `@client.on_channel_state_change` | Channel state changed |
| `ChannelTalkingFinishedEvent` | `@client.on_channel_talking_finished` | Talking detection stopped |
| `ChannelTalkingStartedEvent` | `@client.on_channel_talking_started` | Talking detection started |
| `ChannelToneDetectedEvent` | `@client.on_channel_tone_detected` | Tone detected on a channel |
| `ChannelUnholdEvent` | `@client.on_channel_unhold` | Channel removed from hold |
| `ChannelUsereventEvent` | `@client.on_channel_userevent` | User-defined event received |
| `ChannelVarsetEvent` | `@client.on_channel_varset` | Channel variable set |

### Dial

| Event | Decorator | Description |
|-------|-----------|-------------|
| `DialEvent` | `@client.on_dial` | Dialing state changed |

### Playback

| Event | Decorator | Description |
|-------|-----------|-------------|
| `PlaybackContinuingEvent` | `@client.on_playback_continuing` | Playback is continuing to the next media URI |
| `PlaybackFinishedEvent` | `@client.on_playback_finished` | Playback completed |
| `PlaybackStartedEvent` | `@client.on_playback_started` | Playback started |

### Recording

| Event | Decorator | Description |
|-------|-----------|-------------|
| `RecordingFailedEvent` | `@client.on_recording_failed` | Recording failed |
| `RecordingFinishedEvent` | `@client.on_recording_finished` | Recording completed |
| `RecordingStartedEvent` | `@client.on_recording_started` | Recording started |

## Event Handler Registration

Handlers can be registered in three ways:

```python
# 1. Typed decorator (IDE autocomplete + type checking)
@client.on_channel_destroyed
async def handler(event: ChannelDestroyedEvent):
    print(f"Channel {event.channel.id} destroyed: {event.cause_txt}")

# 2. Method call
async def handler(event: ChannelDestroyedEvent):
    print(f"Channel {event.channel.id} destroyed: {event.cause_txt}")

client.on_channel_destroyed(handler)

# 3. Generic on_event (works with any event type string or EventType enum)
from ari_client import EventType

@client.on_event(EventType.CHANNEL_DESTROYED)
async def handler(event: ChannelDestroyedEvent):
    ...

@client.on_event("ChannelDestroyed")
async def handler(event):
    ...
```

## Model Objects

### Channel

Represents an Asterisk channel with action methods.

**Properties:** `id`, `name`, `state`, `caller`, `connected`, `accountcode`, `dialplan`, `creationtime`, `language`, `channelvars`

**Methods:**

| Method | Description |
|--------|-------------|
| `await channel.answer()` | Answer the channel |
| `await channel.stop()` | Hang up the channel |
| `await channel.dial(caller, timeout)` | Dial the channel |
| `await channel.play(media, lang, ...)` | Play media on the channel, returns `Playback` |
| `await channel.record(name, format, ...)` | Record audio, returns `LiveRecording` |
| `await channel.snoop(spy, whisper, ...)` | Spy/whisper on the channel, returns `Channel` |
| `await channel.send_dtmf(dtmf, ...)` | Send DTMF tones |
| `await channel.redirect(endpoint)` | Redirect to a different endpoint |
| `await channel.move(app, app_args)` | Move to another Stasis application |

### Bridge

Represents an Asterisk bridge with action methods.

**Properties:** `id`, `technology`, `bridge_type`, `bridge_class`, `creator`, `name`, `channels`, `video_mode`, `video_source_id`, `creationtime`

**Methods:**

| Method | Description |
|--------|-------------|
| `await bridge.add_channel(channel_id)` | Add a channel to the bridge |
| `await bridge.stop()` | Destroy the bridge |
| `await bridge.play(media, lang, ...)` | Play media on the bridge, returns `Playback` |
| `await bridge.record(name, format, ...)` | Record bridge audio, returns `LiveRecording` |

### Playback

Represents an active media playback.

**Properties:** `id`, `media_uri`, `next_media_uri`, `target_uri`, `language`, `state`

**Methods:**

| Method | Description |
|--------|-------------|
| `await playback.stop()` | Stop the playback |
| `await playback.control(operation)` | Control playback: `restart`, `pause`, `unpause`, `reverse`, `forward` |

### LiveRecording

Represents a live recording in progress.

**Properties:** `name`, `format`, `state`, `target_uri`, `cause`, `duration`, `talking_duration`, `silence_duration`

**Methods:**

| Method | Description |
|--------|-------------|
| `await recording.stop()` | Stop recording and store it |
| `await recording.download()` | Download the stored recording as bytes |

## Controller (client.ari)

The `AriClientController` is accessible via `client.ari` and provides direct HTTP API access:

**Channels:** `create_channel`, `answer_channel`, `stop_channel`, `originate`, `originate_with_id`, `dial`, `continue_in_dialplan`, `snoop_channel`, `send_dtmf`, `redirect_channel`, `move_channel`, `play_channel`, `record_channel`

**Bridges:** `create_bridge`, `bridge_add_channel`, `stop_bridge`, `play_bridge`, `record_bridge`

**Playback:** `stop_playback`, `control_playback`

**Recordings:** `stop_recording`, `download_recording`

**External Media:** `create_external_media`

## Examples

### Call Bridging with External Media

```python
bridge_map: dict[str, Bridge] = {}

@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    if event.channel.name.startswith("UnicastRTP"):
        return

    await event.channel.answer()

    bridge = await client.ari.create_bridge(type="mixing,proxy_media")
    await bridge.add_channel(event.channel.id)

    external_media = await client.ari.create_external_media(
        external_host="192.168.1.100:10000",
        format="ulaw"
    )
    await bridge.add_channel(external_media.id)
    await external_media.answer()

    bridge_map[event.channel.id] = bridge

@client.on_stasis_end
async def on_stasis_end(event: StasisEndEvent):
    bridge = bridge_map.pop(event.channel.id, None)
    if bridge:
        await bridge.stop()
```

### IVR with DTMF and Playback

```python
from ari_client import (
    AriClient, StasisStartEvent,
    ChannelDtmfReceivedEvent, PlaybackFinishedEvent,
)

client = AriClient(
    host="localhost", port=8088,
    ari_user="asterisk", ari_password="asterisk"
)

@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    await event.channel.answer()
    await event.channel.play(media="sound:press-1-for-sales")

@client.on_channel_dtmf_received
async def on_dtmf(event: ChannelDtmfReceivedEvent):
    if event.digit == "1":
        await event.channel.play(media="sound:connecting")
        await event.channel.redirect(endpoint="PJSIP/sales")
    elif event.digit == "2":
        await event.channel.move(app="queue-handler", app_args="support")
    elif event.digit == "#":
        await event.channel.stop()

@client.on_playback_finished
async def on_playback_done(event: PlaybackFinishedEvent):
    logger.info(f"Playback {event.playback.id} done")
```

### Recording a Call

```python
from ari_client import StasisStartEvent, RecordingFinishedEvent

recordings: dict[str, LiveRecording] = {}

@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    await event.channel.answer()
    recording = await event.channel.record(
        name=f"call-{event.channel.id}",
        format="wav",
        beep=True,
        terminate_on="#",
    )
    recordings[event.channel.id] = recording

@client.on_recording_finished
async def on_recording_done(event: RecordingFinishedEvent):
    logger.info(f"Recording '{event.recording.name}' finished, duration: {event.recording.duration}s")
    data = await event.recording.download()
    with open(f"/tmp/{event.recording.name}.wav", "wb") as f:
        f.write(data)
```

### Bridge Events

```python
from ari_client import (
    ChannelEnteredBridgeEvent,
    ChannelLeftBridgeEvent,
    BridgeDestroyedEvent,
)

@client.on_channel_entered_bridge
async def on_entered(event: ChannelEnteredBridgeEvent):
    logger.info(f"Channel {event.channel.id} entered bridge {event.bridge.id}")

@client.on_channel_left_bridge
async def on_left(event: ChannelLeftBridgeEvent):
    logger.info(f"Channel {event.channel.id} left bridge {event.bridge.id}")
    if len(event.bridge.channels) == 0:
        await event.bridge.stop()

@client.on_bridge_destroyed
async def on_bridge_destroyed(event: BridgeDestroyedEvent):
    logger.info(f"Bridge {event.bridge.id} destroyed")
```

### Dial Progress Tracking

```python
from ari_client import DialEvent

@client.on_dial
async def on_dial(event: DialEvent):
    logger.info(
        f"Dial update: {event.peer.name} status={event.dialstatus}"
        + (f" from {event.caller.name}" if event.caller else "")
    )
```

## Error Handling

The library includes automatic error handling:

- Event handler exceptions are automatically logged and don't crash the event listener
- HTTP API errors raise exceptions with descriptive messages
- WebSocket connection errors are logged and re-raised

Always wrap your operations in try-except blocks when appropriate:

```python
@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    try:
        await event.channel.answer()
    except Exception as e:
        logger.error(f"Failed to answer channel: {e}")
```
