#!/usr/bin/env python
"""Analyze FactSet global identifiers file."""

import csv

# Analyze FactSet identifiers
with open(r'G:\FACTSET\screening\ff_global_identifiers.csv', 'r', encoding='latin-1') as f:
    reader = csv.DictReader(f)
    
    rows = 0
    has_isin = 0
    has_cusip = 0
    has_sedol = 0
    has_perm_sec = 0
    nvidia_rows = []
    
    for row in reader:
        rows += 1
        isin = row.get('ISIN', '').strip()
        cusip = row.get('CUSIP', '').strip()
        sedol = row.get('SEDOL', '').strip()
        perm_sec = row.get('Perm. Sec. ID', '').strip()
        name = row.get('Company Name', '').strip()
        
        if isin and isin != '@NA':
            has_isin += 1
        if cusip and cusip != '@NA':
            has_cusip += 1
        if sedol and sedol != '@NA':
            has_sedol += 1
        if perm_sec and perm_sec != '@NA':
            has_perm_sec += 1
            
        if 'NVIDIA' in name.upper():
            nvidia_rows.append(row)

print(f'Total rows: {rows:,}')
print(f'Has ISIN: {has_isin:,}')
print(f'Has CUSIP: {has_cusip:,}')
print(f'Has SEDOL: {has_sedol:,}')
print(f'Has Perm Sec ID: {has_perm_sec:,}')
print()
print(f'NVIDIA rows: {len(nvidia_rows)}')
for r in nvidia_rows[:5]:
    print(f"  Symbol: {r.get('Company Symbol', '').strip()}")
    print(f"  Name: {r.get('Company Name', '').strip()}")
    print(f"  ISIN: {r.get('ISIN', '').strip()}")
    print(f"  CUSIP: {r.get('CUSIP', '').strip()}")
    print(f"  SEDOL: {r.get('SEDOL', '').strip()}")
    print(f"  Perm Sec ID: {r.get('Perm. Sec. ID', '').strip()}")
    print(f"  Primary Equity: {r.get('Primary Equity Listing', '').strip()}")
    print('---')
