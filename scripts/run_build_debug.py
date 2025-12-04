import traceback
from app.config import PROVIDERS_DIR
from app.pipeline import build_index_for_provider

def main():
    try:
        print('Running build_index_for_provider for Fatima...')
        build_index_for_provider('Fatima', PROVIDERS_DIR)
        print('Build completed successfully')
    except Exception:
        print('Exception during build:')
        traceback.print_exc()

if __name__ == '__main__':
    main()
