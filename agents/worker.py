import os
import asyncio
import json
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
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


# ---------- Kafka ----------

KAFKA = os.getenv("KAFKA", "localhost:29092")
INPUT_TOPIC = os.getenv("INPUT_TOPIC", "error_events")
OUTPUT_TOPIC = os.getenv("OUTPUT_TOPIC", "orchestrator_results")

MAX_CONCURRENCY = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENCY)


# ---------- Worker ----------

async def handle_task(consumer, producer, msg):
    async with semaphore:
        try:
            task = json.loads(msg.value.decode("utf-8"))
            event_id = task.get("referenceId")

            logger.info(f"🧠 Running orchestrator for event_id={event_id}")

            problem = build_problem(task)

            # 🚨 run blocking AI logic outside event loop
            raw_result = await asyncio.to_thread(run_orchestrator, problem)

            result = serialize_result(raw_result)

            payload = {
                "event_id": event_id,
                "result": result
            }

            await producer.send_and_wait(
                OUTPUT_TOPIC,
                json.dumps(payload).encode("utf-8")
            )

            # ✅ commit ONLY after success
            await consumer.commit()

            logger.info(f"📤 Published orchestrator result for {event_id}")

        except Exception as e:
            logger.exception(f"❌ Orchestrator task failed: {e}")


# ---------- Consumer Loop ----------

async def consume_loop():
    consumer = AIOKafkaConsumer(
        INPUT_TOPIC,
        bootstrap_servers=KAFKA.split(","),
        group_id="orchestrator-workers",

        enable_auto_commit=False,
        max_poll_interval_ms=15 * 60 * 1000,   # 15 min
        session_timeout_ms=60_000,
        heartbeat_interval_ms=20_000,
    )

    producer = AIOKafkaProducer(
        bootstrap_servers=KAFKA.split(",")
    )

    await consumer.start()
    await producer.start()

    logger.info(f"🚀 Orchestrator worker started — listening on '{INPUT_TOPIC}'")

    try:
        async for msg in consumer:
            # 🚀 hand off immediately
            asyncio.create_task(handle_task(consumer, producer, msg))

    finally:
        await consumer.stop()
        await producer.stop()


if __name__ == "__main__":
    asyncio.run(consume_loop())
