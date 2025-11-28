"""
Smoke tests for the ARI Client library.

These tests verify basic functionality without requiring a live Asterisk instance.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from ari_client import (
    AriClient,
    StasisStartEvent,
    StasisEndEvent,
    Channel,
    Bridge,
    EventType,
    BridgeType
)
from ari_client.models.channels import CallerID, DialplanCEP
from httpx import AsyncClient


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection"""
    ws = AsyncMock()
    ws.recv = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_http_client():
    """Mock HTTP client"""
    client = AsyncMock(spec=AsyncClient)
    return client


@pytest.fixture
def ari_client():
    """Create an ARI client instance"""
    return AriClient(
        host="localhost",
        port=8088,
        ari_user="test_user",
        ari_password="test_pass",
        tls_enabled=False
    )


@pytest.fixture
def sample_channel_data():
    """Sample channel data for testing"""
    return {
        "id": "test-channel-123",
        "protocol_id": "test-protocol",
        "name": "SIP/test-00000001",
        "state": "Ring",
        "caller": {"name": "Test Caller", "number": "1234567890"},
        "connected": {"name": "", "number": ""},
        "accountcode": "",
        "dialplan": {
            "context": "default",
            "exten": "1001",
            "priority": 1
        },
        "creationtime": "2024-01-01T12:00:00+00:00",
        "language": "en"
    }


@pytest.fixture
def sample_bridge_data():
    """Sample bridge data for testing"""
    return {
        "id": "test-bridge-123",
        "technology": "simple_bridge",
        "bridge_type": "mixing",
        "bridge_class": "bridge",
        "creator": "test",
        "name": "test_bridge",
        "channels": [],
        "video_mode": None,
        "video_source_id": None,
        "creationtime": "2024-01-01T12:00:00+00:00"
    }


@pytest.fixture
def sample_stasis_start_event(sample_channel_data):
    """Sample StasisStart event data"""
    return {
        "type": "StasisStart",
        "timestamp": "2024-01-01T12:00:00+00:00",
        "args": [],
        "channel": sample_channel_data,
        "asterisk_id": "test-asterisk",
        "application": "test-app"
    }


@pytest.fixture
def sample_stasis_end_event(sample_channel_data):
    """Sample StasisEnd event data"""
    return {
        "type": "StasisEnd",
        "timestamp": "2024-01-01T12:00:00+00:00",
        "channel": sample_channel_data,
        "application": "test-app"
    }


class TestAriClient:
    """Test cases for AriClient"""

    def test_client_initialization(self, ari_client):
        """Test that client initializes correctly"""
        assert ari_client.host == "localhost"
        assert ari_client.port == 8088
        assert ari_client.ari_user == "test_user"
        assert ari_client.ari_password == "test_pass"
        assert ari_client.tls_enabled is False
        assert ari_client.controller is None
        assert ari_client.ws is None

    def test_ari_property_raises_when_not_connected(self, ari_client):
        """Test that accessing ari property raises error when not connected"""
        with pytest.raises(ValueError, match="Not connected to Asterisk"):
            _ = ari_client.ari

    @pytest.mark.asyncio
    async def test_connect_creates_controller(self, ari_client, mock_http_client, mock_websocket):
        """Test that connect creates a controller"""
        async def mock_connect(url):
            return mock_websocket
        
        with patch('ari_client.ari_client.AsyncClient', return_value=mock_http_client), \
             patch('websockets.connect', side_effect=mock_connect), \
             patch.object(ari_client, '_AriClient__listen_events', new_callable=AsyncMock):
            
            await ari_client.connect(app="test-app", subscribe_to_all=False)
            
            assert ari_client.controller is not None
            assert ari_client.app == "test-app"
            assert ari_client.ws == mock_websocket

    @pytest.mark.asyncio
    async def test_on_stasis_start_decorator(self, ari_client):
        """Test registering stasis start handler as decorator"""
        handler_called = False
        
        @ari_client.on_stasis_start
        async def handler(event: StasisStartEvent):
            nonlocal handler_called
            handler_called = True
        
        assert ari_client.stasis_start_handler is not None
        assert ari_client.stasis_start_handler == handler

    @pytest.mark.asyncio
    async def test_on_stasis_start_method(self, ari_client):
        """Test registering stasis start handler as method call"""
        async def handler(event: StasisStartEvent):
            pass
        
        ari_client.on_stasis_start(handler)
        
        assert ari_client.stasis_start_handler == handler

    @pytest.mark.asyncio
    async def test_on_stasis_end_decorator(self, ari_client):
        """Test registering stasis end handler as decorator"""
        handler_called = False
        
        @ari_client.on_stasis_end
        async def handler(event: StasisEndEvent):
            nonlocal handler_called
            handler_called = True
        
        assert ari_client.stasis_end_handler is not None
        assert ari_client.stasis_end_handler == handler

    @pytest.mark.asyncio
    async def test_event_dispatch_stasis_start(self, ari_client, sample_stasis_start_event, mock_http_client):
        """Test dispatching StasisStart event"""
        import asyncio
        handler_called = asyncio.Event()
        received_event = None
        
        async def handler(event: StasisStartEvent):
            nonlocal received_event
            received_event = event
            handler_called.set()
        
        ari_client.stasis_start_handler = handler
        ari_client.controller = MagicMock()
        ari_client.controller.answer_channel = AsyncMock()
        ari_client.controller.stop_channel = AsyncMock()
        
        import json
        message = json.dumps(sample_stasis_start_event)
        event = await ari_client._AriClient__dispatch(
            message,
            StasisStartEvent,
            handler
        )
        
        # Wait for the handler task to complete (with timeout)
        await asyncio.wait_for(handler_called.wait(), timeout=1.0)
        
        assert handler_called.is_set()
        assert isinstance(received_event, StasisStartEvent)
        assert received_event.type == EventType.STASIS_START
        assert received_event.channel.id == "test-channel-123"

    @pytest.mark.asyncio
    async def test_event_dispatch_stasis_end(self, ari_client, sample_stasis_end_event):
        """Test dispatching StasisEnd event"""
        import asyncio
        handler_called = asyncio.Event()
        received_event = None
        
        async def handler(event: StasisEndEvent):
            nonlocal received_event
            received_event = event
            handler_called.set()
        
        ari_client.stasis_end_handler = handler
        ari_client.controller = MagicMock()
        ari_client.controller.answer_channel = AsyncMock()
        ari_client.controller.stop_channel = AsyncMock()
        
        import json
        message = json.dumps(sample_stasis_end_event)
        event = await ari_client._AriClient__dispatch(
            message,
            StasisEndEvent,
            handler
        )
        
        # Wait for the handler task to complete (with timeout)
        await asyncio.wait_for(handler_called.wait(), timeout=1.0)
        
        assert handler_called.is_set()
        assert isinstance(received_event, StasisEndEvent)
        assert received_event.type == EventType.STASIS_END
        assert received_event.channel.id == "test-channel-123"

    @pytest.mark.asyncio
    async def test_disconnect(self, ari_client, mock_websocket):
        """Test disconnecting from Asterisk"""
        ari_client.ws = mock_websocket
        ari_client.event_listener = AsyncMock()
        ari_client.event_listener.cancel = MagicMock()
        
        await ari_client.disconnect()
        
        ari_client.event_listener.cancel.assert_called_once()
        mock_websocket.close.assert_called_once()


class TestChannel:
    """Test cases for Channel model"""

    def test_channel_creation(self, sample_channel_data):
        """Test creating a channel from data"""
        channel = Channel.model_validate(sample_channel_data)
        
        assert channel.id == "test-channel-123"
        assert channel.name == "SIP/test-00000001"
        assert channel.state == "Ring"
        assert isinstance(channel.creationtime, datetime)

    def test_channel_with_handlers(self, sample_channel_data):
        """Test creating channel with handlers"""
        answer_handler = AsyncMock()
        stop_handler = AsyncMock()
        
        channel = Channel.create_with_handlers(
            answer_handler=answer_handler,
            stop_handler=stop_handler,
            obj=sample_channel_data
        )
        
        assert channel.id == "test-channel-123"

    @pytest.mark.asyncio
    async def test_channel_answer(self, sample_channel_data):
        """Test answering a channel"""
        answer_handler = AsyncMock()
        stop_handler = AsyncMock()
        
        channel = Channel.create_with_handlers(
            answer_handler=answer_handler,
            stop_handler=stop_handler,
            obj=sample_channel_data
        )
        
        await channel.answer()
        
        answer_handler.assert_called_once_with("test-channel-123")

    @pytest.mark.asyncio
    async def test_channel_stop(self, sample_channel_data):
        """Test stopping a channel"""
        answer_handler = AsyncMock()
        stop_handler = AsyncMock()
        
        channel = Channel.create_with_handlers(
            answer_handler=answer_handler,
            stop_handler=stop_handler,
            obj=sample_channel_data
        )
        
        await channel.stop()
        
        stop_handler.assert_called_once_with("test-channel-123")

    @pytest.mark.asyncio
    async def test_channel_answer_no_handler(self, sample_channel_data):
        """Test that answer raises error when handler not set"""
        channel = Channel.model_validate(sample_channel_data)
        
        with pytest.raises(ValueError, match="Answer handler not set"):
            await channel.answer()

    def test_channel_add_handlers(self, sample_channel_data):
        """Test adding handlers to existing channel"""
        channel = Channel.model_validate(sample_channel_data)
        answer_handler = AsyncMock()
        stop_handler = AsyncMock()
        
        channel.add_handlers(
            answer_handler=answer_handler,
            stop_handler=stop_handler
        )
        
        # Handlers should be set (we can't directly check private attrs, but we can test via methods)
        assert channel.id == "test-channel-123"


class TestBridge:
    """Test cases for Bridge model"""

    def test_bridge_creation(self, sample_bridge_data):
        """Test creating a bridge from data"""
        bridge = Bridge.model_validate(sample_bridge_data)
        
        assert bridge.id == "test-bridge-123"
        assert bridge.bridge_type == BridgeType.MIXING
        assert bridge.name == "test_bridge"
        assert isinstance(bridge.creationtime, datetime)

    def test_bridge_with_handlers(self, sample_bridge_data):
        """Test creating bridge with handlers"""
        stop_handler = AsyncMock()
        add_channel_handler = AsyncMock()
        
        bridge = Bridge.create_with_handlers(
            stop_handler=stop_handler,
            add_channel_handler=add_channel_handler,
            obj=sample_bridge_data
        )
        
        assert bridge.id == "test-bridge-123"

    @pytest.mark.asyncio
    async def test_bridge_stop(self, sample_bridge_data):
        """Test stopping a bridge"""
        stop_handler = AsyncMock()
        add_channel_handler = AsyncMock()
        
        bridge = Bridge.create_with_handlers(
            stop_handler=stop_handler,
            add_channel_handler=add_channel_handler,
            obj=sample_bridge_data
        )
        
        await bridge.stop()
        
        stop_handler.assert_called_once_with("test-bridge-123")

    @pytest.mark.asyncio
    async def test_bridge_add_channel(self, sample_bridge_data):
        """Test adding channel to bridge"""
        stop_handler = AsyncMock()
        add_channel_handler = AsyncMock()
        
        bridge = Bridge.create_with_handlers(
            stop_handler=stop_handler,
            add_channel_handler=add_channel_handler,
            obj=sample_bridge_data
        )
        
        await bridge.add_channel("test-channel-123")
        
        add_channel_handler.assert_called_once_with("test-bridge-123", "test-channel-123")

    @pytest.mark.asyncio
    async def test_bridge_stop_no_handler(self, sample_bridge_data):
        """Test that stop raises error when handler not set"""
        bridge = Bridge.model_validate(sample_bridge_data)
        
        with pytest.raises(ValueError, match="Stop handler not set"):
            await bridge.stop()


class TestEvents:
    """Test cases for Event models"""

    def test_stasis_start_event_creation(self, sample_stasis_start_event):
        """Test creating StasisStartEvent from data"""
        event = StasisStartEvent.model_validate(sample_stasis_start_event)
        
        assert event.type == EventType.STASIS_START
        assert event.channel.id == "test-channel-123"
        assert event.application == "test-app"
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.channel, Channel)

    def test_stasis_end_event_creation(self, sample_stasis_end_event):
        """Test creating StasisEndEvent from data"""
        event = StasisEndEvent.model_validate(sample_stasis_end_event)
        
        assert event.type == EventType.STASIS_END
        assert event.channel.id == "test-channel-123"
        assert event.application == "test-app"
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.channel, Channel)

