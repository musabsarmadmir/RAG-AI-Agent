from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
# Adjusted to new location under sample-files
src_pdf = ROOT / 'sample-files' / 'Fatima_AI_Services-1.pdf'
provider = 'Fatima'
dest_docs = ROOT / 'rag-data' / 'providers' / provider / 'docs'
dest_excel = ROOT / 'rag-data' / 'providers' / provider / 'excel'

dest_docs.mkdir(parents=True, exist_ok=True)
dest_excel.mkdir(parents=True, exist_ok=True)

if not src_pdf.exists():
    print('Source PDF not found:', src_pdf)
    sys.exit(1)

dest_pdf = dest_docs / src_pdf.name
shutil.copy2(src_pdf, dest_pdf)

text = ''
try:
    import pdfplumber
    with pdfplumber.open(dest_pdf) as pdf:
        pages = [p.extract_text() or '' for p in pdf.pages]
        text = '\n'.join(pages)
except Exception:
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(dest_pdf))
        pages = [pg.extract_text() or '' for pg in reader.pages]
        text = '\n'.join(pages)
    except Exception as e:
        print('PDF parsing failed:', e)
        sys.exit(1)

text = re.sub(r'\s+', ' ', text).strip()

import pandas as pd
df = pd.DataFrame([{'Service provider': provider, 'document': text}])
out_path = dest_excel / 'metadata.xlsx'
df.to_excel(out_path, index=False)
print('Wrote metadata to', out_path)
