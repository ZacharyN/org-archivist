#!/usr/bin/env python3
"""
Qdrant Collection Initialization Script

This script initializes the Qdrant vector database collection for storing
document embeddings. It creates the collection with appropriate settings
based on the chosen embedding model.

This script should be run after the Qdrant container is running and healthy.
It can be run manually or as part of the backend initialization.
"""

import os
import sys
from typing import Dict

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct

# =============================================================================
# Configuration
# =============================================================================

# Embedding model dimensions mapping
EMBEDDING_DIMENSIONS: Dict[str, int] = {
    # OpenAI models
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    # Voyage AI models
    "voyage-large-2": 1536,
    "voyage-code-2": 1536,
    # Local models (BAAI)
    "bge-large-en-v1.5": 1024,
    "bge-small-en-v1.5": 384,
    "bge-base-en-v1.5": 768,
}

# Distance metrics
DISTANCE_METRIC = Distance.COSINE  # Cosine similarity (most common for text embeddings)

# =============================================================================
# Helper Functions
# =============================================================================

def get_qdrant_client() -> QdrantClient:
    """
    Create and return a Qdrant client connection.
    Reads connection details from environment variables.
    """
    host = os.getenv("QDRANT_HOST", "localhost")
    port = int(os.getenv("QDRANT_PORT", "6333"))
    api_key = os.getenv("QDRANT_API_KEY")  # Optional

    print(f"Connecting to Qdrant at {host}:{port}")

    if api_key:
        client = QdrantClient(host=host, port=port, api_key=api_key)
    else:
        client = QdrantClient(host=host, port=port)

    return client


def get_vector_dimensions() -> int:
    """
    Get the vector dimensions based on the configured embedding model.
    Falls back to environment variable or default if model not recognized.
    """
    embedding_model = os.getenv("EMBEDDING_MODEL", "bge-large-en-v1.5")

    # Check if dimensions are explicitly set in env
    env_dimensions = os.getenv("EMBEDDING_DIMENSIONS")
    if env_dimensions:
        return int(env_dimensions)

    # Look up dimensions based on model name
    dimensions = EMBEDDING_DIMENSIONS.get(embedding_model)

    if dimensions is None:
        print(f"Warning: Unknown embedding model '{embedding_model}'")
        print("Falling back to default dimensions: 1024")
        dimensions = 1024

    return dimensions


def collection_exists(client: QdrantClient, collection_name: str) -> bool:
    """Check if a collection already exists."""
    try:
        client.get_collection(collection_name)
        return True
    except Exception:
        return False


def create_collection(
    client: QdrantClient,
    collection_name: str,
    vector_size: int,
    distance: Distance = Distance.COSINE
) -> None:
    """
    Create a new Qdrant collection for storing document embeddings.

    Args:
        client: Qdrant client instance
        collection_name: Name of the collection to create
        vector_size: Dimension of the embedding vectors
        distance: Distance metric to use (default: Cosine)
    """
    print(f"Creating collection '{collection_name}'...")
    print(f"  Vector size: {vector_size}")
    print(f"  Distance metric: {distance}")

    client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=vector_size,
            distance=distance
        )
    )

    print(f"✓ Collection '{collection_name}' created successfully")


def get_collection_info(client: QdrantClient, collection_name: str) -> None:
    """Print information about an existing collection."""
    info = client.get_collection(collection_name)
    print(f"\nCollection '{collection_name}' info:")
    print(f"  Vector size: {info.config.params.vectors.size}")
    print(f"  Distance: {info.config.params.vectors.distance}")
    print(f"  Points count: {info.points_count}")
    print(f"  Indexed vectors: {info.indexed_vectors_count}")


# =============================================================================
# Main Script
# =============================================================================

def main():
    """Main initialization function."""
    print("=" * 70)
    print("Qdrant Collection Initialization")
    print("=" * 70)

    # Get configuration
    collection_name = os.getenv("QDRANT_COLLECTION_NAME", "foundation_docs")
    vector_dimensions = get_vector_dimensions()

    print(f"\nConfiguration:")
    print(f"  Collection name: {collection_name}")
    print(f"  Vector dimensions: {vector_dimensions}")
    print(f"  Embedding model: {os.getenv('EMBEDDING_MODEL', 'bge-large-en-v1.5')}")
    print()

    try:
        # Connect to Qdrant
        client = get_qdrant_client()

        # Check if collection already exists
        if collection_exists(client, collection_name):
            print(f"Collection '{collection_name}' already exists.")

            # Get and display collection info
            get_collection_info(client, collection_name)

            # Ask user if they want to recreate
            recreate = input("\nRecreate collection? This will delete all data! (y/N): ")

            if recreate.lower() == 'y':
                print(f"Deleting existing collection '{collection_name}'...")
                client.delete_collection(collection_name)
                print("✓ Collection deleted")

                # Create new collection
                create_collection(client, collection_name, vector_dimensions)
            else:
                print("Keeping existing collection.")
        else:
            # Create new collection
            create_collection(client, collection_name, vector_dimensions)

        # Display final collection info
        get_collection_info(client, collection_name)

        print("\n" + "=" * 70)
        print("Initialization completed successfully!")
        print("=" * 70)

        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        print("\nMake sure Qdrant is running and accessible.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
