from sqlitedict import SqliteDict
from pathlib import Path
from .config import RAG_DATA

APP_DB_PATH = RAG_DATA / 'app_db.sqlite'


def set_client_provider(client_id: int, provider: str):
    """Store provider name (string) for a client id."""
    with SqliteDict(str(APP_DB_PATH), autocommit=True) as d:
        d[str(client_id)] = provider


def set_client_provider_index(client_id: int, provider_index: int):
    """Store provider as numeric index (stored as string) for a client id."""
    with SqliteDict(str(APP_DB_PATH), autocommit=True) as d:
        d[str(client_id)] = str(provider_index)


def get_client_provider(client_id: int):
    """Return provider name for the client id.

    If the stored value is a numeric index, resolve it via provider_index mapping.
    """
    with SqliteDict(str(APP_DB_PATH)) as d:
        val = d.get(str(client_id))
    if val is None:
        return None
    # if stored numeric -> resolve
    try:
        # allow int values or numeric strings
        sval = str(val)
        if sval.isdigit():
            from . import provider_index as _pi

            return _pi.get_provider_by_index(int(sval))
    except Exception:
        pass
    return val


def get_client_provider_index(client_id: int):
    """Return numeric provider index if stored for client, else None."""
    with SqliteDict(str(APP_DB_PATH)) as d:
        val = d.get(str(client_id))
    if val is None:
        return None
    sval = str(val)
    if sval.isdigit():
        try:
            return int(sval)
        except Exception:
            return None
    # if stored provider name, try to get its index
    try:
        from . import provider_index as _pi

        return _pi.get_index_by_provider(sval)
    except Exception:
        return None
