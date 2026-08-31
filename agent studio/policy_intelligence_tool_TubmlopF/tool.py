"""
Policy Intelligence Tool for Danantara Workforce Intelligence.

Supported operations:
- search_policy
- get_policy_context
- compare_policies

Behavior:
- Search governed HR policy chunks from Qdrant.
- Support entity-specific retrieval for BNS, ENP, NSH, DANANTARA.
- If entity is omitted, search across all available policy entities.
- Return grounded source metadata including document title, page,
  section, retrieval score, and source_s3_uri when available.

This tool is read-only.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any

import argparse
import json
import requests


# ============================================================
# CONFIGURATION
# ============================================================

class UserParameters(BaseModel):
    """
    Fixed tool configuration.
    """

    qdrant_base_url: str
    qdrant_api_key: str

    policy_collection: str = "workforce_policies"

    gemini_api_key: str
    embedding_model: str

    timeout_seconds: int = 20


# ============================================================
# TOOL PARAMETERS
# ============================================================

class ToolParameters(BaseModel):

    operation: str = Field(
        description=(
            "Operation to execute. Allowed values: "
            "search_policy, get_policy_context, compare_policies."
        )
    )

    query: Optional[str] = Field(
        default=None,
        description=(
            "Policy question or semantic search query."
        )
    )

    entity: Optional[str] = Field(
        default=None,
        description=(
            "Optional entity filter. Supported values: "
            "BNS, ENP, NSH, DANANTARA. "
            "Leave empty to search across all policy entities."
        )
    )

    entity_a: Optional[str] = Field(
        default=None,
        description=(
            "First entity for comparison. "
            "Supported values: BNS, ENP, NSH, DANANTARA."
        )
    )

    entity_b: Optional[str] = Field(
        default=None,
        description=(
            "Second entity for comparison. "
            "Supported values: BNS, ENP, NSH, DANANTARA."
        )
    )

    limit: int = Field(
        default=5,
        ge=1,
        le=10,
        description=(
            "Maximum number of policy chunks retrieved."
        )
    )


# ============================================================
# CONSTANTS
# ============================================================

SUPPORTED_ENTITIES = {
    "BNS",
    "ENP",
    "NSH",
    "DANANTARA"
}


# ============================================================
# HELPERS
# ============================================================

def normalize_entity(
    value: Optional[str]
) -> Optional[str]:

    if not value:
        return None

    normalized = value.strip().upper()

    if normalized not in SUPPORTED_ENTITIES:

        raise ValueError(
            f"Unsupported entity '{value}'. "
            f"Supported values: "
            f"{', '.join(sorted(SUPPORTED_ENTITIES))}"
        )

    return normalized


def payload_value(
    payload: dict,
    possible_names: list
) -> Any:

    for name in possible_names:

        value = payload.get(name)

        if value is not None:
            return value

    return None


# ============================================================
# GEMINI EMBEDDING
# ============================================================

def create_embedding(
    config: UserParameters,
    text: str
) -> list:

    if not text:
        raise ValueError(
            "Text is required for embedding."
        )

    model = config.embedding_model.strip()

    if model.startswith("models/"):
        model_path = model
    else:
        model_path = f"models/{model}"

    url = (
        "https://generativelanguage.googleapis.com/v1beta/"
        f"{model_path}:embedContent"
    )

    response = requests.post(
        url,
        params={
            "key": config.gemini_api_key
        },
        json={
            "model": model_path,
            "content": {
                "parts": [
                    {
                        "text": text
                    }
                ]
            }
        },
        headers={
            "Content-Type": "application/json"
        },
        timeout=config.timeout_seconds
    )

    if not response.ok:

        raise RuntimeError(
            "Embedding API failed: "
            f"HTTP {response.status_code} "
            f"{response.text[:1000]}"
        )

    data = response.json()

    embedding = (
        data
        .get("embedding", {})
        .get("values", [])
    )

    if not embedding:

        raise RuntimeError(
            "Embedding API returned no vector values."
        )

    return embedding


# ============================================================
# QDRANT RESULT NORMALIZATION
# ============================================================

def normalize_result(
    point: dict
) -> dict:

    payload = (
        point.get("payload", {})
        or {}
    )

    return {
        "point_id": point.get("id"),
        "score": point.get("score"),

        "document_id": payload_value(
            payload,
            [
                "document_id",
                "doc_id"
            ]
        ),

        "title": payload_value(
            payload,
            [
                "title",
                "document_name",
                "source_filename",
                "filename",
                "file_name",
                "source"
            ]
        ),

        "entity": payload_value(
            payload,
            [
                "entity",
                "company",
                "business_entity"
            ]
        ),

        "document_type": payload_value(
            payload,
            [
                "document_type",
                "doc_type",
                "policy_type"
            ]
        ),

        "page": payload_value(
            payload,
            [
                "page",
                "page_number",
                "page_no"
            ]
        ),

        "section": payload_value(
            payload,
            [
                "section",
                "section_name",
                "heading"
            ]
        ),

        "text": payload_value(
            payload,
            [
                "text",
                "chunk_text",
                "content",
                "document_text"
            ]
        ),

        "source_s3_uri": payload_value(
            payload,
            [
                "source_s3_uri",
                "source_uri",
                "s3_uri"
            ]
        )
    }


# ============================================================
# QDRANT SEARCH
# ============================================================

def search_qdrant(
    config: UserParameters,
    query: str,
    entity: Optional[str],
    limit: int
) -> list:

    vector = create_embedding(
        config,
        query
    )

    body = {
        "vector": vector,
        "limit": limit,
        "with_payload": True,
        "with_vector": False
    }

    if entity:

        body["filter"] = {
            "must": [
                {
                    "key": "entity",
                    "match": {
                        "value": entity
                    }
                }
            ]
        }

    url = (
        config.qdrant_base_url.rstrip("/")
        + "/collections/"
        + config.policy_collection
        + "/points/search"
    )

    response = requests.post(
        url,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "api-key": config.qdrant_api_key
        },
        json=body,
        timeout=config.timeout_seconds
    )

    if not response.ok:

        raise RuntimeError(
            "Qdrant search failed: "
            f"HTTP {response.status_code} "
            f"{response.text[:1500]}"
        )

    points = (
        response.json()
        .get("result", [])
        or []
    )

    return [
        normalize_result(point)
        for point in points
    ]


# ============================================================
# SEARCH POLICY
# ============================================================

def search_policy(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.query:

        return {
            "status": "error",
            "message": (
                "query is required for search_policy."
            )
        }

    entity = normalize_entity(
        args.entity
    )

    results = search_qdrant(
        config=config,
        query=args.query,
        entity=entity,
        limit=args.limit
    )

    return {
        "status": "success",
        "operation": "search_policy",

        "query": args.query,

        "entity_filter": (
            entity
            if entity
            else "ALL"
        ),

        "result_count": len(
            results
        ),

        "results": results,

        "instruction": (
            "Use only retrieved policy evidence. "
            "If entity_filter is ALL, results may come from "
            "BNS, ENP, NSH, or DANANTARA. "
            "Do not invent policy information."
        )
    }


# ============================================================
# GET POLICY CONTEXT
# ============================================================

def get_policy_context(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.query:

        return {
            "status": "error",
            "message": (
                "query is required for get_policy_context."
            )
        }

    entity = normalize_entity(
        args.entity
    )

    results = search_qdrant(
        config=config,
        query=args.query,
        entity=entity,
        limit=args.limit
    )

    contexts = []

    for result in results:

        contexts.append({
            "entity": result.get(
                "entity"
            ),

            "title": result.get(
                "title"
            ),

            "document_type": result.get(
                "document_type"
            ),

            "page": result.get(
                "page"
            ),

            "section": result.get(
                "section"
            ),

            "score": result.get(
                "score"
            ),

            "text": result.get(
                "text"
            ),

            "source_s3_uri": result.get(
                "source_s3_uri"
            )
        })

    return {
        "status": "success",
        "operation": "get_policy_context",

        "query": args.query,

        "entity_filter": (
            entity
            if entity
            else "ALL"
        ),

        "context_count": len(
            contexts
        ),

        "contexts": contexts,

        "instruction": (
            "Answer only from retrieved contexts. "
            "Reference title, page, section, and source_s3_uri "
            "when available. "
            "If entity_filter is ALL, explicitly mention which "
            "entity each policy result belongs to. "
            "Do not invent policy rules or values."
        )
    }


# ============================================================
# COMPARE POLICIES
# ============================================================

def compare_policies(
    config: UserParameters,
    args: ToolParameters
) -> dict:

    if not args.query:

        return {
            "status": "error",
            "message": (
                "query is required for compare_policies."
            )
        }

    entity_a = normalize_entity(
        args.entity_a
    )

    entity_b = normalize_entity(
        args.entity_b
    )

    if not entity_a or not entity_b:

        return {
            "status": "error",
            "message": (
                "entity_a and entity_b are required "
                "for compare_policies."
            )
        }

    results_a = search_qdrant(
        config=config,
        query=args.query,
        entity=entity_a,
        limit=args.limit
    )

    results_b = search_qdrant(
        config=config,
        query=args.query,
        entity=entity_b,
        limit=args.limit
    )

    return {
        "status": "success",

        "operation": "compare_policies",

        "query": args.query,

        "entity_a": {
            "name": entity_a,
            "context_count": len(
                results_a
            ),
            "contexts": results_a
        },

        "entity_b": {
            "name": entity_b,
            "context_count": len(
                results_b
            ),
            "contexts": results_b
        },

        "instruction": (
            "Compare only facts explicitly present in "
            "the retrieved contexts. "
            "Do not invent differences. "
            "Reference title, page, section, and source_s3_uri "
            "when available."
        )
    }


# ============================================================
# DISPATCH
# ============================================================

def run_tool(
    config: UserParameters,
    args: ToolParameters
) -> Any:

    operation = (
        args.operation
        .strip()
        .lower()
    )

    if operation == "search_policy":

        return search_policy(
            config,
            args
        )

    if operation == "get_policy_context":

        return get_policy_context(
            config,
            args
        )

    if operation == "compare_policies":

        return compare_policies(
            config,
            args
        )

    return {
        "status": "error",
        "message": (
            "Unsupported operation. Allowed values: "
            "search_policy, get_policy_context, compare_policies."
        )
    }


# ============================================================
# AGENT STUDIO ENTRYPOINT
# ============================================================

OUTPUT_KEY = "tool_output"


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--user-params",
        required=True
    )

    parser.add_argument(
        "--tool-params",
        required=True
    )

    cli = parser.parse_args()

    try:

        config = UserParameters(
            **json.loads(
                cli.user_params
            )
        )

        params = ToolParameters(
            **json.loads(
                cli.tool_params
            )
        )

        output = run_tool(
            config,
            params
        )

        print(
            OUTPUT_KEY,
            json.dumps(
                output,
                ensure_ascii=False,
                default=str
            )
        )

    except Exception as exc:

        print(
            OUTPUT_KEY,
            json.dumps(
                {
                    "status": "error",
                    "error_type": (
                        type(exc).__name__
                    ),
                    "message": str(exc)
                },
                ensure_ascii=False
            )
        )