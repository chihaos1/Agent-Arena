from pinecone import Pinecone
from openai import OpenAI

from core.config import settings

class VectorStore:
    """
    Handle all OpenAI operations for summarizing and embedding and 
    Pinecone operations for storing thhe embeddings
    """

    def __init__(self):
        self.openai = OpenAI(api_key=settings.OPENAI_API_KEY.get_secret_value())
        self.pinecone = Pinecone(api_key=settings.PINECONE_API_KEY.get_secret_value())
        self.pinecone_index = self.pinecone.Index(settings.PINECONE_INDEX_NAME)

    def generate_summary(self, file_path: str, content: str) -> str:
        """Generate semantic summary of a code file using GPT-4o-mini"""

        prompt = f"""
           Summarize this code in 12-18 words (strict limit).

            File: {file_path}
            Code:
            ```
            {content[:3000]}
            ```

            Rules:
            1. START with main constant/function/class names
            2. Use ACTION VERBS (generates, validates, processes, exports, creates, handles)
            3. Mention what it operates on or produces
            4. Use exact technical terms from the code
            5. No labels, no structure, just clear description

            Examples:
            Bad: "Defines a system for managing data"
            Good: "Defines USER_SCHEMA constant for validating user registration with email and password fields"

            Bad: "Handles authentication logic"  
            Good: "Defines validateToken() and refreshSession() functions for JWT-based authentication"

            Bad: "Provides API endpoints"
            Good: "Defines /api/users and /api/login routes using FastAPI router for user management"
        """

        response = self.openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Write ultra-concise code summaries (12-18 words). Start with artifact names. Use action verbs. List multiple artifacts if present. No descriptive fluff."
                },
                {
                    "role":"user",
                    "content":prompt
                }],
            max_tokens=40,
            temperature=0.1
        )

        return response.choices[0].message.content

    def embed_text(self, text: str) -> list[float]:
        """Create embedding using OpenAI"""

        response = self.openai.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )

        return response.data[0].embedding
    
    def create_vector(self, file_path: str, summary: str, repo_name: str) -> dict:
        """Embed summary then return vector structure"""

        embedding = self.embed_text(summary)

        return {
            "id": f"{repo_name}:{file_path}",
            "values": embedding,
            "metadata": {
                "file_path": file_path,
                "summary": summary,
                "repo_name": repo_name
            }
        }
    
    def upsert_batch(self, namespace: str, vectors: list):
        """Batch upsert to Pinecone"""

        self.pinecone_index.upsert(vectors=vectors, namespace=namespace)