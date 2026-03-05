import base64
import logging
from typing import Dict, Set

from fastapi import HTTPException, status
from github import Github, Auth
from github.Repository import Repository

from services.repo.embed import VectorStore
from services.agents.context.tools.parse import CodeParser

logger = logging.getLogger(__name__)

class ContextAssembler:
    """Assemble context for issue by finding relevant files"""

    def __init__(self, github_token):
        self.vector_store = VectorStore()
        self.parser = CodeParser()
        self.github_token = github_token

    def assemble_context(
            self,
            query: str, 
            repo_name: str
        ):
        """
        Gathers a comprehensive context package for the LLM Planner.

        The process follows a three-step pipeline:
        1. Retrieval: Queries Pinecone to find the most semantically relevant file 
           paths and summaries based on the user's issue.
        2. Fetching: Connects to the GitHub API to retrieve the raw source code 
           for each identified file.
        3. Parsing: Uses Tree-sitter to extract high-level code signatures and 
           import dependencies, creating a lightweight 'skeleton' of the codebase.

        Args:
            query: The user's natural language request or issue description.
            repo_name: The full GitHub repository name (e.g., 'owner/repo').

        Returns:
            A dictionary containing the original query, repository language stats, 
            and a list of file objects enriched with summaries, signatures, and imports.
        """

        # Fetch the most relevant scripts' GitHub file paths from Pinecone
        relevant_files = self._search_relevant_files(query=query,repo_name=repo_name)

        if not relevant_files:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="No relevant code files found for this query.") 

        # Initialize GitHub client
        github_auth = Auth.Token(self.github_token)

        with Github(auth=github_auth) as github_client:

            # Connect to GitHub repo
            repo = github_client.get_repo(repo_name)
            languages = repo.get_languages()

            # Fetch project manifest files
            manifests = self._fetch_manifests(repo)
            
            for file in relevant_files:
                    
                # Fetch scripts from GitHub
                content_raw = repo.get_contents(file["file_path"])
                content = content_raw.decoded_content.decode("utf-8", errors="ignore")

                # Extract code signatures from CodeParser
                result = self.parser.extract_code_excerpt(file["file_path"], content)

                file["signatures"] = result["signatures"]
                file["imports"] = result["imports"]

        return {
            "issue": {
                "query": query
            },
            "repo_context": {
                "repo_name": repo_name,
                "language_stack": list(languages.keys())
            },
            "files": relevant_files,
            "manifests": manifests 
        }

    def _search_relevant_files(
            self, 
            query: str, 
            repo_name: str, 
            top_k: int = 10, 
            relative_threshold: float = 0.7,
            absolute_minimum: float = 0.35
        ) -> list[dict]:
        """
        Performs a semantic search in Pinecone and filters results using an adaptive threshold.
        The function calculates an adaptive cutoff based on the highest score found, 
        ensuring that only the most relevant "cluster" of files is returned.

        Args:
        * query (str): The natural language search string or issue description.
        * repo_name (str): The namespace to search within (format: 'owner/repo').
        * top_k (int): Maximum number of raw matches to retrieve from the vector store.
        * relative_threshold (float): The percentage of the top score (0.0 to 1.0) used 
            to filter out irrelevant results.
        * absolute_minimum (float): The absolute lowest relevant score the search results 
            need to meet.

        Returns:
        * list[dict]: A filtered list of relevant file objects containing metadata 
            and similarity scores.
        """
    
        # Embed query
        query_embedding = self.vector_store.embed_text(query)

        # Search Pinecone
        results = self.vector_store.pinecone_index.query(
            vector=query_embedding,
            top_k=top_k,
            namespace=repo_name,
            include_metadata=True
        )

        if not results.get("matches"):
            return []

        # Filter files based on relative scores or absolute minimum
        relevant_matches = []
        top_score = results["matches"][0]["score"]
        relative_cutoff = top_score * relative_threshold
        absolute_cutoff = absolute_minimum
        cutoff_score = max(relative_cutoff, absolute_cutoff)
        
        for result in results["matches"]:
            if result["score"] > cutoff_score:      
                relevant_matches.append({
                    "file_path": result["metadata"]["file_path"],
                    "summary": result["metadata"]["summary"]
                })

        return relevant_matches

    def _search_repo_tree(self, repo: Repository, target_filenames: Set[str]) -> Dict:
        """
        Search repository tree for files by exact filename.
        
        Finds files at any depth in the repository that match the given filenames.
        
        Args:
            repo: GitHub repository object
            target_filenames: Exact filenames to find (e.g., {"package.json", "go.mod"})
        
        Returns:
            Dictionary mapping file paths to their content
        """

        repo_name = repo.full_name
        results = {}

        try: 
            default_branch = repo.default_branch
            logger.info(f"Searching {repo_name} for: {target_filenames} in {default_branch}")

            #  1. Get the full tree map
            tree = repo.get_git_tree(default_branch, recursive=True)

            #  2. Iterate once to fetch filename and file content
            for item in tree.tree:
                if item.type == "blob":
                    filename = item.path.split("/")[-1]

                    if filename in target_filenames:
                        
                        try:
                            blob = repo.get_git_blob(item.sha)
                            content = base64.b64decode(blob.content)

                            blob = repo.get_git_blob(item.sha)
                            raw_content = base64.b64decode(blob.content)

                            # Detect encoding
                            try:
                                content = raw_content.decode("utf-8")
                            except UnicodeDecodeError:
                                try:
                                    content = raw_content.decode("utf-16")
                                    logger.info(f"{item.path} (UTF-16 encoding detected)")
                                except UnicodeDecodeError:
                                    content = raw_content.decode("latin-1", errors="ignore")
                                    logger.warning(f"{item.path} (unknown encoding, using latin-1)")

                            results[item.path] = content

                            logger.info(f"Fetched {item.path} (SHA: {item.sha[:7]})")

                        except Exception as e:
                            logger.error(f"Failed to fetch blob for {item.path}: {e}")
            
            return results

        except Exception as e:
            logger.error(f"Tree search failed for {repo_name}: {e}")

    def _fetch_manifests(self, repo: Repository):
        """Fetch project manifest files using _search_repo_tree"""

        manifest_filenames = {

            # Primary manifests
            'package.json',        
            'requirements.txt',    
            'pyproject.toml',
            'go.mod',              
            'Cargo.toml',          
            
            # Build configs
            'tsconfig.json',
            'vite.config.ts',
            'eslint.config.js',
            
            # Infrastructure
            'Dockerfile',
            'docker-compose.yml',
        }

        return self._search_repo_tree(repo, manifest_filenames)