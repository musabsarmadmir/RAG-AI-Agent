import sys
import traceback
from pathlib import Path

# Ensure project root on sys.path so `app` imports work when running the script directly
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.config import PROVIDERS_DIR
from app.pipeline import build_index_for_provider

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--provider', type=str, default='Fatima', help='Provider name to build')
    args = ap.parse_args()
    try:
        print(f'Running build_index_for_provider for {args.provider}...')
        build_index_for_provider(args.provider, PROVIDERS_DIR)
        print('Build completed successfully')
    except Exception:
        print('Exception during build:')
        traceback.print_exc()

if __name__ == '__main__':
    main()
