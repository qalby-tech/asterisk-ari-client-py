import asyncio
from ari_client import AriClient
from ari_client import StasisStartEvent, StasisEndEvent
from ari_client import Bridge
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = AriClient(
    host="localhost", 
    port=8088, 
    ari_user="user", 
    ari_password="user", 
    tls_enabled=False
)

bridge_map: dict[str, Bridge] = {}

@client.on_stasis_start
async def on_stasis_start(event: StasisStartEvent):
    logger.info(f"Stasis started: {event}")

    if event.channel.name.startswith("UnicastRTP"):
        return
    
    # All actions are done via event, channel, and bridge objects
    await event.channel.answer()
    bridge = await client.ari.create_bridge(type="mixing,proxy_media")
    await bridge.add_channel(event.channel.id)
    external_media = await client.ari.create_external_media(
        external_host="localhost:10000",
        format="ulaw",
    )
    await bridge.add_channel(external_media.id)
    await external_media.answer()
    bridge_map[event.channel.id] = bridge

@client.on_stasis_end
async def on_stasis_end(event: StasisEndEvent):
    logger.info(f"Stasis ended: {event}")
    bridge = bridge_map.pop(event.channel.id, None)
    if bridge:
        await bridge.stop()
    else:
        logger.warning(f"Bridge not found for channel: {event.channel.id}")
    pass

async def main():
    
    await client.connect(app="assistant2", subscribe_to_all=True)

    channel = await client.ari.originate(
        endpoint="SIP/1001",
        timeout=30,
    )
    logger.info(f"Originated channel: {channel.id}")
    
    # Keep running until interrupted
    try:
        await asyncio.sleep(15)  # Run for 15 seconds, or until interrupted
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Shutting down...")
