"""Analyze overlap between GLEIF ISIN-LEI and our database."""
import sqlite3
import csv
from collections import defaultdict

def main():
    # Load GLEIF LEI -> ISIN mappings
    gleif_lei_to_isins = defaultdict(set)
    gleif_isin_to_lei = {}
    
    print("Loading GLEIF ISIN-LEI file...")
    with open('entityspine_data/gleif/lei-isin-20260129T081545.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            lei = row['LEI']
            isin = row['ISIN']
            gleif_lei_to_isins[lei].add(isin)
            gleif_isin_to_lei[isin] = lei
    
    gleif_leis = set(gleif_lei_to_isins.keys())
    gleif_isins = set(gleif_isin_to_lei.keys())
    
    print(f"GLEIF unique LEIs: {len(gleif_leis):,}")
    print(f"GLEIF unique ISINs: {len(gleif_isins):,}")
    
    # Connect to database
    conn = sqlite3.connect('entityspine_data/linked_load.db')
    
    # Get LEIs from claims
    db_leis = set()
    cursor = conn.execute("SELECT DISTINCT value FROM claims WHERE scheme = 'lei'")
    for row in cursor:
        db_leis.add(row[0])
    
    print(f"\nDB LEIs: {len(db_leis):,}")
    
    # Find overlap
    overlap = gleif_leis & db_leis
    print(f"LEIs in BOTH: {len(overlap):,}")
    print(f"DB LEIs NOT in GLEIF: {len(db_leis - gleif_leis):,}")
    
    # Check by source_system
    print(f"\nEntities by source_system:")
    for row in conn.execute('SELECT source_system, COUNT(*) FROM entities GROUP BY source_system'):
        print(f"  {row[0]}: {row[1]:,}")
    
    # Now let's load the identifier bridge and check for ISIN matches
    print("\n" + "=" * 60)
    print("Loading identifier bridge...")
    
    bridge_isins = set()
    bridge_data = []
    with open('entityspine_data/identifier_bridge.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            bridge_data.append(row)
            if row['isin']:
                bridge_isins.add(row['isin'])
    
    print(f"Bridge rows: {len(bridge_data):,}")
    print(f"Bridge unique ISINs: {len(bridge_isins):,}")
    
    # Find ISINs that exist in both GLEIF and bridge
    isin_overlap = gleif_isins & bridge_isins
    print(f"ISINs in BOTH GLEIF and bridge: {len(isin_overlap):,}")
    
    # For matching ISINs, get the LEIs
    matched_leis = set()
    for isin in isin_overlap:
        lei = gleif_isin_to_lei.get(isin)
        if lei:
            matched_leis.add(lei)
    
    print(f"Unique LEIs that match bridge ISINs: {len(matched_leis):,}")
    
    # Check how many of these LEIs are already in the DB
    new_leis = matched_leis - db_leis
    existing_leis = matched_leis & db_leis
    print(f"  - Already in DB: {len(existing_leis):,}")
    print(f"  - NEW (can link Thomson to FactSet): {len(new_leis):,}")
    
    # Show some examples of complete linkages
    print("\n" + "=" * 60)
    print("Sample complete linkages (ISIN -> LEI -> FactSet/Bloomberg):")
    
    count = 0
    for row in bridge_data:
        isin = row['isin']
        if isin in gleif_isin_to_lei:
            lei = gleif_isin_to_lei[isin]
            
            # Check if this LEI is in our DB
            cursor = conn.execute(
                "SELECT e.primary_name, e.source_system FROM entities e "
                "JOIN claims c ON e.entity_id = c.entity_id "
                "WHERE c.scheme = 'lei' AND c.value = ?",
                (lei,)
            )
            db_match = cursor.fetchone()
            
            if db_match:
                count += 1
                if count <= 5:
                    print(f"\n  Name: {row['name']}")
                    print(f"  ISIN: {isin}")
                    print(f"  LEI: {lei}")
                    print(f"  FactSet Entity: {row['factset_entity_id']}")
                    print(f"  Bloomberg FIGI: {row['bloomberg_figi']}")
                    print(f"  DB Match: {db_match[0]} ({db_match[1]})")
    
    print(f"\nTotal linkages possible: {count}")
    
    # Check NVIDIA specifically
    print("\n" + "=" * 60)
    print("NVIDIA check:")
    nvidia_lei = "549300S4KLFTLO7GSQ80"
    nvidia_isins = gleif_lei_to_isins.get(nvidia_lei, set())
    print(f"  LEI: {nvidia_lei}")
    print(f"  GLEIF ISINs: {nvidia_isins}")
    
    # Check if NVIDIA ISIN is in bridge
    nvidia_isin = "US67066G1040"
    if nvidia_isin in gleif_isin_to_lei:
        print(f"  ISIN {nvidia_isin} -> LEI: {gleif_isin_to_lei[nvidia_isin]}")
    
    conn.close()


if __name__ == "__main__":
    main()
