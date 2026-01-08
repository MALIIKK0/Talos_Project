import json
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from deepagents import create_deep_agent
from agents.LLMs import fix_proposal_brain_openrouter  # make sure JB3 is importable
#from tools.jira.create_jira import jira_create_tool

# =========================
# SYSTEM PROMPT
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
prompt_file_path = os.path.join(BASE_DIR, "prompt.md")

with open(prompt_file_path, "r", encoding="utf-8") as f:
    PROMPT = f.read()


# =========================
# BUILD AGENT FUNCTION
# =========================

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
        tools=[],              #tools=[jira_create_tool],
        model=model_to_use,
    )