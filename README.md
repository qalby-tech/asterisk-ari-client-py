# ARI Client Library

A Python client library for Asterisk REST Interface (ARI) that provides an object-oriented approach to managing channels, bridges, and events.

## Architecture

The library follows a clean architecture pattern with separation of concerns:

- **AriClient**: Main client class that handles WebSocket connections and event dispatching
- **AriClientController**: Separate controller class that handles all HTTP API operations
- **Model Objects**: Bridge, Channel, and Event objects that encapsulate state and provide methods for actions

### Key Design Principles

1. **All actions are performed via Bridge, Channel, and Event objects** - This ensures that operations are context-aware and type-safe
2. **Controller is separate from client** - The controller handles HTTP operations, while the client manages WebSocket connections
3. **Objects are self-contained** - Each Bridge, Channel, and Event object has its own controller reference for performing actions

## Installation

```bash
pip install -r requirements.txt
# or using uv
uv sync
```

## Quick Start

```python
import asyncio
from ari_client import AriClient, StasisStartEvent, StasisEndEvent
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create client
client = AriClient(
    host="localhost",
    port=8088,
    ari_user="asterisk",
    ari_password="asterisk",
    tls_enabled=False
)

# Define event handlers
@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    logger.info(f"Channel entered Stasis: {event.channel.id}")
    
    # Answer the channel using the channel object
    await event.channel.answer()
    
    # Create a bridge using the controller
    bridge = await client.ari.create_bridge(type="mixing")
    
    # Add channel to bridge using the bridge object
    await bridge.add_channel(event.channel.id)
    
    # Create external media using the controller
    external_media = await client.ari.create_external_media(
        external_host="192.168.1.100:10000",
        format="ulaw"
    )
    
    # Add external media to bridge
    await bridge.add_channel(external_media.id)
    await external_media.answer()

@client.on_stasis_end
async def on_stasis_end(event: StasisEndEvent):
    logger.info(f"Channel left Stasis: {event.channel.id}")

# Main function
async def main():
    await client.connect(app="myapp", subscribe_to_all=True)
    

    # Originate a call
    channel = await client.ari.originate(
        endpoint="PJSIP/1001",
        timeout=30
    )
    logger.info(f"Originated channel: {channel.id}")
    
    # Keep running
    try:
        await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

## Core Concepts

### Event Objects

Event objects (`StasisStartEvent`, `StasisEndEvent`) are received when channels enter or leave your Stasis application. They contain channel information and can be used to access the channel object for performing actions.

**Note:** To create bridges, external media, or originate calls, use the controller via `client.ari` rather than event methods.

### Channel Objects

Channel objects represent Asterisk channels and provide methods for channel operations:

- `channel.answer()` - Answer the channel
- `channel.stop()` - Hang up the channel

### Bridge Objects

Bridge objects represent Asterisk bridges and provide methods for bridge operations:

- `bridge.add_channel(channel_id)` - Add a channel to the bridge
- `bridge.stop()` - Destroy the bridge

## API Reference

### AriClient

Main client class for connecting to Asterisk ARI.

#### Constructor

```python
AriClient(
    host: str,
    port: int,
    ari_user: str,
    ari_password: str,
    tls_enabled: bool = False
)
```

#### Methods

- `async connect(app: str, subscribe_to_all: bool = False)` - Connect to Asterisk and start listening for events
- `on_stasis_start(handler)` - Register handler for StasisStart events (can be used as decorator)
- `on_stasis_end(handler)` - Register handler for StasisEnd events (can be used as decorator)
- `ari` - Get the ari controller instance for performing actions outside event handlers
- `async disconnect()` - Disconnect from Asterisk

#### Event Handlers

Event handlers can be registered using decorators or method calls:

```python
# As decorator
@client.on_stasis_start
async def handler(event: StasisStartEvent):
    pass

# As method call
async def handler(event: StasisStartEvent):
    pass

client.on_stasis_start(handler)
```

### AriClientController

Controller class that handles all HTTP API operations. Typically accessed via `client.ari` or through event/channel/bridge objects.

#### Methods

- `async answer_channel(channel_id: str)` - Answer a channel
- `async stop_channel(channel_id: str)` - Hang up a channel
- `async create_bridge(type: str, bridge_id: Optional[str] = None, name: Optional[str] = None) -> Bridge` - Create a bridge
- `async bridge_add_channel(bridge_id: str, channel_id: str)` - Add channel to bridge
- `async stop_bridge(bridge_id: str)` - Destroy a bridge
- `async create_external_media(...) -> Channel` - Create external media channel
- `async originate(...) -> Channel` - Originate a new channel

### Event

Base event class for all ARI events.

### StasisStartEvent

Event received when a channel enters your Stasis application.

#### Properties

- `type: EventType` - Event type (STASIS_START)
- `timestamp: datetime` - Event timestamp
- `args: List[str]` - Arguments passed to the Stasis application
- `channel: Channel` - The channel that entered Stasis
- `asterisk_id: str` - Asterisk instance ID
- `application: str` - Application name

### StasisEndEvent

Event received when a channel leaves your Stasis application.

#### Properties

- `type: EventType` - Event type (STASIS_END)
- `timestamp: datetime` - Event timestamp
- `channel: Channel` - The channel that left Stasis
- `application: str` - Application name

### Channel

Represents an Asterisk channel.

#### Properties

- `id: str` - Channel unique identifier
- `name: str` - Channel name
- `state: str` - Channel state
- `caller: CallerID` - Caller information
- `connected: CallerID` - Connected party information
- `creationtime: datetime` - Channel creation timestamp

#### Methods

- `async answer()` - Answer the channel
- `async stop()` - Hang up the channel
- `add_controller(controller: AriClientController)` - Add controller for performing actions

### Bridge

Represents an Asterisk bridge.

#### Properties

- `id: str` - Bridge unique identifier
- `bridge_type: BridgeType` - Type of bridge (MIXING, HOLDING)
- `name: str` - Bridge name
- `channels: List[str]` - List of channel IDs in the bridge
- `video_mode: Optional[VideoMode]` - Video mode if applicable

#### Methods

- `async add_channel(channel_id: str)` - Add a channel to the bridge
- `async stop()` - Destroy the bridge

## Best Practices

1. **Always use event/channel/bridge objects for actions** - This ensures proper context and type safety
2. **Handle exceptions in event handlers** - The library automatically logs exceptions, but you should handle them appropriately
3. **Use the controller for operations** - Access the controller via `client.ari` to create bridges, external media, or originate calls
4. **Store bridge/channel references** - If you need to reference bridges or channels later, store them in a dictionary or similar structure

## Example: Call Bridging

```python
bridge_map: dict[str, Bridge] = {}

@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    # Skip external media channels
    if event.channel.name.startswith("UnicastRTP"):
        return
    
    # Answer the incoming channel
    await event.channel.answer()
    
    # Create a mixing bridge using the controller
    bridge = await client.ari.create_bridge(type="mixing,proxy_media")
    
    # Add the channel to the bridge
    await bridge.add_channel(event.channel.id)
    
    # Create external media for streaming using the controller
    external_media = await client.ari.create_external_media(
        external_host="192.168.1.100:10000",
        format="ulaw"
    )
    
    # Add external media to bridge and answer it
    await bridge.add_channel(external_media.id)
    await external_media.answer()
    
    # Store bridge reference for cleanup
    bridge_map[event.channel.id] = bridge

@client.on_stasis_end
async def on_stasis_end(event: StasisEndEvent):
    # Clean up bridge when channel leaves
    bridge = bridge_map.pop(event.channel.id, None)
    if bridge:
        await bridge.stop()
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

## License

[Your License Here]

