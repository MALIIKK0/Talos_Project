import asyncio
import json
from aiokafka import AIOKafkaConsumer
from loguru import logger
from DataIngestion.app.core.config import settings
import os
print("KAFKA_BOOTSTRAP_SERVERS =", os.getenv("KAFKA_BOOTSTRAP_SERVERS"))

consumer: AIOKafkaConsumer | None = None


async def start_consumer_forever():
    """This consumer is optional: it demonstrates consuming error_events. In our architecture the agents worker consumes directly."""
    topics = settings.KAFKA_TOPIC.split(",") if getattr(settings, "KAFKA_TOPIC", None) else ["error_events"]
    c = AIOKafkaConsumer(*topics, bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","), group_id=settings.KAFKA_CONSUMER_GROUP)
    await c.start()
    logger.info(f"Kafka consumer started. Subscribed to: {topics}")
    try:
        async for msg in c:
            payload = json.loads(msg.value.decode("utf-8"))
            logger.info(f"Consumed: {payload}")
    finally:
        await c.stop()