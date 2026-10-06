import pytest
import server

def test_qbt_add_options():
    """Test helper that constructs qBittorrent form options."""
    opts = server._qbt_add_options(category="lidarr-classical", save_path="/media/classical", paused=True)
    assert opts["category"] == "lidarr-classical"
    assert opts["savepath"] == "/media/classical"
    assert opts["autoTMM"] == "false"
    assert opts["paused"] == "true"
    assert opts["stopped"] == "true"

def test_qbt_add_url_with_category(mocker):
    """Test _qbt_add_url sending category to POST /torrents/add."""
    mock_qbt = mocker.patch.object(server, "_qbt", return_value="Ok.")

    ok, detail = server._qbt_add_url(
        "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209",
        category="lidarr-classical"
    )

    assert ok is True
    assert detail == ""
    mock_qbt.assert_called_once()
    call_args = mock_qbt.call_args
    assert call_args[0][0] == "/torrents/add"
    assert call_args[1]["data"]["category"] == "lidarr-classical"
    assert call_args[1]["data"]["urls"] == "magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209"

def test_qbt_add_magnet_tool(mocker):
    """Test qbt_add_magnet tool."""
    mock_qbt = mocker.patch.object(server, "_qbt", return_value="Ok.")

    result = server.qbt_add_magnet(
        magnet_url="magnet:?xt=urn:btih:d5ca2cb8fde84fa00d6a9ebf5dd89f1982b5f209",
        category="lidarr-classical"
    )

    assert "Magnet added to qBittorrent" in result
    mock_qbt.assert_called_once()
    assert mock_qbt.call_args[1]["data"]["category"] == "lidarr-classical"

def test_qbt_set_category(mocker):
    """Test qbt_set_category tool."""
    mock_qbt = mocker.patch.object(server, "_qbt", return_value="")

    result = server.qbt_set_category(
        torrent_hash="1a6534f53067ebe9111e357e31c86d1b42290446",
        category="video-filebot"
    )

    assert "Category set to 'video-filebot'" in result
    mock_qbt.assert_called_once_with(
        "/torrents/setCategory",
        method="POST",
        data={"hashes": "1a6534f53067ebe9111e357e31c86d1b42290446", "category": "video-filebot"}
    )
