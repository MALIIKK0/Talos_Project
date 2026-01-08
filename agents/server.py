# server.py
import asyncio
import os
import traceback
from datetime import datetime
from typing import Any, Dict

from bson import ObjectId
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from pymongo import MongoClient

# Import your orchestrator
from agents.coordinator.agent import run_orchestrator

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = os.getenv("MONGO_DB", "fastapi_db")
COLLECTION_NAME = os.getenv("MONGO_COLLECTION", "application_logs")

if not MONGO_URI:
    raise RuntimeError("MONGO_URI not set in environment. Set it in .env or env variables.")

# Initialize Mongo client
client = MongoClient(
    MONGO_URI,
    tls=True,
    tlsAllowInvalidCertificates=False
)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]
orchestrator_results_col = db.get_collection("orchestrator_results")

app = FastAPI(title="Application Log Receiver & Orchestrator")

# ----------------------
# Helpers
# ----------------------
def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB types to JSON-serializable format."""
    serialized = dict(doc)
    if "_id" in serialized:
        serialized["_id"] = str(serialized["_id"])
    if "_received_at" in serialized and isinstance(serialized["_received_at"], datetime):
        # Return in ISO-8601 with trailing Z (UTC)
        serialized["_received_at"] = serialized["_received_at"].isoformat() + "Z"
    return serialized

def prepare_doc(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Prepare a document to be stored in MongoDB."""
    doc = dict(payload)
    doc["_received_at"] = datetime.utcnow()
    return doc

async def call_orchestrator_and_store(doc: Dict[str, Any]) -> None:
    """
    Call the orchestrator (sync or async) and store the result in the DB.
    - If run_orchestrator is synchronous, run it in a thread via asyncio.to_thread.
    - If it is async, await it directly.
    """
    # Keep a stable reference to the source document ID and data
    source_doc_id = doc.get("_id")
    try:
        # Detect if run_orchestrator is coroutine function or not
        if asyncio.iscoroutinefunction(run_orchestrator):
            result = await run_orchestrator(doc)
        else:
            # Run blocking function in a thread so we don't block the event loop
            result = await asyncio.to_thread(run_orchestrator, doc)

        # Save result to DB for auditing/debugging
        res_doc = {
            "_source_doc_id": str(source_doc_id) if source_doc_id is not None else None,
            "_input_doc": serialize_doc(doc),
            "_result": result,
            "_processed_at": datetime.utcnow(),
        }
        orchestrator_results_col.insert_one(res_doc)

    except Exception as e:
        # Log full traceback into orchestrator_results so you can inspect failures
        tb = traceback.format_exc()
        err_doc = {
            "_source_doc_id": str(source_doc_id) if source_doc_id is not None else None,
            "_input_doc": serialize_doc(doc),
            "_error": str(e),
            "_traceback": tb,
            "_failed_at": datetime.utcnow(),
        }
        try:
            orchestrator_results_col.insert_one(err_doc)
        except Exception:
            # If even storing the error fails, print to stdout (last resort)
            print("Failed to store orchestrator error doc:")
            print(err_doc)
            print("Traceback:")
            print(tb)

# ----------------------
# POST endpoint
# ----------------------
@app.post("/application-log")
async def receive_log(request: Request):
    """
    Accept JSON, form data, or query params.
    Insert the document to MongoDB, then schedule the orchestrator in background.
    """
    data = None
    # Try parsing JSON body
    try:
        data = await request.json()
    except Exception:
        # Try form data
        try:
            form = await request.form()
            if form:
                data = dict(form)
        except Exception:
            data = None

    # If still no data, use query params
    if not data:
        data = dict(request.query_params)

    if not data:
        raise HTTPException(status_code=400, detail="Empty request. Send JSON, form data, or query params.")

    # Prepare and insert into MongoDB
    doc = prepare_doc(data)
    try:
        inserted = collection.insert_one(doc)
        inserted_id = inserted.inserted_id
        # attach actual _id to the doc so the background task sees it
        doc["_id"] = inserted_id
        stored_doc = serialize_doc(doc)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB insert failed: {e}")

    # Schedule the orchestrator in the background (non-blocking)
    try:
        # Use create_task so the HTTP response returns immediately
        asyncio.create_task(call_orchestrator_and_store(doc))
    except Exception as e:
        # If scheduling failed, still return success for insert, but report the scheduling error
        return {
            "ok": True,
            "inserted_id": str(inserted_id),
            "stored_data": stored_doc,
            "orchestrator_scheduled": False,
            "orchestrator_error": str(e),
        }

    return {
        "ok": True,
        "inserted_id": str(inserted_id),
        "stored_data": stored_doc,
        "orchestrator_scheduled": True,
    }

# ----------------------
# GET endpoint
# ----------------------
@app.get("/application-log")
async def get_logs(limit: int = 50):
    """
    Retrieve the latest logs (descending by _received_at).
    """
    try:
        cursor = collection.find().sort("_received_at", -1).limit(limit)
        logs = [serialize_doc(doc) for doc in cursor]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB query failed: {e}")

    return {"ok": True, "count": len(logs), "logs": logs}

# ----------------------
# Optional: Inspect orchestrator results
# ----------------------
@app.get("/orchestrator-results")
async def get_orchestrator_results(limit: int = 50):
    try:
        cursor = orchestrator_results_col.find().sort("_processed_at", -1).limit(limit)
        results = [serialize_doc(doc) for doc in cursor]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"MongoDB query failed: {e}")

    return {"ok": True, "count": len(results), "results": results}
