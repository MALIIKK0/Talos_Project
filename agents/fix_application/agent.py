# agents/fix_application/agent.py
import os
from deepagents import create_deep_agent

from agents.tools.github.git import apply_apex_patch, git_create_branch, git_commit, git_push
from agents.tools.github.github import github_create_pr
from agents.LLMs import fix_application_brain_openrouter


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROMPT_PATH = os.path.join(BASE_DIR, "prompt.md")

with open(PROMPT_PATH, "r", encoding="utf-8") as f:
    FIX_APPLICATION_PROMPT = f.read()


def build_agent(model_instance=None):
    """
    Build the FIX APPLICATION agent.

    This agent:
    - Accepts 1–3 fixes
    - Creates 1 PR per fix
    - References the same Jira ticket in all PRs
    """

    model_to_use = model_instance or fix_application_brain_openrouter

    return create_deep_agent(
        system_prompt=FIX_APPLICATION_PROMPT,
        model=model_to_use,
        tools=[
            # File modification
            apply_apex_patch,

            # Git operations
            git_create_branch,
            git_commit,
            git_push,

            # GitHub
            github_create_pr
        ],
<<<<<<< HEAD
    )
=======
    )
>>>>>>> 754bb64d906ae5488224821736a0146af0de0344
