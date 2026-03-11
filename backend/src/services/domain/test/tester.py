"""
Test Agent

Executes generated code in sandbox environment.
Handles command preparation and sandbox communication.
"""

import logging
import requests
from typing import Dict, List

from core.config import settings

logger = logging.getLogger(__name__)
SANDBOX_URL = settings.SANDBOX_URL

class TestAgent:
    """Executes code in isolated sandbox environment"""

    def __init__(self, github_token: str):
        self.github_token = github_token
        self.sandbox_url = SANDBOX_URL

    def run_tests(self, generated_files: List[Dict], sandbox_config: Dict, repo_name: str) -> Dict:
        """
        Execute tests in sandbox environment.
        
        Args:
            generated_files: List of files with 'path' and 'content'
            sandbox_config: Configuration with runtimes, setup_commands, test_commands
            repo_name: Repository name (owner/repo)
        
        Returns:
            {
                "success": bool,
                "output": str,
                "exit_code": int,
                "duration": float
            }
        """

        logger.info(f"Running tests for {len(generated_files)} files")

        # Extract configuration
        runtimes = sandbox_config.get("runtimes", ["node"])
        setup_cmds = sandbox_config.get("setup_commands", [])
        test_cmds = sandbox_config.get("test_commands", [])

        # Prepare commands
        final_cmds = self._prepare_commands(setup_cmds, test_cmds)

        logger.info(f"Runtimes: {runtimes}")
        logger.info(f"Commands: {final_cmds}")

        # Execute in sandbox
        result = self._execute_sandbox(
            files=generated_files,
            commands=final_cmds,
            runtimes=runtimes,
            repo_name=repo_name
        )

        logger.info(f"Test execution completed: success={result.get('success')}")
        
        return result

    def _prepare_commands(self, setup_cmds: List[str], test_cmds: List[str]) -> str:
        """Combine setup and test commands with subshell wrapping"""

        all_cmds = setup_cmds + test_cmds
        
        # Wrap each command in subshell for proper error propagation
        subshells = [f"({cmd})" for cmd in all_cmds]
        
        # Chain with && so failure stops execution
        final_cmds = " && ".join(subshells)
        
        return final_cmds
    
    def _execute_sandbox(self, files: List[Dict], commands: str, runtimes: List[str], repo_name: str) -> Dict:
        """Send request to sandbox service"""

        payload = {
            "files": files,
            "commands": commands,
            "repo_name": repo_name,
            "github_token": self.github_token,
            "runtime": runtimes
        }

        logger.info(f"Sending request to sandbox at {self.sandbox_url}")
        
        response = requests.post(
            f"{self.sandbox_url}/execute",
            json=payload,
            timeout=600
        )

        response.raise_for_status()
        
        return response.json()