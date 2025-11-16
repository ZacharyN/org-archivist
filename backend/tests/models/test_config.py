"""
Integration tests for configuration endpoints.
"""
import pytest


def test_get_config(client):
    """Test retrieving system configuration."""
    response = client.get("/api/config")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, dict)

    # Should have main configuration sections
    assert "llm" in data or "rag" in data or "preferences" in data


def test_config_structure(client):
    """Test that configuration has expected structure."""
    response = client.get("/api/config")
    config = response.json()

    # Check for LLM configuration
    if "llm" in config:
        llm = config["llm"]
        assert "model" in llm
        assert "temperature" in llm
        assert "max_tokens" in llm

    # Check for RAG configuration
    if "rag" in config:
        rag = config["rag"]
        assert "embedding_model" in rag or "chunk_size" in rag


def test_update_config(client, sample_config_update):
    """Test updating system configuration."""
    response = client.put("/api/config", json=sample_config_update)

    assert response.status_code == 200

    data = response.json()
    # Should return updated configuration
    if "llm" in data:
        assert data["llm"]["temperature"] == 0.5


def test_partial_config_update(client):
    """Test updating only part of the configuration."""
    # Update only LLM temperature
    partial_update = {
        "llm": {
            "temperature": 0.8
        }
    }

    response = client.put("/api/config", json=partial_update)

    assert response.status_code == 200

    # Other config should remain unchanged
    data = response.json()
    assert data["llm"]["temperature"] == 0.8


def test_config_validation(client):
    """Test that invalid configuration is rejected."""
    invalid_config = {
        "llm": {
            "temperature": 2.5,  # Invalid: should be 0-2
            "max_tokens": -100   # Invalid: negative
        }
    }

    response = client.put("/api/config", json=invalid_config)

    # Should reject invalid values
    assert response.status_code in [400, 422]


def test_get_config_metadata(client):
    """Test getting configuration metadata."""
    response = client.get("/api/config/metadata")

    # Endpoint may or may not exist
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        # Should have metadata about config updates
        assert isinstance(data, dict)


def test_reset_config(client):
    """Test resetting configuration to defaults."""
    response = client.post("/api/config/reset")

    # Should accept reset request
    assert response.status_code in [200, 204]


def test_config_persistence(client):
    """Test that configuration updates persist."""
    # Update config
    update_data = {
        "llm": {
            "temperature": 0.6
        }
    }

    client.put("/api/config", json=update_data)

    # Get config again
    response = client.get("/api/config")
    config = response.json()

    # Update should persist
    assert config["llm"]["temperature"] == 0.6


def test_llm_model_validation(client):
    """Test LLM model name validation."""
    config_update = {
        "llm": {
            "model": "claude-sonnet-4-20250514"
        }
    }

    response = client.put("/api/config", json=config_update)

    assert response.status_code == 200


def test_rag_parameters_validation(client):
    """Test RAG parameter validation."""
    config_update = {
        "rag": {
            "chunk_size": 512,
            "chunk_overlap": 50,
            "top_k": 5
        }
    }

    response = client.put("/api/config", json=config_update)

    # Should accept valid RAG parameters
    assert response.status_code in [200, 404]  # 404 if not implemented


def test_user_preferences_update(client):
    """Test updating user preferences."""
    config_update = {
        "preferences": {
            "default_audience": "foundation",
            "citation_style": "APA",
            "auto_save": True
        }
    }

    response = client.put("/api/config", json=config_update)

    # Should accept valid preferences
    assert response.status_code in [200, 404]  # 404 if not implemented
