# orchestrator.py
import sys, os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from deepagents import create_deep_agent, CompiledSubAgent
from agents.LLMs import model,llama,coordinator_brain_openrouter
from agents.context_retrieval.agent import build_agent as build_context_agent
from agents.fix_proposal.agent import build_agent as build_fix_proposal_agent
from agents.fix_application.agent import build_agent as build_fix_application_agent

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
prompt_file_path = os.path.join(BASE_DIR, "prompt.md")

with open(prompt_file_path, "r", encoding="utf-8") as f:
    ORCHESTRATOR_PROMPT = f.read()
def create_orchestrator(additional_tools=None, model=model):
    """
    Creates the orchestrator agent with sub-agents.
    
    Args:
        additional_tools: Optional list of extra tools to provide
        model: Optional model override for the orchestrator
    
    Returns:
        The orchestrator agent
    """

    """CompiledSubAgent(
    name="root-cause-analysis",
    description=(
        "Input: JSON as produced by context-retrieval with keys: "
        "`original_input` (error object), `query`, `retrieved_at`, `results` (weaviate/web hits), "
        "`salesforce_context` (faulty_class, related_sobject, missing_fields_detected, missing_fields_enriched, test_classes). "
        "Output: JSON with fields: "
        "`root_cause` (short string), `root_cause_type` (code|config|data|permission|other), "
        "`evidence` (array of {type, source, excerpt, location}), `confidence` (0.0-1.0), "
        "`impact` (low|medium|high), `reproduction_steps` (list), `fix_suggestions` (list of actions), "
        "`automatable` (bool), `affected_components` (list), `references` (urls or docs)."
    ),
    runnable=root_cause_agent
),"""
    
    # Build all sub-agents as compiled graphs
    context_agent = build_context_agent()
    fix_proposal_agent = build_fix_proposal_agent()
    fix_application_agent = build_fix_application_agent()
# context_agent = build_context_agent(model=model)
# root_cause_agent = build_root_cause_agent(model=model)
# fix_proposal_agent = build_fix_proposal_agent(model=model)
# fix_application_agent = build_fix_application_agent(model=model)

    # Define sub-agents for the orchestrator
    
    subagents = [
       
         CompiledSubAgent(
        name="context-retrieval",
        description="""Retrieves relevant context for an error from Salesforce, Weaviate, and web sources.
Input: JSON object representing an error with keys like _id, stackTrace, message, source, function, etc.
Output: JSON with context_meta, retrieval_query, retrieved_context, and status.""",
        runnable=context_agent
    ),
        CompiledSubAgent(
            name="fix-proposal",
            description="Proposes one or more fixes with code diffs or patch instructions (it analyse and create the root cause if not provided).   Input: JSON as produced by context-retrieval with keys: "
        "`original_input` (error object), `query`, `retrieved_at`, `results` (weaviate/web hits), "
        "`salesforce_context` (faulty_class, related_sobject, missing_fields_detected, missing_fields_enriched, test_classes).  Output: detailed fix proposals with code changes.",
            runnable=fix_proposal_agent
        ),
        CompiledSubAgent(
            name="fix-application",
            description="Applies approved fixes: creates branch, commits changes, opens PR, updates JIRA. REQUIRES human approval before execution. Input: fix proposal. Output: PR link and status.",
            runnable=fix_application_agent
        )
    ]
    
    # Create orchestrator with subagents
    orchestrator = create_deep_agent(
        system_prompt=ORCHESTRATOR_PROMPT,
        subagents=subagents,
        model=coordinator_brain_openrouter,
        tools=additional_tools or [],
#         interrupt_on={
#     "fix-application": {"*": {"reason": "Human approval required"}}
# }
#         interrupt_on={
#     "fix-application": {}     # empty config allowed
# } # Human approval checkpoint
    )
    
    return orchestrator


class AgentOrchestrator:
    """Orchestrates multiple agents in a coordinated workflow."""
    
    def __init__(self, additional_tools=None, model=model):
        self.orchestrator = create_orchestrator(additional_tools, model)
    
    def run(self, problem_description: str, config=None):
        """
        Execute the orchestrator workflow.
        
        Args:
            problem_description: The bug description or stack trace
            config: Optional configuration dict
        
        Returns:
            Final result from the orchestrator
        """
        messages = [{"role": "user", "content": problem_description}]
        return self.orchestrator.invoke({"messages": messages}, config=config)
    
    def stream(self, problem_description: str, config=None):
        """
        Stream the orchestrator workflow responses.
        
        Args:
            problem_description: The bug description or stack trace
            config: Optional configuration dict
        
        Yields:
            Streamed chunks from the orchestrator
        """
        messages = [{"role": "user", "content": problem_description}]
        yield from self.orchestrator.stream({"messages": messages}, config=config)
    
    def run_with_approval(self, problem_description: str, thread_id="bug_fix_workflow"):
        """
        Run workflow with human approval checkpoints.
        
        Args:
            problem_description: The bug description or stack trace
            thread_id: Thread ID for tracking the conversation
        
        Returns:
            Dict with status and result
        """
        config = {"configurable": {"thread_id": thread_id}}
        
        # Start the workflow
        result = self.orchestrator.invoke(
            {"messages": [{"role": "user", "content": problem_description}]},
            config=config
        )
        
        # Check if waiting for approval
        state = self.orchestrator.get_state(config)
        if state.next:
            return {
                "status": "pending_approval",
                "next_action": state.next,
                "result": result,
                "config": config
            }
        
        return {"status": "completed", "result": result}
    
    def approve_and_continue(self, config):
        """
        Approve the pending action and continue execution.
        
        Args:
            config: Configuration dict from run_with_approval
        
        Returns:
            Final result after approval
        """
        # Continue from the interrupt
        return self.orchestrator.invoke(None, config=config)
    
    def reject_and_modify(self, feedback: str, config):
        """
        Reject the pending action with feedback.
        
        Args:
            feedback: Human feedback on why the action was rejected
            config: Configuration dict from run_with_approval
        
        Returns:
            Result after processing feedback
        """
        return self.orchestrator.invoke(
            {"messages": [{"role": "user", "content": feedback}]},
            config=config
        )


# Convenience functions
def run_orchestrator(problem_description: str):
    """Quick run function for simple usage."""
    orchestrator = AgentOrchestrator()
    return orchestrator.run(problem_description)


## Create a global orchestrator instance


#for the langgraph CLI   ( in the langgraphCLI.py file)
# orchestrator = create_orchestrator()



# in the main (main.py)

# # Example usage
# if __name__ == "__main__":
#     problem = """
#     Stack trace shows NullPointerException in OrderController.apex line 45.
#     Error occurs when processing orders with null shipping addresses.
#     """
    
#     print("Starting orchestrator workflow...")
#     result = run_orchestrator(problem)
#     print("\n✅ Workflow completed!")
#     print(result)
#     # print(f"Final response: {result['messages'][-1]['content']}")