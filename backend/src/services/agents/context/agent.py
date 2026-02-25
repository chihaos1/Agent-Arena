from fastapi import HTTPException, status
from github import Github, Auth

from services.repo.embed import VectorStore
from services.agents.context.tools.parse import CodeParser

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
            "files": relevant_files
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
                # print(result["metadata"]["file_path"], result["score"])

        return relevant_matches