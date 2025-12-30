import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from deepagents import create_deep_agent
from agents.LLMs import judge_brain_openrouter,coordinator_brain_gemini  # <-- your judge LLM


# =========================
# LOAD SYSTEM PROMPT
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
prompt_file_path = os.path.join(BASE_DIR, "prompt.md")

with open(prompt_file_path, "r", encoding="utf-8") as f:
    PROMPT = f.read()


# =========================
# BUILD AGENT
# =========================
def build_agent(model_instance=None):
    """
    Build the judge-fix agent.

    Input:
    {
      "context": <context-retrieval output>,
      "fix_proposals": <fix-proposal output>
    }

    Output (STRICT JSON):
    {
      "approved": true | false,
      "score": 0-100,
      "reasons": [],
      "feedback_for_regeneration": "string | null"
    }
    """

    model_to_use = model_instance or coordinator_brain_gemini

    # Ensure instance, not class
    if isinstance(model_to_use, type):
        model_to_use = model_to_use()

    print(
        f"Building judge-fix agent with model: "
        f"{getattr(model_to_use, 'model_name', str(model_to_use))}"
    )

    return create_deep_agent(
        system_prompt=PROMPT,
        tools=[],          # ❌ NO TOOLS (VERY IMPORTANT)
        model=model_to_use
    )

