"""Verify sample-files/Aimdtalk.xlsx contains the expected parsed sheet and data."""
from pathlib import Path
import sys
import pandas as pd

TARGET = Path('sample-files') / 'Aimdtalk.xlsx'
SHEET = 'Fatima_parsed'

def main():
    if not TARGET.exists():
        print('Target file not found:', TARGET)
        return 2
    xl = pd.ExcelFile(str(TARGET))
    if SHEET not in xl.sheet_names:
        print('Sheet not found:', SHEET)
        print('Available sheets:', xl.sheet_names)
        return 3
    df = pd.read_excel(xl, sheet_name=SHEET)
    print('Columns:', df.columns.tolist())
    if df.empty:
        print('Sheet is empty')
        return 4
    if 'services_summary' not in df.columns:
        print('services_summary column missing')
        return 5
    val = df.loc[0, 'services_summary']
    if not str(val).strip():
        print('services_summary is empty')
        return 6
    print('Verification OK: sheet', SHEET, 'contains data')
    return 0

if __name__ == '__main__':
    rc = main()
    sys.exit(rc)
