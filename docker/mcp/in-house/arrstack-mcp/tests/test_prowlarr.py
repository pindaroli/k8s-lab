import pytest
from unittest.mock import patch, MagicMock
import server

def test_prowlarr_search(mocker):
    """Test searching Prowlarr indexers and caching results."""
    mock_releases = [
        {
            "title": "Mozart - Le nozze di Figaro (2023) FLAC",
            "size": 6390000000,
            "seeders": 6,
            "indexer": "LimeTorrents",
            "magnetUrl": "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209",
            "downloadUrl": "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209",
            "guid": "guid-123"
        }
    ]
    mocker.patch.object(server, "_prowlarr", return_value=mock_releases)

    result = server.prowlarr_search("Mozart Figaro")
    assert "Mozart - Le nozze di Figaro" in result
    assert len(server._prowlarr_search_cache) == 1
    assert server._prowlarr_search_cache[0]["title"] == "Mozart - Le nozze di Figaro (2023) FLAC"

def test_prowlarr_grab_no_cache():
    """Test prowlarr_grab when no search has been run."""
    result = server.prowlarr_grab(0)
    assert "No cached search results" in result

def test_prowlarr_grab_invalid_index():
    """Test prowlarr_grab with invalid index."""
    server._prowlarr_search_cache = [{"title": "Test Release"}]
    result = server.prowlarr_grab(5)
    assert "Invalid index 5" in result

def test_prowlarr_grab_default_category(mocker):
    """Test prowlarr_grab without specifying category."""
    server._prowlarr_search_cache = [
        {
            "title": "Mozart - Le nozze di Figaro",
            "magnetUrl": "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209"
        }
    ]
    mock_add_url = mocker.patch.object(server, "_qbt_add_url", return_value=(True, ""))

    result = server.prowlarr_grab(0)
    assert "Sent magnet to qBittorrent" in result
    mock_add_url.assert_called_once_with(
        "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209",
        category=""
    )

def test_prowlarr_grab_with_category(mocker):
    """Test prowlarr_grab with explicit category parameter."""
    server._prowlarr_search_cache = [
        {
            "title": "Mozart - Le nozze di Figaro (2023) FLAC",
            "magnetUrl": "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209"
        }
    ]
    mock_add_url = mocker.patch.object(server, "_qbt_add_url", return_value=(True, ""))

    result = server.prowlarr_grab(0, category="lidarr-classical")
    assert "Sent magnet to qBittorrent" in result
    assert "[category: lidarr-classical]" in result

    mock_add_url.assert_called_once_with(
        "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209",
        category="lidarr-classical"
    )
