-- ============================================================================
-- ENTITY SPINE DATABASE SCHEMA
-- ============================================================================
-- A comprehensive schema for financial data, company profiles, knowledge graphs,
-- and SEC filing analysis.
--
-- Version: 1.0
-- Last Updated: January 27, 2026
-- ============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For fuzzy text search

-- ============================================================================
-- SECTION 1: COMPANIES & SECURITIES
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 1.1 COMPANIES - Core company information
-- ---------------------------------------------------------------------------
CREATE TABLE companies (
    company_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    -- Identifiers
    cik TEXT UNIQUE NOT NULL,          -- SEC Central Index Key
    ticker TEXT,                        -- Primary stock ticker
    cusip TEXT,                         -- CUSIP number
    isin TEXT,                          -- ISIN number
    lei TEXT,                           -- Legal Entity Identifier
    
    -- Basic Info
    name TEXT NOT NULL,
    legal_name TEXT,
    former_names TEXT[],
    description TEXT,
    
    -- Classification
    sector TEXT,
    industry TEXT,
    sub_industry TEXT,
    sic_code TEXT,
    sic_description TEXT,
    naics_code TEXT,
    
    -- Location
    headquarters_address TEXT,
    headquarters_city TEXT,
    headquarters_state TEXT,
    headquarters_country TEXT DEFAULT 'US',
    mailing_address TEXT,
    
    -- Corporate Info
    incorporated_state TEXT,
    incorporated_country TEXT,
    fiscal_year_end TEXT,               -- 'December', 'June', etc.
    filer_status TEXT,                  -- 'Large Accelerated', 'Accelerated', etc.
    
    -- Contact
    website TEXT,
    phone TEXT,
    ir_website TEXT,                    -- Investor relations
    
    -- Market Data (cached)
    market_cap DECIMAL(20,2),
    enterprise_value DECIMAL(20,2),
    shares_outstanding BIGINT,
    float_shares BIGINT,
    
    -- Key Metrics (cached from latest financials)
    revenue_ttm DECIMAL(20,2),
    net_income_ttm DECIMAL(20,2),
    gross_margin DECIMAL(8,4),
    operating_margin DECIMAL(8,4),
    net_margin DECIMAL(8,4),
    roe DECIMAL(8,4),
    roa DECIMAL(8,4),
    pe_ratio DECIMAL(10,2),
    ps_ratio DECIMAL(10,2),
    pb_ratio DECIMAL(10,2),
    
    -- Employees
    employees INTEGER,
    employees_date DATE,
    
    -- Status
    status TEXT DEFAULT 'active',       -- 'active', 'inactive', 'merged', 'delisted'
    is_public BOOLEAN DEFAULT true,
    exchange TEXT,                      -- 'NYSE', 'NASDAQ', etc.
    
    -- Timestamps
    founded_year INTEGER,
    ipo_date DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_filing_date DATE,
    
    -- Search
    search_vector TSVECTOR
);

-- Indexes
CREATE INDEX idx_companies_cik ON companies(cik);
CREATE INDEX idx_companies_ticker ON companies(ticker);
CREATE INDEX idx_companies_name ON companies USING gin(name gin_trgm_ops);
CREATE INDEX idx_companies_sector ON companies(sector);
CREATE INDEX idx_companies_industry ON companies(industry);
CREATE INDEX idx_companies_sic ON companies(sic_code);
CREATE INDEX idx_companies_market_cap ON companies(market_cap DESC NULLS LAST);
CREATE INDEX idx_companies_search ON companies USING gin(search_vector);

COMMENT ON TABLE companies IS 'Core company information and cached metrics';

-- ---------------------------------------------------------------------------
-- 1.2 COMPANY_TICKERS - All tickers for a company (historical)
-- ---------------------------------------------------------------------------
CREATE TABLE company_tickers (
    ticker_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    ticker TEXT NOT NULL,
    exchange TEXT,
    is_primary BOOLEAN DEFAULT false,
    valid_from DATE,
    valid_to DATE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(ticker, exchange, valid_from)
);

CREATE INDEX idx_company_tickers_company ON company_tickers(company_id);
CREATE INDEX idx_company_tickers_ticker ON company_tickers(ticker);

-- ---------------------------------------------------------------------------
-- 1.3 SECTORS - Sector definitions (GICS hierarchy)
-- ---------------------------------------------------------------------------
CREATE TABLE sectors (
    sector_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_sector_id UUID REFERENCES sectors(sector_id),
    code TEXT NOT NULL UNIQUE,          -- GICS code
    name TEXT NOT NULL,
    description TEXT,
    level INTEGER NOT NULL,             -- 1=Sector, 2=Industry Group, 3=Industry, 4=Sub-Industry
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_sectors_parent ON sectors(parent_sector_id);
CREATE INDEX idx_sectors_level ON sectors(level);

-- Insert GICS sectors
INSERT INTO sectors (code, name, level, description) VALUES
    ('10', 'Energy', 1, 'Energy sector'),
    ('15', 'Materials', 1, 'Materials sector'),
    ('20', 'Industrials', 1, 'Industrials sector'),
    ('25', 'Consumer Discretionary', 1, 'Consumer Discretionary sector'),
    ('30', 'Consumer Staples', 1, 'Consumer Staples sector'),
    ('35', 'Health Care', 1, 'Health Care sector'),
    ('40', 'Financials', 1, 'Financials sector'),
    ('45', 'Information Technology', 1, 'Information Technology sector'),
    ('50', 'Communication Services', 1, 'Communication Services sector'),
    ('55', 'Utilities', 1, 'Utilities sector'),
    ('60', 'Real Estate', 1, 'Real Estate sector');

-- ============================================================================
-- SECTION 2: SEC FILINGS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 2.1 FILINGS - SEC filing records
-- ---------------------------------------------------------------------------
CREATE TABLE filings (
    filing_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    
    -- SEC Identifiers
    accession_number TEXT UNIQUE NOT NULL,
    file_number TEXT,
    film_number TEXT,
    
    -- Filing Details
    form_type TEXT NOT NULL,            -- '10-K', '10-Q', '8-K', '4', etc.
    form_description TEXT,
    primary_document TEXT,               -- Main document filename
    primary_doc_description TEXT,
    
    -- Dates
    filed_at DATE NOT NULL,
    accepted_at TIMESTAMPTZ,
    period_of_report DATE,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    
    -- Size
    size_bytes BIGINT,
    
    -- URLs
    sec_url TEXT,
    filing_index_url TEXT,
    
    -- Status
    status TEXT DEFAULT 'captured',     -- 'captured', 'parsing', 'parsed', 'error'
    is_amended BOOLEAN DEFAULT false,
    amends_filing_id UUID REFERENCES filings(filing_id),
    
    -- Processing
    captured_at TIMESTAMPTZ DEFAULT NOW(),
    parsed_at TIMESTAMPTZ,
    last_error TEXT,
    
    -- Search
    search_vector TSVECTOR,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes
CREATE INDEX idx_filings_company ON filings(company_id);
CREATE INDEX idx_filings_form_type ON filings(form_type);
CREATE INDEX idx_filings_filed ON filings(filed_at DESC);
CREATE INDEX idx_filings_accession ON filings(accession_number);
CREATE INDEX idx_filings_period ON filings(period_of_report);
CREATE INDEX idx_filings_status ON filings(status);
CREATE INDEX idx_filings_search ON filings USING gin(search_vector);

COMMENT ON TABLE filings IS 'SEC filing metadata and status';

-- ---------------------------------------------------------------------------
-- 2.2 FILING_DOCUMENTS - Individual documents within a filing
-- ---------------------------------------------------------------------------
CREATE TABLE filing_documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID NOT NULL REFERENCES filings(filing_id) ON DELETE CASCADE,
    
    -- Document Info
    sequence INTEGER,
    filename TEXT NOT NULL,
    description TEXT,
    document_type TEXT,                 -- '10-K', 'EX-21', 'EX-31.1', etc.
    size_bytes BIGINT,
    
    -- Content Type
    content_type TEXT,                  -- 'text/html', 'application/pdf', etc.
    is_primary BOOLEAN DEFAULT false,
    
    -- URLs
    url TEXT,
    
    -- Content (for parsed documents)
    content_text TEXT,
    content_html TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_filing_documents_filing ON filing_documents(filing_id);
CREATE INDEX idx_filing_documents_type ON filing_documents(document_type);

-- ---------------------------------------------------------------------------
-- 2.3 FILING_SECTIONS - Parsed sections from filings
-- ---------------------------------------------------------------------------
CREATE TABLE filing_sections (
    section_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID NOT NULL REFERENCES filings(filing_id) ON DELETE CASCADE,
    document_id UUID REFERENCES filing_documents(document_id),
    
    -- Section Info
    section_type TEXT NOT NULL,         -- 'item_1', 'item_1a', 'item_7', etc.
    section_title TEXT,
    section_number TEXT,
    
    -- Content
    content_text TEXT,
    content_html TEXT,
    word_count INTEGER,
    
    -- Position
    start_position INTEGER,
    end_position INTEGER,
    
    -- Search
    search_vector TSVECTOR,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_filing_sections_filing ON filing_sections(filing_id);
CREATE INDEX idx_filing_sections_type ON filing_sections(section_type);
CREATE INDEX idx_filing_sections_search ON filing_sections USING gin(search_vector);

-- ---------------------------------------------------------------------------
-- 2.4 FILING_CHANGES - Track changes between filings
-- ---------------------------------------------------------------------------
CREATE TABLE filing_changes (
    change_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID NOT NULL REFERENCES filings(filing_id) ON DELETE CASCADE,
    previous_filing_id UUID REFERENCES filings(filing_id),
    
    -- Change Summary
    section_type TEXT,
    change_type TEXT NOT NULL,          -- 'added', 'removed', 'modified'
    change_summary TEXT,
    
    -- Content
    old_content TEXT,
    new_content TEXT,
    diff_html TEXT,
    
    -- Importance
    significance_score DECIMAL(3,2),    -- 0.0 to 1.0
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_filing_changes_filing ON filing_changes(filing_id);
CREATE INDEX idx_filing_changes_type ON filing_changes(change_type);

-- ============================================================================
-- SECTION 3: FINANCIAL DATA (XBRL)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 3.1 FINANCIAL_STATEMENTS - Structured financial data
-- ---------------------------------------------------------------------------
CREATE TABLE financial_statements (
    statement_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    filing_id UUID REFERENCES filings(filing_id) ON DELETE SET NULL,
    
    -- Statement Type
    statement_type TEXT NOT NULL,       -- 'income', 'balance', 'cashflow', 'equity'
    period_type TEXT NOT NULL,          -- 'annual', 'quarterly'
    
    -- Period
    period_start DATE,
    period_end DATE NOT NULL,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    
    -- Currency
    currency TEXT DEFAULT 'USD',
    
    -- Data (structured JSONB)
    data JSONB NOT NULL,
    
    -- Source
    source TEXT DEFAULT 'xbrl',         -- 'xbrl', 'manual', 'estimated'
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, statement_type, period_type, period_end)
);

CREATE INDEX idx_financial_statements_company ON financial_statements(company_id);
CREATE INDEX idx_financial_statements_type ON financial_statements(statement_type);
CREATE INDEX idx_financial_statements_period ON financial_statements(period_end DESC);
CREATE INDEX idx_financial_statements_data ON financial_statements USING gin(data);

-- ---------------------------------------------------------------------------
-- 3.2 FINANCIAL_METRICS - Time series of key metrics
-- ---------------------------------------------------------------------------
CREATE TABLE financial_metrics (
    metric_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    filing_id UUID REFERENCES filings(filing_id),
    
    -- Metric
    metric_name TEXT NOT NULL,          -- 'revenue', 'net_income', 'eps', etc.
    metric_value DECIMAL(20,4) NOT NULL,
    
    -- Period
    period_type TEXT NOT NULL,          -- 'annual', 'quarterly', 'ttm'
    period_end DATE NOT NULL,
    
    -- Context
    currency TEXT DEFAULT 'USD',
    unit TEXT,                          -- 'USD', 'shares', 'percent', etc.
    
    -- Comparison
    yoy_change DECIMAL(10,4),
    qoq_change DECIMAL(10,4),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(company_id, metric_name, period_type, period_end)
);

CREATE INDEX idx_financial_metrics_company ON financial_metrics(company_id);
CREATE INDEX idx_financial_metrics_name ON financial_metrics(metric_name);
CREATE INDEX idx_financial_metrics_period ON financial_metrics(period_end DESC);

-- ---------------------------------------------------------------------------
-- 3.3 XBRL_FACTS - Raw XBRL fact data
-- ---------------------------------------------------------------------------
CREATE TABLE xbrl_facts (
    fact_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID NOT NULL REFERENCES filings(filing_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id),
    
    -- XBRL Element
    taxonomy TEXT NOT NULL,             -- 'us-gaap', 'dei', 'custom'
    element_name TEXT NOT NULL,
    label TEXT,
    
    -- Value
    value TEXT NOT NULL,
    value_numeric DECIMAL(20,4),
    unit TEXT,
    decimals INTEGER,
    
    -- Context
    period_type TEXT,                   -- 'instant', 'duration'
    period_start DATE,
    period_end DATE,
    segment JSONB,                      -- Dimensional data
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_xbrl_facts_filing ON xbrl_facts(filing_id);
CREATE INDEX idx_xbrl_facts_company ON xbrl_facts(company_id);
CREATE INDEX idx_xbrl_facts_element ON xbrl_facts(taxonomy, element_name);
CREATE INDEX idx_xbrl_facts_period ON xbrl_facts(period_end);

-- ============================================================================
-- SECTION 4: KNOWLEDGE GRAPH (ENTITIES & RELATIONSHIPS)
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 4.1 ENTITIES - Extracted entities from filings
-- ---------------------------------------------------------------------------
CREATE TABLE entities (
    entity_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Type
    entity_type TEXT NOT NULL,          -- 'company', 'person', 'location', 'product', 'event'
    
    -- Identity
    name TEXT NOT NULL,
    normalized_name TEXT,               -- Lowercase, cleaned for matching
    aliases TEXT[],
    
    -- Linking (for companies/people with known records)
    company_id UUID REFERENCES companies(company_id),
    
    -- Properties
    properties JSONB DEFAULT '{}',
    
    -- Source
    first_seen_filing_id UUID REFERENCES filings(filing_id),
    
    -- Confidence
    confidence DECIMAL(3,2) DEFAULT 1.0,
    is_verified BOOLEAN DEFAULT false,
    
    -- Search
    search_vector TSVECTOR,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_name ON entities USING gin(name gin_trgm_ops);
CREATE INDEX idx_entities_normalized ON entities(normalized_name);
CREATE INDEX idx_entities_company ON entities(company_id);
CREATE INDEX idx_entities_search ON entities USING gin(search_vector);

COMMENT ON TABLE entities IS 'Entities extracted from SEC filings for knowledge graph';

-- ---------------------------------------------------------------------------
-- 4.2 RELATIONSHIPS - Entity relationships
-- ---------------------------------------------------------------------------
CREATE TABLE relationships (
    relationship_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Entities
    source_entity_id UUID NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    target_entity_id UUID NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    
    -- Relationship
    relationship_type TEXT NOT NULL,    -- 'subsidiary_of', 'officer_of', 'investor_in', etc.
    relationship_subtype TEXT,
    
    -- Properties
    properties JSONB DEFAULT '{}',
    
    -- Validity
    valid_from DATE,
    valid_to DATE,
    is_current BOOLEAN DEFAULT true,
    
    -- Source
    source_filing_id UUID REFERENCES filings(filing_id),
    source_section TEXT,
    
    -- Confidence
    confidence DECIMAL(3,2) DEFAULT 1.0,
    extraction_method TEXT,             -- 'rule', 'ml', 'manual'
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_relationships_source ON relationships(source_entity_id);
CREATE INDEX idx_relationships_target ON relationships(target_entity_id);
CREATE INDEX idx_relationships_type ON relationships(relationship_type);
CREATE INDEX idx_relationships_current ON relationships(is_current) WHERE is_current;

COMMENT ON TABLE relationships IS 'Relationships between entities in knowledge graph';

-- ---------------------------------------------------------------------------
-- 4.3 ENTITY_MENTIONS - Where entities are mentioned
-- ---------------------------------------------------------------------------
CREATE TABLE entity_mentions (
    mention_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID NOT NULL REFERENCES entities(entity_id) ON DELETE CASCADE,
    filing_id UUID NOT NULL REFERENCES filings(filing_id) ON DELETE CASCADE,
    section_id UUID REFERENCES filing_sections(section_id),
    
    -- Context
    mention_text TEXT NOT NULL,
    context_text TEXT,                  -- Surrounding text
    
    -- Position
    start_position INTEGER,
    end_position INTEGER,
    
    -- Sentiment
    sentiment_score DECIMAL(3,2),       -- -1.0 to 1.0
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_entity_mentions_entity ON entity_mentions(entity_id);
CREATE INDEX idx_entity_mentions_filing ON entity_mentions(filing_id);

-- ---------------------------------------------------------------------------
-- 4.4 RELATIONSHIP_TYPES - Relationship type definitions
-- ---------------------------------------------------------------------------
CREATE TABLE relationship_types (
    type_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    description TEXT,
    inverse_name TEXT,                  -- e.g., 'subsidiary_of' inverse is 'parent_of'
    source_entity_types TEXT[],
    target_entity_types TEXT[],
    properties_schema JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Insert common relationship types
INSERT INTO relationship_types (name, display_name, inverse_name, source_entity_types, target_entity_types, description) VALUES
    ('subsidiary_of', 'Subsidiary Of', 'parent_of', ARRAY['company'], ARRAY['company'], 'Company A is a subsidiary of Company B'),
    ('officer_of', 'Officer Of', 'has_officer', ARRAY['person'], ARRAY['company'], 'Person is an officer of Company'),
    ('director_of', 'Director Of', 'has_director', ARRAY['person'], ARRAY['company'], 'Person is a director of Company'),
    ('investor_in', 'Investor In', 'has_investor', ARRAY['company', 'person'], ARRAY['company'], 'Entity has invested in Company'),
    ('competitor_of', 'Competitor Of', 'competitor_of', ARRAY['company'], ARRAY['company'], 'Companies are competitors'),
    ('supplier_of', 'Supplier Of', 'customer_of', ARRAY['company'], ARRAY['company'], 'Company A supplies Company B'),
    ('customer_of', 'Customer Of', 'supplier_of', ARRAY['company'], ARRAY['company'], 'Company A is a customer of Company B'),
    ('partner_of', 'Partner Of', 'partner_of', ARRAY['company'], ARRAY['company'], 'Companies are partners'),
    ('acquired_by', 'Acquired By', 'acquired', ARRAY['company'], ARRAY['company'], 'Company A was acquired by Company B'),
    ('located_in', 'Located In', 'location_of', ARRAY['company', 'person'], ARRAY['location'], 'Entity is located in Location');

-- ============================================================================
-- SECTION 5: PEOPLE & OFFICERS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 5.1 PEOPLE - Individual people (officers, directors, etc.)
-- ---------------------------------------------------------------------------
CREATE TABLE people (
    person_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_id UUID REFERENCES entities(entity_id),
    
    -- Name
    full_name TEXT NOT NULL,
    first_name TEXT,
    middle_name TEXT,
    last_name TEXT,
    suffix TEXT,
    
    -- Identity
    aliases TEXT[],
    normalized_name TEXT,
    
    -- Profile
    bio TEXT,
    education JSONB,
    
    -- Properties
    properties JSONB DEFAULT '{}',
    
    -- Search
    search_vector TSVECTOR,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_people_name ON people USING gin(full_name gin_trgm_ops);
CREATE INDEX idx_people_normalized ON people(normalized_name);
CREATE INDEX idx_people_entity ON people(entity_id);
CREATE INDEX idx_people_search ON people USING gin(search_vector);

-- ---------------------------------------------------------------------------
-- 5.2 COMPANY_OFFICERS - Officer positions
-- ---------------------------------------------------------------------------
CREATE TABLE company_officers (
    officer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_id UUID NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    person_id UUID REFERENCES people(person_id),
    
    -- From filing
    filing_id UUID REFERENCES filings(filing_id),
    
    -- Position
    title TEXT NOT NULL,
    position_type TEXT,                 -- 'officer', 'director', 'both'
    is_ceo BOOLEAN DEFAULT false,
    is_cfo BOOLEAN DEFAULT false,
    is_chairman BOOLEAN DEFAULT false,
    
    -- Term
    appointed_date DATE,
    resigned_date DATE,
    is_current BOOLEAN DEFAULT true,
    
    -- Compensation (if disclosed)
    compensation_year INTEGER,
    total_compensation DECIMAL(16,2),
    salary DECIMAL(16,2),
    bonus DECIMAL(16,2),
    stock_awards DECIMAL(16,2),
    option_awards DECIMAL(16,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_company_officers_company ON company_officers(company_id);
CREATE INDEX idx_company_officers_person ON company_officers(person_id);
CREATE INDEX idx_company_officers_current ON company_officers(is_current) WHERE is_current;

-- ---------------------------------------------------------------------------
-- 5.3 INSIDER_TRANSACTIONS - Form 4 transactions
-- ---------------------------------------------------------------------------
CREATE TABLE insider_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    filing_id UUID REFERENCES filings(filing_id),
    company_id UUID NOT NULL REFERENCES companies(company_id),
    person_id UUID REFERENCES people(person_id),
    
    -- Insider Info
    insider_name TEXT NOT NULL,
    insider_title TEXT,
    is_director BOOLEAN,
    is_officer BOOLEAN,
    is_ten_percent_owner BOOLEAN,
    
    -- Transaction
    transaction_date DATE NOT NULL,
    transaction_code TEXT,              -- 'P', 'S', 'A', 'D', etc.
    transaction_type TEXT,              -- 'Buy', 'Sell', 'Grant', etc.
    
    -- Shares
    shares_transacted DECIMAL(16,4),
    price_per_share DECIMAL(16,4),
    total_value DECIMAL(20,2),
    shares_owned_after DECIMAL(16,4),
    
    -- Ownership
    ownership_type TEXT,                -- 'D' (direct), 'I' (indirect)
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insider_transactions_company ON insider_transactions(company_id);
CREATE INDEX idx_insider_transactions_person ON insider_transactions(person_id);
CREATE INDEX idx_insider_transactions_date ON insider_transactions(transaction_date DESC);
CREATE INDEX idx_insider_transactions_type ON insider_transactions(transaction_type);

-- ============================================================================
-- SECTION 6: SEARCH & DISCOVERY
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 6.1 SAVED_SEARCHES - User saved searches
-- ---------------------------------------------------------------------------
CREATE TABLE saved_searches (
    search_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Search Definition
    name TEXT NOT NULL,
    description TEXT,
    search_type TEXT NOT NULL,          -- 'company', 'filing', 'entity', 'universal'
    
    -- Query
    query_text TEXT,
    query_filters JSONB NOT NULL DEFAULT '{}',
    
    -- Usage
    is_pinned BOOLEAN DEFAULT false,
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_saved_searches_user ON saved_searches(user_id);

-- ---------------------------------------------------------------------------
-- 6.2 SEARCH_HISTORY - Search history
-- ---------------------------------------------------------------------------
CREATE TABLE search_history (
    history_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Search
    search_type TEXT NOT NULL,
    query_text TEXT,
    query_filters JSONB,
    result_count INTEGER,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_search_history_user ON search_history(user_id, created_at DESC);

-- ============================================================================
-- SECTION 7: USER DATA
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 7.1 WATCHLISTS - User watchlists
-- ---------------------------------------------------------------------------
CREATE TABLE watchlists (
    watchlist_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    name TEXT NOT NULL DEFAULT 'Default',
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_watchlists_user ON watchlists(user_id);

-- ---------------------------------------------------------------------------
-- 7.2 WATCHLIST_ITEMS - Companies in watchlists
-- ---------------------------------------------------------------------------
CREATE TABLE watchlist_items (
    watchlist_id UUID NOT NULL REFERENCES watchlists(watchlist_id) ON DELETE CASCADE,
    company_id UUID NOT NULL REFERENCES companies(company_id) ON DELETE CASCADE,
    
    -- Settings
    alert_on_filing BOOLEAN DEFAULT true,
    alert_on_insider BOOLEAN DEFAULT true,
    notes TEXT,
    
    -- Position Tracking (optional)
    shares_owned DECIMAL(16,4),
    cost_basis DECIMAL(16,4),
    
    added_at TIMESTAMPTZ DEFAULT NOW(),
    
    PRIMARY KEY (watchlist_id, company_id)
);

CREATE INDEX idx_watchlist_items_company ON watchlist_items(company_id);

-- ---------------------------------------------------------------------------
-- 7.3 USER_ALERTS - Custom alerts
-- ---------------------------------------------------------------------------
CREATE TABLE user_alerts (
    alert_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Alert Definition
    name TEXT NOT NULL,
    description TEXT,
    alert_type TEXT NOT NULL,           -- 'filing', 'insider', 'keyword', 'metric'
    enabled BOOLEAN DEFAULT true,
    
    -- Conditions
    conditions JSONB NOT NULL,
    
    -- Delivery
    delivery_channels TEXT[] DEFAULT ARRAY['in_app'],
    
    -- Stats
    triggered_count INTEGER DEFAULT 0,
    last_triggered_at TIMESTAMPTZ,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_alerts_user ON user_alerts(user_id);
CREATE INDEX idx_user_alerts_enabled ON user_alerts(enabled) WHERE enabled;

-- ---------------------------------------------------------------------------
-- 7.4 ALERT_TRIGGERS - Alert history
-- ---------------------------------------------------------------------------
CREATE TABLE alert_triggers (
    trigger_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id UUID NOT NULL REFERENCES user_alerts(alert_id) ON DELETE CASCADE,
    
    -- Trigger Info
    triggered_at TIMESTAMPTZ DEFAULT NOW(),
    trigger_reason TEXT,
    
    -- Related Records
    company_id UUID REFERENCES companies(company_id),
    filing_id UUID REFERENCES filings(filing_id),
    
    -- Status
    acknowledged BOOLEAN DEFAULT false,
    acknowledged_at TIMESTAMPTZ
);

CREATE INDEX idx_alert_triggers_alert ON alert_triggers(alert_id);
CREATE INDEX idx_alert_triggers_time ON alert_triggers(triggered_at DESC);

-- ---------------------------------------------------------------------------
-- 7.5 USER_NOTES - Notes on companies/filings
-- ---------------------------------------------------------------------------
CREATE TABLE user_notes (
    note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Target
    target_type TEXT NOT NULL,          -- 'company', 'filing', 'entity'
    company_id UUID REFERENCES companies(company_id),
    filing_id UUID REFERENCES filings(filing_id),
    entity_id UUID REFERENCES entities(entity_id),
    
    -- Content
    content TEXT NOT NULL,
    is_pinned BOOLEAN DEFAULT false,
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_user_notes_user ON user_notes(user_id);
CREATE INDEX idx_user_notes_company ON user_notes(company_id);
CREATE INDEX idx_user_notes_filing ON user_notes(filing_id);

-- ============================================================================
-- SECTION 8: AI & ANALYTICS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 8.1 AI_SUMMARIES - AI-generated summaries
-- ---------------------------------------------------------------------------
CREATE TABLE ai_summaries (
    summary_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Target
    target_type TEXT NOT NULL,          -- 'filing', 'section', 'company'
    filing_id UUID REFERENCES filings(filing_id),
    section_id UUID REFERENCES filing_sections(section_id),
    company_id UUID REFERENCES companies(company_id),
    
    -- Summary
    summary_type TEXT NOT NULL,         -- 'brief', 'detailed', 'key_points', 'risks'
    summary_text TEXT NOT NULL,
    key_points JSONB,
    
    -- Model
    model_name TEXT,
    model_version TEXT,
    
    -- Quality
    confidence DECIMAL(3,2),
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_summaries_filing ON ai_summaries(filing_id);
CREATE INDEX idx_ai_summaries_company ON ai_summaries(company_id);
CREATE INDEX idx_ai_summaries_type ON ai_summaries(summary_type);

-- ---------------------------------------------------------------------------
-- 8.2 AI_INSIGHTS - AI-generated insights
-- ---------------------------------------------------------------------------
CREATE TABLE ai_insights (
    insight_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Insight
    insight_type TEXT NOT NULL,         -- 'anomaly', 'trend', 'relationship', 'risk'
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    
    -- Related Entities
    company_ids UUID[],
    filing_ids UUID[],
    entity_ids UUID[],
    
    -- Importance
    importance_score DECIMAL(3,2),
    
    -- Status
    is_dismissed BOOLEAN DEFAULT false,
    
    -- Model
    model_name TEXT,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_ai_insights_type ON ai_insights(insight_type);
CREATE INDEX idx_ai_insights_created ON ai_insights(created_at DESC);

-- ---------------------------------------------------------------------------
-- 8.3 TRENDING - Trending companies/topics
-- ---------------------------------------------------------------------------
CREATE TABLE trending (
    trending_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Entity
    entity_type TEXT NOT NULL,          -- 'company', 'sector', 'keyword', 'form_type'
    entity_id TEXT NOT NULL,
    entity_name TEXT,
    
    -- Score
    score DECIMAL(10,4) NOT NULL,
    period TEXT NOT NULL,               -- 'hour', 'day', 'week'
    
    -- Context
    driver TEXT,                        -- What's driving the trend
    metadata JSONB DEFAULT '{}',
    
    calculated_at TIMESTAMPTZ DEFAULT NOW(),
    
    UNIQUE(entity_type, entity_id, period)
);

CREATE INDEX idx_trending_type ON trending(entity_type, period, score DESC);

-- ============================================================================
-- SECTION 9: DASHBOARDS & VIEWS
-- ============================================================================

-- ---------------------------------------------------------------------------
-- 9.1 DASHBOARDS - Custom dashboards
-- ---------------------------------------------------------------------------
CREATE TABLE dashboards (
    dashboard_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    
    -- Dashboard Info
    name TEXT NOT NULL,
    description TEXT,
    is_default BOOLEAN DEFAULT false,
    is_shared BOOLEAN DEFAULT false,
    
    -- Layout
    layout JSONB NOT NULL DEFAULT '{"widgets": []}',
    
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dashboards_user ON dashboards(user_id);

-- ---------------------------------------------------------------------------
-- 9.2 DASHBOARD_WIDGETS - Widget configurations
-- ---------------------------------------------------------------------------
CREATE TABLE dashboard_widgets (
    widget_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    dashboard_id UUID NOT NULL REFERENCES dashboards(dashboard_id) ON DELETE CASCADE,
    
    -- Widget Type
    widget_type TEXT NOT NULL,          -- 'watchlist', 'filings', 'chart', 'insights'
    
    -- Configuration
    config JSONB NOT NULL DEFAULT '{}',
    
    -- Position
    position_x INTEGER DEFAULT 0,
    position_y INTEGER DEFAULT 0,
    width INTEGER DEFAULT 1,
    height INTEGER DEFAULT 1,
    
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_dashboard_widgets_dashboard ON dashboard_widgets(dashboard_id);

-- ============================================================================
-- SECTION 10: TRIGGERS & FUNCTIONS
-- ============================================================================

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to tables
CREATE TRIGGER companies_updated_at BEFORE UPDATE ON companies FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER filings_updated_at BEFORE UPDATE ON filings FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER entities_updated_at BEFORE UPDATE ON entities FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER relationships_updated_at BEFORE UPDATE ON relationships FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER people_updated_at BEFORE UPDATE ON people FOR EACH ROW EXECUTE FUNCTION update_updated_at();
CREATE TRIGGER dashboards_updated_at BEFORE UPDATE ON dashboards FOR EACH ROW EXECUTE FUNCTION update_updated_at();

-- Update search vector for companies
CREATE OR REPLACE FUNCTION update_company_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = 
        setweight(to_tsvector('english', COALESCE(NEW.ticker, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(NEW.cik, '')), 'B') ||
        setweight(to_tsvector('english', COALESCE(NEW.description, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.sector, '')), 'C') ||
        setweight(to_tsvector('english', COALESCE(NEW.industry, '')), 'C');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER companies_search_vector 
    BEFORE INSERT OR UPDATE OF ticker, name, cik, description, sector, industry ON companies
    FOR EACH ROW EXECUTE FUNCTION update_company_search_vector();

-- Update search vector for entities
CREATE OR REPLACE FUNCTION update_entity_search_vector()
RETURNS TRIGGER AS $$
BEGIN
    NEW.search_vector = 
        setweight(to_tsvector('english', COALESCE(NEW.name, '')), 'A') ||
        setweight(to_tsvector('english', COALESCE(array_to_string(NEW.aliases, ' '), '')), 'B');
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER entities_search_vector 
    BEFORE INSERT OR UPDATE OF name, aliases ON entities
    FOR EACH ROW EXECUTE FUNCTION update_entity_search_vector();

-- ============================================================================
-- SECTION 11: VIEWS
-- ============================================================================

-- Recent filings with company info
CREATE OR REPLACE VIEW recent_filings_view AS
SELECT 
    f.filing_id,
    f.accession_number,
    f.form_type,
    f.filed_at,
    f.period_of_report,
    f.sec_url,
    c.company_id,
    c.cik,
    c.ticker,
    c.name as company_name,
    c.sector,
    c.industry,
    c.market_cap
FROM filings f
JOIN companies c ON c.company_id = f.company_id
ORDER BY f.filed_at DESC;

-- Company with latest metrics
CREATE OR REPLACE VIEW company_metrics_view AS
SELECT 
    c.*,
    (SELECT json_agg(json_build_object(
        'metric_name', fm.metric_name,
        'value', fm.metric_value,
        'period_end', fm.period_end,
        'yoy_change', fm.yoy_change
    ))
    FROM financial_metrics fm 
    WHERE fm.company_id = c.company_id 
    AND fm.period_type = 'ttm'
    ) as ttm_metrics
FROM companies c;

-- Entity with relationships count
CREATE OR REPLACE VIEW entity_overview AS
SELECT 
    e.*,
    (SELECT COUNT(*) FROM relationships r WHERE r.source_entity_id = e.entity_id) as outgoing_relationships,
    (SELECT COUNT(*) FROM relationships r WHERE r.target_entity_id = e.entity_id) as incoming_relationships,
    (SELECT COUNT(*) FROM entity_mentions em WHERE em.entity_id = e.entity_id) as mention_count
FROM entities e;

-- ============================================================================
-- END OF SCHEMA
-- ============================================================================
