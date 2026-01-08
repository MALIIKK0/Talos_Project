"""
FastAPI application entrypoint (optimized).
"""
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import uvicorn
from asyncio import create_task
from DataIngestion.app.core.config import settings
from DataIngestion.app.api.routes import router as api_router
from DataIngestion.app.db.engine import init_engine, dispose_engine
from DataIngestion.app.db.init_db import validate_connection, init_db
from DataIngestion.app.kafka.producer import get_kafka_producer, close_kafka_producer
from DataIngestion.app.kafka.consumer import start_consumer_forever

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Unified startup & shutdown logic.
    """
    logger.info("🚀 Starting service...")

    # Database startup
    try:
        await init_engine()
        await validate_connection()
        await init_db()
        logger.info("✅ Database ready")
    except Exception as e:
        logger.error(f"❌ Database error: {e}")

    # Kafka
    try:
        await get_kafka_producer()
        logger.info("✅ Kafka producer ready")
    except Exception as e:
        logger.warning(f"⚠ Kafka unavailable: {e}")
    # --------------------------------------------------------
    # 🔥 START THE KAFKA CONSUMER IN BACKGROUND
    # --------------------------------------------------------
    try:
        app.state.consumer_task = create_task(start_consumer_forever())
        logger.info("🔁 Kafka consumer started in background")
    except Exception as e:
        logger.error(f"❌ Failed to start Kafka consumer: {e}")

    yield


    logger.info("🛑 Shutting down...")

    await close_kafka_producer()
    await dispose_engine()

    logger.info("👋 Shutdown complete")


app = FastAPI(
    title=settings.SERVICE_NAME,
    docs_url="/docs",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)



@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = datetime.utcnow()
    response = await call_next(request)
    duration = (datetime.utcnow() - start).total_seconds() * 1000
    logger.info(f"{request.method} {request.url.path} → {response.status_code} ({duration:.2f}ms)")
    return response



if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.is_development,
    )
