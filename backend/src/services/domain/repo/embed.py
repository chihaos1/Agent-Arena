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
            Summarize in 12-18 words what this code DOES.

            File: {file_path}
            Code: {content[:3000]}

            **Rules:**
            1. Start with action verb (Renders, Displays, Processes, Manages, Handles, Validates)
            2. Include key hardcoded values (scale=2, timeout=5000, max_retries=3)
            3. Use outcome language: what users see/get, not internal structure
            4. For models/types: describe the entities they represent
            5. Mention tech layer when relevant (React component, API endpoint, database schema)

            **Examples:**

            Bad: "Exports Brain component with GLTF processing and rotation state"
            Good: "React component that displays a 3D brain model with scale=2 and interactive rotation controls."

            Bad: "Defines API route for mind map creation"
            Good: "API endpoint generating mind map nodes using Claude with max_tokens=4096"

            Bad: "Contains User interface definition"
            Good: "TypeScript type defining User with email, role, and subscription fields"

            Bad: "Validates authentication tokens"
            Good: "Validates JWT tokens with 300-second expiry and refresh logic"
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