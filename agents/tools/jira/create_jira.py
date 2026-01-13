import os
import requests
import json
import ast
from typing import Dict, Any, List, Optional, Union
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_core.tools import StructuredTool
import psycopg2
from psycopg2 import Error

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
# PostgreSQL Environment
# =========================
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
#DB_TABLE = os.getenv("DB_TABLE", "error_events")
DB_TABLE = os.getenv("DB_TABLE", "state_db.error_events")

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
    blocks = []

    title = fix.get("title", "Unnamed Fix")
    blocks.append(adf_heading(f"✅ {title}", level=3))

    meta = []
    if fix.get("risk"): meta.append(f"Risk: {fix['risk']}")
    if fix.get("effort"): meta.append(f"Effort: {fix['effort']}")
    if fix.get("confidence") is not None: meta.append(f"Confidence: {fix['confidence']}")
    if meta:
        blocks.append(adf_bullet_list(meta))

    if fix.get("explanation"):
        blocks.append(adf_panel([adf_paragraph(fix["explanation"])], panel_type="note"))

    if fix.get("code"):
        blocks.append({
            "type": "codeBlock",
            "attrs": {"language": fix.get("language", "apex")},
            "content": [{"type": "text", "text": fix["code"]}]
        })
    update_postgres_severity(fix["risk"])

    return blocks


def adf_text(text: str, strong: bool = False, code: bool = False) -> dict:
    node = {"type": "text", "text": text}
    marks = []
    if strong:
        marks.append({"type": "strong"})
    if code:
        marks.append({"type": "code"})
    if marks:
        node["marks"] = marks
    return node

def adf_heading(text: str, level: int = 2) -> dict:
    return {
        "type": "heading",
        "attrs": {"level": level},
        "content": [adf_text(text, strong=True)]
    }

def adf_paragraph(text: str) -> dict:
    return {"type": "paragraph", "content": [adf_text(text)]}

def adf_rule() -> dict:
    return {"type": "rule"}

def adf_panel(children: List[dict], panel_type: str = "info") -> dict:
    # panel_type: "info" | "note" | "warning" | "success"
    return {"type": "panel", "attrs": {"panelType": panel_type}, "content": children}

def adf_bullet_list(items: List[str]) -> dict:
    return {
        "type": "bulletList",
        "content": [
            {
                "type": "listItem",
                "content": [{"type": "paragraph", "content": [adf_text(it)]}]
            } for it in items if it and str(it).strip()
        ]
    }

def adf_table(rows: List[List[str]]) -> dict:
    # rows: [["Header1","Header2"],["v1","v2"]...]
    return {
        "type": "table",
        "content": [
            {
                "type": "tableRow",
                "content": [
                    {
                        "type": "tableHeader" if r_i == 0 else "tableCell",
                        "content": [{"type": "paragraph", "content": [adf_text(cell, strong=(r_i == 0))]}]
                    }
                    for cell in row
                ]
            }
            for r_i, row in enumerate(rows)
        ]
    }


def build_structured_adf_description(root_cause: str, fixes: List[Dict[str, Any]]) -> dict:
    content: List[dict] = []

    # Header
    content.append(adf_heading("⚠️ Bug Report", level=2))
    content.append(adf_panel(
        [adf_paragraph("Auto-generated ticket with structured root cause and proposed fixes.")],
        panel_type="info"
    ))
    content.append(adf_rule())

    # Root cause
    content.append(adf_heading("🧠 Root Cause", level=2))
    if root_cause and str(root_cause).strip():
        # keep your existing line splitting logic but within a panel
        rc_paras = build_adf_from_text(root_cause)["content"]
        content.append(adf_panel(rc_paras, panel_type="warning"))
    else:
        content.append(adf_panel([adf_paragraph("Root cause not provided.")], panel_type="warning"))

    content.append(adf_rule())

    # Fixes
    content.append(adf_heading("🛠️ Proposed Fixes", level=2))
    if fixes:
        for i, fix in enumerate(fixes, start=1):
            # Optional: add numbering feel
            fix = dict(fix)
            if "title" in fix and fix["title"]:
                fix["title"] = f"Option {i} — {fix['title']}"
            content.extend(build_fix_section(fix))
            if i != len(fixes):
                content.append(adf_rule())
    else:
        content.append(adf_panel([adf_paragraph("No fixes provided.")], panel_type="note"))

    return {"type": "doc", "version": 1, "content": content}

def normalize_description(description: Union[str, Dict[str, Any]]) -> Union[str, Dict[str, Any]]:
    # If already a dict -> ok
    if isinstance(description, dict):
        return description

    if not isinstance(description, str):
        return str(description)

    s = description.strip()

    # Try JSON first
    if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
        try:
            return json.loads(s)
        except Exception:
            pass

    # Try Python literal dict (single quotes) -> ast
    try:
        val = ast.literal_eval(s)
        if isinstance(val, dict):
            return val
    except Exception:
        pass

    # fallback: keep as text
    return s


# =========================
# PostgreSQL Functions
# =========================
def risk_to_severity(risk: str) -> str:
    """Map risk level to severity for PostgreSQL."""
    risk_severity_map = {
        "LOW": "LOW",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "CRITICAL"
    }
    return risk_severity_map.get(str(risk).upper(), "MEDIUM")


def extract_max_risk(fixes: List[Dict[str, Any]]) -> str:
    """Extract the maximum risk level from all fixes."""
    if not fixes:
        return "MEDIUM"
    
    risk_hierarchy = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
    max_risk = "MEDIUM"
    max_score = 2
    
    for fix in fixes:
        risk = str(fix.get("risk", "MEDIUM")).upper()
        score = risk_hierarchy.get(risk, 2)
        if score > max_score:
            max_score = score
            max_risk = risk
    
    return max_risk


def update_postgres_severity(
   # jira_key: str,   # kept for compatibility, NOT used
    severity: str,
    error_event_id: Optional[str] = None  # kept for compatibility, NOT used
) -> bool:
    """Update ONLY the severity of the latest error_event row."""
    try:
        conn = psycopg2.connect(
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()

        update_query = f"""
            UPDATE {DB_TABLE}
            SET severity = %s
            WHERE id = (
                SELECT id
                FROM {DB_TABLE}
                ORDER BY created_at DESC
                LIMIT 1
            )
        """

        cursor.execute(update_query, (severity,))
        conn.commit()

        rows_updated = cursor.rowcount

        cursor.close()
        conn.close()

        if rows_updated == 1:
            print(f"✅ PostgreSQL updated latest severity={severity}")
            return True
        else:
            print("⚠️ PostgreSQL: No row updated")
            return False

    except Error as e:
        print(f"❌ PostgreSQL Error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during PostgreSQL update: {e}")
        return False


# =========================
# Jira Creation Logic
# =========================
def create_jira_bug(payload: Dict[str, Any]) -> Dict[str, str]:
    title = payload.get("title")
    description = normalize_description(payload.get("description"))

    # normalize: if description is a JSON string, parse it
    if isinstance(description, str):
        s = description.strip()
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                description = json.loads(s)
            except Exception:
                pass

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

    print("=== JIRA DEBUG ===")
    print("description python type:", type(description))
    print("description preview:", str(description)[:300])
    print("==================")

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

    print("=== JIRA PAYLOAD SENT ===")
    print("description field type:", type(issue_payload["fields"]["description"]))
    print(json.dumps(issue_payload["fields"]["description"], indent=2)[:1500])
    print("=========================")

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

    # Extract max risk from fixes and update PostgreSQL severity
    if isinstance(description, dict):
        fixes = description.get("fixes", [])
        max_risk = extract_max_risk(fixes)
        severity = risk_to_severity(max_risk)
        #update_postgres_severity(jira_key, severity)

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



#mainnnnnnnnn

if __name__ == "__main__":
    res = create_jira_bug_wrapper(
        title="TEST ADF DESIGN",
        description={
            "root_cause": "This is a test root cause.",
            "fixes": [
                {
                    "title": "Wrap update in try/catch",
                    "explanation": "Catch DmlException and log it properly.",
                    "code": "try {\n  update l;\n} catch (DmlException e) {\n  System.debug(e.getMessage());\n}",
                    "language": "apex",
                    "risk": "LOW",
                    "effort": "LOW",
                    "confidence": 0.9
                }
            ]
        },
        priority="Medium",
        labels=["talos", "adf-test"],
        components=["JiraTool"]
    )
    print(res)