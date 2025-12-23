import os
import requests
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool

load_dotenv()

# =========================
# Jira Environment
# =========================
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL")
JIRA_EMAIL = os.getenv("JIRA_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")
JIRA_PROJECT_KEY = os.getenv("JIRA_PROJECT_KEY")
JIRA_ISSUE_TYPE = os.getenv("JIRA_ISSUE_TYPE", "Bug")

if not all([JIRA_BASE_URL, JIRA_EMAIL, JIRA_API_TOKEN, JIRA_PROJECT_KEY]):
    raise RuntimeError("Missing required Jira environment variables")

# =========================
# Pydantic Schema
# =========================
class JiraBugInput(BaseModel):
    title: str = Field(..., description="Title/summary of the bug")
    description: Union[str, Dict[str, Any]] = Field(
        ..., description="Plain text OR structured description with root cause & fixes"
    )
    priority: str = Field(default="Medium", description="Low, Medium, High, Critical")
    labels: List[str] = Field(default_factory=list)
    components: List[str] = Field(default_factory=list)

# =========================
# ADF HELPERS
# =========================
def build_adf_from_text(text: str) -> dict:
    """Convert multiline text into ADF paragraphs."""
    content = []

    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        content.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": line}]
        })

    return {
        "type": "doc",
        "version": 1,
        "content": content
    }


def build_fix_section(fix: Dict[str, Any]) -> List[dict]:
    """Build ADF blocks for one fix."""
    blocks = []

    # Fix title
    blocks.append({
        "type": "paragraph",
        "content": [{
            "type": "text",
            "text": f"🔧 Fix: {fix.get('title', 'Unnamed Fix')}",
            "marks": [{"type": "strong"}]
        }]
    })

    # Explanation
    if fix.get("explanation"):
        blocks.append({
            "type": "paragraph",
            "content": [{"type": "text", "text": fix["explanation"]}]
        })

    # Code snippet
    if fix.get("code"):
        blocks.append({
            "type": "codeBlock",
            "attrs": {"language": fix.get("language", "apex")},
            "content": [{"type": "text", "text": fix["code"]}]
        })

    return blocks


def build_structured_adf_description(root_cause: str, fixes: List[Dict[str, Any]]) -> dict:
    """Build full Jira ADF description with root cause + fixes."""
    content = []

    # Root Cause Header
    content.append({
        "type": "paragraph",
        "content": [{
            "type": "text",
            "text": "🧠 Root Cause",
            "marks": [{"type": "strong"}]
        }]
    })

    content.extend(build_adf_from_text(root_cause)["content"])

    # Fixes Header
    content.append({
        "type": "paragraph",
        "content": [{
            "type": "text",
            "text": "✅ Proposed Fixes",
            "marks": [{"type": "strong"}]
        }]
    })

    for fix in fixes:
        content.extend(build_fix_section(fix))

    return {
        "type": "doc",
        "version": 1,
        "content": content
    }

# =========================
# Jira Creation Logic
# =========================
def create_jira_bug(payload: Dict[str, Any]) -> Dict[str, str]:
    title = payload.get("title")
    description = payload.get("description")

    if not title or description is None:
        raise ValueError("Jira payload must include title and description")

    # Priority mapping
    priority_map = {
        "LOW": "Low",
        "MEDIUM": "Medium",
        "HIGH": "High",
        "CRITICAL": "Highest"
    }
    priority_value = priority_map.get(
        str(payload.get("priority", "Medium")).upper(),
        "Medium"
    )

    # Description handling (string OR structured)
    if isinstance(description, dict):
        adf_description = build_structured_adf_description(
            root_cause=description.get("root_cause", ""),
            fixes=description.get("fixes", [])
        )
    else:
        adf_description = build_adf_from_text(str(description))

    issue_payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": title,
            "description": adf_description,
            "issuetype": {"name": JIRA_ISSUE_TYPE},
            "priority": {"name": priority_value},
            "labels": payload.get("labels", []),
            "components": [{"name": c} for c in payload.get("components", [])],
        }
    }

    url = f"{JIRA_BASE_URL}/rest/api/3/issue"
    response = requests.post(
        url,
        json=issue_payload,
        auth=(JIRA_EMAIL, JIRA_API_TOKEN),
        headers={
            "Accept": "application/json",
            "Content-Type": "application/json"
        },
        timeout=15
    )

    if response.status_code not in (200, 201):
        raise RuntimeError(
            f"Jira creation failed: {response.status_code} - {response.text}"
        )

    data = response.json()
    jira_key = data["key"]
    jira_url = f"{JIRA_BASE_URL}/browse/{jira_key}"

    return {"jira_key": jira_key, "jira_url": jira_url}

# =========================
# StructuredTool Wrapper
# =========================
def create_jira_bug_wrapper(
    title: str,
    description: Union[str, Dict[str, Any]],
    priority: str = "Medium",
    labels: Optional[List[str]] = None,
    components: Optional[List[str]] = None
) -> Dict[str, str]:
    payload = {
        "title": title,
        "description": description,
        "priority": priority,
        "labels": labels or [],
        "components": components or [],
    }
    return create_jira_bug(payload)

# =========================
# Tool Instance
# =========================
jira_create_tool = StructuredTool.from_function(
    func=create_jira_bug_wrapper,
    name="create_jira_bug",
    description=(
        "Create a Jira Bug with rich description. "
        "Supports root cause, fixes, and code snippets."
    ),
    args_schema=JiraBugInput,
)
