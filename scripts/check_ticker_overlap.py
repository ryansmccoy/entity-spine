#!/usr/bin/env python
"""Check ticker/exchange overlap between Bloomberg pub/priv and Thomson quotes."""

import csv
import gzip
import re
from pathlib import Path

# Get tickers from Bloomberg pub/priv  
bb_tickers = {}
bb_file = Path(r'b:\github\py-sec-edgar\data\bb_pubpriv_20150101.csv')

print(f"Loading Bloomberg pub/priv from {bb_file}...")
with open(bb_file, 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    for row in reader:
        ticker_exch = row.get('Tkr & Exch', '').strip()
        figi = row.get('ID BB Global', '')
        name = row.get('Name', '')
        if ticker_exch and figi:
            # Parse 'NVDA    US' format
            parts = ticker_exch.split()
            if len(parts) >= 2:
                ticker = parts[0]
                exch = parts[-1]
                bb_tickers[(ticker.upper(), exch.upper())] = {
                    'figi': figi,
                    'name': name,
                    'ticker_exch': ticker_exch
                }

print(f"Bloomberg ticker/exchange pairs: {len(bb_tickers)}")
print(f"Sample: {list(bb_tickers.items())[:3]}")

# Now check Thomson quote file for matching tickers
print("\nScanning Thomson quote file...")
quote_file = Path(r'G:\THOMSON\OpenPermID-bulk-quote-20200830_085319.ttl.gz')
matches = []

ticker_pattern = re.compile(r'hasExchangeTicker\s+"([^"]+)"')
exch_pattern = re.compile(r'hasExchangeCode\s+"([^"]+)"')
permid_pattern = re.compile(r'<https://permid\.org/1-(\d+)>')

current_permid = None
current_ticker = None
current_exch = None
lines_checked = 0

with gzip.open(quote_file, 'rt', encoding='utf-8') as f:
    for line in f:
        lines_checked += 1
        
        # New entity
        m = permid_pattern.search(line)
        if m:
            # Save previous if matched
            if current_ticker and current_exch:
                key = (current_ticker.upper(), current_exch.upper())
                if key in bb_tickers:
                    matches.append({
                        'thomson_permid': current_permid,
                        'ticker': current_ticker,
                        'exchange': current_exch,
                        'bb_figi': bb_tickers[key]['figi'],
                        'bb_name': bb_tickers[key]['name']
                    })
            current_permid = m.group(1)
            current_ticker = None
            current_exch = None
            
        m = ticker_pattern.search(line)
        if m:
            current_ticker = m.group(1)
            
        m = exch_pattern.search(line)
        if m:
            current_exch = m.group(1)
        
        if lines_checked % 1000000 == 0:
            print(f"  Checked {lines_checked:,} lines, found {len(matches)} matches so far")

# Don't forget last one
if current_ticker and current_exch:
    key = (current_ticker.upper(), current_exch.upper())
    if key in bb_tickers:
        matches.append({
            'thomson_permid': current_permid,
            'ticker': current_ticker,
            'exchange': current_exch,
            'bb_figi': bb_tickers[key]['figi'],
            'bb_name': bb_tickers[key]['name']
        })

print(f"\nTotal: {len(matches)} ticker/exchange matches")
print("\nSample matches:")
for m in matches[:20]:
    print(f"  Thomson permid:{m['thomson_permid']} ({m['ticker']}:{m['exchange']}) -> BB {m['bb_figi']} {m['bb_name']}")

# Check for NVIDIA specifically
nvda_matches = [m for m in matches if 'NVDA' in m['ticker'].upper() or 'NVIDIA' in m.get('bb_name', '').upper()]
print(f"\nNVIDIA matches: {len(nvda_matches)}")
for m in nvda_matches:
    print(f"  {m}")
