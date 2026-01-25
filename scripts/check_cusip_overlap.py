#!/usr/bin/env python
"""Check CUSIP overlap between FactSet and Bloomberg."""

import csv

# Get CUSIPs from FactSet
factset_cusips = {}
with open(r'G:\FACTSET\screening\ff_global_identifiers.csv', 'r', encoding='latin-1') as f:
    reader = csv.DictReader(f)
    reader.fieldnames = [c.strip() for c in reader.fieldnames]
    for row in reader:
        cusip = row.get('CUSIP', '').strip()
        name = row.get('Company Name', '').strip()
        perm_sec = row.get('Perm. Sec. ID', '').strip()
        if cusip and len(cusip) >= 8 and not cusip.startswith('@'):
            factset_cusips[cusip] = {'name': name, 'perm_sec_id': perm_sec}

print(f'FactSet CUSIPs: {len(factset_cusips):,}')

# Check Bloomberg pub/priv for matching CUSIPs  
bb_cusips = {}
with open(r'b:\github\py-sec-edgar\data\bb_pubpriv_20150101.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        isin = row.get('ISIN', '').strip()
        figi = row.get('ID BB Global', '')
        name = row.get('Name', '')
        # Extract CUSIP from ISIN (positions 3-11 for US ISINs)
        if isin and isin.startswith('US') and len(isin) == 12:
            cusip = isin[2:11]  # 9-char CUSIP
            bb_cusips[cusip] = {'figi': figi, 'name': name, 'isin': isin}

print(f'Bloomberg CUSIPs (from ISIN): {len(bb_cusips):,}')

# Find matches
matches = 0
sample_matches = []
for cusip, fs_data in factset_cusips.items():
    if cusip in bb_cusips:
        matches += 1
        if len(sample_matches) < 10:
            sample_matches.append({
                'cusip': cusip,
                'factset_name': fs_data['name'],
                'bb_name': bb_cusips[cusip]['name'],
                'bb_figi': bb_cusips[cusip]['figi']
            })

print(f'Matching CUSIPs: {matches:,}')
print()
for m in sample_matches:
    print(f"  CUSIP: {m['cusip']}")
    print(f"  FactSet: {m['factset_name']}")
    print(f"  Bloomberg: {m['bb_name']} (FIGI: {m['bb_figi']})")
    print('---')

# Check NVIDIA specifically
nvidia_cusip = '67066G104'
print(f"\nNVIDIA CUSIP {nvidia_cusip}:")
if nvidia_cusip in factset_cusips:
    print(f"  In FactSet: {factset_cusips[nvidia_cusip]}")
if nvidia_cusip in bb_cusips:
    print(f"  In Bloomberg: {bb_cusips[nvidia_cusip]}")
