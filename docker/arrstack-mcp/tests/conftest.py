import os
import sys
import pytest

# Add parent directory (docker/arrstack-mcp) to sys.path so server.py can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set mock env vars for testing before server import if needed
os.environ.setdefault("PROWLARR_URL", "http://localhost:9696")
os.environ.setdefault("PROWLARR_API_KEY", "test-prowlarr-key")
os.environ.setdefault("QBITTORRENT_URL", "http://localhost:8080")

import server

@pytest.fixture(autouse=True)
def reset_search_cache():
    """Reset prowlarr search cache before each test."""
    server._prowlarr_search_cache = []
    yield
    server._prowlarr_search_cache = []
