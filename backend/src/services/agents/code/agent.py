from langgraph.graph import StateGraph, END

from .nodes import (
    fetch_files,
    generate_code,
    validate_code
)
from .state import CoderState

class CoderAgent:
    """
    """

    def __init__(self):
        self.graph = self._build_graph()

    def _build_graph(self):
        """Build the LangGraph graph"""

        # Nodes
        workflow = StateGraph(CoderState)
        workflow.add_node("fetch", fetch_files)
        workflow.add_node("generate", generate_code)
        workflow.add_node("validate", validate_code)

        # Edges
        workflow.add_edge("fetch", "generate")
        workflow.add_edge("generate", "validate")
        workflow.add_edge("validate", END)

        # Entry Point
        workflow.set_entry_point("fetch")
        return workflow.compile()

    def run(self, file_group, understanding, issue, repo):
        """
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

        print(final_state)

        # fetch_files(initial_state)

        # print(final_state)

        # final_state = self.graph.invoke(initial_state)