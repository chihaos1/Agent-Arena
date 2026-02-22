from fastapi import APIRouter, HTTPException
from github import GithubException

from schemas.request.repo.embed import EmbedRepoRequest
from schemas.response.repo.embed import EmbedRepoResponse
from services.repo.embed import VectorStore

from github import Github, Auth

router = APIRouter(prefix="/repo", tags=["repo"])

@router.post("/embed-repo", response_model=EmbedRepoResponse)
async def embed_repo(request: EmbedRepoRequest):
    """
    Traverse a GitHub repository, generates AI summaries for code files, 
    and stores them as vector embeddings in Pinecone to be used by context builder.

    Args:
    * request (EmbedRepoRequest): The validated request body.
    * Attributes:
        * github_token (SecretStr): A valid GitHub Personal Access Token.
        * repo_name (str): Full name of the repository (e.g., 'owner/repo').

    Returns:
    * EmbedRepoResponse: Contains the detailed result of the embedding process.
    * Attributes:
        * success (bool): True if the process completed without fatal errors.
        * files_embedded (int): Total number of source code files successfully processed.
        * namespace (str): The Pinecone namespace where the vectors were stored.
        * message (str): Human-readable confirmation of the indexing results.
    """

    batch = []
    item_count = 0

    try: 
        github_auth = Auth.Token(request.github_token.get_secret_value())

        with Github(auth=github_auth) as github_client:

            # Initialize vector store client (OpenAI + Pinecone)
            vector_store = VectorStore()

            # Connect to GitHub repo
            repo = github_client.get_repo(request.repo_name)
            
            # Get all the files
            tree = repo.get_git_tree(sha=repo.default_branch, recursive=True)

            # Filter for code files only
            code_extensions = [
                '.py', '.js', '.jsx', '.ts', '.tsx', '.java', 
                '.go', '.rs', '.cpp', '.c', '.rb', '.php'
            ]

            code_files = [
                item for item in tree.tree
                if item.type == "blob" and any(item.path.endswith(ext) for ext in code_extensions)
            ]

            for code_file in code_files:
                try:
                    
                    # Get and Decode the code script content
                    file_content_raw = repo.get_contents(code_file.path)
                    file_content_decoded = file_content_raw.decoded_content.decode("utf-8", errors="ignore")

                    # Summarize and embed the summary
                    file_content_summary = vector_store.generate_summary(code_file.path, file_content_decoded)
                    file_content_summary_vector = vector_store.create_vector(code_file.path, file_content_summary, repo.full_name)
                    batch.append(file_content_summary_vector)
                    item_count += 1

                    # Upsert the batched when it reached 50 items
                    if len(batch) >= 50:
                        vector_store.upsert_batch(repo.full_name, batch)
                        batch = []

                except Exception as e:
                    continue
        
            if batch:
                vector_store.upsert_batch(repo.full_name, batch)

        return EmbedRepoResponse(
            success=True,
            files_embedded=item_count,
            namespace=repo.full_name,
            message=f"Successfully embedded {item_count} scripts into {repo.full_name}"
        )

    except GithubException as e:
        if e.status == 401:
            raise HTTPException(status_code=401, detail="Invalid Github token")
        elif e.status == 404:
            raise HTTPException(status_code=404, detail=f"Repository {request.repo_name} was not found or no permission to access")
        else:
            raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")