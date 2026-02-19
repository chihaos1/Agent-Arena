from github import Github, Auth

from services.repo.embed import VectorStore

class ContextAssembler:
    """Assemble context for issue by finding relevant files"""

    def __init__(self, github_token):
        self.vector_store = VectorStore()
        self.github_token = github_token
        self._handlers = {
            # ".py": self._extract_python_signatures
            # ".ts": self._extract_typescript_signatures,
            # ".tsx": self._extract_tsx_signatures,
            # ".css": self._extract_css_excerpt,
            # ".html": self._extract_html_excerpt,
        }

    def assemble_context(
            self,
            query: str, 
            repo_name: str
        ):

        # Fetch the most relevant scripts' GitHub file paths from Pinecone
        relevant_files = self._search_relevant_files(query=query,repo_name=repo_name)

        # Fetch the actual code files from GitHub using the file paths
        github_auth = Auth.Token(self.github_token)

        with Github(auth=github_auth) as github_client:

            # Connect to GitHub repo
            repo = github_client.get_repo(repo_name)
            
            # Fetch the code content from GitHub
            for file in relevant_files:
                    
                # Get and Decode the code script content
                file_content_raw = repo.get_contents(file["file_path"])
                file_content_decoded = file_content_raw.decoded_content.decode("utf-8", errors="ignore")
                code_excerpt = self._extract_code_excerpt(file["file_path"], file_content_decoded)

    def _search_relevant_files(
            self, 
            query: str, 
            repo_name: str, 
            top_k: int = 10, 
            relative_threshold: float = 0.7
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

        # Filter files based on relative scores
        relevant_matches = []
        top_score = results["matches"][0]["score"]
        cutoff_score = top_score * relative_threshold

        for result in results["matches"]:
           if result["score"] > cutoff_score:      
                relevant_matches.append({
                    "file_path": result["metadata"]["file_path"],
                    "summary": result["metadata"]["summary"],
                    "score": result["score"]
                })

        return relevant_matches

    def _extract_code_excerpt(self, file_path: str, content: str):
        """
        Docstring for _extract_code_excerpt
        
        :param self: Description
        """

        file_ext = file_path.split(".")[-1]

        # Uses the parser for specific language, fall back to first 50 lines if language not found
        handler = self._handlers.get(
            file_ext, 
            lambda content: "\n".join(content.splitlines()[:50])
        )

        return handler(content)

