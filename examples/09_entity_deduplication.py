#!/usr/bin/env python3
"""
EntitySpine - Entity Deduplication Example

Demonstrates the "cluster-first, merge-later" pattern for safe entity
deduplication with real-world SEC filing data variations.

This example shows:
1. Fuzzy name matching with variations
2. Duplicate detection and scoring
3. Creating clusters for review
4. Merging approved duplicates
5. Batch deduplication workflows

Run: python examples/09_entity_deduplication.py
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

# Add src to path for development
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from entityspine import (
    EntityResolver,
    EntityStatus,
    EntityType,
    create_entity,
    SqliteStore,
)
from entityspine.services.resolver import ResolverConfig
from entityspine.services.fuzzy import (
    FuzzyMatcher,
    compute_name_similarity,
    normalize_company_name,
)
from entityspine.services.clustering import ClusteringService
from entityspine.domain.clustering import BlockingConfig, ClusterStatus


def print_header(title: str) -> None:
    """Print a formatted section header."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_subheader(title: str) -> None:
    """Print a subsection header."""
    print(f"\n  --- {title} ---\n")


def setup_messy_data(store: SqliteStore) -> dict[str, str]:
    """
    Create realistic messy entity data typical of SEC filings.
    
    SEC filings have many naming variations:
    - Different legal suffixes (Inc, Inc., Incorporated, Corp, etc.)
    - State of incorporation suffixes (/DE, /NV, etc.)
    - Abbreviations vs full names
    - Typos and OCR errors
    - Holding company vs subsidiary names
    
    Returns:
        Dict mapping friendly names to entity IDs.
    """
    print("  Creating realistic messy SEC filing data...\n")
    
    entities = {}
    
    def add_entity(key: str, name: str, cik: str | None = None) -> None:
        """Helper to create and store an entity."""
        entity = create_entity(
            primary_name=name,
            entity_type=EntityType.ORGANIZATION,
            source_system="sec_edgar",
            source_id=cik,
        )
        store.save_entity(entity)
        entities[key] = entity.entity_id
    
    # Apple - common variations
    add_entity("apple_1", "Apple Inc.", "0000320193")
    add_entity("apple_2", "APPLE INC")  # All caps, no period
    add_entity("apple_3", "Apple Inc")  # Missing period
    add_entity("apple_4", "Apple, Inc.")  # With comma
    
    # Microsoft - state incorporation variations
    add_entity("msft_1", "Microsoft Corporation", "0000789019")
    add_entity("msft_2", "MICROSOFT CORP")  # Abbreviated
    add_entity("msft_3", "Microsoft Corporation /WA/")  # State suffix
    
    # JPMorgan - holding vs subsidiary
    add_entity("jpm_1", "JPMorgan Chase & Co.", "0000019617")
    add_entity("jpm_2", "JPMORGAN CHASE & CO")  # All caps, no period
    add_entity("jpm_3", "J.P. Morgan Chase & Co.")  # Different punctuation
    add_entity("jpm_4", "JP Morgan Chase")  # Simplified
    
    # AT&T - special characters
    add_entity("att_1", "AT&T Inc.", "0000732717")
    add_entity("att_2", "AT&T INC")
    add_entity("att_3", "A T & T Inc")  # Spaces around ampersand
    
    # Berkshire - complex name
    add_entity("brk_1", "Berkshire Hathaway Inc.", "0001067983")
    add_entity("brk_2", "BERKSHIRE HATHAWAY INC")
    add_entity("brk_3", "Berkshire Hathaway Inc. /DE/")
    
    # Coca-Cola - hyphenation variations
    add_entity("ko_1", "The Coca-Cola Company", "0000021344")
    add_entity("ko_2", "Coca-Cola Co")  # No "The", abbreviated
    add_entity("ko_3", "COCA COLA COMPANY")  # No hyphen
    
    # 3M - number in name
    add_entity("mmm_1", "3M Company", "0000066740")
    add_entity("mmm_2", "3M CO")
    add_entity("mmm_3", "3M COMPANY")  # All caps
    
    # Add some distinct companies that shouldn't match
    add_entity("google", "Alphabet Inc.", "0001652044")
    add_entity("amazon", "Amazon.com, Inc.", "0001018724")
    add_entity("meta", "Meta Platforms, Inc.", "0001326801")
    
    print(f"  Created {len(entities)} entities with naming variations\n")
    return entities


def example_1_fuzzy_matching() -> None:
    """Demonstrate fuzzy name matching algorithms."""
    print_header("Example 1: Fuzzy Name Matching")
    
    print_subheader("Name Normalization")
    
    names = [
        "Apple Inc.",
        "APPLE INC",
        "Apple, Inc.",
        "Apple Incorporated",
        "MICROSOFT CORPORATION",
        "Microsoft Corp",
        "Microsoft Corporation /WA/",
        "The Coca-Cola Company",
        "COCA COLA CO",
        "JPMorgan Chase & Co.",
        "JP Morgan Chase",
    ]
    
    print("  Raw Name                         -> Normalized")
    print("  " + "-" * 55)
    for name in names:
        normalized = normalize_company_name(name)
        print(f"  {name:35} -> {normalized}")
    
    print_subheader("Similarity Scoring")
    
    comparisons = [
        ("Apple Inc.", "APPLE INC"),
        ("Apple Inc.", "Apple Incorporated"),
        ("Apple Inc.", "Appleseed Inc."),
        ("Microsoft Corporation", "Microsoft Corp"),
        ("Microsoft Corporation", "Microsoft Corporation /WA/"),
        ("JPMorgan Chase & Co.", "J.P. Morgan Chase"),
        ("JPMorgan Chase & Co.", "Morgan Stanley"),  # Should NOT match
        ("Coca-Cola Company", "COCA COLA CO"),
        ("3M Company", "3M CO"),
    ]
    
    print("  Name A                    vs Name B                   Score")
    print("  " + "-" * 65)
    
    for name_a, name_b in comparisons:
        score = compute_name_similarity(name_a, name_b)
        indicator = "MATCH" if score >= 0.85 else "LOW" if score >= 0.7 else "NO"
        print(f"  {name_a:25} vs {name_b:25} {score:.2f} [{indicator}]")


def example_2_duplicate_detection(
    clustering: ClusteringService,
    entities: dict[str, str],
) -> None:
    """Demonstrate duplicate detection with scoring."""
    print_header("Example 2: Duplicate Detection")
    
    print_subheader("Finding duplicates for Apple Inc.")
    
    # Find duplicates for the main Apple entity
    candidates = clustering.find_duplicates_for_entity(entities["apple_1"])
    
    print("  Potential duplicates found:\n")
    for i, candidate in enumerate(candidates, 1):
        print(f"  {i}. {candidate.entity_b.primary_name}")
        print(f"     Score: {candidate.similarity_score:.2f}")
        print(f"     Reasons: {', '.join(candidate.match_reasons)}")
        print()
    
    print_subheader("Finding duplicates for JPMorgan")
    
    candidates = clustering.find_duplicates_for_entity(entities["jpm_1"])
    
    print("  Potential duplicates found:\n")
    for i, candidate in enumerate(candidates, 1):
        print(f"  {i}. {candidate.entity_b.primary_name}")
        print(f"     Score: {candidate.similarity_score:.2f}")
        print()
    
    print_subheader("Pre-create check: Does 'Apple Computer' exist?")
    
    # Before creating a new entity, check if it exists
    candidates = clustering.find_duplicates_by_name("Apple Computer Inc.")
    
    if candidates:
        print("  ALERT: Similar entities already exist:\n")
        for candidate in candidates:
            print(f"    - {candidate.entity_b.primary_name} (score: {candidate.similarity_score:.2f})")
        print("\n  Recommendation: Use existing entity instead of creating duplicate")
    else:
        print("  No similar entities found - safe to create")


def example_3_cluster_management(
    clustering: ClusteringService,
    entities: dict[str, str],
) -> None:
    """Demonstrate cluster creation and management."""
    print_header("Example 3: Cluster Management")
    
    print_subheader("Creating Apple Duplicates Cluster")
    
    # Create a cluster for the Apple entities
    apple_ids = [entities["apple_1"], entities["apple_2"], entities["apple_3"], entities["apple_4"]]
    
    cluster_info = clustering.create_cluster(
        entity_ids=apple_ids,
        reason="Name variations of Apple Inc. identified by fuzzy matching",
    )
    
    print(f"  Created cluster: {cluster_info.cluster.cluster_id}")
    print(f"  Status: {cluster_info.status.value}")
    print(f"  Members: {cluster_info.member_count}")
    print(f"  Reason: {cluster_info.cluster.reason}")
    
    print_subheader("Creating JPMorgan Duplicates Cluster")
    
    jpm_ids = [entities["jpm_1"], entities["jpm_2"], entities["jpm_3"], entities["jpm_4"]]
    
    cluster_jpm = clustering.create_cluster(
        entity_ids=jpm_ids,
        reason="JPMorgan Chase naming variations",
    )
    
    print(f"  Created cluster: {cluster_jpm.cluster.cluster_id}")
    print(f"  Members: {cluster_jpm.member_count}")
    
    print_subheader("Reviewing Pending Clusters")
    
    pending = clustering.get_pending_clusters()
    
    print(f"  Clusters awaiting review: {len(pending)}\n")
    
    for i, c in enumerate(pending, 1):
        print(f"  {i}. Cluster {c.cluster.cluster_id[:8]}...")
        print(f"     Status: {c.status.value}")
        print(f"     Members: {c.member_count}")
        print(f"     Reason: {c.cluster.reason}")
        print()


def example_4_merge_workflow(
    clustering: ClusteringService,
    store: SqliteStore,
    entities: dict[str, str],
) -> None:
    """Demonstrate the full merge workflow."""
    print_header("Example 4: Merge Workflow")
    
    print_subheader("Creating Microsoft Duplicates Cluster")
    
    msft_ids = [entities["msft_1"], entities["msft_2"], entities["msft_3"]]
    
    cluster_info = clustering.create_cluster(
        entity_ids=msft_ids,
        reason="Microsoft Corporation naming variations",
    )
    
    print(f"  Cluster ID: {cluster_info.cluster.cluster_id}")
    print(f"  Status: {cluster_info.status.value}")
    print()
    
    # Show entities before merge
    print("  Entities BEFORE merge:")
    for eid in msft_ids:
        entity = store.get_entity(eid)
        if entity:
            cik = entity.source_id or "No CIK"
            print(f"    - {entity.primary_name} (CIK: {cik})")
    
    print_subheader("Approving and Merging Cluster")
    
    # Merge cluster - use the entity with CIK as canonical
    print(f"  Merging into canonical entity: Microsoft Corporation (has CIK)\n")
    
    merged = clustering.merge_cluster(
        cluster_id=cluster_info.cluster.cluster_id,
        canonical_id=entities["msft_1"],  # Has CIK
    )
    
    if merged:
        print(f"  SUCCESS: Merged {len(msft_ids)} entities")
        print(f"  Canonical entity: {merged.primary_name}")
        print(f"  CIK: {merged.source_id}")
        
        # Show what happened to the other entities
        print("\n  Merged entities now redirect to canonical:")
        for eid in msft_ids[1:]:  # Skip canonical
            entity = store.get_entity(eid)
            if entity and entity.status == EntityStatus.MERGED:
                print(f"    - {entity.primary_name} -> {merged.primary_name}")


def example_5_batch_deduplication(
    clustering: ClusteringService,
) -> None:
    """Demonstrate batch deduplication workflow."""
    print_header("Example 5: Batch Deduplication Workflow")
    
    print_subheader("Scanning All Entities for Duplicates")
    
    # Find all duplicates
    candidates = list(clustering.find_all_duplicates())
    
    print(f"  Total duplicate pairs found: {len(candidates)}\n")
    
    # Group by similarity score
    high_confidence = [c for c in candidates if c.similarity_score >= 0.95]
    medium_confidence = [c for c in candidates if 0.85 <= c.similarity_score < 0.95]
    low_confidence = [c for c in candidates if c.similarity_score < 0.85]
    
    print("  By Confidence Level:")
    print(f"    High (>=0.95):   {len(high_confidence)} pairs")
    print(f"    Medium (0.85-0.95): {len(medium_confidence)} pairs")
    print(f"    Low (<0.85):     {len(low_confidence)} pairs")
    
    print_subheader("High-Confidence Duplicates (Auto-cluster Candidates)")
    
    print("  These pairs have very high similarity and could be")
    print("  auto-clustered for quick review:\n")
    
    for candidate in high_confidence[:5]:  # Show top 5
        print(f"  - '{candidate.entity_a.primary_name}'")
        print(f"    '{candidate.entity_b.primary_name}'")
        print(f"    Score: {candidate.similarity_score:.2f}")
        print()
    
    print_subheader("Medium-Confidence Duplicates (Manual Review)")
    
    print("  These require human review:\n")
    
    for candidate in medium_confidence[:3]:  # Show top 3
        print(f"  - '{candidate.entity_a.primary_name}'")
        print(f"    '{candidate.entity_b.primary_name}'")
        print(f"    Score: {candidate.similarity_score:.2f}")
        print(f"    Reasons: {', '.join(candidate.match_reasons)}")
        print()


def example_6_identifier_matching() -> None:
    """Demonstrate using identifiers for confident matching."""
    print_header("Example 6: Identifier-Based Matching")
    
    print_subheader("CIK Matching (Most Reliable)")
    
    print("  When two entities share the same SEC CIK, they're definitely")
    print("  the same legal entity, regardless of name variations.\n")
    
    # Create a fresh store for this demo
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        store = SqliteStore(db_path)
        store.initialize()
        
        # Same CIK, different name variations
        entity1 = create_entity(
            primary_name="Apple Inc.",
            source_system="sec_edgar",
            source_id="0000320193",
            entity_type=EntityType.ORGANIZATION,
        )
        store.save_entity(entity1)
        
        entity2 = create_entity(
            primary_name="APPLE INCORPORATED",
            source_system="sec_edgar",
            source_id="0000320193",  # Same CIK!
            entity_type=EntityType.ORGANIZATION,
        )
        store.save_entity(entity2)
        
        print("  Entity 1: 'Apple Inc.'        CIK: 0000320193")
        print("  Entity 2: 'APPLE INCORPORATED' CIK: 0000320193")
        print()
        
        # Look up by source_id (CIK)
        results = store.search_entities("Apple", limit=10)
        
        if results:
            entity, _ = results[0]
            print(f"  Resolved to: {entity.primary_name}")
            print("  CIK match provides 100% confidence!")
        
        print_subheader("Source ID as Primary Key")
        
        print("  When entities share a source_id (like SEC CIK), they can be")
        print("  confidently linked as the same entity:\n")
        
        # Microsoft example
        entity3 = create_entity(
            primary_name="Microsoft Corporation",
            source_system="sec_edgar",
            source_id="0000789019",
            entity_type=EntityType.ORGANIZATION,
        )
        store.save_entity(entity3)
        
        entity4 = create_entity(
            primary_name="MSFT",  # Common shorthand 
            source_system="internal",
            source_id=None,  # No CIK
            entity_type=EntityType.ORGANIZATION,
        )
        store.save_entity(entity4)
        
        # The entity with CIK is authoritative
        print(f"  Authoritative: {entity3.primary_name}")
        print(f"    Source: {entity3.source_system}")
        print(f"    CIK: {entity3.source_id}")
        print()
        print(f"  Unknown: {entity4.primary_name}")
        print(f"    Source: {entity4.source_system}")
        print(f"    CIK: {entity4.source_id or 'None'}")
        print()
        print("  Use fuzzy matching + CIK verification to link them!")
        
        store.close()


def main() -> None:
    """Run all deduplication examples."""
    print("\n" + "=" * 70)
    print("  EntitySpine - Entity Deduplication")
    print("  Demonstrating the cluster-first, merge-later pattern")
    print("=" * 70)
    
    # Example 1 doesn't need a database
    example_1_fuzzy_matching()
    
    # Create store and clustering service for remaining examples
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "dedup_demo.db"
        store = SqliteStore(storage_path)
        store.initialize()
        
        # Create clustering service with custom config
        clustering = ClusteringService(
            store,
            blocking_config=BlockingConfig(
                min_similarity=0.80,  # Lower threshold for demo
                max_candidates_per_entity=10,
            ),
        )
        
        print_header("Setup: Creating Messy Data")
        entities = setup_messy_data(store)
        
        # Run examples
        example_2_duplicate_detection(clustering, entities)
        example_3_cluster_management(clustering, entities)
        example_4_merge_workflow(clustering, store, entities)
        example_5_batch_deduplication(clustering)
        
        # Close store to release file lock
        store.close()
    
    # Identifier matching in separate context
    example_6_identifier_matching()
    
    print_header("Summary")
    print("""
  Key Takeaways:

  1. NORMALIZE FIRST: Use name normalization to handle common variations
     (Inc vs Inc. vs Incorporated, case differences, etc.)

  2. CLUSTER-FIRST: Never auto-merge! Create clusters for human review
     to catch false positives and preserve audit trail.

  3. USE IDENTIFIERS: CIK and ticker matches are 100% reliable -
     use them when available for confident matching.

  4. BATCH WORKFLOW: Regularly scan for duplicates to keep data clean.
     Auto-cluster high-confidence matches, manually review others.

  5. PRESERVE HISTORY: Merged entities redirect to canonical entity,
     preserving relationships and audit trail.
""")


if __name__ == "__main__":
    main()
