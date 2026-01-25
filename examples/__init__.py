"""
EntitySpine Examples

Working demonstrations of EntitySpine capabilities:

TIER EXAMPLES:
- tier0_json_memory.py  : JSON/Memory store (zero deps)
- tier1_sqlite.py       : SQLite store (zero deps)
- tier_comparison.py    : Compare all tiers

INGESTION EXAMPLES:
- ingestion_patterns.py : 5 ways to ingest data
- sec_data_pipeline.py  : Complete SEC EDGAR pipeline

QUICK START:
    from entityspine import JsonEntityStore
    
    store = JsonEntityStore()
    store.initialize()
    store.load_sec_data()  # Load from SEC EDGAR API
    
    # Resolve by ticker
    entities = store.get_entities_by_ticker("AAPL")
    print(entities[0].primary_name)  # "Apple Inc."

Run examples:
    python -m examples.tier0_json_memory
    python -m examples.tier1_sqlite
    python -m examples.tier_comparison
    python -m examples.ingestion_patterns
    python -m examples.sec_data_pipeline
"""
