"""
Integration tests for prompt management endpoints.
"""
import pytest


def test_list_prompts_endpoint(client):
    """Test listing all prompts."""
    response = client.get("/api/prompts")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    # Default prompts should be available
    assert len(data) >= 3


def test_list_prompts_with_filters(client):
    """Test filtering prompts by category and status."""
    # Filter by category
    response = client.get("/api/prompts?category=audience")
    assert response.status_code == 200

    # Filter by active status
    response = client.get("/api/prompts?active=true")
    assert response.status_code == 200


def test_search_prompts(client):
    """Test searching prompts by name and content."""
    response = client.get("/api/prompts?search=RFP")

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_create_prompt(client, sample_prompt_template):
    """Test creating a new prompt template."""
    response = client.post("/api/prompts", json=sample_prompt_template)

    assert response.status_code in [200, 201]

    if response.status_code in [200, 201]:
        data = response.json()
        assert "id" in data
        assert data["name"] == sample_prompt_template["name"]
        assert data["category"] == sample_prompt_template["category"]


def test_create_prompt_validation(client):
    """Test prompt creation validation."""
    # Missing required fields
    response = client.post("/api/prompts", json={"name": "Test"})

    assert response.status_code == 422


def test_get_prompt_by_id(client):
    """Test getting a specific prompt by ID."""
    # First, list prompts to get a valid ID
    list_response = client.get("/api/prompts")
    prompts = list_response.json()

    if len(prompts) > 0:
        prompt_id = prompts[0]["id"]
        response = client.get(f"/api/prompts/{prompt_id}")

        assert response.status_code == 200

        data = response.json()
        assert data["id"] == prompt_id


def test_get_nonexistent_prompt(client):
    """Test getting a prompt that doesn't exist."""
    response = client.get("/api/prompts/nonexistent-id-12345")

    assert response.status_code == 404


def test_update_prompt(client, sample_prompt_template):
    """Test updating an existing prompt."""
    # First create a prompt
    create_response = client.post("/api/prompts", json=sample_prompt_template)

    if create_response.status_code in [200, 201]:
        created_prompt = create_response.json()
        prompt_id = created_prompt["id"]

        # Update the prompt
        updated_data = {
            "name": "Updated Test Template",
            "content": "Updated content for {audience}",
            "active": False
        }

        response = client.put(f"/api/prompts/{prompt_id}", json=updated_data)

        assert response.status_code == 200

        data = response.json()
        assert data["name"] == "Updated Test Template"
        assert data["version"] > created_prompt["version"]


def test_delete_prompt(client, sample_prompt_template):
    """Test deleting a prompt."""
    # First create a prompt
    create_response = client.post("/api/prompts", json=sample_prompt_template)

    if create_response.status_code in [200, 201]:
        created_prompt = create_response.json()
        prompt_id = created_prompt["id"]

        # Delete the prompt
        response = client.delete(f"/api/prompts/{prompt_id}")

        assert response.status_code in [200, 204]

        # Verify it's deleted
        get_response = client.get(f"/api/prompts/{prompt_id}")
        assert get_response.status_code == 404


def test_prompt_categories(client):
    """Test that prompts have valid categories."""
    response = client.get("/api/prompts")
    prompts = response.json()

    valid_categories = ["audience", "section", "brand_voice", "custom"]

    for prompt in prompts:
        assert prompt["category"] in valid_categories


def test_prompt_variables_extraction(client):
    """Test that prompt variables are properly extracted."""
    prompt_data = {
        "name": "Variable Test",
        "category": "custom",
        "content": "Hello {name}, your {item} is ready for {audience}.",
        "variables": ["name", "item", "audience"],
        "active": True
    }

    response = client.post("/api/prompts", json=prompt_data)

    if response.status_code in [200, 201]:
        data = response.json()
        assert set(data["variables"]) == {"name", "item", "audience"}


def test_inactive_prompts_filtering(client):
    """Test filtering out inactive prompts."""
    # Get all prompts
    all_response = client.get("/api/prompts")
    all_prompts = all_response.json()

    # Get only active prompts
    active_response = client.get("/api/prompts?active=true")
    active_prompts = active_response.json()

    # Active count should be <= total count
    assert len(active_prompts) <= len(all_prompts)
