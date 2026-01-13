# agents/context_retrieval/agent.py
import sys
import os
import json
import re
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from pydantic import BaseModel, Field

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from deepagents import create_deep_agent
from langchain_core.tools import StructuredTool
import weaviate
from weaviate.auth import Auth
from agents.LLMs import context_retrieval_brain_openrouter,coordinator_brain_gemini  # This should be an instance
from tavily import TavilyClient
from simple_salesforce import Salesforce, SalesforceAuthenticationFailed

load_dotenv()

# ========================================
# AGENT PROMPT
# ========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
prompt_file_path = os.path.join(BASE_DIR, "prompt.md")

with open(prompt_file_path, "r", encoding="utf-8") as f:
    PROMPT = f.read()

# ========================================
# WEAVIATE CLIENT SETUP
# ========================================
WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")

# connect safely (if env vars missing, client remains None)
client = None
try:
    client = weaviate.connect_to_weaviate_cloud(
        cluster_url=WEAVIATE_URL,
        auth_credentials=Auth.api_key(WEAVIATE_API_KEY),
    )
    print("Weaviate ready:", client.is_ready())
except Exception as e:
    print("Weaviate connection failed:", e)

CLASS_NAME = "Errors"

def close_client():
    global client
    try:
        if client:
            client.close()
            print("Weaviate client closed successfully.")
    except Exception as e:
        print("Error closing Weaviate client:", e)

def clean_text(text: str, max_len: int = 600) -> str:
    """Normalize and truncate text safely"""
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_len]

# ========================================
# TAVILY CLIENT
# ========================================
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
tavily_client = None
try:
    tavily_client = TavilyClient(api_key=TAVILY_API_KEY)
except Exception as e:
    print("Tavily client init failed:", e)

# ========================================
# SALESFORCE CLIENT
# ========================================
SF_USERNAME = os.getenv("SF_USERNAME")
SF_PASSWORD = os.getenv("SF_PASSWORD")
SF_SECURITY_TOKEN = os.getenv("SF_SECURITY_TOKEN")

sf = None
try:
    if SF_USERNAME and SF_PASSWORD:
        sf = Salesforce(
            username=SF_USERNAME,
            password=SF_PASSWORD,
            security_token=SF_SECURITY_TOKEN
        )
        print("✅ Salesforce connection established.")
    else:
        print("Salesforce env vars not set; skipping connection.")
except SalesforceAuthenticationFailed as e:
    print("❌ Salesforce authentication failed:", str(e))
    sf = None  # continue without Salesforce
except Exception as e:
    print("❌ Salesforce connection error:", e)
    sf = None

# ========================================
# INPUT MODEL - CRITICAL FIX
# ========================================
class ErrorInput(BaseModel):
    """Input for the context retrieval tool"""
    error_data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Error JSON object with keys like _id, stackTrace, message, source, function, etc."
    )

# ========================================
# SEARCH FUNCTIONS
# ========================================
def search_weaviate(query: str) -> List[Dict[str, str]]:
    if not client:
        return []

    try:
        collection = client.collections.use(CLASS_NAME)
        response = collection.query.near_text(
            query=query,
            limit=3,
            return_properties=["error", "solution", "category"],
        )

        results = []
        for obj in response.objects or []:
            p = obj.properties or {}
            results.append({
                "error": p.get("error", ""),
                "solution": p.get("solution", ""),
                "category": p.get("category", ""),
            })
        return results
    except Exception as e:
        print("Weaviate search error:", e)
        return []

def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    if not tavily_client:
        return []

    try:
        resp = tavily_client.search(
            query=query,
            max_results=max_results,
            search_depth="basic",
            include_raw_content=False,
        )
        return [{
            "title": r.get("title", ""),
            "content": r.get("content", "")
        } for r in resp.get("results", [])]
    except Exception as e:
        print("Web search error:", e)
        return []

# ======================================================
# SUMMARIZATION (RULE-BASED, FAST, SAFE)
# ======================================================
def summarize_weaviate(items: List[Dict[str, str]]) -> Dict[str, Any]:
    if not items:
        return {}

    propositions = []
    for it in items:
        if it["solution"]:
            propositions.append(clean_text(it["solution"], 200))

    return {
        "propositions": list(dict.fromkeys(propositions))[:3],
    }

def summarize_web(items: List[Dict[str, str]]) -> Dict[str, Any]:
    if not items:
        return {}

    propositions = []
    for it in items:
        if it["content"]:
            propositions.append(clean_text(it["content"], 200))

    return {
        "propositions": list(dict.fromkeys(propositions))[:3],
    }

# ========================================
# SALESFORCE HELPERS & FIELD DETECTION
# ========================================

# simple in-memory cache for sObject describe() results (per process)
_DESCRIBE_CACHE: Dict[str, Dict[str, Any]] = {}

# Field synonyms for common mappings (expand as you encounter more cases)
FIELD_SYNONYMS = {
    "Contact": {
        "name": ["LastName", "FirstName", "Name"],
    },
    "Account": {
        "name": ["Name"]
    },
    "Lead": {
        "name": ["LastName", "FirstName"]
    }
}

def extract_missing_fields_from_message(message: str) -> List[str]:
    """
    Parse typical Salesforce REQUIRED_FIELD_MISSING / 'Required fields are missing' messages.
    Returns a list of field tokens (API-like or label-like).
    """
    if not message:
        return []
    fields = set()

    # "Required fields are missing: [Name]" or "Required fields are missing: [Name, Email]"
    m = re.search(r"Required fields are missing\s*:\s*\[([^\]]+)\]", message, flags=re.IGNORECASE)
    if m:
        for f in re.split(r"[,\:]\s*", m.group(1)):
            fn = f.strip()
            if fn:
                fields.add(fn)

    # "REQUIRED_FIELD_MISSING, Required fields are missing: [Name]: [Name]" (some logs repeat)
    m2 = re.findall(r"REQUIRED_FIELD_MISSING(?:,|:)?\s*(?:Required fields are missing:)?\s*\[?([A-Za-z0-9_]+)\]?", message, flags=re.IGNORECASE)
    for f in m2:
        if f:
            fields.add(f.strip())

    # fallback: "Missing required fields: Name, Email"
    m3 = re.search(r"Missing required fields?\s*[:\-]\s*([A-Za-z0-9_,\s]+)", message, flags=re.IGNORECASE)
    if m3:
        for f in re.split(r"[,\s]+", m3.group(1)):
            fn = f.strip()
            if fn:
                fields.add(fn)

    # fallback heuristic: bracketed tokens anywhere
    m4 = re.findall(r"\[([A-Za-z0-9_,\s]+)\]", message)
    for group in m4:
        for f in re.split(r"[,\s]+", group):
            fn = f.strip()
            if fn and len(fn) <= 100:
                fields.add(fn)

    return list(fields)

def get_sobject_fields_metadata(sobject_api_name: str) -> Dict[str, Any]:
    """
    Return a mapping apiName -> metadata for fields on the sObject.
    Uses a simple in-memory cache to avoid repeated describe calls.
    """
    if not sf or not sobject_api_name:
        return {}

    # Normalize: try to use passed form (e.g., Contact, Account)
    cache_key = sobject_api_name
    if cache_key in _DESCRIBE_CACHE:
        return _DESCRIBE_CACHE[cache_key]

    desc = None
    try:
        # simple_salesforce exposes objects as attributes: sf.Contact.describe()
        # Try direct attribute first
        obj = getattr(sf, sobject_api_name, None)
        if obj:
            desc = obj.describe()
    except Exception:
        desc = None

    # try a few fallbacks: suffix __c, PascalCase, upper first char
    if not desc:
        try_names = []
        if not sobject_api_name.endswith("__c"):
            try_names.append(sobject_api_name + "__c")
        try_names.append(sobject_api_name[0].upper() + sobject_api_name[1:] if sobject_api_name else sobject_api_name)
        for tn in try_names:
            try:
                obj = getattr(sf, tn, None)
                if obj:
                    desc = obj.describe()
                    if desc:
                        break
            except Exception:
                continue

    if not desc:
        _DESCRIBE_CACHE[cache_key] = {}
        return {}

    fields_meta = {}
    for f in desc.get("fields", []):
        fields_meta[f["name"]] = {
            "label": f.get("label"),
            "type": f.get("type"),
            "nillable": f.get("nillable"),
            "length": f.get("length"),
            "inlineHelpText": f.get("inlineHelpText"),
            "picklistValues": [{"value": p.get("value"), "active": p.get("active")} for p in f.get("picklistValues", [])] if f.get("picklistValues") else [],
            "deprecatedAndHidden": f.get("deprecatedAndHidden", False)
        }

    _DESCRIBE_CACHE[cache_key] = fields_meta
    return fields_meta

def map_requested_field_to_api(sobject: str, requested: str, sobject_fields: Dict[str, Any]) -> Tuple[str, List[str]]:
    """
    Try to map a requested field string (from error) to one or more API field names.
    Returns best_match (or empty string) and a list of candidate suggestions.
    """
    if not requested:
        return "", []

    requested_str = requested.strip()
    # direct API name match
    if requested_str in sobject_fields:
        return requested_str, [requested_str]

    # case-insensitive exact
    for api in sobject_fields.keys():
        if api.lower() == requested_str.lower():
            return api, [api]

    # try synonyms mapping based on sObject
    candidates = []
    syn_key = requested_str.lower()
    if sobject and sobject in FIELD_SYNONYMS and syn_key in FIELD_SYNONYMS[sobject]:
        for syn in FIELD_SYNONYMS[sobject][syn_key]:
            if syn in sobject_fields:
                candidates.append(syn)

    # fuzzy: substring matches in API name or label
    if not candidates:
        for api, meta in sobject_fields.items():
            if requested_str.lower() in api.lower():
                candidates.append(api)
            else:
                lbl = (meta.get("label") or "").lower()
                if requested_str.lower() in lbl:
                    candidates.append(api)

    # dedupe
    candidates = list(dict.fromkeys(candidates))
    return (candidates[0] if candidates else "", candidates)

def get_apex_classes() -> List[Dict[str, Any]]:
    """Retrieve ApexClass Id, Name, Body (full body)"""
    if not sf:
        return []
    try:
        result = sf.query_all("SELECT Id, Name, Body FROM ApexClass")
        return result.get("records", [])
    except Exception as e:
        print("❌ Error fetching Apex classes:", e)
        return []

def get_test_classes(related_class_name: Optional[str] = None,
                     related_sobject: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Improved test-class detection:
      - Detects tests by @isTest, testmethod, System.assert, or class name ending with 'Test'
      - Detects references to the related class via multiple patterns:
          word boundary, 'new ClassName(', 'ClassName.' (method call), etc.
      - Detects references to sObject via plain name, __c form, List< SObject >, new SObject( ... )
      - Inclusion logic is tolerant: tests are included when either test-like markers OR references match,
        depending on which filters are provided.
    """
    apex_list = get_apex_classes()
    if not apex_list:
        return []

    def looks_like_test(body: str, class_name: str) -> bool:
        if not body:
            return False
        lb = body.lower()
        if "@istest" in lb or "testmethod" in lb or "system.assert" in lb:
            return True
        if class_name and class_name.lower().endswith("test"):
            return True
        # heuristic: a method named testSomething or comments including 'test'
        if re.search(r"\btest[A-Za-z0-9_]*\b", body):
            return True
        return False

    def references_related_class(body: str, related: Optional[str]) -> bool:
        if not body or not related:
            return False
        # patterns to catch usages like: SimpleProcess, new SimpleProcess(, SimpleProcess., SimpleProcess::method
        pats = [
            rf"\b{re.escape(related)}\b",
            rf"new\s+{re.escape(related)}\s*\(",
            rf"{re.escape(related)}\s*\.",
            rf"{re.escape(related)}\s*::"
        ]
        for p in pats:
            if re.search(p, body):
                return True
        # final fallback: case-insensitive contains
        if related.lower() in body.lower():
            return True
        return False

    def references_sobject(body: str, sobject: Optional[str]) -> bool:
        if not body or not sobject:
            return False
        candidates = {
            sobject,
            sobject.lower(),
            sobject.upper(),
            sobject + "__c",
            (sobject + "__c").lower()
        }
        for cand in candidates:
            if cand and cand in body:
                return True
        # look for List< SObject > or new SObject(
        if re.search(rf"List<\s*{re.escape(sobject)}\s*>", body, flags=re.IGNORECASE):
            return True
        if re.search(rf"new\s+{re.escape(sobject)}\s*\(", body, flags=re.IGNORECASE):
            return True
        return False

    matched_tests: List[Dict[str, Any]] = []
    for a in apex_list:
        body = a.get("Body") or ""
        name = a.get("Name") or ""

        is_test_like = looks_like_test(body, name)
        ref_class = references_related_class(body, related_class_name) if related_class_name else False
        ref_sobj = references_sobject(body, related_sobject) if related_sobject else False

        # Inclusion logic (tolerant):
        # - If both related_class_name and related_sobject provided: require test-like AND (ref_class OR ref_sobj)
        # - If only related_class_name provided: include if test-like OR ref_class
        # - If only related_sobject provided: include if test-like OR ref_sobj
        # - If neither provided: include if test-like
        include = False
        if related_class_name and related_sobject:
            include = is_test_like and (ref_class or ref_sobj)
        elif related_class_name:
            include = is_test_like or ref_class
        elif related_sobject:
            include = is_test_like or ref_sobj
        else:
            include = is_test_like

        if include:
            matched_tests.append({
                "Id": a.get("Id"),
                "Name": name,
                "Body": body
            })

    return matched_tests


def get_custom_objects() -> List[str]:
    if not sf:
        return []
    try:
        result = sf.query_all(
            "SELECT QualifiedApiName FROM EntityDefinition WHERE IsCustomizable = TRUE"
        )
        return [r["QualifiedApiName"] for r in result.get("records", [])]
    except Exception as e:
        print("❌ Error fetching custom objects:", e)
        return []

def extract_class_name_from_trace(stack_trace: str) -> str:
    if not stack_trace:
        return ""
    m = re.search(r"Class\.([A-Za-z0-9_]+)\.", stack_trace)
    return m.group(1) if m else ""

def detect_sobject_from_body(body: str) -> str:
    if not body:
        return ""
    patterns = [
        r"new\s+([A-Z][A-Za-z0-9_]+)\s*\(",
        r"List<\s*([A-Z][A-Za-z0-9_]+)\s*>",
        r"(?:insert|update|delete|upsert)\s+([A-Z][A-Za-z0-9_]+)"
    ]
    for p in patterns:
        m = re.search(p, body, flags=re.IGNORECASE)
        if m:
            return m.group(1)
    return ""

def retrieve_salesforce_context(input_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Enriched Salesforce context:
    - faulty_class (Id, Name, Body) if found
    - related_sobject (string)
    - missing_fields_detected (list)
    - missing_fields_enriched (list of dicts with mapping and metadata)
    - test_classes (list)
    """
    if not sf:
        return {}

    stack = input_json.get("stackTrace") or ""
    class_name = extract_class_name_from_trace(stack)
    guessed_sobject = None

    # If class name not found, attempt heuristic detection from message/source
    if not class_name:
        text = " ".join([str(input_json.get(k, "")) for k in ("message_short", "message", "source")]).lower()
        if "contact" in text:
            guessed_sobject = "Contact"
        elif "account" in text:
            guessed_sobject = "Account"
        elif "lead" in text:
            guessed_sobject = "Lead"

    apex_list = get_apex_classes()
    faulty_class = next((a for a in apex_list if a.get("Name") == class_name), None) if class_name else None

    # detect sobject from the class body if possible, else use guessed
    sobject = ""
    if faulty_class:
        sobject = detect_sobject_from_body(faulty_class.get("Body", "")) or ""
    if not sobject and guessed_sobject:
        sobject = guessed_sobject

    # extract missing field names from message
    missing_fields = extract_missing_fields_from_message((input_json.get("message") or "") + " " + (input_json.get("message_short") or ""))

    # if no sobject detected, try to detect from message tokens (e.g., 'contact')
    if not sobject:
        msg_text = (input_json.get("message_short", "") + " " + input_json.get("message", "")).lower()
        if "contact" in msg_text:
            sobject = "Contact"
        elif "account" in msg_text:
            sobject = "Account"

    sobject_fields_meta = get_sobject_fields_metadata(sobject) if sobject else {}

    # map and enrich each missing field
    fields_enriched = []
    for mf in missing_fields:
        api_match, suggestions = map_requested_field_to_api(sobject, mf, sobject_fields_meta)
        meta = sobject_fields_meta.get(api_match, {}) if api_match else {}
        confidence = 0.0
        if api_match:
            confidence = 0.95  # exact-ish
        elif suggestions:
            confidence = 0.7
        else:
            confidence = 0.3
        fields_enriched.append({
            "requested": mf,
            "mapped_api_name": api_match or "",
            "candidates": suggestions,
            "field_metadata": meta,
            "mapping_confidence": confidence
        })

    test_classes = get_test_classes(related_class_name=class_name, related_sobject=sobject) if class_name or sobject else []

    return {
        "faulty_class": {
            "Id": faulty_class.get("Id"),
            "Name": faulty_class.get("Name"),
            "Body": faulty_class.get("Body")
        } if faulty_class else None,
        "related_sobject": sobject or None,
        "missing_fields_detected": missing_fields,
        "missing_fields_enriched": fields_enriched,
        "test_classes": test_classes
    }

# ========================================
# COMBINED CONTEXT RETRIEVAL
# ========================================
def retrieve_context_from_json(input_json: Dict[str, Any]) -> Dict[str, Any]:
    # Build a query string
    query_parts = [
        input_json.get("message_short", ""),
        input_json.get("message", ""),
        input_json.get("stackTrace", ""),
        input_json.get("function", ""),
        input_json.get("source", "")
    ]
    query = " | ".join([p for p in query_parts if p])

    vector_result = search_weaviate(query)
    web_result = search_web(query)

    # Add Salesforce context (enriched)
    sf_context = {}
    try:
        sf_context = retrieve_salesforce_context(input_json)
    except Exception as e:
        print("Error retrieving Salesforce context:", e)
        sf_context = {}

    return {
        "query": query,
        "retrieved_at": datetime.utcnow().isoformat() + "Z",
        "results": {
            "weaviate": summarize_weaviate(vector_result),
            "web": summarize_web(web_result),
        },
        "salesforce_context": sf_context
    }

# ========================================
# MAIN TOOL FUNCTION - FIXED VERSION
# ========================================
def retrieve_salesforce_context_tool(error_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main tool function with clean signature.
    This will be called with {'error_data': {...}}
    """
    if not error_data:
        error_data = {}
    
    # Ensure we have a dict
    if isinstance(error_data, str):
        try:
            error_data = json.loads(error_data)
        except:
            error_data = {"input": error_data}
    
    # Call your existing function
    return retrieve_context_from_json(error_data)

# ========================================
# CREATE THE TOOL - CORRECT STRUCTURE
# ========================================
retriever_tool = StructuredTool.from_function(
    func=retrieve_salesforce_context_tool,
    name="retrieve_salesforce_context",
    description="Receive JSON input (error object), search Weaviate, web, and Salesforce, return top context.",
    args_schema=ErrorInput,
)

# ========================================
# BUILD AGENT FUNCTION
# ========================================
def build_agent(model_instance=None):
    """
    Build the context retrieval agent.
    
    Args:
        model_instance: A model instance (not class)
    
    Returns:
        The compiled agent
    """
    # Use provided instance or default
    model_to_use = model_instance or coordinator_brain_gemini#context_retrieval_brain_openrouter
    
    # Verify it's an instance, not a class
    if isinstance(model_to_use, type):
        print(f"WARNING: Model {model_to_use} is a class, trying to instantiate...")
        try:
            model_to_use = model_to_use()
        except Exception as e:
            print(f"Failed to instantiate model: {e}")
            raise ValueError(f"Model must be an instance, not a class: {model_to_use}")
    
    print(f"Building context agent with model: {getattr(model_to_use, 'model_name', str(model_to_use))}")
    
    return create_deep_agent(
        system_prompt=PROMPT,
        tools=[retriever_tool],
        model=model_to_use,
    )

# ========================================
# MAIN TEST
# ========================================
if __name__ == "__main__":
    example_input = {
      
      "stackTrace": "Class.SimpleProcess.createContactWithError: line 10, column 1\nAnonymousBlock: line 1, column 1\nAnonymousBlock: line 1, column 1",
      "source": "SimpleProcess",
      "message_short": "Erreur Contact",
      "message": "Erreur lors de la création du contact\nMessage: Insert failed. First exception on row 0; first error: REQUIRED_FIELD_MISSING, Required fields are missing: [Name]: [Name]",
      "logCode": "null",
      "function": "createContactWithError",
      "name": "a00g5000003KesQ",
      "id": "a00g5000003KesQAAS",
    }
    
    print("=== Testing retrieve_context_from_json ===")
    result = retrieve_context_from_json(example_input)
    print(json.dumps(result, indent=2, ensure_ascii=False))

    close_client()