from typing import List
import os
import logging

logger = logging.getLogger(__name__)

DEFAULT_SBERT = "all-MiniLM-L6-v2"


def get_default_embedding_model() -> str:
    """Return a string key for the preferred embedding model on this machine.

    Format: '<provider>:<model-name>' e.g. 'openai:text-embedding-3-small' or
    'sbert:all-MiniLM-L6-v2'. This is used to record what was used at index time.
    """
    if os.environ.get("OPENAI_API_KEY"):
        return "openai:text-embedding-3-small"
    return f"sbert:{DEFAULT_SBERT}"


class EmbeddingProvider:
    """Model-aware embedding utility.

    Usage:
      - call `embed_texts_with_model(model_key, texts)` to request embeddings
        from a specific provider/model.
      - call `get_default_embedding_model()` to decide what to use when building
        an index.
    """

    def __init__(self):
        self.sbert_models = {}

    def _ensure_sbert(self, model_name: str):
        from sentence_transformers import SentenceTransformer

        if model_name not in self.sbert_models:
            logger.info("Loading SBERT model %s", model_name)
            self.sbert_models[model_name] = SentenceTransformer(model_name)
        return self.sbert_models[model_name]

    def embed_texts_with_model(self, model_key: str, texts: List[str]) -> List[List[float]]:
        """Embed texts using the named model key.

        model_key examples:
          - 'openai:text-embedding-3-small'
          - 'sbert:all-MiniLM-L6-v2'
        """
        if model_key.startswith("openai:"):
            model_name = model_key.split(":", 1)[1]
            # require API key otherwise fail-fast
            if not os.environ.get("OPENAI_API_KEY"):
                raise RuntimeError("OPENAI_API_KEY not set for openai embedding model")
            try:
                # try new OpenAI client
                from openai import OpenAI as NewOpenAIClient

                client = NewOpenAIClient()
                resp = client.embeddings.create(model=model_name, input=texts)
                return [e.embedding for e in resp.data]
            except Exception:
                try:
                    import openai as old_openai

                    resp = old_openai.Embedding.create(model=model_name, input=texts)
                    return [e["embedding"] for e in resp["data"]]
                except Exception as e:
                    logger.exception("OpenAI embedding call failed: %s", e)
                    raise

        if model_key.startswith("sbert:"):
            model_name = model_key.split(":", 1)[1]
            model = self._ensure_sbert(model_name)
            embs = model.encode(texts, show_progress_bar=False)
            # sentence-transformers may return numpy array
            if hasattr(embs, 'tolist'):
                embs = embs.tolist()
            return [list(map(float, e)) for e in embs]

        raise ValueError(f"Unknown embedding model key: {model_key}")

    def embed_text_with_model(self, model_key: str, text: str) -> List[float]:
        return self.embed_texts_with_model(model_key, [text])[0]


default_embedding_provider = EmbeddingProvider()
