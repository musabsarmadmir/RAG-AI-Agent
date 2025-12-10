"""Quick test for OpenAI embeddings using the repository's embedding provider.

Usage (with venv activated):
  python scripts/test_embeddings_openai.py

This script:
- loads local.env if present
- imports the provider and embedding model from the app
- requests an embedding for a short sample text and prints the vector length and a few values
"""
import os
import sys
from pathlib import Path
import traceback

# Try to load local.env if present
try:
    from dotenv import load_dotenv
    dotenv_path = Path('local.env')
    if dotenv_path.exists():
        load_dotenv(dotenv_path)
except Exception:
    pass

try:
    # Ensure repo root is importable
    ROOT = Path(__file__).resolve().parents[1]
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))

    from app.embeddings import default_embedding_provider, get_default_embedding_model
    from app.config import EMBEDDING_MODEL

    model_key = os.environ.get('EMBEDDING_MODEL') or get_default_embedding_model()
    print('Using embedding model key:', model_key)

    sample = 'This is a short test sentence to verify embeddings.'
    vec = default_embedding_provider.embed_text_with_model(model_key, sample)
    print('Received embedding vector length:', len(vec))
    # Print first 8 elements for sanity
    print('First 8 vector values:', [float(x) for x in vec[:8]])
    # Basic type checks
    assert all(isinstance(x, (float, int)) for x in vec), 'Embedding elements are not numeric'
    if len(vec) < 1:
        raise SystemExit('Empty embedding vector received')
    print('Embedding test passed')
    sys.exit(0)
except Exception:
    traceback.print_exc()
    sys.exit(2)
