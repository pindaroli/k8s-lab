import pytest
from server import mcp


@pytest.mark.asyncio
async def test_list_prompts():
    """Verifica che i 3 prompt MCP siano registrati e visibili in list_prompts."""
    prompts = await mcp.list_prompts()
    prompt_names = [p.name for p in prompts]

    assert "audit_downloads" in prompt_names
    assert "search_and_grab" in prompt_names
    assert "media_health_check" in prompt_names

    for prompt in prompts:
        assert prompt.description is not None
        assert len(prompt.description) > 0


@pytest.mark.asyncio
async def test_get_prompt_audit_downloads():
    """Verifica che prompts/get per audit_downloads generi il template corretto."""
    result = await mcp.get_prompt("audit_downloads", {"client": "qbt"})
    assert result is not None
    assert len(result.messages) == 1
    content = result.messages[0].content.text
    assert "qbt" in content
    assert "qbt_list_torrents" in content


@pytest.mark.asyncio
async def test_get_prompt_search_and_grab():
    """Verifica che prompts/get per search_and_grab includa titolo e istruzioni di grab."""
    result = await mcp.get_prompt("search_and_grab", {"title": "Dune", "media_type": "movie"})
    assert result is not None
    assert len(result.messages) == 1
    content = result.messages[0].content.text
    assert "Dune" in content
    assert "prowlarr_search" in content
    assert "prowlarr_grab" in content


@pytest.mark.asyncio
async def test_get_prompt_media_health_check():
    """Verifica che prompts/get per media_health_check contenga i controlli *arr."""
    result = await mcp.get_prompt("media_health_check")
    assert result is not None
    assert len(result.messages) == 1
    content = result.messages[0].content.text
    assert "prowlarr_health" in content
    assert "radarr_queue" in content
    assert "sonarr_queue" in content
