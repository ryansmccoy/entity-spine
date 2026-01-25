"""
EntitySpine Advanced Features Demo

This example demonstrates the powerful new features that make EntitySpine 
actually useful for real-world entity resolution and knowledge graph work.

Features demonstrated:
1. EntityResolver - One-line entity resolution
2. Fuzzy Matching - Match "Apple" to "Apple Inc."
3. Graph Traversal - Get subsidiaries, officers, find paths
4. Entity Clustering - Detect and manage duplicates
5. Timeline Service - Track entity history over time

Run this example:
    cd entityspine
    python examples/06_advanced_features_demo.py
"""

from datetime import date, timedelta
from pprint import pprint

# ==============================================================================
# 1. ENTITY RESOLVER - The "Killer Feature"
# ==============================================================================
print("=" * 70)
print("1. ENTITY RESOLVER - One-line resolution for any identifier")
print("=" * 70)

from entityspine import EntityResolver, ResolverConfig

# Zero-config - just works!
resolver = EntityResolver()

# Resolve by ticker
print("\n📈 Resolving 'AAPL' (ticker)...")
result = resolver.resolve("AAPL")
if result.found:
    print(f"   Found: {result.entity.primary_name}")
    print(f"   CIK: {result.entity.source_id}")
    print(f"   Confidence: {result.confidence:.2f}")

# Resolve by CIK (any format)
print("\n🔢 Resolving '320193' (CIK without padding)...")
result = resolver.resolve("320193")
if result.found:
    print(f"   Found: {result.entity.primary_name}")

# Resolve by padded CIK
print("\n🔢 Resolving '0000320193' (padded CIK)...")
result = resolver.resolve("0000320193")
if result.found:
    print(f"   Found: {result.entity.primary_name}")

# Batch resolution - efficient!
print("\n📦 Batch resolving ['AAPL', 'MSFT', 'GOOGL']...")
results = resolver.resolve_many(["AAPL", "MSFT", "GOOGL"])
for r in results:
    if r.found:
        print(f"   {r.query} → {r.entity.primary_name}")

# ==============================================================================
# 2. FUZZY MATCHING - Match partial/misspelled names
# ==============================================================================
print("\n" + "=" * 70)
print("2. FUZZY MATCHING - Handle typos and variations")
print("=" * 70)

from entityspine import compute_name_similarity, normalize_company_name, FuzzyMatcher

# Test name normalization
print("\n🧹 Name normalization:")
test_names = [
    "Apple Inc.",
    "APPLE INCORPORATED", 
    "The Apple Company, Inc.",
    "MICROSOFT CORPORATION",
]
for name in test_names:
    normalized = normalize_company_name(name)
    print(f"   '{name}' → '{normalized}'")

# Test similarity computation
print("\n📊 Similarity scores:")
pairs = [
    ("Apple Inc.", "APPLE INCORPORATED"),
    ("Microsoft", "Microsft"),  # Typo
    ("Apple", "Oracle"),
    ("Meta Platforms", "Facebook Inc"),  # Different name, same company!
]
for name1, name2 in pairs:
    score = compute_name_similarity(name1, name2)
    print(f"   '{name1}' vs '{name2}': {score:.2f}")

# Fuzzy resolution
print("\n🔍 Fuzzy resolution:")
fuzzy_queries = ["Apple", "Microsft", "Amzon"]  # Intentional typos
for query in fuzzy_queries:
    result = resolver.resolve(query)
    if result.found:
        print(f"   '{query}' → {result.entity.primary_name} (confidence: {result.confidence:.2f})")
    else:
        print(f"   '{query}' → No match found")

# ==============================================================================
# 3. GRAPH TRAVERSAL - Explore entity relationships
# ==============================================================================
print("\n" + "=" * 70)
print("3. GRAPH TRAVERSAL - Navigate the knowledge graph")
print("=" * 70)

from entityspine import GraphService, SqliteStore

# Use the resolver's store
graph = GraphService(resolver.store)

# Find an entity to explore
apple_result = resolver.resolve("AAPL")
if apple_result.found:
    apple_id = apple_result.entity.entity_id
    
    print(f"\n🏢 Exploring: {apple_result.entity.primary_name}")
    
    # Get related entities (would need relationship data loaded)
    print("\n📊 Related entities:")
    related = graph.get_related_entities(apple_id)
    if related:
        for rel in related[:5]:
            print(f"   {rel.relationship_type}: {rel.entity.primary_name}")
    else:
        print("   (No relationships loaded - add some with store.save_entity_relationship())")
    
    # Get officers (would need role data loaded)
    print("\n👔 Officers:")
    officers = graph.get_officers(apple_id)
    if officers:
        for officer in officers[:5]:
            print(f"   {officer.role_type}: {officer.person.primary_name}")
    else:
        print("   (No officer data loaded - add some with store.save_role_assignment())")

    # Demonstrate path finding API
    print("\n🛤️  Path finding API:")
    print("   graph.find_path(company_a, company_b) - finds shortest path")
    print("   graph.get_entity_network(company_id, max_depth=2) - builds network")
    print("   graph.get_ultimate_parent(subsidiary_id) - finds top of hierarchy")

# ==============================================================================
# 4. ENTITY CLUSTERING - Detect duplicates
# ==============================================================================
print("\n" + "=" * 70)
print("4. ENTITY CLUSTERING - Detect and manage duplicates")
print("=" * 70)

from entityspine import ClusteringService, BlockingConfig

clustering = ClusteringService(
    resolver.store,
    blocking_config=BlockingConfig(
        min_similarity=0.7,
        max_candidates_per_entity=10,
    ),
)

# Find potential duplicates for a name
print("\n🔍 Finding duplicates for 'Apple Inc.'...")
candidates = clustering.find_duplicates_by_name("Apple Inc.", limit=5)
for candidate in candidates:
    print(f"   Score: {candidate.similarity_score:.2f}")
    print(f"   Match: {candidate.entity_b.primary_name}")
    print(f"   Reasons: {', '.join(candidate.match_reasons)}")
    print(f"   Confidence: {candidate.confidence}")
    print()

# Demonstrate clustering workflow
print("\n📋 Clustering workflow:")
print("   1. clustering.find_all_duplicates() - scan entire database")
print("   2. clustering.create_cluster([id1, id2], reason='...') - group candidates")
print("   3. clustering.get_pending_clusters() - review candidates")
print("   4. clustering.set_canonical(cluster_id, canonical_id) - pick winner")
print("   5. clustering.merge_cluster(cluster_id) - merge entities (irreversible)")
print("   6. clustering.reject_cluster(cluster_id) - mark as false positive")

# ==============================================================================
# 5. TIMELINE SERVICE - Track history
# ==============================================================================
print("\n" + "=" * 70)
print("5. TIMELINE SERVICE - Track entity history over time")
print("=" * 70)

from entityspine import TimelineService, EventType

timeline = TimelineService(resolver.store)

if apple_result.found:
    apple_id = apple_result.entity.entity_id
    
    print(f"\n📅 Timeline for: {apple_result.entity.primary_name}")
    
    # Get entity timeline
    events = timeline.get_entity_timeline(apple_id)
    if events:
        print("\n   Recent events:")
        for event in events[:5]:
            print(f"   {event.event_date}: {event.description}")
    else:
        print("   (Timeline populated from role/listing/identifier changes)")
    
    # Point-in-time query
    print("\n⏱️  Point-in-time queries:")
    print("   snapshot = timeline.get_entity_at(entity_id, date(2020, 1, 1))")
    print("   - Returns entity state at that specific date")
    print("   - Includes identifiers, listings, officers at that time")
    
    # State comparison
    print("\n📊 State comparison:")
    print("   diff = timeline.compare_states(entity_id, date1, date2)")
    print("   - Shows what changed between two dates")
    print("   - Name changes, new identifiers, officer changes, etc.")

# ==============================================================================
# 6. PUTTING IT ALL TOGETHER
# ==============================================================================
print("\n" + "=" * 70)
print("6. ADVANCED USE CASE: SEC Filing Enrichment")
print("=" * 70)

print("""
📄 Real-world workflow: Enrich SEC filings with entity data

# 1. Load filing data
filings = load_filings_from_sec()

# 2. Batch resolve all companies
ciks = [f.cik for f in filings]
results = resolver.resolve_many(ciks)

# 3. Build entity map
entity_map = {r.query: r.entity for r in results if r.found}

# 4. For each filing, enrich with:
for filing in filings:
    entity = entity_map.get(filing.cik)
    if entity:
        # Graph context
        filing.officers = graph.get_officers(entity.entity_id)
        filing.subsidiaries = graph.get_subsidiaries(entity.entity_id)
        
        # Historical context
        filing.entity_state = timeline.get_entity_at(
            entity.entity_id, 
            filing.date
        )
        
        # Dedup check
        filing.potential_duplicates = clustering.find_duplicates_for_entity(
            entity.entity_id
        )
""")

# ==============================================================================
# SUMMARY
# ==============================================================================
print("\n" + "=" * 70)
print("SUMMARY - EntitySpine Advanced Features")
print("=" * 70)

print("""
🎯 What makes EntitySpine useful now:

1. ONE-LINE RESOLUTION
   result = resolver.resolve("AAPL")  # Just works!

2. FUZZY MATCHING
   "Apple" → "Apple Inc." with confidence score

3. GRAPH TRAVERSAL
   Get subsidiaries, officers, find paths between entities

4. DUPLICATE DETECTION
   Find and manage potential duplicate entities safely

5. TEMPORAL QUERIES
   Query entity state at any point in time

📚 Key Imports:
   from entityspine import (
       EntityResolver,       # Main resolver API
       GraphService,         # Relationship traversal
       ClusteringService,    # Duplicate detection
       TimelineService,      # Historical queries
       FuzzyMatcher,         # String matching
   )

🚀 Get started:
   resolver = EntityResolver()  # Auto-loads SEC data
   result = resolver.resolve("AAPL")
   print(result.entity.primary_name)  # Apple Inc.
""")

print("\n✅ Demo complete!")
