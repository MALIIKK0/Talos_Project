# app/kafka/producer.py
import asyncio
import json
from aiokafka import AIOKafkaProducer
from DataIngestion.app.core.config import settings
from loguru import logger

producer: AIOKafkaProducer | None = None

async def get_kafka_producer() -> AIOKafkaProducer:
    global producer
    if producer is None:
        producer = AIOKafkaProducer(bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS.split(","))
        await producer.start()
        logger.info("Kafka producer started")
    return producer

async def close_kafka_producer():
    global producer
    if producer:
        await producer.stop()
        logger.info("Kafka producer stopped")
        producer = None

async def publish_event(topic: str, key: str | None, value: dict):
    p = await get_kafka_producer()
    value_bytes = json.dumps(value, default=str).encode("utf-8")
    try:
        await p.send_and_wait(topic, value=value_bytes, key=(key.encode("utf-8") if key else None))
        logger.debug("Published event to kafka topic {}", topic)
    except Exception as e:
        logger.exception("Failed to publish event to Kafka: {}", e)
        raise
