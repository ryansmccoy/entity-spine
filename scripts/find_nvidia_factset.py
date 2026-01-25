#!/usr/bin/env python
"""Find NVIDIA and count identifiers in FactSet global identifiers."""

import csv

with open(r'G:\FACTSET\screening\ff_global_identifiers.csv', 'r', encoding='latin-1') as f:
    reader = csv.DictReader(f)
    # Strip column names
    reader.fieldnames = [c.strip() for c in reader.fieldnames]
    
    rows = 0
    has_isin = 0
    has_cusip = 0
    has_sedol = 0
    nvidia_rows = []
    
    for row in reader:
        rows += 1
        isin = row.get('ISIN', '').strip()
        cusip = row.get('CUSIP', '').strip()
        sedol = row.get('SEDOL', '').strip()
        name = row.get('Company Name', '').strip()
        
        if isin and len(isin) >= 10 and not isin.startswith('@'):
            has_isin += 1
        if cusip and len(cusip) >= 8 and not cusip.startswith('@'):
            has_cusip += 1
        if sedol and len(sedol) >= 6 and not sedol.startswith('@'):
            has_sedol += 1
            
        if 'NVIDIA' in name.upper():
            nvidia_rows.append({k: v.strip() for k, v in row.items()})

print(f'Total rows: {rows:,}')
print(f'Has ISIN: {has_isin:,}')
print(f'Has CUSIP: {has_cusip:,}')  
print(f'Has SEDOL: {has_sedol:,}')
print()
print(f'NVIDIA rows: {len(nvidia_rows)}')
for r in nvidia_rows[:10]:
    name = r.get('Company Name', '').strip()
    symbol = r.get('Company Symbol', '').strip()
    perm_sec = r.get('Perm. Sec. ID', '').strip()
    primary_eq = r.get('Primary Equity Listing', '').strip()
    isin = r.get('ISIN', '').strip()
    cusip = r.get('CUSIP', '').strip()
    sedol = r.get('SEDOL', '').strip()
    ticker = r.get('FDS Ticker Symbol', '').strip()
    
    print(f'  Name: {name}')
    print(f'  Symbol: {symbol}')
    print(f'  Perm Sec ID: {perm_sec}')
    print(f'  Primary Equity: {primary_eq}')
    print(f'  ISIN: {isin}')
    print(f'  CUSIP: {cusip}')
    print(f'  SEDOL: {sedol}')
    print(f'  Ticker: {ticker}')
    print('---')
