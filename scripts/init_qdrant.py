#!/usr/bin/env python3
"""
Qdrant Initializer
Vector database collection'larını oluşturur
"""
import os
import sys

try:
    from qdrant_client import QdrantClient
    from qdrant_client.http import models as qdrant_models
except ImportError:
    print("Error: qdrant-client is not installed.")
    print("Install with: pip install qdrant-client")
    sys.exit(1)


# Configuration
QDRANT_HOST = os.getenv("QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("QDRANT_PORT", "6333"))

# Embedding dimension (qwen3-embedding-8b)
EMBEDDING_DIM = 4096

# Collections to create
COLLECTIONS = {
    "companies": {
        "description": "Firma embedding'leri - geçmiş raporlar ve kararlar",
        "size": EMBEDDING_DIM,
        "distance": qdrant_models.Distance.COSINE
    },
    "reports": {
        "description": "Rapor embedding'leri - benzer rapor araması",
        "size": EMBEDDING_DIM,
        "distance": qdrant_models.Distance.COSINE
    },
    "news": {
        "description": "Haber embedding'leri - benzer haber araması",
        "size": EMBEDDING_DIM,
        "distance": qdrant_models.Distance.COSINE
    },
    "council_decisions": {
        "description": "Komite kararları - tutarlılık için geçmiş kararlar",
        "size": EMBEDDING_DIM,
        "distance": qdrant_models.Distance.COSINE
    }
}


def get_client():
    """Qdrant client oluştur"""
    return QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)


def init_collections():
    """Collection'ları oluştur"""
    client = get_client()

    print(f"Connecting to Qdrant at {QDRANT_HOST}:{QDRANT_PORT}...")
    print()

    # Check connection
    try:
        client.get_collections()
        print("✓ Connected to Qdrant")
    except Exception as e:
        print(f"✗ Failed to connect to Qdrant: {e}")
        return False

    print()
    print("Creating collections...")
    print()

    for name, config in COLLECTIONS.items():
        try:
            # Check if collection exists
            existing = client.collection_exists(name)

            if existing:
                print(f"  {name}: Already exists (skipped)")
                continue

            # Create collection
            client.create_collection(
                collection_name=name,
                vectors_config=qdrant_models.VectorParams(
                    size=config["size"],
                    distance=config["distance"]
                )
            )

            print(f"  {name}: Created ✓")
            print(f"    - Description: {config['description']}")
            print(f"    - Dimension: {config['size']}")
            print(f"    - Distance: {config['distance']}")

        except Exception as e:
            print(f"  {name}: Error - {e}")

    print()
    return True


def list_collections():
    """Mevcut collection'ları listele"""
    client = get_client()

    print("Existing collections:")
    print()

    collections = client.get_collections()

    for collection in collections.collections:
        info = client.get_collection(collection.name)
        print(f"  - {collection.name}")
        print(f"    Points: {info.points_count}")
        print(f"    Vectors: {info.vectors_count}")


def delete_collections():
    """Tüm collection'ları sil (dikkatli kullan!)"""
    client = get_client()

    print("Deleting all collections...")

    for name in COLLECTIONS.keys():
        try:
            if client.collection_exists(name):
                client.delete_collection(name)
                print(f"  {name}: Deleted ✓")
            else:
                print(f"  {name}: Does not exist (skipped)")
        except Exception as e:
            print(f"  {name}: Error - {e}")


def main():
    """Main function"""
    import argparse

    parser = argparse.ArgumentParser(description="Qdrant Collection Manager")
    parser.add_argument(
        "action",
        choices=["init", "list", "delete"],
        default="init",
        nargs="?",
        help="Action to perform (default: init)"
    )

    args = parser.parse_args()

    print("=" * 50)
    print("KKB Firma İstihbarat - Qdrant Manager")
    print("=" * 50)
    print()

    if args.action == "init":
        init_collections()
    elif args.action == "list":
        list_collections()
    elif args.action == "delete":
        confirm = input("Are you sure you want to delete all collections? (yes/no): ")
        if confirm.lower() == "yes":
            delete_collections()
        else:
            print("Cancelled.")

    print()
    print("Done!")


if __name__ == "__main__":
    main()
