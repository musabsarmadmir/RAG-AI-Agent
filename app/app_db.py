from sqlitedict import SqliteDict
from pathlib import Path
from .config import RAG_DATA

APP_DB_PATH = RAG_DATA / 'app_db.sqlite'


def set_client_provider(client_id: int, provider: str):
    with SqliteDict(str(APP_DB_PATH), autocommit=True) as d:
        d[str(client_id)] = provider


def get_client_provider(client_id: int):
    with SqliteDict(str(APP_DB_PATH)) as d:
        return d.get(str(client_id))
