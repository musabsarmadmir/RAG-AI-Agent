"""
Create test provider data and register a client mapping for quick local testing.

Usage (PowerShell):
    python .\scripts\create_test_provider.py myprovider 100

This will:
 - create directories under `rag-data/providers/myprovider`
 - write a sample `metadata.xlsx` and a `myprovider_sample.txt` doc
 - map client id `100` to `myprovider` in the application DB
"""
import sys
from pathlib import Path
from app.utils import ensure_provider_dirs
from app.app_db import set_client_provider
import pandas as pd


def create(provider: str, client_id: int):
    base = Path(__file__).resolve().parents[1] / 'rag-data' / 'providers'
    dirs = ensure_provider_dirs(base, provider)
    # metadata
    df = pd.DataFrame([
        {
            'name': f'{provider} Test Provider',
            'email': f'contact@{provider}.example',
            'phone': '555-0100',
            'services_summary': 'Test services: alpha, beta',
            'charges': 'Variable'
        }
    ])
    df.to_excel(dirs['excel'] / 'metadata.xlsx', index=False)
    # sample doc
    txt = (
        f"Provider {provider} sample document.\nThis document is used to test the pipeline.\n"
        "Contains sample content about services, fees and contact details."
    )
    (dirs['docs'] / f'{provider}_sample.txt').write_text(txt, encoding='utf-8')

    # map client
    set_client_provider(int(client_id), provider)
    print(f'Created provider {provider} and mapped client {client_id} -> {provider}')


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print('Usage: python create_test_provider.py <provider> <client_id>')
        sys.exit(1)
    create(sys.argv[1], int(sys.argv[2]))
