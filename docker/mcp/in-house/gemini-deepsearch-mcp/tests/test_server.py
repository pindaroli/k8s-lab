import pytest
from unittest.mock import MagicMock
from langchain_core.messages import AIMessage

from src import main

def test_deep_search_low_effort(mocker):
    """Test deep_search tool with low effort."""
    mock_graph_result = {
        "messages": [AIMessage(content="Synthetic search answer for test query")],
        "sources_gathered": ["https://example.com/source1"]
    }
    mock_invoke = mocker.patch.object(main.graph, "invoke", return_value=mock_graph_result)

    result = main.deep_search(query="Quantum computing status 2026", effort="low")

    assert result["answer"] == "Synthetic search answer for test query"
    assert result["sources"] == ["https://example.com/source1"]
    mock_invoke.assert_called_once()
    state = mock_invoke.call_args[0][0]
    assert state["initial_search_query_count"] == 1
    assert state["max_research_loops"] == 1

def test_deep_search_high_effort(mocker):
    """Test deep_search tool with high effort."""
    mock_graph_result = {
        "messages": [AIMessage(content="High effort deep research report")],
        "sources_gathered": ["https://example.com/source1", "https://example.com/source2"]
    }
    mock_invoke = mocker.patch.object(main.graph, "invoke", return_value=mock_graph_result)

    result = main.deep_search(query="Kubernetes Talos OS benchmarking", effort="high")

    assert result["answer"] == "High effort deep research report"
    assert len(result["sources"]) == 2
    mock_invoke.assert_called_once()
    state = mock_invoke.call_args[0][0]
    assert state["initial_search_query_count"] == 5
    assert state["max_research_loops"] == 3
