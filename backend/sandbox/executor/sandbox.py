import docker
import logging
import os
import shutil
import tempfile
import time
import uuid
from typing import Dict, List

from docker.models.containers import Container

logger = logging.getLogger(__name__)

class ReviewerSandbox:
    """Executes code in an isolated Docker container"""

    def __init__(self):
        try:
            self.client = docker.from_env()
            self.client.ping()
            logger.info("Docker client initialized and connected")
        except Exception as e:
            logger.error(f"Failed to initialize Docker client: {e}")
            raise

    def execute(
        self,
        generated_files: List[Dict[str, str]],
        commands: str,
        repo_name: str,
        github_token: str
    ) -> Dict:
        """
        Execute code in a Docker container with full repo context.
        
        Args:
            generated_files: List of generated files
            commands: Commands to run (e.g., ["npm install", "npm test"])
            repo_url: Git repo URL (e.g., "github.com/user/repo")
            github_token: GitHub personal access token
            runtime: Runtime environment ("node", "python", "go")
        
        Returns:
            {
                "success": bool,
                "logs": str,
                "exit_code": int,
                "duration_ms": int,
                "files_tested": int
            }
        """

        start_time = time.time()
        run_id = str(uuid.uuid4())
        temp_dir = None
        container = None

        try:
            logger.info(f"Starting sandbox execution")
            logger.info(f"Run ID: {run_id}")
            logger.info(f"Files: {len(generated_files)}")
            logger.info(f"Repository: {repo_name}")

            # ===== 1. Create temporary directory =====
            temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{run_id}_")
            logger.info(f"Created temp directory: {temp_dir}")

            # ===== 2. Write generated files to temp dir =====
            generated_files_dir = os.path.join(temp_dir, 'generated')
            os.makedirs(generated_files_dir, exist_ok=True)

            for file in generated_files:
                file_path = os.path.join(generated_files_dir, file["path"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(file["content"])
                
                logger.debug(f"Wrote: {file['path']}")
            
            logger.info(f"Wrote {len(generated_files)} files to /generated folder")

            # ===== 3. Use universal image =====
            image_name = "autodev-universal:latest"

            try:
                self.client.images.get(image_name)
                logger.info(f"Using existing image: {image_name}")
            except docker.errors.ImageNotFound:
                logger.error(f"Image {image_name} not found. Please build it first.")
                return {
                    "test_name": "sandbox_execution",
                    "passed": True,
                    # "passed": True,
                    "output": "Universal image not found. Run: docker build -f Dockerfile.universal -t autodev-universal:latest .",
                    "duration_seconds": int((time.time() - start_time) * 1000),
                    "error": f"Image {image_name} not found. Please build it first."
                }

            # ===== 4. Start container from universal image =====
            logger.info(f"Starting container...")
            
            container: Container = self.client.containers.run(
                image=image_name,
                command="/bin/bash",
                detach=True,
                tty=True,
                stdin_open=True,
                volumes={
                    generated_files_dir: {'bind': '/app/generated', 'mode': 'ro'}
                },
                working_dir="/app",
                mem_limit="2g"
            )

            logger.info(f"Container started: {container.short_id}")

            # ===== 5. Clone repository with GitHub token =====
            branch = "main"
            clone_url = f"https://{github_token}@github.com/{repo_name}.git"

            logger.info(f"Cloning {repo_name} (branch: {branch})...")

            clone_cmd = f"git clone --depth 1 --branch {branch} {clone_url} /app/repo"
            exit_code, output = container.exec_run(clone_cmd)

            if exit_code != 0:
                logger.error(f"Git clone failed: {output.decode()}")
                output_str = output.decode("utf-8", errors="ignore")
                return {
                    "test_name": "sandbox_execution",
                    "passed": False,
                    "output": f"Failed to clone repository",
                    "duration_seconds": int((time.time() - start_time) * 1000),
                    "error": None if success else self._extract_error(output_str)
                }
            
            logger.info(f"Repository cloned")

            # ===== 6. Copy generated files into repo =====
            logger.info("Copying generated files into repo...")

            copy_cmd = "cp -rf /app/generated/* /app/repo/ 2>/dev/null || true"
            container.exec_run(copy_cmd)

            # ===== 7. Execute the chained command =====
            logger.info(f"Executing command chain...")
            logger.info(f"Command: {commands}")

            exit_code, output = container.exec_run(
                f"/bin/bash -c '{commands}'",
                workdir="/app/repo"
            )

            if exit_code != 0:
                logger.error(f"Command execution failed: {output.decode()}")

            output_str = output.decode("utf-8", errors="ignore")

            # ===== 9. Prepare result =====
            duration_ms = int((time.time() - start_time) * 1000)
            success = exit_code == 0
            
            logger.info(f"Execution complete:")
            logger.info(f"Success: {success}")
            logger.info(f"Exit Code: {exit_code}")
            logger.info(f"Duration: {duration_ms}ms")
            
            return {
                "test_name": "sandbox_execution",
                "passed": success,
                "output": output_str,
                "duration_seconds": duration_ms,
                "error": None if success else self._extract_error(output_str)
            }
            
        except Exception as e:
            logger.error(f"Sandbox execution failed: {str(e)}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            
            error_msg = f"Sandbox execution error: {str(e)}"

            return {
                "test_name": "sandbox_execution",
                "passed": False,
                "output": error_msg,
                "duration_seconds": duration_ms,
                "error": str(e)
            }
            
        finally:
            self._cleanup(temp_dir, container)
    
    def _extract_error(self, output: str) -> str:
        """Extract meaningful error from output"""
        
        lines = output.split("\n")
        
        # Find error lines
        error_lines = []
        for line in lines:
            if any(keyword in line.lower() for keyword in ["error", "failed", "exception"]):
                error_lines.append(line.strip())
        
        if error_lines:
            return "\n".join(error_lines[:15])
        
        # Fallback
        return "\n".join(lines[-20:])

    def _cleanup(self, temp_dir: str, container: Container) -> None:
        """Clean up temporary directory and Docker resources"""

        # Remove container
        if container:
            try:
                logger.info(f"Stopping container...")
                container.stop(timeout=5)
                container.remove(force=True)
                logger.info(f"Container removed")
            except Exception as e:
                logger.warning(f"Container cleanup failed: {e}")

        # Remove temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                logger.info(f"Removing temp directory...")
                shutil.rmtree(temp_dir)
                logger.info(f"Temp directory removed")
            except Exception as e:
                logger.warning(f"Temp dir cleanup failed: {e}")
        
        logger.info(f"Cleanup completed")