"""Debug FIGI matching between bridge and database."""
import sqlite3
import csv

conn = sqlite3.connect('entityspine_data/linked_load.db')

# Check sample FIGIs from bridge
with open('entityspine_data/identifier_bridge.csv', 'r') as f:
    reader = csv.DictReader(f)
    sample_figis = []
    for i, row in enumerate(reader):
        if row.get('bloomberg_figi'):
            sample_figis.append((row['bloomberg_figi'], row['name']))
            if len(sample_figis) >= 5:
                break

print('Sample FIGIs from bridge:')
for figi, name in sample_figis:
    print(f'  {figi} - {name}')
    # Check in DB
    cursor = conn.execute("SELECT value FROM claims WHERE scheme = 'figi' AND value = ?", (figi,))
    result = cursor.fetchone()
    print(f'    In DB: {result}')

# Check sample FIGIs from DB
print('\nSample FIGIs from DB:')
cursor = conn.execute("SELECT value FROM claims WHERE scheme = 'figi' LIMIT 5")
for row in cursor:
    print(f'  {row[0]}')

# Check if the bridge has the right format
print('\nBridge FIGI format check:')
with open('entityspine_data/identifier_bridge.csv', 'r') as f:
    reader = csv.DictReader(f)
    count_with_figi = 0
    figi_lengths = {}
    for row in reader:
        figi = row.get('bloomberg_figi', '')
        if figi:
            count_with_figi += 1
            length = len(figi)
            figi_lengths[length] = figi_lengths.get(length, 0) + 1

print(f'  Rows with FIGI: {count_with_figi}')
print(f'  FIGI length distribution: {figi_lengths}')

# Check DB FIGI format
print('\nDB FIGI format check:')
cursor = conn.execute("SELECT LENGTH(value), COUNT(*) FROM claims WHERE scheme = 'figi' GROUP BY LENGTH(value)")
for row in cursor:
    print(f'  Length {row[0]}: {row[1]} rows')

conn.close()

# Reopen and check match rate
conn = sqlite3.connect('entityspine_data/linked_load.db')
found = 0
not_found = 0
with open('entityspine_data/identifier_bridge.csv', 'r') as f:
    reader = csv.DictReader(f)
    for row in reader:
        figi = row.get('bloomberg_figi', '')
        if figi:
            cursor = conn.execute("SELECT 1 FROM claims WHERE scheme = 'figi' AND value = ?", (figi,))
            if cursor.fetchone():
                found += 1
            else:
                not_found += 1

print(f'\nBridge FIGIs found in DB: {found:,}')
print(f'Bridge FIGIs NOT in DB: {not_found:,}')
print(f'Match rate: {found/(found+not_found)*100:.1f}%')
conn.close()
