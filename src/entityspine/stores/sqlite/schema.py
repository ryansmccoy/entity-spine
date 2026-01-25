"""Database schema definitions for SQLite store."""

# Full schema SQL for all EntitySpine tables
SCHEMA_SQL = """
-- Entities table
CREATE TABLE IF NOT EXISTS entities (
    entity_id TEXT PRIMARY KEY,
    primary_name TEXT NOT NULL,
    entity_type TEXT NOT NULL DEFAULT 'organization',
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT,
    source_id TEXT,
    jurisdiction TEXT,
    sic_code TEXT,
    redirect_to TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(primary_name);
CREATE INDEX IF NOT EXISTS idx_entities_source ON entities(source_system, source_id);
CREATE INDEX IF NOT EXISTS idx_entities_status ON entities(status);

-- Securities table
CREATE TABLE IF NOT EXISTS securities (
    security_id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    security_type TEXT NOT NULL DEFAULT 'common_stock',
    status TEXT NOT NULL DEFAULT 'active',
    description TEXT,
    source_system TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_securities_entity ON securities(entity_id);
CREATE INDEX IF NOT EXISTS idx_securities_type ON securities(security_type);

-- Listings table (TICKER LIVES HERE!)
CREATE TABLE IF NOT EXISTS listings (
    listing_id TEXT PRIMARY KEY,
    security_id TEXT NOT NULL,
    ticker TEXT NOT NULL,
    exchange TEXT NOT NULL,
    mic TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    is_primary INTEGER NOT NULL DEFAULT 0,
    start_date TEXT,
    end_date TEXT,
    source_system TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (security_id) REFERENCES securities(security_id)
);

CREATE INDEX IF NOT EXISTS idx_listings_security ON listings(security_id);
CREATE INDEX IF NOT EXISTS idx_listings_ticker ON listings(ticker);
CREATE INDEX IF NOT EXISTS idx_listings_exchange ON listings(exchange);

-- Identifier Claims table (canonical identifier storage)
CREATE TABLE IF NOT EXISTS claims (
    claim_id TEXT PRIMARY KEY,
    entity_id TEXT,
    security_id TEXT,
    listing_id TEXT,
    scheme TEXT NOT NULL,
    value TEXT NOT NULL,
    namespace TEXT NOT NULL DEFAULT 'UNKNOWN',
    status TEXT NOT NULL DEFAULT 'active',
    confidence REAL NOT NULL DEFAULT 1.0,
    source TEXT,
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id),
    FOREIGN KEY (listing_id) REFERENCES listings(listing_id)
);

CREATE INDEX IF NOT EXISTS idx_claims_scheme_value ON claims(scheme, value);
CREATE INDEX IF NOT EXISTS idx_claims_entity ON claims(entity_id);
CREATE INDEX IF NOT EXISTS idx_claims_security ON claims(security_id);
CREATE INDEX IF NOT EXISTS idx_claims_listing ON claims(listing_id);

-- Addresses table (normalized addresses)
CREATE TABLE IF NOT EXISTS addresses (
    address_id TEXT PRIMARY KEY,
    line1 TEXT,
    line2 TEXT,
    city TEXT,
    region TEXT,
    postal TEXT,
    country TEXT NOT NULL DEFAULT 'US',
    normalized_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_addresses_hash ON addresses(normalized_hash);
CREATE INDEX IF NOT EXISTS idx_addresses_city ON addresses(city);

-- Entity-Address link table
CREATE TABLE IF NOT EXISTS entity_addresses (
    entity_id TEXT NOT NULL,
    address_id TEXT NOT NULL,
    address_type TEXT NOT NULL DEFAULT 'business',
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (entity_id, address_id, address_type),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE INDEX IF NOT EXISTS idx_entity_addresses_entity ON entity_addresses(entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_addresses_address ON entity_addresses(address_id);

-- Geographic locations
CREATE TABLE IF NOT EXISTS geos (
    geo_id TEXT PRIMARY KEY,
    geo_type TEXT NOT NULL,
    name TEXT NOT NULL,
    iso_code TEXT,
    parent_geo_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (parent_geo_id) REFERENCES geos(geo_id)
);

CREATE INDEX IF NOT EXISTS idx_geos_iso ON geos(iso_code);
CREATE INDEX IF NOT EXISTS idx_geos_type ON geos(geo_type);
CREATE INDEX IF NOT EXISTS idx_geos_name ON geos(name);

-- Role assignments
CREATE TABLE IF NOT EXISTS role_assignments (
    role_assignment_id TEXT PRIMARY KEY,
    person_entity_id TEXT NOT NULL,
    org_entity_id TEXT NOT NULL,
    role_type TEXT NOT NULL,
    title TEXT,
    start_date TEXT,
    end_date TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    filing_id TEXT,
    section_id TEXT,
    snippet_hash TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (person_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (org_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_role_assignments_person ON role_assignments(person_entity_id);
CREATE INDEX IF NOT EXISTS idx_role_assignments_org ON role_assignments(org_entity_id);
CREATE INDEX IF NOT EXISTS idx_role_assignments_role ON role_assignments(role_type);
CREATE INDEX IF NOT EXISTS idx_role_assignments_dates ON role_assignments(start_date, end_date);

-- Entity relationships
CREATE TABLE IF NOT EXISTS entity_relationships (
    relationship_id TEXT PRIMARY KEY,
    from_entity_id TEXT NOT NULL,
    to_entity_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    status TEXT NOT NULL DEFAULT 'active',
    evidence_text TEXT,
    filing_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (from_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (to_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_relationships_from ON entity_relationships(from_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_to ON entity_relationships(to_entity_id);
CREATE INDEX IF NOT EXISTS idx_relationships_type ON entity_relationships(relationship_type);

-- Generic relationships (NodeRef pattern)
CREATE TABLE IF NOT EXISTS relationships (
    relationship_id TEXT PRIMARY KEY,
    source_kind TEXT NOT NULL,
    source_id TEXT NOT NULL,
    target_kind TEXT NOT NULL,
    target_id TEXT NOT NULL,
    relationship_type TEXT NOT NULL,
    subtype TEXT,
    valid_from TEXT,
    valid_to TEXT,
    captured_at TEXT NOT NULL,
    source_system TEXT,
    source_ref TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    evidence_filing_id TEXT,
    evidence_section_id TEXT,
    evidence_excerpt_hash TEXT,
    evidence_snippet TEXT,
    metrics TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_generic_rel_source ON relationships(source_kind, source_id);
CREATE INDEX IF NOT EXISTS idx_generic_rel_target ON relationships(target_kind, target_id);
CREATE INDEX IF NOT EXISTS idx_generic_rel_type ON relationships(relationship_type);

-- Legal cases
CREATE TABLE IF NOT EXISTS cases (
    case_id TEXT PRIMARY KEY,
    case_type TEXT NOT NULL,
    case_number TEXT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'unknown',
    authority_entity_id TEXT,
    target_entity_id TEXT,
    opened_date TEXT,
    closed_date TEXT,
    description TEXT,
    source_system TEXT,
    source_ref TEXT,
    filing_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (authority_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_cases_type ON cases(case_type);
CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status);
CREATE INDEX IF NOT EXISTS idx_cases_authority ON cases(authority_entity_id);
CREATE INDEX IF NOT EXISTS idx_cases_target ON cases(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_cases_number ON cases(case_number);

-- Entity clusters
CREATE TABLE IF NOT EXISTS entity_clusters (
    cluster_id TEXT PRIMARY KEY,
    reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

-- Cluster membership
CREATE TABLE IF NOT EXISTS entity_cluster_members (
    cluster_id TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'member',
    confidence REAL NOT NULL DEFAULT 1.0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (cluster_id, entity_id),
    FOREIGN KEY (cluster_id) REFERENCES entity_clusters(cluster_id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_cluster_members_entity ON entity_cluster_members(entity_id);
CREATE INDEX IF NOT EXISTS idx_cluster_members_role ON entity_cluster_members(role);

-- Assets table
CREATE TABLE IF NOT EXISTS assets (
    asset_id TEXT PRIMARY KEY,
    asset_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner_entity_id TEXT,
    operator_entity_id TEXT,
    geo_id TEXT,
    address_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (operator_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (geo_id) REFERENCES geos(geo_id),
    FOREIGN KEY (address_id) REFERENCES addresses(address_id)
);

CREATE INDEX IF NOT EXISTS idx_assets_type ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_name ON assets(name);
CREATE INDEX IF NOT EXISTS idx_assets_owner ON assets(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_assets_status ON assets(status);
CREATE INDEX IF NOT EXISTS idx_assets_source ON assets(source_system, source_id);

-- Contracts table
CREATE TABLE IF NOT EXISTS contracts (
    contract_id TEXT PRIMARY KEY,
    contract_type TEXT NOT NULL,
    title TEXT NOT NULL,
    effective_date TEXT,
    termination_date TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    value_usd REAL,
    source_system TEXT,
    source_id TEXT,
    filing_id TEXT,
    content_hash TEXT,
    summary TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_contracts_type ON contracts(contract_type);
CREATE INDEX IF NOT EXISTS idx_contracts_status ON contracts(status);
CREATE INDEX IF NOT EXISTS idx_contracts_effective ON contracts(effective_date);
CREATE INDEX IF NOT EXISTS idx_contracts_source ON contracts(source_system, source_id);
CREATE INDEX IF NOT EXISTS idx_contracts_filing ON contracts(filing_id);

-- Products table
CREATE TABLE IF NOT EXISTS products (
    product_id TEXT PRIMARY KEY,
    product_type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    owner_entity_id TEXT,
    status TEXT NOT NULL DEFAULT 'active',
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_products_type ON products(product_type);
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_owner ON products(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_products_status ON products(status);
CREATE INDEX IF NOT EXISTS idx_products_source ON products(source_system, source_id);

-- Brands table
CREATE TABLE IF NOT EXISTS brands (
    brand_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    owner_entity_id TEXT,
    description TEXT,
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (owner_entity_id) REFERENCES entities(entity_id)
);

CREATE INDEX IF NOT EXISTS idx_brands_name ON brands(name);
CREATE INDEX IF NOT EXISTS idx_brands_owner ON brands(owner_entity_id);
CREATE INDEX IF NOT EXISTS idx_brands_source ON brands(source_system, source_id);

-- KG Events table
CREATE TABLE IF NOT EXISTS kg_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'announced',
    occurred_on TEXT,
    announced_on TEXT,
    payload TEXT,
    evidence_filing_id TEXT,
    evidence_section_id TEXT,
    evidence_snippet TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    source_system TEXT,
    source_id TEXT,
    captured_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_kg_events_type ON kg_events(event_type);
CREATE INDEX IF NOT EXISTS idx_kg_events_status ON kg_events(status);
CREATE INDEX IF NOT EXISTS idx_kg_events_occurred ON kg_events(occurred_on);
CREATE INDEX IF NOT EXISTS idx_kg_events_announced ON kg_events(announced_on);
CREATE INDEX IF NOT EXISTS idx_kg_events_source ON kg_events(source_system, source_id);
CREATE INDEX IF NOT EXISTS idx_kg_events_filing ON kg_events(evidence_filing_id);

-- =============================================================================
-- v2.3.4: Audit Trail Tables
-- =============================================================================

-- Provenance table (tracks where data came from)
CREATE TABLE IF NOT EXISTS provenance (
    provenance_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL DEFAULT 'file',
    namespace TEXT NOT NULL DEFAULT 'internal',
    source_uri TEXT,
    source_hash TEXT,
    captured_at TEXT NOT NULL,
    captured_by TEXT,
    file_name TEXT,
    api_endpoint TEXT,
    api_params TEXT,
    batch_id TEXT,
    notes TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_provenance_kind ON provenance(kind);
CREATE INDEX IF NOT EXISTS idx_provenance_namespace ON provenance(namespace);
CREATE INDEX IF NOT EXISTS idx_provenance_batch ON provenance(batch_id);
CREATE INDEX IF NOT EXISTS idx_provenance_captured ON provenance(captured_at);

-- Source records table (preserves raw ingested data)
CREATE TABLE IF NOT EXISTS source_records (
    record_id TEXT PRIMARY KEY,
    provenance_id TEXT,
    raw_data TEXT,
    record_type TEXT NOT NULL DEFAULT 'unknown',
    source_key TEXT,
    processed INTEGER NOT NULL DEFAULT 0,
    processed_at TEXT,
    entity_id TEXT,
    security_id TEXT,
    listing_id TEXT,
    error_message TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (provenance_id) REFERENCES provenance(provenance_id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id),
    FOREIGN KEY (listing_id) REFERENCES listings(listing_id)
);

CREATE INDEX IF NOT EXISTS idx_source_records_provenance ON source_records(provenance_id);
CREATE INDEX IF NOT EXISTS idx_source_records_type ON source_records(record_type);
CREATE INDEX IF NOT EXISTS idx_source_records_processed ON source_records(processed);
CREATE INDEX IF NOT EXISTS idx_source_records_entity ON source_records(entity_id);

-- Merge events table (tracks entity merges)
CREATE TABLE IF NOT EXISTS merge_events (
    event_id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    target_entity_id TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'duplicate_resolution',
    explanation_id TEXT,
    run_id TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    merged_by TEXT,
    merged_at TEXT NOT NULL,
    source_snapshot TEXT,
    reversible INTEGER NOT NULL DEFAULT 1,
    reversed INTEGER NOT NULL DEFAULT 0,
    reversed_at TEXT,
    reversed_by TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (target_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (explanation_id) REFERENCES explanations(explanation_id),
    FOREIGN KEY (run_id) REFERENCES resolution_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_merge_events_source ON merge_events(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_merge_events_target ON merge_events(target_entity_id);
CREATE INDEX IF NOT EXISTS idx_merge_events_run ON merge_events(run_id);
CREATE INDEX IF NOT EXISTS idx_merge_events_merged_at ON merge_events(merged_at);

-- Split events table (tracks entity splits)
CREATE TABLE IF NOT EXISTS split_events (
    event_id TEXT PRIMARY KEY,
    source_entity_id TEXT NOT NULL,
    target_entity_ids TEXT NOT NULL,
    reason TEXT NOT NULL DEFAULT 'spinoff',
    explanation_id TEXT,
    run_id TEXT,
    split_by TEXT,
    split_at TEXT NOT NULL,
    effective_date TEXT,
    source_snapshot TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (source_entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (explanation_id) REFERENCES explanations(explanation_id),
    FOREIGN KEY (run_id) REFERENCES resolution_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_split_events_source ON split_events(source_entity_id);
CREATE INDEX IF NOT EXISTS idx_split_events_run ON split_events(run_id);
CREATE INDEX IF NOT EXISTS idx_split_events_split_at ON split_events(split_at);

-- Explanations table (decision reasoning)
CREATE TABLE IF NOT EXISTS explanations (
    explanation_id TEXT PRIMARY KEY,
    decision_type TEXT NOT NULL DEFAULT 'match',
    summary TEXT,
    details TEXT,
    factors TEXT,
    confidence REAL NOT NULL DEFAULT 1.0,
    match_scores TEXT,
    rule_hits TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_explanations_type ON explanations(decision_type);
CREATE INDEX IF NOT EXISTS idx_explanations_confidence ON explanations(confidence);

-- Resolution runs table (batch execution tracking)
CREATE TABLE IF NOT EXISTS resolution_runs (
    run_id TEXT PRIMARY KEY,
    input_params TEXT,
    source_record_ids TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    stage_metrics TEXT,
    entities_created INTEGER NOT NULL DEFAULT 0,
    entities_updated INTEGER NOT NULL DEFAULT 0,
    entities_merged INTEGER NOT NULL DEFAULT 0,
    claims_created INTEGER NOT NULL DEFAULT 0,
    claims_superseded INTEGER NOT NULL DEFAULT 0,
    avg_confidence REAL NOT NULL DEFAULT 0.0,
    ambiguous_count INTEGER NOT NULL DEFAULT 0,
    error_count INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'RUNNING',
    error_message TEXT,
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_resolution_runs_status ON resolution_runs(status);
CREATE INDEX IF NOT EXISTS idx_resolution_runs_started ON resolution_runs(started_at);

-- Data quality rules table
CREATE TABLE IF NOT EXISTS data_quality_rules (
    rule_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'consistency',
    severity TEXT NOT NULL DEFAULT 'WARNING',
    target_type TEXT NOT NULL DEFAULT 'entity',
    check_expression TEXT,
    enabled INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_quality_rules_category ON data_quality_rules(category);
CREATE INDEX IF NOT EXISTS idx_quality_rules_severity ON data_quality_rules(severity);
CREATE INDEX IF NOT EXISTS idx_quality_rules_enabled ON data_quality_rules(enabled);

-- Data quality results table
CREATE TABLE IF NOT EXISTS data_quality_results (
    result_id TEXT PRIMARY KEY,
    rule_id TEXT NOT NULL,
    rule_name TEXT,
    passed INTEGER NOT NULL DEFAULT 1,
    severity TEXT NOT NULL DEFAULT 'INFO',
    message TEXT,
    details TEXT,
    entity_id TEXT,
    claim_id TEXT,
    security_id TEXT,
    listing_id TEXT,
    run_id TEXT,
    checked_at TEXT NOT NULL,
    resolved INTEGER NOT NULL DEFAULT 0,
    resolved_at TEXT,
    resolved_by TEXT,
    resolution_notes TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (rule_id) REFERENCES data_quality_rules(rule_id),
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (claim_id) REFERENCES claims(claim_id),
    FOREIGN KEY (security_id) REFERENCES securities(security_id),
    FOREIGN KEY (listing_id) REFERENCES listings(listing_id),
    FOREIGN KEY (run_id) REFERENCES resolution_runs(run_id)
);

CREATE INDEX IF NOT EXISTS idx_quality_results_rule ON data_quality_results(rule_id);
CREATE INDEX IF NOT EXISTS idx_quality_results_entity ON data_quality_results(entity_id);
CREATE INDEX IF NOT EXISTS idx_quality_results_passed ON data_quality_results(passed);
CREATE INDEX IF NOT EXISTS idx_quality_results_resolved ON data_quality_results(resolved);
CREATE INDEX IF NOT EXISTS idx_quality_results_run ON data_quality_results(run_id);

-- Add provenance_id and explanation_id to claims table if not exists
-- (Note: SQLite doesn't support ADD COLUMN IF NOT EXISTS, so we use a migration approach)
"""

# v2.3.4: Migration SQL to add audit trail columns to existing tables
MIGRATION_V234_SQL = """
-- Add provenance tracking to claims table
ALTER TABLE claims ADD COLUMN provenance_id TEXT REFERENCES provenance(provenance_id);
ALTER TABLE claims ADD COLUMN explanation_id TEXT REFERENCES explanations(explanation_id);

-- Create indexes for new columns
CREATE INDEX IF NOT EXISTS idx_claims_provenance ON claims(provenance_id);
CREATE INDEX IF NOT EXISTS idx_claims_explanation ON claims(explanation_id);
"""
