from langgraph.graph import StateGraph, END

from .nodes import (
    fetch_files,
    generate_code,
    validate_code,
    correct_code,
    return_result
)
from .state import CoderState

class CoderAgent:
    """
    An autonomous coding agent that uses a directed acyclic graph (DAG) to generate, 
    validate, and self-correct code changes.

    The agent follows a stateful workflow:
    1. Fetch: Retrieves the necessary files from the repository.
    2. Generate: Produces code changes based on the issue description.
    3. Validate: Checks the generated code for syntax or logical errors.
    4. Correct: If errors are found, attempts to fix the code (up to MAX_RETRIES).
    5. Finish: Packages the final result for the workflow.

    Attributes:
        MAX_RETRIES (int): The maximum number of times the agent will attempt 
                           to fix code errors before giving up.
        graph (CompiledGraph): The compiled LangGraph state machine.
    """

    MAX_RETRIES = 1

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph graph"""

        # Nodes
        workflow = StateGraph(CoderState)
        workflow.add_node("fetch", fetch_files)
        workflow.add_node("generate", generate_code)
        workflow.add_node("validate", validate_code)
        workflow.add_node("correct", correct_code)
        workflow.add_node("finish", return_result)

        # Entry Point
        workflow.set_entry_point("fetch")

        # Edges
        workflow.add_edge("fetch", "generate")
        workflow.add_edge("generate", "validate")

        workflow.add_conditional_edges(
            "validate",
            self._should_retry,
            {
                "finish": "finish",
                "correct": "correct"
            }
        )
        workflow.add_edge("correct", "generate")

        workflow.add_edge("finish", END)

        return workflow.compile()

    def _should_retry(self, state: CoderState) -> str:
        """
        Decide whether to retry or finish.
        
        Returns:
            "finish" - If valid or max retries reached
            "correct" - If invalid and retries remaining. Sent to self-correct
        """

        if state["is_valid"]:
            return "finish"

        if state["retry_count"] >= self.MAX_RETRIES:
            return "finish"
        
        return "correct"

    def run(self, file_group, understanding, issue, repo):
        """
        Executes the agent's coding workflow for a specific set of files.

        Will initializes the CoderState and invokes the compiled graph, 
        managing the transition between fetching, generating, and validating code.

        Args:
            file_group (FileGroup): A Pydantic model or dict containing the 
                                    target files and group metadata.
            understanding (str): The strategic plan provided by the Planner agent.
            issue (str): The original user issue or task description.
            repo (Repository): The GitHub repository object to interact with.

        Returns:
            dict: The final result containing status, modified files, and 
                  any error messages if the task failed.
        """

        initial_state = {
            "file_group": file_group,
            "understanding": understanding,
            "issue": issue,
            "repo": repo,
            "generated_files": [],
            "reasoning": "",
            "is_valid": False,
            "errors": [],
            "retry_count": 0,
            "result": {}
        }

        final_state = self.graph.invoke(initial_state)

        return final_state["result"]