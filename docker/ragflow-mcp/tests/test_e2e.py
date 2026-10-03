import pytest
from unittest.mock import AsyncMock, patch
from ragflow_claude_mcp.client.ragflow import RAGFlowMCPServer

@pytest.mark.asyncio
async def test_ragflow_client_search_datasets(mocker):
    """Test mocked dataset search in RAGFlowMCPServer."""
    mock_datasets = {
        "code": 0,
        "data": [
            {"id": "ds-1", "name": "Homelab Wiki", "doc_count": 42}
        ]
    }
    client = RAGFlowMCPServer(base_url="http://localhost:8000", api_key="test-key")
    mocker.patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_datasets)

    res = await client.list_datasets()
    assert res["code"] == 0
    assert len(res["data"]) == 1
    assert res["data"][0]["name"] == "Homelab Wiki"

@pytest.mark.asyncio
async def test_ragflow_client_retrieval_query(mocker):
    """Test mocked retrieval_query in RAGFlowMCPServer."""
    mock_chunks = {
        "code": 0,
        "data": {
            "chunks": [
                {"content": "Talos Linux on Proxmox PVE3 documentation", "dataset_id": "ds-1"}
            ]
        }
    }
    client = RAGFlowMCPServer(base_url="http://localhost:8000", api_key="test-key")
    mocker.patch.object(client, "_make_request", new_callable=AsyncMock, return_value=mock_chunks)

    res = await client.retrieval_query(dataset_ids=["ds-1"], query="Talos PVE3")
    assert "chunks" in res["data"]
    assert res["data"]["chunks"][0]["content"] == "Talos Linux on Proxmox PVE3 documentation"
