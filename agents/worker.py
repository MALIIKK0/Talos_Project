import os
import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.structs import TopicPartition, OffsetAndMetadata
from loguru import logger
from langchain_core.messages import BaseMessage

from agents.coordinator.agent import run_orchestrator


# ---------- Utils ----------

def serialize_result(result):
    if isinstance(result, dict):
        out = {}
        for k, v in result.items():
            if isinstance(v, list):
                out[k] = [
                    {
                        "type": m.type,
                        "content": m.content,
                    } if isinstance(m, BaseMessage) else str(m)
                    for m in v
                ]
            elif isinstance(v, BaseMessage):
                out[k] = {
                    "type": v.type,
                    "content": v.content,
                }
            else:
                out[k] = v
        return out
    return str(result)


def build_problem(event: dict) -> str:
    stack = event.get("stackTrace") or ""
    if len(stack) > 2000:
        stack = stack[:2000] + "\n...[truncated]"

    return (
        f"Error event:\n"
        f"Source: {event.get('source')}\n"
        f"Function: {event.get('function')}\n"
        f"Message: {event.get('message')}\n"
        f"Reference: {event.get('referenceId')}\n"
        f"Stack:\n{stack}\n"
    )


# ---------- Kafka Config ----------

<<<<<<< HEAD
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:29092")
INPUT_TOPIC = os.getenv("KAFKA_TOPIC", "error_events")
=======
KAFKA = os.getenv("KAFKA", "localhost:29092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "error_events")
>>>>>>> 754bb64d906ae5488224821736a0146af0de0344
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "orchestrator_results")

GROUP_ID = "orchestrator-workers"

MAX_CONCURRENCY = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

shutdown_event = asyncio.Event()


# ---------- Worker ----------

async def handle_task(consumer, producer, msg):
    async with semaphore:
        try:
            task = json.loads(msg.value.decode("utf-8"))
            event_id = task.get("referenceId")

            logger.info(f"🧠 Running orchestrator for event_id={event_id}")

            problem = build_problem(task)

            # run blocking AI outside event loop
            raw_result = await asyncio.to_thread(run_orchestrator, problem)
            result = serialize_result(raw_result)

            payload = {
                "event_id": event_id,
                "result": result,
            }

            await producer.send_and_wait(
                OUTPUT_TOPIC,
                json.dumps(payload).encode("utf-8"),
            )

            # ✅ commit ONLY this message offset
            tp = TopicPartition(msg.topic, msg.partition)
            offsets = {tp: OffsetAndMetadata(msg.offset + 1, "")}
            await consumer.commit(offsets=offsets)

            logger.info(f"📤 Published result for {event_id}")

        except Exception as e:
            logger.exception(f"❌ Orchestrator task failed: {e}")


# ---------- Consumer Loop ----------

async def consume_loop():
    consumer = AIOKafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(","),
        group_id=GROUP_ID,
        enable_auto_commit=False,
        max_poll_interval_ms=15 * 60 * 1000,
        session_timeout_ms=60_000,
        heartbeat_interval_ms=20_000,
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS.split(",")
    )

    await consumer.start()
    await producer.start()

    logger.info(f"🚀 Orchestrator worker started — listening on '{INPUT_TOPIC}'")

    tasks: set[asyncio.Task] = set()

    try:
        async for msg in consumer:
            if shutdown_event.is_set():
                break

            task = asyncio.create_task(handle_task(consumer, producer, msg))
            tasks.add(task)
            task.add_done_callback(tasks.discard)

    except asyncio.CancelledError:
        pass

    finally:
        shutdown_event.set()
        logger.info("🛑 Shutting down orchestrator worker...")

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        await consumer.stop()
        await producer.stop()

        logger.info("👋 Worker stopped cleanly")


# ---------- Entry Point ----------

if __name__ == "__main__":
    try:
        asyncio.run(consume_loop())
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
