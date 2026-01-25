#!/usr/bin/env python
"""Query GLEIF API for LEI information."""

import urllib.request
import json

# Query GLEIF for NVIDIA's LEI
lei = '549300S4KLFTLO7GSQ80'
url = f'https://api.gleif.org/api/v1/lei-records/{lei}'

print(f"Querying GLEIF for LEI: {lei}")
try:
    with urllib.request.urlopen(url, timeout=10) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        data = result.get('data', {}).get('attributes', {})
        entity = data.get('entity', {})
        
        print(f"Legal Name: {entity.get('legalName', {}).get('name')}")
        print(f"Jurisdiction: {entity.get('jurisdiction')}")
        print(f"Legal Address Country: {entity.get('legalAddress', {}).get('country')}")
        print(f"Category: {entity.get('category')}")
        print(f"Status: {entity.get('status')}")
        
        # Check for other identifiers in the record
        print(f"\nFull attributes keys: {list(data.keys())}")
        
        # Check registration info
        reg = data.get('registration', {})
        print(f"\nRegistration status: {reg.get('status')}")
        
        # Check for additional identifiers  
        print(f"\n--- Additional Identifiers ---")
        if data.get('bic'):
            print(f"BIC: {data.get('bic')}")
        if data.get('mic'):
            print(f"MIC: {data.get('mic')}")
        if data.get('ocid'):
            print(f"OCID (OpenCorporates): {data.get('ocid')}")
        if data.get('qcc'):
            print(f"QCC: {data.get('qcc')}")
        if data.get('spglobal'):
            print(f"S&P Global: {data.get('spglobal')}")
            
        # Print full response
        print(f"\n--- Full Attributes ---")
        print(json.dumps(data, indent=2))
        
except Exception as e:
    print(f'Error: {e}')
