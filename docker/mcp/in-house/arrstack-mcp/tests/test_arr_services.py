import pytest
import server

def test_radarr_list_movies(mocker):
    """Test radarr_list_movies tool."""
    mock_movies = [
        {"id": 1, "title": "Inception", "year": 2010, "hasFile": True, "monitored": True, "qualityProfileId": 1}
    ]
    mock_profiles = [{"id": 1, "name": "HD-1080p"}]

    mocker.patch.object(server, "_radarr", side_effect=[mock_movies, mock_profiles])

    result = server.radarr_list_movies()
    assert "Inception (2010)" in result

def test_lidarr_list_artists(mocker):
    """Test lidarr_list_artists tool."""
    mock_artists = [
        {"id": 1, "artistName": "Wolfgang Amadeus Mozart", "monitored": True}
    ]
    mocker.patch.object(server, "_lidarr", return_value=mock_artists)

    result = server.lidarr_list_artists()
    assert "Wolfgang Amadeus Mozart" in result
