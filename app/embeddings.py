from typing import List
import os
import logging

logger = logging.getLogger(__name__)


def get_default_embedding_model() -> str:
    """Return a string key for the preferred embedding model on this machine.

    Format: '<provider>:<model-name>' e.g. 'openai:text-embedding-3-small'. This is used to record what was used at index time.
    """
    # Allow explicit override via environment (recommended): EMBEDDING_MODEL
    if os.environ.get('EMBEDDING_MODEL'):
        val = os.environ.get('EMBEDDING_MODEL')
        if not val.startswith('openai:'):
            raise RuntimeError("EMBEDDING_MODEL must be an OpenAI model key (start with 'openai:') when embeddings are configured as OpenAI-only")
        return val
    # Enforce OpenAI-only embeddings: require OPENAI_API_KEY
    if not os.environ.get('OPENAI_API_KEY'):
        raise RuntimeError('OPENAI_API_KEY not set: this deployment requires OpenAI embeddings')
    # default OpenAI embeddings model
    return "openai:text-embedding-3-small"


class EmbeddingProvider:

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
        # Only OpenAI model keys are supported in this deployment
        raise ValueError(f"Unsupported embedding model key: {model_key}; this deployment only supports OpenAI embedding models (keys starting with 'openai:')")

    def embed_text_with_model(self, model_key: str, text: str) -> List[float]:
        return self.embed_texts_with_model(model_key, [text])[0]


default_embedding_provider = EmbeddingProvider()
