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
    ChannelDtmfReceivedEvent,
    ChannelCreatedEvent,
    ChannelDestroyedEvent,
    ChannelEnteredBridgeEvent,
    BridgeCreatedEvent,
    DialEvent,
    PlaybackStartedEvent,
    PlaybackFinishedEvent,
    Channel,
    Bridge,
    Playback,
    EventType,
    BridgeType,
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
def sample_playback_data():
    """Sample playback data for testing"""
    return {
        "id": "test-playback-123",
        "media_uri": "sound:hello-world",
        "target_uri": "channel:test-channel-123",
        "language": "en",
        "state": "playing",
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


@pytest.fixture
def sample_dtmf_received_event(sample_channel_data):
    """Sample ChannelDtmfReceived event data"""
    return {
        "type": "ChannelDtmfReceived",
        "timestamp": "2024-01-01T12:00:01+00:00",
        "digit": "5",
        "duration_ms": 100,
        "channel": sample_channel_data,
        "asterisk_id": "test-asterisk",
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
        @ari_client.on_stasis_start
        async def handler(event: StasisStartEvent):
            pass
        
        assert ari_client._event_handlers.get("StasisStart") is handler

    @pytest.mark.asyncio
    async def test_on_stasis_start_method(self, ari_client):
        """Test registering stasis start handler as method call"""
        async def handler(event: StasisStartEvent):
            pass
        
        ari_client.on_stasis_start(handler)
        
        assert ari_client._event_handlers.get("StasisStart") is handler

    @pytest.mark.asyncio
    async def test_on_stasis_end_decorator(self, ari_client):
        """Test registering stasis end handler as decorator"""
        @ari_client.on_stasis_end
        async def handler(event: StasisEndEvent):
            pass
        
        assert ari_client._event_handlers.get("StasisEnd") is handler

    @pytest.mark.asyncio
    async def test_on_channel_dtmf_received_decorator(self, ari_client):
        """Test registering DTMF received handler as decorator"""
        @ari_client.on_channel_dtmf_received
        async def handler(event: ChannelDtmfReceivedEvent):
            pass

        assert ari_client._event_handlers.get("ChannelDtmfReceived") is handler

    @pytest.mark.asyncio
    async def test_on_channel_dtmf_received_method(self, ari_client):
        """Test registering DTMF received handler as method call"""
        async def handler(event: ChannelDtmfReceivedEvent):
            pass

        ari_client.on_channel_dtmf_received(handler)

        assert ari_client._event_handlers.get("ChannelDtmfReceived") is handler

    @pytest.mark.asyncio
    async def test_on_event_generic_decorator(self, ari_client):
        """Test generic on_event registration"""
        @ari_client.on_event(EventType.BRIDGE_CREATED)
        async def handler(event: BridgeCreatedEvent):
            pass

        assert ari_client._event_handlers.get("BridgeCreated") is handler

    @pytest.mark.asyncio
    async def test_on_event_generic_string(self, ari_client):
        """Test generic on_event with raw string"""
        @ari_client.on_event("ChannelDestroyed")
        async def handler(event):
            pass

        assert ari_client._event_handlers.get("ChannelDestroyed") is handler

    @pytest.mark.asyncio
    async def test_on_dial_decorator(self, ari_client):
        """Test registering dial handler"""
        @ari_client.on_dial
        async def handler(event: DialEvent):
            pass

        assert ari_client._event_handlers.get("Dial") is handler

    @pytest.mark.asyncio
    async def test_on_playback_started_decorator(self, ari_client):
        """Test registering playback started handler"""
        @ari_client.on_playback_started
        async def handler(event: PlaybackStartedEvent):
            pass

        assert ari_client._event_handlers.get("PlaybackStarted") is handler

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
        channel = Channel.create_with_handlers(
            answer_handler=AsyncMock(),
            stop_handler=AsyncMock(),
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=AsyncMock(),
            redirect_handler=AsyncMock(),
            move_handler=AsyncMock(),
            play_handler=AsyncMock(),
            obj=sample_channel_data
        )
        
        assert channel.id == "test-channel-123"

    @pytest.mark.asyncio
    async def test_channel_answer(self, sample_channel_data):
        """Test answering a channel"""
        answer_handler = AsyncMock()
        
        channel = Channel.create_with_handlers(
            answer_handler=answer_handler,
            stop_handler=AsyncMock(),
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=AsyncMock(),
            redirect_handler=AsyncMock(),
            move_handler=AsyncMock(),
            play_handler=AsyncMock(),
            obj=sample_channel_data
        )
        
        await channel.answer()
        
        answer_handler.assert_called_once_with("test-channel-123")

    @pytest.mark.asyncio
    async def test_channel_stop(self, sample_channel_data):
        """Test stopping a channel"""
        stop_handler = AsyncMock()
        
        channel = Channel.create_with_handlers(
            answer_handler=AsyncMock(),
            stop_handler=stop_handler,
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=AsyncMock(),
            redirect_handler=AsyncMock(),
            move_handler=AsyncMock(),
            play_handler=AsyncMock(),
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
        
        channel.add_handlers(
            answer_handler=AsyncMock(),
            stop_handler=AsyncMock(),
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=AsyncMock(),
            redirect_handler=AsyncMock(),
            move_handler=AsyncMock(),
            play_handler=AsyncMock(),
        )
        
        assert channel.id == "test-channel-123"

    @pytest.mark.asyncio
    async def test_channel_send_dtmf(self, sample_channel_data):
        """Test sending DTMF to a channel"""
        send_dtmf_handler = AsyncMock()

        channel = Channel.create_with_handlers(
            answer_handler=AsyncMock(),
            stop_handler=AsyncMock(),
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=send_dtmf_handler,
            redirect_handler=AsyncMock(),
            move_handler=AsyncMock(),
            play_handler=AsyncMock(),
            obj=sample_channel_data
        )

        await channel.send_dtmf(dtmf="1234", between=200, duration=150)

        send_dtmf_handler.assert_called_once_with(
            channel_id="test-channel-123",
            dtmf="1234",
            before=None,
            between=200,
            duration=150,
            after=None,
        )

    @pytest.mark.asyncio
    async def test_channel_send_dtmf_no_handler(self, sample_channel_data):
        """Test that send_dtmf raises error when handler not set"""
        channel = Channel.model_validate(sample_channel_data)

        with pytest.raises(ValueError, match="Send DTMF handler not set"):
            await channel.send_dtmf(dtmf="1")

    @pytest.mark.asyncio
    async def test_channel_redirect(self, sample_channel_data):
        """Test redirecting a channel"""
        redirect_handler = AsyncMock()

        channel = Channel.create_with_handlers(
            answer_handler=AsyncMock(),
            stop_handler=AsyncMock(),
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=AsyncMock(),
            redirect_handler=redirect_handler,
            move_handler=AsyncMock(),
            play_handler=AsyncMock(),
            obj=sample_channel_data
        )

        await channel.redirect(endpoint="PJSIP/2001")

        redirect_handler.assert_called_once_with(
            channel_id="test-channel-123",
            endpoint="PJSIP/2001",
        )

    @pytest.mark.asyncio
    async def test_channel_redirect_no_handler(self, sample_channel_data):
        """Test that redirect raises error when handler not set"""
        channel = Channel.model_validate(sample_channel_data)

        with pytest.raises(ValueError, match="Redirect handler not set"):
            await channel.redirect(endpoint="PJSIP/2001")

    @pytest.mark.asyncio
    async def test_channel_move(self, sample_channel_data):
        """Test moving a channel to another Stasis app"""
        move_handler = AsyncMock()

        channel = Channel.create_with_handlers(
            answer_handler=AsyncMock(),
            stop_handler=AsyncMock(),
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=AsyncMock(),
            redirect_handler=AsyncMock(),
            move_handler=move_handler,
            play_handler=AsyncMock(),
            obj=sample_channel_data
        )

        await channel.move(app="other-app", app_args="arg1,arg2")

        move_handler.assert_called_once_with(
            channel_id="test-channel-123",
            app="other-app",
            app_args="arg1,arg2",
        )

    @pytest.mark.asyncio
    async def test_channel_move_no_handler(self, sample_channel_data):
        """Test that move raises error when handler not set"""
        channel = Channel.model_validate(sample_channel_data)

        with pytest.raises(ValueError, match="Move handler not set"):
            await channel.move(app="other-app")

    @pytest.mark.asyncio
    async def test_channel_play(self, sample_channel_data):
        """Test playing media on a channel"""
        play_handler = AsyncMock()

        channel = Channel.create_with_handlers(
            answer_handler=AsyncMock(),
            stop_handler=AsyncMock(),
            dial_handler=AsyncMock(),
            record_handler=AsyncMock(),
            snoop_handler=AsyncMock(),
            send_dtmf_handler=AsyncMock(),
            redirect_handler=AsyncMock(),
            move_handler=AsyncMock(),
            play_handler=play_handler,
            obj=sample_channel_data
        )

        await channel.play(media="sound:hello-world", lang="en")

        play_handler.assert_called_once_with(
            channel_id="test-channel-123",
            media="sound:hello-world",
            lang="en",
            offsetms=None,
            skipms=None,
            playback_id=None,
        )

    @pytest.mark.asyncio
    async def test_channel_play_no_handler(self, sample_channel_data):
        """Test that play raises error when handler not set"""
        channel = Channel.model_validate(sample_channel_data)

        with pytest.raises(ValueError, match="Play handler not set"):
            await channel.play(media="sound:hello")


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
        bridge = Bridge.create_with_handlers(
            stop_handler=AsyncMock(),
            add_channel_handler=AsyncMock(),
            record_handler=AsyncMock(),
            play_handler=AsyncMock(),
            obj=sample_bridge_data
        )
        
        assert bridge.id == "test-bridge-123"

    @pytest.mark.asyncio
    async def test_bridge_stop(self, sample_bridge_data):
        """Test stopping a bridge"""
        stop_handler = AsyncMock()
        
        bridge = Bridge.create_with_handlers(
            stop_handler=stop_handler,
            add_channel_handler=AsyncMock(),
            record_handler=AsyncMock(),
            play_handler=AsyncMock(),
            obj=sample_bridge_data
        )
        
        await bridge.stop()
        
        stop_handler.assert_called_once_with("test-bridge-123")

    @pytest.mark.asyncio
    async def test_bridge_add_channel(self, sample_bridge_data):
        """Test adding channel to bridge"""
        add_channel_handler = AsyncMock()
        
        bridge = Bridge.create_with_handlers(
            stop_handler=AsyncMock(),
            add_channel_handler=add_channel_handler,
            record_handler=AsyncMock(),
            play_handler=AsyncMock(),
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

    @pytest.mark.asyncio
    async def test_bridge_play(self, sample_bridge_data):
        """Test playing media on a bridge"""
        play_handler = AsyncMock()

        bridge = Bridge.create_with_handlers(
            stop_handler=AsyncMock(),
            add_channel_handler=AsyncMock(),
            record_handler=AsyncMock(),
            play_handler=play_handler,
            obj=sample_bridge_data
        )

        await bridge.play(media="sound:hello-world")

        play_handler.assert_called_once_with(
            bridge_id="test-bridge-123",
            media="sound:hello-world",
            lang=None,
            offsetms=None,
            skipms=None,
            playback_id=None,
            announcer_format=None,
        )

    def test_bridge_add_handlers(self, sample_bridge_data):
        """Test adding handlers to existing bridge"""
        bridge = Bridge.model_validate(sample_bridge_data)

        bridge.add_handlers(
            stop_handler=AsyncMock(),
            add_channel_handler=AsyncMock(),
            record_handler=AsyncMock(),
            play_handler=AsyncMock(),
        )

        assert bridge.id == "test-bridge-123"


class TestPlayback:
    """Test cases for Playback model"""

    def test_playback_creation(self, sample_playback_data):
        """Test creating a playback from data"""
        playback = Playback.model_validate(sample_playback_data)

        assert playback.id == "test-playback-123"
        assert playback.media_uri == "sound:hello-world"
        assert playback.state == "playing"

    @pytest.mark.asyncio
    async def test_playback_stop(self, sample_playback_data):
        """Test stopping a playback"""
        stop_handler = AsyncMock()

        playback = Playback.create_with_handlers(
            stop_handler=stop_handler,
            control_handler=AsyncMock(),
            obj=sample_playback_data,
        )

        await playback.stop()

        stop_handler.assert_called_once_with("test-playback-123")

    @pytest.mark.asyncio
    async def test_playback_control(self, sample_playback_data):
        """Test controlling a playback"""
        control_handler = AsyncMock()

        playback = Playback.create_with_handlers(
            stop_handler=AsyncMock(),
            control_handler=control_handler,
            obj=sample_playback_data,
        )

        await playback.control("pause")

        control_handler.assert_called_once_with("test-playback-123", "pause")

    @pytest.mark.asyncio
    async def test_playback_stop_no_handler(self, sample_playback_data):
        """Test that stop raises error when handler not set"""
        playback = Playback.model_validate(sample_playback_data)

        with pytest.raises(ValueError, match="Stop handler not set"):
            await playback.stop()


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

    def test_channel_dtmf_received_event_creation(self, sample_dtmf_received_event):
        """Test creating ChannelDtmfReceivedEvent from data"""
        event = ChannelDtmfReceivedEvent.model_validate(sample_dtmf_received_event)

        assert event.type == EventType.CHANNEL_DTMF_RECEIVED
        assert event.digit == "5"
        assert event.duration_ms == 100
        assert event.channel.id == "test-channel-123"
        assert event.application == "test-app"
        assert event.asterisk_id == "test-asterisk"
        assert isinstance(event.timestamp, datetime)
        assert isinstance(event.channel, Channel)

    def test_channel_destroyed_event(self, sample_channel_data):
        """Test creating ChannelDestroyedEvent"""
        event = ChannelDestroyedEvent.model_validate({
            "type": "ChannelDestroyed",
            "timestamp": "2024-01-01T12:00:00+0300",
            "cause": 16,
            "cause_txt": "Normal Clearing",
            "channel": sample_channel_data,
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.type == EventType.CHANNEL_DESTROYED
        assert event.cause == 16
        assert event.cause_txt == "Normal Clearing"
        assert isinstance(event.timestamp, datetime)

    def test_channel_entered_bridge_event(self, sample_channel_data, sample_bridge_data):
        """Test creating ChannelEnteredBridgeEvent"""
        event = ChannelEnteredBridgeEvent.model_validate({
            "type": "ChannelEnteredBridge",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "bridge": sample_bridge_data,
            "channel": sample_channel_data,
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.type == EventType.CHANNEL_ENTERED_BRIDGE
        assert isinstance(event.bridge, Bridge)
        assert isinstance(event.channel, Channel)
        assert event.bridge.id == "test-bridge-123"

    def test_bridge_created_event(self, sample_bridge_data):
        """Test creating BridgeCreatedEvent"""
        event = BridgeCreatedEvent.model_validate({
            "type": "BridgeCreated",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "bridge": sample_bridge_data,
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.type == EventType.BRIDGE_CREATED
        assert isinstance(event.bridge, Bridge)

    def test_dial_event(self, sample_channel_data):
        """Test creating DialEvent"""
        peer_data = dict(sample_channel_data)
        peer_data["id"] = "peer-channel-456"
        peer_data["name"] = "SIP/peer-00000002"

        event = DialEvent.model_validate({
            "type": "Dial",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "caller": sample_channel_data,
            "peer": peer_data,
            "dialstatus": "ANSWER",
            "dialstring": "SIP/peer",
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.type == EventType.DIAL
        assert isinstance(event.caller, Channel)
        assert isinstance(event.peer, Channel)
        assert event.peer.id == "peer-channel-456"
        assert event.dialstatus == "ANSWER"

    def test_playback_started_event(self, sample_playback_data):
        """Test creating PlaybackStartedEvent"""
        event = PlaybackStartedEvent.model_validate({
            "type": "PlaybackStarted",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "playback": sample_playback_data,
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.type == EventType.PLAYBACK_STARTED
        assert isinstance(event.playback, Playback)
        assert event.playback.id == "test-playback-123"

    def test_playback_finished_event(self, sample_playback_data):
        """Test creating PlaybackFinishedEvent"""
        data = dict(sample_playback_data)
        data["state"] = "done"

        event = PlaybackFinishedEvent.model_validate({
            "type": "PlaybackFinished",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "playback": data,
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.type == EventType.PLAYBACK_FINISHED
        assert event.playback.state == "done"

    def test_channel_varset_event_with_channel(self, sample_channel_data):
        """Test ChannelVarsetEvent with a channel"""
        from ari_client import ChannelVarsetEvent

        event = ChannelVarsetEvent.model_validate({
            "type": "ChannelVarset",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "variable": "CDR(answer)",
            "value": "2024-01-01 12:00:00",
            "channel": sample_channel_data,
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.variable == "CDR(answer)"
        assert isinstance(event.channel, Channel)

    def test_channel_varset_event_global(self):
        """Test ChannelVarsetEvent without a channel (global variable)"""
        from ari_client import ChannelVarsetEvent

        event = ChannelVarsetEvent.model_validate({
            "type": "ChannelVarset",
            "timestamp": "2024-01-01T12:00:00+00:00",
            "variable": "GLOBAL_VAR",
            "value": "42",
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert event.variable == "GLOBAL_VAR"
        assert event.channel is None

    def test_timestamp_with_non_standard_offset(self, sample_channel_data):
        """Test that timestamps with non-standard offsets (e.g. +0300) are parsed correctly"""
        event = ChannelCreatedEvent.model_validate({
            "type": "ChannelCreated",
            "timestamp": "2024-01-01T12:00:00.000+0300",
            "channel": sample_channel_data,
            "asterisk_id": "test",
            "application": "test-app",
        })

        assert isinstance(event.timestamp, datetime)
