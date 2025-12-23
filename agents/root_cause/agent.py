# agents/root_cause/agent.py
from deepagents import create_deep_agent
from agents.LLMs import model

PROMPT = """
You are the root cause analysis agent. Given logs and context, find the most likely root cause and confidence.
Return structured analysis and reproduction steps (if possible).
if you dont have context just try to give one general possible root causes.
"""
# PROMPT = """
# You are the root cause analysis agent. Given logs and context, find the most likely root cause and confidence.
# Return structured analysis and reproduction steps (if possible).
# """
"""prompt_file_path = "prompt.md"
with open(prompt_file_path, "r", encoding="utf-8") as f:
    PROMPT = f.read()"""

def build_agent(tools=None, model=model):
    print("Building root cause agent with model:", model.model_name)
    return create_deep_agent(
        system_prompt=PROMPT,
        tools=tools or [],
        model=model
        )
