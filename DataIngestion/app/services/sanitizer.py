# app/services/sanitizer.py
import re
from typing import Dict, Any
from datetime import datetime
from dateutil import parser

EMAIL_RE = re.compile(r'([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)')
UUID_RE = re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\b')
TOKEN_RE = re.compile(r'(?i)(token|bearer|jwt)[:=]\s*([A-Za-z0-9\-\._~\+/]+=*)')
ID_RE = re.compile(r'\bID[:=]?\s*[A-Za-z0-9_-]{6,}\b')

REDACT = "[REDACTED]"

def redact_emails(text: str) -> str:
    if not text:
        return text
    return EMAIL_RE.sub(lambda m: f"[email:{hash(m.group(0)) & 0xffff}]", text)

def redact_uuids(text: str) -> str:
    if not text:
        return text
    return UUID_RE.sub("[UUID]", text)

def redact_tokens(text: str) -> str:
    if not text:
        return text
    return TOKEN_RE.sub(lambda m: f"{m.group(1)}:{REDACT}", text)

def redact_ids(text: str) -> str:
    if not text:
        return text
    return ID_RE.sub("[ID]", text)

def sanitize_string(text: str) -> str:
    if not text:
        return text
    t = redact_emails(text)
    t = redact_tokens(t)
    t = redact_uuids(t)
    t = redact_ids(t)
    return t

def normalize_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    - Normalize createdDate to a Python datetime if string provided.
    - Apply sanitization to message, stackTrace, referenceId, etc.
    - Return normalized dict with consistent keys (snake_case for storing).
    """
    out = dict(payload)  # shallow copy

    # normalize createdDate
    cd = out.get("createdDate") or out.get("created_date")
    if cd:
        if isinstance(cd, str):
            try:
                out["createdDate"] = parser.isoparse(cd)
            except Exception:
                # fallback to dateutil parser
                out["createdDate"] = parser.parse(cd)
        # if already datetime leave it

    # sanitize textual fields
    for k in ["message", "stackTrace", "messageCourt", "referenceId", "function", "source"]:
        v = out.get(k)
        if isinstance(v, str):
            out[k] = sanitize_string(v)

    # ensure keys exist
    out.setdefault("message", None)
    out.setdefault("stackTrace", None)
    return out
