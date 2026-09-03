"""
ragflow-mcp — Model Context Protocol (MCP) server for RAGFlow knowledge base.

Exposes RAGFlow datasets and document retrieval capabilities to AI agents in Antigravity.
Optimized for hardware datasheets, installation manuals, and lab documentation (dataset: 'k8s-lab').
"""

import os
import sys
import json
import logging
from typing import Optional, Any, Dict, List

import httpx
from mcp.server.fastmcp import FastMCP

logging.basicConfig(
    level=os.environ.get("LOG_LEVEL", "INFO"),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("ragflow-mcp")

# ── Configuration ──
RAGFLOW_BASE_URL = os.environ.get("RAGFLOW_BASE_URL", "https://ragflow-internal.pindaroli.org").rstrip("/")
RAGFLOW_API_KEY = os.environ.get("RAGFLOW_API_KEY", "")
VERIFY_SSL = os.environ.get("VERIFY_SSL", "false").lower() in ("true", "1", "yes")
DEFAULT_DATASET = os.environ.get("DEFAULT_DATASET", "k8s-lab")

mcp = FastMCP("ragflow-mcp")

# In-memory cache for dataset name -> id mappings
_dataset_cache: Dict[str, str] = {}
# In-memory cache for doc_id -> doc_name mappings
_doc_cache: Dict[str, str] = {}


def _get_client() -> httpx.AsyncClient:
    headers = {
        "Authorization": f"Bearer {RAGFLOW_API_KEY}",
        "Content-Type": "application/json",
    }
    return httpx.AsyncClient(
        base_url=RAGFLOW_BASE_URL,
        headers=headers,
        verify=VERIFY_SSL,
        timeout=45.0,
    )


async def _resolve_dataset_id(client: httpx.AsyncClient, dataset_name: str) -> Optional[str]:
    """Resolves a dataset name to its corresponding ID in RAGFlow."""
    global _dataset_cache
    if dataset_name in _dataset_cache:
        return _dataset_cache[dataset_name]

    try:
        resp = await client.get("/api/v1/datasets", params={"page": 1, "page_size": 100})
        if resp.status_code != 200:
            logger.error("Failed to list datasets: HTTP %d: %s", resp.status_code, resp.text)
            return None

        res_data = resp.json()
        items = res_data.get("data", [])
        if isinstance(items, dict):
            items = items.get("datasets", [])

        for ds in items:
            name = ds.get("name")
            ds_id = ds.get("id")
            if name and ds_id:
                _dataset_cache[name] = ds_id
                if name.lower() == dataset_name.lower():
                    return ds_id

        # Check if dataset_name is already a valid UUID / dataset ID
        for ds in items:
            if ds.get("id") == dataset_name:
                return dataset_name

    except Exception as e:
        logger.error("Error resolving dataset ID: %s", e)

    return None


@mcp.tool(
    name="ragflow_list_datasets",
    description=(
        "List all knowledge bases (datasets) available in RAGFlow. "
        "Returns dataset names, IDs, document counts, and chunk statistics."
    ),
)
async def ragflow_list_datasets() -> str:
    """Lists all datasets configured in RAGFlow."""
    if not RAGFLOW_API_KEY:
        return "Error: RAGFLOW_API_KEY environment variable is not configured."

    async with _get_client() as client:
        try:
            resp = await client.get("/api/v1/datasets", params={"page": 1, "page_size": 100})
            if resp.status_code != 200:
                return f"Error from RAGFlow API (HTTP {resp.status_code}): {resp.text}"

            res = resp.json()
            items = res.get("data", [])
            if isinstance(items, dict):
                items = items.get("datasets", [])

            if not items:
                return "No datasets found in RAGFlow."

            output = ["### RAGFlow Datasets:\n"]
            for ds in items:
                ds_id = ds.get("id", "N/A")
                name = ds.get("name", "Unnamed")
                doc_count = ds.get("document_count", ds.get("doc_num", 0))
                chunk_count = ds.get("chunk_count", ds.get("chunk_num", 0))
                emb_model = ds.get("embedding_model_name", "N/A")
                desc = ds.get("description", "").strip() or "No description provided."
                output.append(f"- **{name}** (ID: `{ds_id}`)")
                output.append(f"  - Documents: {doc_count} | Chunks: {chunk_count} | Embedding: {emb_model}")
                output.append(f"  - Description: {desc}\n")

            return "\n".join(output)
        except Exception as exc:
            return f"Failed to connect to RAGFlow at {RAGFLOW_BASE_URL}: {exc}"


@mcp.tool(
    name="ragflow_list_documents",
    description=(
        "List all documents, manuals, and datasheets indexed within a specific dataset in RAGFlow. "
        "Defaults to the 'k8s-lab' hardware knowledge base."
    ),
)
async def ragflow_list_documents(dataset_name: str = DEFAULT_DATASET) -> str:
    """Lists documents in the specified dataset."""
    if not RAGFLOW_API_KEY:
        return "Error: RAGFLOW_API_KEY environment variable is not configured."

    async with _get_client() as client:
        try:
            ds_id = await _resolve_dataset_id(client, dataset_name)
            if not ds_id:
                return f"Dataset '{dataset_name}' could not be found in RAGFlow."

            resp = await client.get(f"/api/v1/datasets/{ds_id}/documents", params={"page": 1, "page_size": 100})
            if resp.status_code != 200:
                return f"Error fetching documents for dataset '{dataset_name}' (HTTP {resp.status_code}): {resp.text}"

            res = resp.json()
            data = res.get("data", {})
            if isinstance(data, dict):
                docs = data.get("docs", data.get("documents", []))
            elif isinstance(data, list):
                docs = data
            else:
                docs = []

            if not docs:
                return f"No documents found in dataset '{dataset_name}' (ID: `{ds_id}`)."

            output = [f"### Documents in Dataset '{dataset_name}' (`{ds_id}`):\n"]
            for doc in docs:
                name = doc.get("name", "Unnamed")
                doc_id = doc.get("id", "N/A")
                status = doc.get("run", doc.get("status", "N/A"))
                size_kb = round(doc.get("size", 0) / 1024, 1)
                chunk_num = doc.get("chunk_num", doc.get("chunk_count", 0))

                # Update doc cache
                if doc_id and name:
                    _doc_cache[doc_id] = name

                output.append(f"- **{name}** (ID: `{doc_id}`)")
                output.append(f"  - Status: `{status}` | Size: {size_kb} KB | Chunks: {chunk_num}\n")

            return "\n".join(output)
        except Exception as exc:
            return f"Failed to fetch documents from RAGFlow: {exc}"


@mcp.tool(
    name="ragflow_search",
    description=(
        "Search the homelab hardware knowledge base (dataset: 'k8s-lab') in RAGFlow. "
        "Use this tool when answering questions about physical hardware manuals, datasheets, "
        "installation guides, motherboard pinouts, PCIe lane allocation, BIOS/IPMI settings, "
        "switch ports, cabling, or component specifications. "
        "Returns matching text chunks, tables, page numbers, and document citations."
    ),
)
async def ragflow_search(
    query: str,
    dataset_name: str = DEFAULT_DATASET,
    top_k: int = 6,
    similarity_threshold: float = 0.2,
) -> str:
    """Performs semantic/hybrid search across documents in the specified dataset."""
    if not RAGFLOW_API_KEY:
        return "Error: RAGFLOW_API_KEY environment variable is not configured."

    async with _get_client() as client:
        try:
            ds_id = await _resolve_dataset_id(client, dataset_name)
            if not ds_id:
                return f"Dataset '{dataset_name}' could not be resolved in RAGFlow."

            payload = {
                "question": query,
                "dataset_ids": [ds_id],
                "page": 1,
                "page_size": top_k,
                "similarity_threshold": similarity_threshold,
                "vector_similarity_weight": 0.3,
                "top_k": 1024,
            }

            resp = await client.post("/api/v1/retrieval", json=payload)
            if resp.status_code != 200:
                return f"Error querying RAGFlow retrieval API (HTTP {resp.status_code}): {resp.text}"

            res = resp.json()
            data = res.get("data", {})
            chunks = data.get("chunks", []) if isinstance(data, dict) else []

            if not chunks:
                return f"No relevant chunks found in dataset '{dataset_name}' for query: '{query}' (threshold: {similarity_threshold})."

            output = [
                f"### RAGFlow Retrieval Results for '{query}'",
                f"**Dataset**: `{dataset_name}` (`{ds_id}`) | **Matches**: {len(chunks)}\n",
            ]

            for idx, chunk in enumerate(chunks, 1):
                doc_name = (
                    chunk.get("document_keyword")
                    or chunk.get("docnm_kwd")
                    or chunk.get("document_name")
                    or _doc_cache.get(chunk.get("document_id", ""), "Unknown Document")
                )
                similarity = chunk.get("similarity", 0.0)
                content = chunk.get("content", "").strip()
                doc_type = chunk.get("doc_type_kwd", [])
                type_str = f" [{', '.join(doc_type)}]" if doc_type else ""

                # Try to extract page number from positions: positions is usually [[page, x1, x2, y1, y2], ...]
                page_str = ""
                positions = chunk.get("positions", [])
                if positions and isinstance(positions, list) and len(positions) > 0:
                    first_pos = positions[0]
                    if isinstance(first_pos, list) and len(first_pos) > 0:
                        page_str = f" | Page: {first_pos[0]}"

                output.append(f"#### [{idx}] Document: **{doc_name}**{type_str} (Score: {similarity:.4f}{page_str})")
                output.append(f"> {content}\n")

            return "\n".join(output)

        except Exception as exc:
            return f"Failed to execute search on RAGFlow: {exc}"


def main():
    logger.info("Starting ragflow-mcp server on stdio transport...")
    logger.info("Base URL: %s | Verify SSL: %s | Default Dataset: %s", RAGFLOW_BASE_URL, VERIFY_SSL, DEFAULT_DATASET)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
