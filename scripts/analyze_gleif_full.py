"""Analyze GLEIF Full LEI file for entity mapping."""
import csv

# Open the file
with open('entityspine_data/gleif/gleif_lei_full.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    row = next(reader)
    
    print("First row keys (first 20):")
    keys = list(row.keys())
    for i, key in enumerate(keys[:20]):
        print(f"  {i}: {key}")

# Check Registration Authority IDs
print("\n" + "=" * 60)
print("Analyzing Registration Authority IDs...")

auth_ids = {}
us_entities = 0
total = 0

with open('entityspine_data/gleif/gleif_lei_full.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        total += 1
        
        # Get keys
        keys = list(row.keys())
        
        # Find registration authority ID
        for key in keys:
            if 'RegistrationAuthorityID' in key and 'Other' not in key:
                auth_id = row[key].strip('"')
                if auth_id:
                    auth_ids[auth_id] = auth_ids.get(auth_id, 0) + 1
                break
        
        # Count US entities
        for key in keys:
            if 'LegalJurisdiction' in key or 'Country' in key:
                val = row[key].strip('"')
                if val == 'US' or val.startswith('US-'):
                    us_entities += 1
                    break
        
        if total >= 100000:
            break

print(f"\nScanned {total:,} rows")
print(f"US entities: {us_entities:,}")
print(f"\nTop 20 Registration Authority IDs:")
for auth_id, count in sorted(auth_ids.items(), key=lambda x: -x[1])[:20]:
    print(f"  {auth_id}: {count:,}")

# Look for SEC specifically
print("\n" + "=" * 60)
print("Looking for SEC-registered entities...")

sec_entities = []
with open('entityspine_data/gleif/gleif_lei_full.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for i, row in enumerate(reader):
        keys = list(row.keys())
        
        # Find registration authority ID
        for key in keys:
            if 'RegistrationAuthorityID' in key and 'Other' not in key:
                auth_id = row[key].strip('"')
                if 'SEC' in auth_id or 'RA000602' in auth_id:  # RA000602 is SEC
                    lei_key = [k for k in keys if k.strip('"') == 'LEI'][0]
                    name_key = [k for k in keys if 'LegalName' in k and 'xmllang' not in k][0]
                    entity_id_key = [k for k in keys if 'RegistrationAuthorityEntityID' in k and 'Other' not in k][0]
                    
                    sec_entities.append({
                        'lei': row[lei_key].strip('"'),
                        'name': row[name_key].strip('"'),
                        'auth_id': auth_id,
                        'entity_id': row.get(entity_id_key, '').strip('"')
                    })
                break
        
        if len(sec_entities) >= 20:
            break

print(f"Found {len(sec_entities)} SEC-registered entities (sample):")
for e in sec_entities[:10]:
    print(f"  LEI: {e['lei']}")
    print(f"    Name: {e['name']}")
    print(f"    Auth: {e['auth_id']}")
    print(f"    Entity ID: {e['entity_id']}")
    print()
