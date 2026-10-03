import os
import sys
import pytest

# Add src to sys.path so ragflow_claude_mcp package can be imported
src_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

os.environ.setdefault("RAGFLOW_API_KEY", "test-ragflow-key")
os.environ.setdefault("RAGFLOW_HOST", "http://localhost:8000")

from ragflow_claude_mcp import server

@pytest.fixture(autouse=True)
def reset_ragflow_client():
    """Reset singleton RAGFlow client before each test."""
    server._ragflow_client = None
    yield
    server._ragflow_client = None
