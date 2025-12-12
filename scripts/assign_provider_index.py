#!/usr/bin/env python3
import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app import provider_index


def main():
    p = argparse.ArgumentParser()
    p.add_argument('provider', help='Provider name to assign')
    p.add_argument('index', type=int, help='Numeric index to assign')
    p.add_argument('--overwrite', action='store_true', help='Overwrite any existing assignment')
    args = p.parse_args()

    try:
        provider_index.set_provider_index(args.provider, args.index, overwrite=args.overwrite)
        print(f'Assigned index {args.index} -> provider {args.provider}')
    except Exception as e:
        print('Error:', e)


if __name__ == '__main__':
    main()
