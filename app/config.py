from pathlib import Path
import os

BASE_DIR = Path(__file__).resolve().parent.parent
RAG_DATA = BASE_DIR / "rag-data"
PROVIDERS_DIR = RAG_DATA / "providers"

# Create directories if missing
PROVIDERS_DIR.mkdir(parents=True, exist_ok=True)

# Load local.env if present so OPENAI_API_KEY and other vars are available
try:
	from dotenv import load_dotenv
	dotenv_path = BASE_DIR / 'local.env'
	if dotenv_path.exists():
		load_dotenv(dotenv_path)
except Exception:
	# python-dotenv is optional; ignore if not installed
	pass

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')

# API keys for securing public endpoints
# Support either a single `API_KEY` or a comma-separated `API_KEYS`
API_KEYS = []
if os.environ.get('API_KEYS'):
	API_KEYS = [k.strip() for k in os.environ.get('API_KEYS', '').split(',') if k.strip()]
elif os.environ.get('API_KEY'):
	API_KEYS = [os.environ.get('API_KEY')]

# CORS origins: comma-separated list, default allow-all for local/dev
_cors_raw = os.environ.get('CORS_ORIGINS')
if _cors_raw:
	CORS_ORIGINS = [o.strip() for o in _cors_raw.split(',') if o.strip()]
else:
	CORS_ORIGINS = ["*"]

# Optional overrides
# EMBEDDING_MODEL: explicit embedding model key, e.g. 'openai:text-embedding-3-small'
EMBEDDING_MODEL = os.environ.get('EMBEDDING_MODEL')
# LLM model to use for chat/completions, default is 'gpt-4o-mini' but can be overridden
LLM_MODEL = os.environ.get('LLM_MODEL', 'gpt-4o-mini')
# Firestore toggle: set to '1' to enable Firestore-backed provider index storage
FIRESTORE_ENABLED = os.environ.get('FIRESTORE_ENABLED') in ('1', 'true', 'True')
