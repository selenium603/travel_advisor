"""
CrewAI tool wrappers — only the knowledge/RAG tool remains as a CrewAI tool
since it's used directly by AI agents during reasoning.
"""

from crewai.tools import BaseTool
from typing import Type, Optional
from pydantic import BaseModel, Field


class TravelKnowledgeInput(BaseModel):
    """Input for TravelKnowledgeTool"""
    query: str = Field(..., description="Question about travel, visa, culture, etc")
    destination: Optional[str] = Field(default=None, description="Specific destination (optional)")


class TravelKnowledgeTool(BaseTool):
    name: str = "Get Travel Knowledge"
    description: str = (
        "Get travel tips, visa requirements, cultural information, and best practices "
        "for destinations. Use this to answer questions about customs, etiquette, "
        "packing, and destination-specific advice."
    )
    args_schema: Type[BaseModel] = TravelKnowledgeInput

    def _run(self, query: str, destination: Optional[str] = None) -> str:
        """Retrieve travel knowledge from RAG system."""
        from backend.services.knowledge.rag import RAGService
        rag = RAGService()
        return rag.query(query=query, destination=destination)
