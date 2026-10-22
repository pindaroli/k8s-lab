import json
from unittest.mock import AsyncMock, patch
import pytest
import server


@pytest.mark.asyncio
async def test_bitmagnet_not_configured(monkeypatch):
    """Verifica che i tool restituiscano un messaggio chiaro se Bitmagnet non è configurato."""
    monkeypatch.setattr(server, "BITMAGNET_GRAPHQL_URL", "")

    res_simple = await server.bitmagnet_simple_search(query="Ubuntu", contentType=None, limit=5)
    assert "Bitmagnet non è configurato" in res_simple

    res_complex = await server.bitmagnet_complex_search(
        queryString="Ubuntu",
        contentTypes=None,
        videoResolutions=None,
        videoSources=None,
        videoCodecs=None,
        languages=None,
        releaseYear=None,
        minSeeders=None,
        tags=None,
        orderBy=None,
        limit=10,
        page=1,
        includeTotalCount=True,
        maxFilesPerTorrent=25,
    )
    assert "Bitmagnet non è configurato" in res_complex


@pytest.mark.asyncio
async def test_bitmagnet_simple_search(monkeypatch):
    """Verifica bitmagnet_simple_search e la formattazione di sizeFormatted."""
    monkeypatch.setattr(server, "BITMAGNET_GRAPHQL_URL", "http://10.10.20.50:3333/graphql")

    mock_graphql_data = {
        "torrentContent": {
            "search": {
                "items": [
                    {
                        "id": "tc-1",
                        "infoHash": "abcdef1234567890",
                        "title": "Beethoven Complete Symphonies FLAC",
                        "contentType": "music",
                        "seeders": 42,
                        "leechers": 3,
                        "publishedAt": "2026-01-15T10:00:00Z",
                        "torrent": {
                            "name": "Beethoven.Complete.Symphonies.FLAC",
                            "size": 1073741824,
                            "magnetUri": "magnet:?xt=urn:btih:abcdef1234567890",
                            "filesCount": 9,
                        },
                    }
                ]
            }
        }
    }

    with patch.object(server, "_bitmagnet_execute_graphql", new=AsyncMock(return_value=mock_graphql_data)) as mock_exec:
        raw_out = await server.bitmagnet_simple_search(query="Beethoven", contentType="music", limit=5)
        payload = json.loads(raw_out)

        assert payload["count"] == 1
        assert payload["items"][0]["seeders"] == 42
        assert "sizeFormatted" in payload["items"][0]["torrent"]

        called_query, called_vars = mock_exec.call_args[0]
        assert called_vars["input"]["queryString"] == "Beethoven"
        assert called_vars["input"]["limit"] == 5
        assert called_vars["input"]["facets"] == {"contentType": {"filter": ["music"]}}


@pytest.mark.asyncio
async def test_bitmagnet_complex_search_filtering(monkeypatch):
    """Verifica mappatura WEB->WEBDL/WEBRip, filtro post-query minSeeders/videoCodecs e troncamento file."""
    monkeypatch.setattr(server, "BITMAGNET_GRAPHQL_URL", "http://10.10.20.50:3333/graphql")

    mock_graphql_data = {
        "torrentContent": {
            "search": {
                "totalCount": 3,
                "hasNextPage": False,
                "items": [
                    {
                        "id": "1",
                        "title": "Movie 4K HEVC Valid",
                        "seeders": 25,
                        "videoCodec": "H265",
                        "torrent": {
                            "size": 5000000000,
                            "files": [
                                {"index": 0, "path": "movie.mkv", "size": 4990000000},
                                {"index": 1, "path": "subs.srt", "size": 50000},
                                {"index": 2, "path": "info.nfo", "size": 1000},
                            ],
                        },
                    },
                    {
                        "id": "2",
                        "title": "Movie Low Seeders (Filtered Out)",
                        "seeders": 2,
                        "videoCodec": "x265",
                        "torrent": {"size": 4000000000, "files": []},
                    },
                    {
                        "id": "3",
                        "title": "Movie Wrong Codec (Filtered Out)",
                        "seeders": 50,
                        "videoCodec": "x264",
                        "torrent": {"size": 3000000000, "files": []},
                    },
                ],
                "aggregations": {"contentType": [{"value": "movie", "count": 3}]},
            }
        }
    }

    with patch.object(server, "_bitmagnet_execute_graphql", new=AsyncMock(return_value=mock_graphql_data)) as mock_exec:
        raw_out = await server.bitmagnet_complex_search(
            queryString="Movie",
            contentTypes=["movie"],
            videoResolutions=["V2160p"],
            videoSources=["WEB"],
            videoCodecs=["x265"],
            languages=["it", "en"],
            releaseYear=2025,
            minSeeders=10,
            tags=["uhd"],
            orderBy=None,
            limit=20,
            page=1,
            includeTotalCount=True,
            maxFilesPerTorrent=2,
        )
        payload = json.loads(raw_out)

        assert payload["totalCount"] == 3
        assert payload["returnedCount"] == 1
        item = payload["items"][0]
        assert item["id"] == "1"
        assert item["torrent"]["filesTruncated"] is True
        assert item["torrent"]["filesTotalCount"] == 3
        assert len(item["torrent"]["files"]) == 2

        _, called_vars = mock_exec.call_args[0]
        facets = called_vars["input"]["facets"]
        assert set(facets["videoSource"]["filter"]) == {"WEBDL", "WEBRip"}
        assert facets["releaseYear"]["filter"] == [2025]
        assert facets["torrentTag"] == {"filter": ["uhd"]}
