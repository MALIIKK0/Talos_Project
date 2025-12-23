import json
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from deepagents import create_deep_agent
from agents.LLMs import fix_proposal_brain_openrouter  # make sure JB3 is importable
from agents.tools.jira.create_jira import jira_create_tool

# =========================
# SYSTEM PROMPT
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
prompt_file_path = os.path.join(BASE_DIR, "prompt.md")

with open(prompt_file_path, "r", encoding="utf-8") as f:
    PROMPT = f.read()

""" 
You are a FIX PROPOSAL AGENT specialized in Salesforce (Apex, Flows, sObjects).

INPUT:
You receive a single JSON object containing:
- query
- retrieved_at
- results
- salesforce_context:
    - faulty_class (Id, Name, Body)
    - related_sobject
    - missing_fields_detected
    - missing_fields_enriched
    - test_classes

YOUR RESPONSIBILITIES:
1. Identify the ROOT CAUSE of the Salesforce error.
2. Propose between 1 and 3 FIXES maximum.
3. Each fix must be technically correct and follow Salesforce best practices.
4. Prefer Apex code fixes when faulty_class exists.
5. Handle REQUIRED_FIELD_MISSING and NullPointerException properly.
6. For EACH fix:
   - Build a Jira Bug payload
   - CALL the tool `create_jira_bug`
   - Capture the returned jira_key and jira_url

RULES:
- Call `create_jira_bug` exactly once per fix.
- Never invent Jira keys or URLs.
- Do NOT expose tool calls in final output.
- Output MUST be valid JSON only.
- No explanations, no markdown.

OUTPUT FORMAT:
Return ONLY a JSON ARRAY:

[
  {
    "id": "FIX-001",
    "title": "...",
    "root_cause": "...",
    "description": "...",
    "jira": {
      "key": "...",
      "url": "..."
    },
    "apex_fix": "...",
    "risk": "LOW|MEDIUM|HIGH",
    "effort": "LOW|MEDIUM|HIGH"
  }
]

BEGIN.
"""

# =========================
# BUILD AGENT FUNCTION
# =========================
"""def build_agent():
    # ALWAYS instantiate JB3 if it's callable (a class)
    if callable(JB3):
        try:
            # Try to instantiate with no arguments
            model_instance = JB3()
        except TypeError:
            # If it needs arguments, try with defaults
            try:
                model_instance = JB3(model_name="jb3", temperature=0.7)
            except:
                # Last resort: check if it's actually an instance already
                if not hasattr(JB3, '__call__'):
                    model_instance = JB3
                else:
                    raise ValueError("JB3 cannot be instantiated")
    else:
        model_instance = JB3  # It's already an instance
    
    # Debug print
    print(f"Fix proposal agent using model: {type(model_instance)}")
    
    return create_deep_agent(
        system_prompt=PROMPT,
        tools=[jira_create_tool],
        model=model_instance,
    )"""

def build_agent(model_instance=None):
    """
    Build the context retrieval agent.
    
    Args:
        model_instance: A model instance (not class)
    
    Returns:
        The compiled agent
    """
    # Use provided instance or default
    model_to_use = model_instance or fix_proposal_brain_openrouter
    
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
        tools=[jira_create_tool],
        model=model_to_use,
    )
