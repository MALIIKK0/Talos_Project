# agents/fix_application/agent.py
from deepagents import create_deep_agent
from agents.LLMs import model
from agents.LLMs import llama
PROMPT = """
You are the fix application agent.
Apply fixes: create a branch, commit changes, open a PR, and update JIRA.
"""
# PROMPT = """
# You are the fix application agent.
# Apply approved fixes: create a branch, commit changes, open a PR, and update JIRA.
# This agent MUST request human approval before performing any destructive action.
# """


def build_agent(tools=None, model=model):
# configure interrupt_on when creating the deep agent from coordinator
    print("Building fix_application_agent with model:", model.model_name)
    return create_deep_agent(
        system_prompt=PROMPT,
        tools=tools or [],
        model=model )
