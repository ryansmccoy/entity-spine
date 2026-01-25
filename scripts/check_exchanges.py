#!/usr/bin/env python
"""Check exchange codes in Thomson vs Bloomberg."""

import gzip
import re
from collections import Counter

# Get exchange codes from Thomson quotes
exch_pattern = re.compile(r'hasExchangeCode\s+"([^"]+)"')
exchanges = Counter()

print("Scanning Thomson quote file for exchange codes...")
with gzip.open(r'G:\THOMSON\OpenPermID-bulk-quote-20200830_085319.ttl.gz', 'rt', encoding='utf-8') as f:
    for i, line in enumerate(f):
        m = exch_pattern.search(line)
        if m:
            exchanges[m.group(1)] += 1
        if i > 5000000:
            break

print('Top 30 Thomson exchange codes:')
for code, count in exchanges.most_common(30):
    print(f'  {code}: {count:,}')
