import os
from app import provider_index

def main():
    print('PWD:', os.getcwd())
    print('Python:', os.sys.version.splitlines()[0])
    print('FIRESTORE_ENABLED:', bool(os.getenv('FIRESTORE_ENABLED')))
    try:
        m = provider_index.load_index_map()
    except Exception as e:
        print('load_index_map() raised:', repr(e))
        m = None
    print('load_index_map() ->', m)
    print('rag-agent-firestore.json exists ->', os.path.exists('rag-agent-firestore.json'))

if __name__ == '__main__':
    main()
