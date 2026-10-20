import pytest
from ragflow_claude_mcp import server
from ragflow_claude_mcp.common.validation import validate_dataset_id, redact_sensitive_data
from ragflow_claude_mcp.common.exceptions import ValidationError

def test_load_config_missing_file(tmp_path, monkeypatch):
    """Test load_config returns empty dict if file is missing."""
    non_existent = str(tmp_path / "non_existent_config.json")
    monkeypatch.setenv("RAGFLOW_CONFIG_PATH", non_existent)
    config = server.load_config()
    assert config == {}

def test_validate_dataset_id_valid():
    """Test validate_dataset_id with valid ID."""
    assert validate_dataset_id("dataset-12345") == "dataset-12345"

def test_validate_dataset_id_invalid():
    """Test validate_dataset_id raises ValidationError on invalid ID."""
    with pytest.raises(ValidationError):
        validate_dataset_id("")

def test_redact_sensitive_data():
    """Test redact_sensitive_data masks API keys in dictionaries and string bearer tokens."""
    data = {"api_key": "ragflow-1234567890abcdef", "name": "test"}
    redacted = redact_sensitive_data(data)
    assert redacted["api_key"] == "[REDACTED]"
    assert redacted["name"] == "test"

    token_str = redact_sensitive_data("Bearer ragflow-1234567890abcdef")
    assert token_str == "[REDACTED]"
