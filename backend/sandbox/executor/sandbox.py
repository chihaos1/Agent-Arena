import docker
import logging
import os
import shutil
import tempfile
import time
from typing import Dict, List

from docker.models.containers import Container

logger = logging.getLogger(__name__)

RUNTIME_IMAGES = {
    "node": "node:18-slim",
    "python": "python:3.11-slim",
    "go": "golang:1.21-alpine",
    "java": "openjdk:17-slim"
}

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
        commands: List[str],
        workflow_id: str,
        repo_name: str,
        github_token: str,
        repo_branch: str = "main",
        runtime: str = "node",
        timeout: int = 300
    ) -> Dict:
        """
        Execute code in a Docker container with full repo context.
        
        Args:
            generated_files: List of generated files
            commands: Commands to run (e.g., ["npm install", "npm test"])
            workflow_id: Workflow identifier
            repo_url: Git repo URL (e.g., "github.com/user/repo")
            github_token: GitHub personal access token
            repo_branch: Branch to checkout (default: "main")
            runtime: Runtime environment ("node", "python", "go")
            timeout: Max execution time in seconds (default: 300)
        
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
        temp_dir = None
        container = None
        image_tag = None

        try:
            logger.info(f"Starting sandbox execution")
            logger.info(f"\tWorkflow: {workflow_id}")
            logger.info(f"\tFiles: {len(generated_files)}")
            logger.info(f"\tRepository: {repo_name}")

            # ===== 1. Create temporary directory =====
            temp_dir = tempfile.mkdtemp(prefix=f"sandbox_{workflow_id}_")
            logger.info(f"Created temp directory: {temp_dir}")

            # ===== 2. Create Dockerfile with GitHub auth =====
            dockerfile_content = self._create_dockerfile(
                runtime=runtime,
                repo_name=repo_name,
                github_token=github_token,
                repo_branch=repo_branch
            )
            dockerfile_path = os.path.join(temp_dir, 'Dockerfile')

            with open(dockerfile_path, "w") as file:
                file.write(dockerfile_content)

            logger.info(f"\tCreated Dockerfile for runtime: {runtime}")

            # ===== 3. Write generated files to temp dir =====
            generated_files_dir = os.path.join(temp_dir, 'generated')
            os.makedirs(generated_files_dir, exist_ok=True)

            for file in generated_files:
                file_path = os.path.join(generated_files_dir, file["path"])
                os.makedirs(os.path.dirname(file_path), exist_ok=True)

                with open(file_path, "w", encoding="utf-8") as file:
                    file.write(file["content"])
                
                logger.debug(f"\tWrote: {file['path']}")
            
            logger.info(f"Wrote {len(generated_files)} files to /generated folder")

            # ===== 4. Build Docker image =====
            image_tag = f"sandbox-{workflow_id}".lower().replace('_', '-')
            logger.info(f"Building Docker image: {image_tag}")

            try:
                image, build_logs = self.client.images.build(
                    path=temp_dir,
                    tag=image_tag,
                    rm=True,
                    forcerm=True,
                    timeout=300
                )
                logger.info(f"Image built: {image.short_id}")
            except docker.errors.BuildError as e:
                logger.error(f"Docker build failed")
                build_log = "\n".join([line.get('stream', '') for line in e.build_log if 'stream' in line])
                return {
                    "success": False,
                    "logs": f"Docker build failed:\n{build_log}",
                    "exit_code": 1,
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "files_tested": len(generated_files)
                }

            # ===== 5. Run container =====
            logger.info(f"Starting container...")
            
            container = self.client.containers.run(
                image=image_tag,
                command="/bin/sh",
                detach=True,
                tty=True,
                mem_limit="1g",
                network_mode="bridge",
                remove=False
            )

            logger.info(f"\tContainer started: {container.short_id}")

            # ===== 6. Execute commands sequentially =====
            all_logs = []
            final_exit_code = 0

            for i, cmd in enumerate(commands, 1):
                logger.info(f"\t\tCommand {i}/{len(commands)}: {cmd[:60]}...")

                try:
                    exit_code, output = container.exec_run(
                        f"/bin/sh -c {cmd}",
                        demux=False,
                        stream=False
                    )

                    output_str = output.decode("utf-8", errors="replace") if isinstance(output, bytes) else str(output)
                    
                    all_logs.append(f"\n{"="*70}\n")
                    all_logs.append(f"Command {i}/{len(commands)}: {cmd}\n")
                    all_logs.append(f"Exit Code: {exit_code}\n")
                    all_logs.append(f"{'='*70}\n")
                    all_logs.append(output_str)

                    if exit_code != 0:
                        logger.warning(f"\t\t\tCommand failed with exit code {exit_code}")
                        final_exit_code = exit_code
                        break
                    else:
                        logger.info(f"\t\t\tCommand succeeded")

                except Exception as e:
                    logger.error(f"\t\t\tCommand execution error: {e}")
                    all_logs.append(f"\nError executing command: {str(e)}\n")
                    final_exit_code = 1
                    break
            
            # ===== 7. Consolidate logs =====
            full_logs = "".join(all_logs)
            duration_ms = int((time.time() - start_time) * 1000)
            success = (final_exit_code == 0)
            
            logger.info(f"Execution complete:")
            logger.info(f"Success: {success}")
            logger.info(f"Exit Code: {final_exit_code}")
            logger.info(f"Duration: {duration_ms}ms")
            
            return {
                "success": success,
                "logs": full_logs,
                "exit_code": final_exit_code,
                "duration_ms": duration_ms,
                "files_tested": len(generated_files)
            }
            
        except Exception as e:
            logger.error(f"Sandbox execution failed: {str(e)}", exc_info=True)
            duration_ms = int((time.time() - start_time) * 1000)
            
            return {
                "success": False,
                "logs": f"Sandbox execution error: {str(e)}",
                "exit_code": 1,
                "duration_ms": duration_ms,
                "files_tested": len(generated_files) if generated_files else 0
            }
            
        finally:
            self._cleanup(temp_dir, container, image_tag)
    
    def _create_dockerfile(
        self,
        runtime: str,
        repo_name: str,
        github_token: str,
        repo_branch: str = "main"
    ) -> str:
        """Create Dockerfile with GitHub authentication"""

        # Get base image
        base_image = RUNTIME_IMAGES.get(runtime, "node:18-slim")
        
        # Create GitHub clone URL
        github_auth_url = f'https://{github_token}@github.com/{repo_name}.git'

        dockerfile = f"""
            FROM {base_image}

            # Install git
            RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

            WORKDIR /app

            # Clone repository with authentication
            RUN git clone --depth 1 --branch {repo_branch} {github_auth_url} /app/repo

            # Copy generated files
            COPY generated /app/generated

            # Overwrite repo files with generated versions
            RUN cp -rf /app/generated/* /app/repo/ 2>/dev/null || true

            # Set working directory to repo
            WORKDIR /app/repo

            # Default command
            CMD ["/bin/sh"]
        """

        return dockerfile

    def _cleanup(self, temp_dir: str, container: Container, image_tag: str) -> None:
        """Clean up temporary directory and Docker resources"""

        # Remove container
        if container:
            try:
                logger.info(f"\tStopping container...")
                container.stop(timeout=5)
                container.remove(force=True)
                logger.info(f"\tContainer removed")
            except Exception as e:
                logger.warning(f"\t\tContainer cleanup failed: {e}")

        # Remove image
        if image_tag:
            try:
                logger.info(f"\tRemoving image: {image_tag}")
                self.client.images.remove(image_tag, force=True)
                logger.info(f"\tImage removed")
            except Exception as e:
                logger.warning(f"\t\tImage cleanup failed: {e}")

        # Remove temp directory
        if temp_dir and os.path.exists(temp_dir):
            try:
                logger.info(f"\tRemoving temp directory...")
                shutil.rmtree(temp_dir)
                logger.info(f"\tTemp directory removed")
            except Exception as e:
                logger.warning(f"\t\tTemp dir cleanup failed: {e}")
        
        logger.info(f"Cleanup completed")