import asyncio
import json
import os
from aiokafka import AIOKafkaConsumer
from loguru import logger
from DataIngestion.app.core.config import settings
from DataIngestion.app.db.session import get_session_factory
from DataIngestion.app.db.engine import init_engine
from DataIngestion.app.models.error_event import ErrorEvent
from sqlalchemy import select


consumer: AIOKafkaConsumer | None = None


async def start_consumer_forever():
    """Consume `orchestrator_results` and mark corresponding ErrorEvent as resolved."""
    output_topic = os.getenv("OUTPUT_TOPIC", "orchestrator_results")
    c = AIOKafkaConsumer(output_topic, bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","), group_id=settings.KAFKA_CONSUMER_GROUP)
    await c.start()
    logger.info(f"Kafka consumer started. Subscribed to: {[output_topic]}")

    # Ensure DB engine is initialized before creating sessions
    await init_engine()
    session_factory = get_session_factory()

    try:
        async for msg in c:
            try:
                payload = json.loads(msg.value.decode("utf-8"))
            except Exception:
                logger.exception("Failed to decode orchestrator result payload")
                continue

            logger.info(f"Consumed orchestrator result: {payload}")

            event_id = payload.get("event_id") or payload.get("referenceId")
            if not event_id:
                logger.warning("Orchestrator result missing event id")
                continue

            async with session_factory() as session:
                try:
                    q = select(ErrorEvent).filter(ErrorEvent.reference_id == event_id)
                    res = await session.execute(q)
                    obj = res.scalars().first()
                    if obj:
                        obj.status = "resolved"
                        await session.commit()
                        logger.info(f"Marked ErrorEvent reference_id={event_id} as resolved")
                    else:
                        logger.warning(f"No ErrorEvent found for reference_id={event_id}")
                except Exception as e:
                    logger.exception(f"Failed to update DB for event {event_id}: {e}")

    finally:
        await c.stop()


if __name__ == "__main__":
    asyncio.run(start_consumer_forever())