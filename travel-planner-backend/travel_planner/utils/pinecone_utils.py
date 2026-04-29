"""
Pinecone Vector Store Helpers

Provides a soft-degradable wrapper around Pinecone for two use cases:
1. Knowledge base RAG (namespace: "knowledge") - destinations, attractions, restaurants
2. Plan history retrieval (namespace: "plans") - past successful travel plans

If PINECONE_API_KEY is missing or any Pinecone operation fails, every public
method returns a safe empty result so the rest of the pipeline keeps working.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from typing import Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from openai import OpenAI

logger = logging.getLogger(__name__)

load_dotenv()

EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIM = 1536

KNOWLEDGE_NAMESPACE = "knowledge"
PLANS_NAMESPACE = "plans"

PINECONE_METADATA_TEXT_LIMIT = 1000
PINECONE_METADATA_PLAN_LIMIT = 30000


class KnowledgeItem(TypedDict, total=False):
    id: str
    text: str
    metadata: Dict[str, Any]


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pinecone metadata only accepts str, number, bool, or list[str].
    Drop None values and coerce lists to list[str].
    """
    cleaned: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        elif isinstance(value, list):
            str_list = [str(v) for v in value if v is not None]
            if str_list:
                cleaned[key] = str_list
        else:
            cleaned[key] = str(value)
    return cleaned


class PineconeStore:
    """Singleton wrapper around Pinecone with soft-fail behavior."""

    _instance: Optional["PineconeStore"] = None

    @classmethod
    def instance(cls) -> "PineconeStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        self.api_key = os.getenv("PINECONE_API_KEY")
        self.index_name = os.getenv("PINECONE_INDEX_NAME", "travel-planner")
        self.cloud = os.getenv("PINECONE_CLOUD", "aws")
        self.region = os.getenv("PINECONE_REGION", "us-east-1")

        self.pc = None
        self.index = None
        self.openai_client: Optional[OpenAI] = None
        self.enabled = False

        if not self.api_key:
            logger.warning(
                "PINECONE_API_KEY not set. PineconeStore disabled - RAG features will be no-ops."
            )
            return

        if not os.getenv("OPENAI_API_KEY"):
            logger.warning(
                "OPENAI_API_KEY not set. PineconeStore disabled - cannot generate embeddings."
            )
            return

        try:
            from pinecone import Pinecone, ServerlessSpec  # type: ignore

            self.pc = Pinecone(api_key=self.api_key)

            existing = {idx["name"] for idx in self.pc.list_indexes()}
            if self.index_name not in existing:
                logger.info(
                    f"Creating Pinecone index '{self.index_name}' "
                    f"(dim={EMBEDDING_DIM}, metric=cosine, cloud={self.cloud}, region={self.region})..."
                )
                self.pc.create_index(
                    name=self.index_name,
                    dimension=EMBEDDING_DIM,
                    metric="cosine",
                    spec=ServerlessSpec(cloud=self.cloud, region=self.region),
                )
                logger.info(f"Pinecone index '{self.index_name}' created.")

            self.index = self.pc.Index(self.index_name)
            self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
            self.enabled = True
            logger.info(f"PineconeStore enabled (index='{self.index_name}').")
        except Exception as e:
            logger.warning(f"Failed to initialize Pinecone, disabling: {e}")
            self.enabled = False

    def embed_text(self, text: str) -> Optional[List[float]]:
        """Embed text using OpenAI. Returns None on failure or when disabled."""
        if not self.enabled or not text or not self.openai_client:
            return None
        try:
            resp = self.openai_client.embeddings.create(
                model=EMBEDDING_MODEL,
                input=text[:8000],
            )
            return resp.data[0].embedding
        except Exception as e:
            logger.warning(f"Embedding failed: {e}")
            return None

    def upsert_knowledge(
        self,
        items: List[KnowledgeItem],
        namespace: str = KNOWLEDGE_NAMESPACE,
    ) -> int:
        """
        Upsert a batch of items. Each item needs an 'id' and 'text', plus optional metadata.
        The original text is stored under metadata['text'] (truncated) so it can be returned on query.

        Returns number of vectors actually upserted.
        """
        if not self.enabled or not items or not self.index:
            return 0
        try:
            vectors = []
            for item in items:
                text = item.get("text", "")
                if not text:
                    continue
                vec = self.embed_text(text)
                if not vec:
                    continue
                metadata = dict(item.get("metadata", {}) or {})
                metadata["text"] = text[:PINECONE_METADATA_TEXT_LIMIT]
                vectors.append(
                    {
                        "id": item["id"],
                        "values": vec,
                        "metadata": _sanitize_metadata(metadata),
                    }
                )
            if not vectors:
                return 0
            self.index.upsert(vectors=vectors, namespace=namespace)
            logger.info(
                f"Pinecone upsert: {len(vectors)} vectors -> namespace='{namespace}'"
            )
            return len(vectors)
        except Exception as e:
            logger.warning(f"Pinecone upsert failed (namespace={namespace}): {e}")
            return 0

    def query_knowledge(
        self,
        query: str,
        filter: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
        namespace: str = KNOWLEDGE_NAMESPACE,
    ) -> List[Dict[str, Any]]:
        """
        Semantic search. Returns list of {id, score, metadata} dicts.
        metadata['text'] holds the original (truncated) source text.
        """
        if not self.enabled or not query or not self.index:
            return []
        vec = self.embed_text(query)
        if not vec:
            return []
        try:
            res = self.index.query(
                vector=vec,
                top_k=top_k,
                filter=filter,
                namespace=namespace,
                include_metadata=True,
            )
            matches = res.get("matches", []) if isinstance(res, dict) else getattr(res, "matches", [])
            output = []
            for m in matches:
                if isinstance(m, dict):
                    output.append(
                        {
                            "id": m.get("id"),
                            "score": m.get("score"),
                            "metadata": m.get("metadata", {}) or {},
                        }
                    )
                else:
                    output.append(
                        {
                            "id": getattr(m, "id", None),
                            "score": getattr(m, "score", None),
                            "metadata": getattr(m, "metadata", {}) or {},
                        }
                    )
            logger.info(
                f"Pinecone query (namespace='{namespace}', top_k={top_k}): {len(output)} hits"
            )
            return output
        except Exception as e:
            logger.warning(f"Pinecone query failed (namespace={namespace}): {e}")
            return []

    def upsert_plan(self, plan: Dict[str, Any]) -> bool:
        """Index a complete travel plan into the 'plans' namespace."""
        if not self.enabled or not plan:
            return False
        try:
            destination = plan.get("destination", "")
            constraints = plan.get("constraints", {}) or {}
            interests = constraints.get("interests") or []
            if isinstance(interests, str):
                interests = [interests]
            travel_type = constraints.get("travel_type") or "general"
            travelers = constraints.get("travelers")
            budget_limit = constraints.get("budget_limit")
            days = plan.get("days") or []

            text_parts = [
                f"Destination: {destination}",
                f"Travel type: {travel_type}",
                f"Interests: {', '.join(str(i) for i in interests)}",
                f"Duration: {len(days)} days",
            ]
            for day in days:
                text_parts.append(
                    f"Day {day.get('day')}: {day.get('summary', '')}"
                )
                for item in day.get("items", []) or []:
                    text_parts.append(
                        f"  - [{item.get('time', '')}] {item.get('place', '')}: {item.get('reason', '')}"
                    )
            text = "\n".join(text_parts)

            generated_at = plan.get("generated_at", "")
            version = plan.get("version", 1)
            stable_id = hashlib.md5(
                f"plan|{destination}|{generated_at}|{version}".encode("utf-8")
            ).hexdigest()

            metadata: Dict[str, Any] = {
                "destination": destination,
                "interests": interests,
                "travel_type": travel_type,
                "duration_days": len(days),
                "generated_at": generated_at,
                "version": version,
                "plan_json": json.dumps(plan, ensure_ascii=False)[
                    :PINECONE_METADATA_PLAN_LIMIT
                ],
            }
            if travelers is not None:
                metadata["travelers"] = travelers
            if budget_limit is not None:
                metadata["budget_limit"] = float(budget_limit)

            count = self.upsert_knowledge(
                [{"id": stable_id, "text": text, "metadata": metadata}],
                namespace=PLANS_NAMESPACE,
            )
            return count > 0
        except Exception as e:
            logger.warning(f"upsert_plan failed: {e}")
            return False

    def query_similar_plans(
        self,
        destination: str,
        interests: Optional[List[str]] = None,
        travel_type: Optional[str] = None,
        top_k: int = 3,
    ) -> List[Dict[str, Any]]:
        """Find similar past plans by destination + interests + travel_type."""
        if not self.enabled or not destination:
            return []
        interests_str = ", ".join(interests or [])
        query_text = (
            f"Destination: {destination}\n"
            f"Travel type: {travel_type or 'general'}\n"
            f"Interests: {interests_str}"
        )
        return self.query_knowledge(
            query_text,
            top_k=top_k,
            namespace=PLANS_NAMESPACE,
        )


def make_place_id(kind: str, place_id: Optional[str], fallback_text: str) -> str:
    """
    Build a stable, idempotent vector ID for a place.

    Args:
        kind: 'attraction' or 'restaurant' or 'destination'
        place_id: Google Maps place_id if available
        fallback_text: text used to derive a hash if place_id is missing

    Returns:
        Stable string ID safe to use as a Pinecone vector id.
    """
    if place_id:
        return f"{kind}|{place_id}"
    digest = hashlib.md5(fallback_text.lower().encode("utf-8")).hexdigest()
    return f"{kind}|{digest}"


def make_destination_id(destination: str) -> str:
    """Stable ID for a destination guide entry."""
    return f"destination|{destination.strip().lower()}"
