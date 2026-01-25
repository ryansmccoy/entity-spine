/**
 * Entity Relationships Data - Boeing Ecosystem
 * Complete corporate hierarchy, supply chain, and relationships
 */

// ============================================================================
// TYPES
// ============================================================================

export interface EntityNode {
  id: string;
  name: string;
  type: 'company' | 'person' | 'fund' | 'government' | 'organization' | 'subsidiary';
  category?: string;
  description?: string;
  marketCap?: number;
  revenue?: number;
  employees?: number;
  founded?: number;
  headquarters?: string;
  incorporation?: string;
  cik?: string;
  lei?: string;
  ticker?: string;
  industry?: string;
  sector?: string;
  website?: string;
  parentId?: string;
  // Graph properties
  x?: number;
  y?: number;
  z?: number;
  vx?: number;
  vy?: number;
  vz?: number;
  fx?: number | null;
  fy?: number | null;
  fz?: number | null;
}

export interface RelationshipLink {
  source: string | EntityNode;
  target: string | EntityNode;
  type: 'owns' | 'supplies' | 'competes' | 'partners' | 'invests' | 'regulates' | 'employs' | 'licenses' | 'subsidiary' | 'customer';
  strength?: number;
  value?: number;
  ownership?: number;
  description?: string;
}

export interface GraphData {
  nodes: EntityNode[];
  links: RelationshipLink[];
}

export interface HierarchyEntity {
  id: string;
  name: string;
  relationship: 'Parent' | 'Subsidiary' | 'Related Entity' | 'Integrated' | 'Jointly Owned';
  incorporation?: string;
  industry?: string;
  industrySubGroup?: string;
  entityType?: string;
  ownership?: number;
  status?: 'active' | 'inactive';
  hasFinancials?: boolean;
  hasFilings?: boolean;
  children?: HierarchyEntity[];
}

export interface EntityIdentifier {
  scheme: string;
  value: string;
  source: string;
  confidence: number;
}

export interface SecurityListing {
  ticker: string;
  exchange: string;
  securityType: string;
  isin?: string;
  cusip?: string;
}

// ============================================================================
// BOEING ENTITY PROFILE
// ============================================================================

export const BOEING_PROFILE = {
  entityId: '01ARZ3NDEKTSV4RRFFQ69G5FAV',
  primaryName: 'The Boeing Company',
  legalName: 'The Boeing Co.',
  entityType: 'Public Company',
  status: 'Active',
  description: 'The Boeing Co. is an aerospace company, which engages in the manufacture of commercial jetliners and defense, space and security systems. It operates through the following segments: Commercial Airplanes, Defense, Space and Security, Global Services, and Boeing Capital.',
  
  identifiers: [
    { scheme: 'CIK', value: '0000012927', source: 'SEC EDGAR', confidence: 1.0 },
    { scheme: 'LEI', value: 'RVHJWBXLJ1RFUBSY1F30', source: 'GLEIF', confidence: 1.0 },
    { scheme: 'EIN', value: '91-0425694', source: 'IRS', confidence: 0.95 },
    { scheme: 'DUNS', value: '05-548-3743', source: 'D&B', confidence: 0.9 },
    { scheme: 'ISIN', value: 'US0970231058', source: 'Market Data', confidence: 1.0 },
    { scheme: 'CUSIP', value: '097023105', source: 'Market Data', confidence: 1.0 },
  ],
  
  listings: [
    { ticker: 'BA', exchange: 'NYSE', securityType: 'Common Stock', isin: 'US0970231058', cusip: '097023105' },
  ],
  
  headquarters: 'Arlington, VA',
  website: 'https://www.boeing.com',
  employees: 161100,
  founded: 1916,
  incorporation: 'Delaware',
  fiscalYearEnd: 'December',
  
  sector: 'Industrials',
  industry: 'Aerospace & Defense',
  subIndustry: 'Aerospace & Defense',
  sicCode: '3721',
  sicDescription: 'Aircraft',
  naicsCode: '336411',
  naicsDescription: 'Aircraft Manufacturing',
  
  financials: {
    marketCap: 127640000000,
    revenue: 77794000000,
    netIncome: -2222000000,
    totalAssets: 137012000000,
    totalDebt: 52334000000,
    cash: 12691000000,
  },
  
  keyStats: {
    '52WeekHigh': 391.00,
    '52WeekLow': 89.00,
    avgVolume: 27685018,
    sharesOutstanding: 564300000,
    floatPercent: 99.8,
    institutionalOwnership: 66.8,
    dividendYield: 0,
  },
};

// ============================================================================
// BOEING CORPORATE HIERARCHY
// ============================================================================

export const BOEING_HIERARCHY: HierarchyEntity = {
  id: 'boeing',
  name: 'The Boeing Company',
  relationship: 'Parent',
  incorporation: 'United States (DE)',
  industry: 'Aerospace & Defense',
  industrySubGroup: 'Aerospace & Defense',
  entityType: 'Public Company',
  hasFinancials: true,
  hasFilings: true,
  children: [
    {
      id: 'bca',
      name: 'Boeing Commercial Airplanes',
      relationship: 'Subsidiary',
      incorporation: 'United States (WA)',
      industry: 'Aerospace',
      industrySubGroup: 'Commercial Aviation',
      hasFilings: true,
      children: [
        { id: 'bca-aus', name: 'Boeing Aerostructures Australia', relationship: 'Subsidiary', incorporation: 'Australia', industry: 'Aerospace' },
        { id: 'bca-shanghai', name: 'Boeing Shanghai Aviation Services', relationship: 'Subsidiary', incorporation: 'China', industry: 'Aviation Services' },
        { id: 'bca-tianjin', name: 'Boeing Tianjin Composites', relationship: 'Subsidiary', incorporation: 'China', industry: 'Manufacturing' },
        { id: 'bca-canada', name: 'Boeing Canada Operations Ltd', relationship: 'Subsidiary', incorporation: 'Canada', industry: 'Aerospace', children: [
          { id: 'bca-winnipeg', name: 'Boeing Winnipeg', relationship: 'Subsidiary', incorporation: 'Canada (MB)', industry: 'Aerospace' },
        ]},
      ],
    },
    {
      id: 'bds',
      name: 'Boeing Defense, Space & Security',
      relationship: 'Subsidiary',
      incorporation: 'United States (MO)',
      industry: 'Defense',
      industrySubGroup: 'Defense Systems',
      hasFilings: true,
      children: [
        { id: 'insitu', name: 'Insitu Inc.', relationship: 'Subsidiary', incorporation: 'United States (WA)', industry: 'Defense', industrySubGroup: 'Unmanned Systems' },
        { id: 'spectrolab', name: 'Spectrolab Inc.', relationship: 'Subsidiary', incorporation: 'United States (CA)', industry: 'Aerospace', industrySubGroup: 'Space Systems' },
        { id: 'tapestry', name: 'Tapestry Solutions Inc.', relationship: 'Subsidiary', incorporation: 'United States (CA)', industry: 'Defense', industrySubGroup: 'Software' },
        { id: 'millennium', name: 'Millennium Space Systems', relationship: 'Subsidiary', incorporation: 'United States (CA)', industry: 'Aerospace', industrySubGroup: 'Satellites' },
        { id: 'aurora', name: 'Aurora Flight Sciences', relationship: 'Subsidiary', incorporation: 'United States (VA)', industry: 'Aerospace', industrySubGroup: 'R&D' },
      ],
    },
    {
      id: 'bgs',
      name: 'Boeing Global Services',
      relationship: 'Subsidiary',
      incorporation: 'United States (TX)',
      industry: 'Aviation Services',
      hasFilings: true,
      children: [
        { id: 'aviall', name: 'Aviall Services Inc.', relationship: 'Subsidiary', incorporation: 'United States (TX)', industry: 'Distribution' },
        { id: 'jeppesen', name: 'Jeppesen Sanderson Inc.', relationship: 'Subsidiary', incorporation: 'United States (CO)', industry: 'Aviation Services', industrySubGroup: 'Navigation' },
        { id: 'kgss', name: 'KLX Aerospace Solutions', relationship: 'Subsidiary', incorporation: 'United States (FL)', industry: 'Distribution' },
      ],
    },
    {
      id: 'bcc',
      name: 'Boeing Capital Corporation',
      relationship: 'Subsidiary',
      incorporation: 'United States (DE)',
      industry: 'Financial Services',
      industrySubGroup: 'Aircraft Leasing',
      hasFilings: true,
    },
    {
      id: 'boeing-intl',
      name: 'Boeing International Corporation',
      relationship: 'Subsidiary',
      incorporation: 'United States (DE)',
      industry: 'Holding Company',
      children: [
        { id: 'boeing-uk', name: 'Boeing UK Ltd', relationship: 'Subsidiary', incorporation: 'United Kingdom', industry: 'Aerospace' },
        { id: 'boeing-de', name: 'Boeing Deutschland GmbH', relationship: 'Subsidiary', incorporation: 'Germany', industry: 'Aerospace' },
        { id: 'boeing-india', name: 'Boeing India Private Ltd', relationship: 'Subsidiary', incorporation: 'India', industry: 'Aerospace' },
        { id: 'boeing-japan', name: 'Boeing Japan KK', relationship: 'Subsidiary', incorporation: 'Japan', industry: 'Aerospace' },
        { id: 'boeing-aus', name: 'Boeing Australia Holdings', relationship: 'Subsidiary', incorporation: 'Australia', industry: 'Aerospace' },
        { id: 'boeing-china', name: 'Boeing China Co. Ltd', relationship: 'Subsidiary', incorporation: 'China', industry: 'Aerospace' },
      ],
    },
  ],
};

// ============================================================================
// BOEING ECOSYSTEM GRAPH DATA
// ============================================================================

export const BOEING_ECOSYSTEM: GraphData = {
  nodes: [
    // Boeing Parent
    { id: 'boeing', name: 'The Boeing Company', type: 'company', category: 'aerospace', description: 'Global aerospace company', marketCap: 127640000000, revenue: 77794000000, employees: 161100, founded: 1916, headquarters: 'Arlington, VA', ticker: 'BA', cik: '0000012927', lei: 'RVHJWBXLJ1RFUBSY1F30', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'boeing.com' },
    
    // Boeing Subsidiaries
    { id: 'bca', name: 'Boeing Commercial Airplanes', type: 'subsidiary', category: 'commercial', description: 'Commercial aircraft division', revenue: 32255000000, employees: 50000, headquarters: 'Renton, WA', parentId: 'boeing' },
    { id: 'bds', name: 'Boeing Defense, Space & Security', type: 'subsidiary', category: 'defense', description: 'Defense and space systems', revenue: 26227000000, employees: 45000, headquarters: 'St. Louis, MO', parentId: 'boeing' },
    { id: 'bgs', name: 'Boeing Global Services', type: 'subsidiary', category: 'services', description: 'Aviation services and support', revenue: 18466000000, employees: 25000, headquarters: 'Dallas, TX', parentId: 'boeing' },
    { id: 'bcc', name: 'Boeing Capital Corporation', type: 'subsidiary', category: 'finance', description: 'Aircraft financing', headquarters: 'Chicago, IL', parentId: 'boeing' },
    
    // BCA Subsidiaries
    { id: 'insitu', name: 'Insitu Inc.', type: 'subsidiary', category: 'defense', description: 'Unmanned aircraft systems', employees: 1000, headquarters: 'Bingen, WA', parentId: 'bds' },
    { id: 'aurora', name: 'Aurora Flight Sciences', type: 'subsidiary', category: 'defense', description: 'Autonomous systems R&D', employees: 600, headquarters: 'Manassas, VA', parentId: 'bds' },
    { id: 'spectrolab', name: 'Spectrolab Inc.', type: 'subsidiary', category: 'space', description: 'Solar cells for spacecraft', employees: 500, headquarters: 'Sylmar, CA', parentId: 'bds' },
    { id: 'jeppesen', name: 'Jeppesen', type: 'subsidiary', category: 'services', description: 'Navigation and flight planning', employees: 3000, headquarters: 'Englewood, CO', parentId: 'bgs' },
    { id: 'aviall', name: 'Aviall Services', type: 'subsidiary', category: 'services', description: 'Aircraft parts distribution', employees: 2500, headquarters: 'Dallas, TX', parentId: 'bgs' },
    
    // Competitors
    { id: 'airbus', name: 'Airbus SE', type: 'company', category: 'aerospace', description: 'European aerospace company', marketCap: 135000000000, revenue: 65446000000, employees: 134000, founded: 1970, headquarters: 'Leiden, Netherlands', ticker: 'AIR.PA', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'airbus.com' },
    { id: 'lockheed', name: 'Lockheed Martin', type: 'company', category: 'defense', description: 'Defense and aerospace company', marketCap: 115000000000, revenue: 67571000000, employees: 116000, founded: 1995, headquarters: 'Bethesda, MD', ticker: 'LMT', cik: '0000936468', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'lockheedmartin.com' },
    { id: 'raytheon', name: 'RTX Corporation', type: 'company', category: 'defense', description: 'Aerospace and defense', marketCap: 145000000000, revenue: 68920000000, employees: 182000, founded: 2020, headquarters: 'Arlington, VA', ticker: 'RTX', cik: '0000101829', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'rtx.com' },
    { id: 'northrop', name: 'Northrop Grumman', type: 'company', category: 'defense', description: 'Defense technology company', marketCap: 72000000000, revenue: 39290000000, employees: 100500, founded: 1994, headquarters: 'Falls Church, VA', ticker: 'NOC', cik: '0001133421', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'northropgrumman.com' },
    { id: 'gd', name: 'General Dynamics', type: 'company', category: 'defense', description: 'Aerospace and defense', marketCap: 75000000000, revenue: 42272000000, employees: 106500, founded: 1952, headquarters: 'Reston, VA', ticker: 'GD', cik: '0000040533', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'gd.com' },
    { id: 'embraer', name: 'Embraer S.A.', type: 'company', category: 'aerospace', description: 'Brazilian aerospace manufacturer', marketCap: 5600000000, revenue: 4500000000, employees: 18000, founded: 1969, headquarters: 'São José dos Campos, Brazil', ticker: 'ERJ', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'embraer.com' },
    
    // Suppliers
    { id: 'ge-aerospace', name: 'GE Aerospace', type: 'company', category: 'supplier', description: 'Aircraft engines', marketCap: 175000000000, revenue: 32600000000, employees: 51000, headquarters: 'Evendale, OH', ticker: 'GE', cik: '0000040545', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'geaerospace.com' },
    { id: 'pratt', name: 'Pratt & Whitney', type: 'subsidiary', category: 'supplier', description: 'Aircraft engines (RTX subsidiary)', revenue: 22000000000, employees: 39000, headquarters: 'East Hartford, CT', parentId: 'raytheon' },
    { id: 'rolls', name: 'Rolls-Royce Holdings', type: 'company', category: 'supplier', description: 'Aircraft engines', marketCap: 56000000000, revenue: 16540000000, employees: 42000, founded: 1906, headquarters: 'London, UK', ticker: 'RR.L', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'rolls-royce.com' },
    { id: 'safran', name: 'Safran S.A.', type: 'company', category: 'supplier', description: 'Aerospace components and engines', marketCap: 85000000000, revenue: 23035000000, employees: 91500, founded: 2005, headquarters: 'Paris, France', ticker: 'SAF.PA', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'safran-group.com' },
    { id: 'honeywell', name: 'Honeywell Aerospace', type: 'subsidiary', category: 'supplier', description: 'Avionics and systems', revenue: 13800000000, employees: 40000, headquarters: 'Phoenix, AZ', parentId: 'honeywell-intl' },
    { id: 'honeywell-intl', name: 'Honeywell International', type: 'company', category: 'conglomerate', description: 'Diversified technology', marketCap: 132000000000, revenue: 36662000000, employees: 95000, headquarters: 'Charlotte, NC', ticker: 'HON', cik: '0000773840', industry: 'Industrial Conglomerates', sector: 'Industrials', website: 'honeywell.com' },
    { id: 'spirit', name: 'Spirit AeroSystems', type: 'company', category: 'supplier', description: 'Aerostructures manufacturer', marketCap: 3500000000, revenue: 5400000000, employees: 14000, founded: 2005, headquarters: 'Wichita, KS', ticker: 'SPR', cik: '0001364885', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'spiritaero.com' },
    { id: 'hexcel', name: 'Hexcel Corporation', type: 'company', category: 'supplier', description: 'Advanced composites', marketCap: 5000000000, revenue: 1580000000, employees: 5000, headquarters: 'Stamford, CT', ticker: 'HXL', cik: '0000717605', industry: 'Aerospace & Defense', sector: 'Industrials', website: 'hexcel.com' },
    
    // Major Airline Customers
    { id: 'united', name: 'United Airlines', type: 'company', category: 'customer', description: 'Major US airline', marketCap: 19000000000, revenue: 51289000000, employees: 99300, headquarters: 'Chicago, IL', ticker: 'UAL', cik: '0000100517', industry: 'Airlines', sector: 'Industrials', website: 'united.com' },
    { id: 'delta', name: 'Delta Air Lines', type: 'company', category: 'customer', description: 'Major US airline', marketCap: 30000000000, revenue: 54668000000, employees: 100000, headquarters: 'Atlanta, GA', ticker: 'DAL', cik: '0000027904', industry: 'Airlines', sector: 'Industrials', website: 'delta.com' },
    { id: 'american', name: 'American Airlines', type: 'company', category: 'customer', description: 'Major US airline', marketCap: 9000000000, revenue: 52788000000, employees: 129400, headquarters: 'Fort Worth, TX', ticker: 'AAL', cik: '0000006201', industry: 'Airlines', sector: 'Industrials', website: 'aa.com' },
    { id: 'southwest', name: 'Southwest Airlines', type: 'company', category: 'customer', description: 'Low-cost US airline', marketCap: 18000000000, revenue: 26091000000, employees: 72500, headquarters: 'Dallas, TX', ticker: 'LUV', cik: '0000092380', industry: 'Airlines', sector: 'Industrials', website: 'southwest.com' },
    { id: 'ryanair', name: 'Ryanair Holdings', type: 'company', category: 'customer', description: 'European low-cost airline', marketCap: 26000000000, revenue: 13444000000, employees: 21500, headquarters: 'Dublin, Ireland', ticker: 'RYAAY', industry: 'Airlines', sector: 'Industrials', website: 'ryanair.com' },
    { id: 'emirates', name: 'Emirates', type: 'company', category: 'customer', description: 'Dubai-based airline', revenue: 32600000000, employees: 102000, headquarters: 'Dubai, UAE', industry: 'Airlines', sector: 'Industrials', website: 'emirates.com' },
    
    // Government/Regulatory
    { id: 'faa', name: 'Federal Aviation Administration', type: 'government', category: 'regulator', description: 'US aviation safety regulator', headquarters: 'Washington, DC', website: 'faa.gov' },
    { id: 'dod', name: 'US Department of Defense', type: 'government', category: 'customer', description: 'US military procurement', headquarters: 'Washington, DC', website: 'defense.gov' },
    { id: 'nasa', name: 'NASA', type: 'government', category: 'customer', description: 'US space agency', employees: 18000, headquarters: 'Washington, DC', website: 'nasa.gov' },
    { id: 'easa', name: 'European Union Aviation Safety Agency', type: 'government', category: 'regulator', description: 'European aviation regulator', headquarters: 'Cologne, Germany', website: 'easa.europa.eu' },
    
    // Major Investors
    { id: 'vanguard', name: 'Vanguard Group', type: 'fund', category: 'investor', description: 'Largest institutional investor', employees: 19000, headquarters: 'Malvern, PA', website: 'vanguard.com' },
    { id: 'blackrock', name: 'BlackRock Inc', type: 'fund', category: 'investor', description: 'World\'s largest asset manager', marketCap: 115000000000, revenue: 17859000000, employees: 19800, headquarters: 'New York, NY', ticker: 'BLK', cik: '0001364742', website: 'blackrock.com' },
    { id: 'state-street', name: 'State Street Corp', type: 'fund', category: 'investor', description: 'Major institutional investor', marketCap: 27000000000, revenue: 12000000000, employees: 43000, headquarters: 'Boston, MA', ticker: 'STT', website: 'statestreet.com' },
    { id: 'newport', name: 'Newport Trust Company', type: 'fund', category: 'investor', description: 'Boeing pension fund trustee', headquarters: 'Wilmington, DE' },
    
    // Key Executives
    { id: 'calhoun', name: 'David Calhoun', type: 'person', category: 'executive', description: 'Former CEO of Boeing (2020-2024)' },
    { id: 'ortberg', name: 'Kelly Ortberg', type: 'person', category: 'executive', description: 'CEO of Boeing (2024-present)' },
    { id: 'kellner', name: 'Larry Kellner', type: 'person', category: 'executive', description: 'Chairman of the Board' },
    { id: 'west', name: 'Brian West', type: 'person', category: 'executive', description: 'CFO of Boeing' },
    
    // Joint Ventures
    { id: 'cfm', name: 'CFM International', type: 'organization', category: 'joint-venture', description: 'GE-Safran engine joint venture', revenue: 35000000000, employees: 15000, headquarters: 'Cincinnati, OH' },
    { id: 'ula', name: 'United Launch Alliance', type: 'organization', category: 'joint-venture', description: 'Boeing-Lockheed space launch JV', revenue: 2500000000, employees: 3500, headquarters: 'Centennial, CO' },
  ],
  
  links: [
    // Boeing ownership of subsidiaries
    { source: 'boeing', target: 'bca', type: 'owns', ownership: 100, description: 'Wholly owned subsidiary' },
    { source: 'boeing', target: 'bds', type: 'owns', ownership: 100, description: 'Wholly owned subsidiary' },
    { source: 'boeing', target: 'bgs', type: 'owns', ownership: 100, description: 'Wholly owned subsidiary' },
    { source: 'boeing', target: 'bcc', type: 'owns', ownership: 100, description: 'Wholly owned subsidiary' },
    { source: 'bds', target: 'insitu', type: 'owns', ownership: 100, description: 'Acquired 2008' },
    { source: 'bds', target: 'aurora', type: 'owns', ownership: 100, description: 'Acquired 2017' },
    { source: 'bds', target: 'spectrolab', type: 'owns', ownership: 100, description: 'Wholly owned subsidiary' },
    { source: 'bgs', target: 'jeppesen', type: 'owns', ownership: 100, description: 'Acquired 2000' },
    { source: 'bgs', target: 'aviall', type: 'owns', ownership: 100, description: 'Acquired 2006' },
    
    // Supplier relationships
    { source: 'ge-aerospace', target: 'boeing', type: 'supplies', strength: 0.95, description: 'Engine supplier for 737, 747, 777, 787' },
    { source: 'rolls', target: 'boeing', type: 'supplies', strength: 0.8, description: 'Engine supplier for 787, 777' },
    { source: 'pratt', target: 'boeing', type: 'supplies', strength: 0.5, description: 'Engine supplier (via RTX)' },
    { source: 'safran', target: 'boeing', type: 'supplies', strength: 0.7, description: 'Landing gear, nacelles' },
    { source: 'honeywell', target: 'boeing', type: 'supplies', strength: 0.8, description: 'Avionics, APUs, flight controls' },
    { source: 'spirit', target: 'boeing', type: 'supplies', strength: 0.95, description: 'Fuselage, nacelles for 737' },
    { source: 'hexcel', target: 'boeing', type: 'supplies', strength: 0.7, description: 'Composite materials' },
    { source: 'cfm', target: 'boeing', type: 'supplies', strength: 0.9, description: 'CFM56 and LEAP engines for 737' },
    
    // Customer relationships
    { source: 'boeing', target: 'united', type: 'customer', strength: 0.9, description: 'Major 737 MAX and 787 customer' },
    { source: 'boeing', target: 'delta', type: 'customer', strength: 0.85, description: 'Major wide-body customer' },
    { source: 'boeing', target: 'american', type: 'customer', strength: 0.85, description: 'Major 737 and 787 customer' },
    { source: 'boeing', target: 'southwest', type: 'customer', strength: 1.0, description: 'Exclusive 737 operator' },
    { source: 'boeing', target: 'ryanair', type: 'customer', strength: 1.0, description: 'Largest 737 MAX customer' },
    { source: 'boeing', target: 'emirates', type: 'customer', strength: 0.8, description: 'Major 777 customer' },
    { source: 'boeing', target: 'dod', type: 'customer', strength: 0.9, description: 'Defense contractor' },
    { source: 'boeing', target: 'nasa', type: 'customer', strength: 0.8, description: 'Space systems contractor' },
    
    // Competitive relationships
    { source: 'boeing', target: 'airbus', type: 'competes', strength: 1.0, description: 'Primary competitor in commercial aircraft' },
    { source: 'boeing', target: 'lockheed', type: 'competes', strength: 0.8, description: 'Competitor in defense contracts' },
    { source: 'boeing', target: 'northrop', type: 'competes', strength: 0.7, description: 'Competitor in defense programs' },
    { source: 'bds', target: 'lockheed', type: 'competes', strength: 0.9, description: 'Fighter jet competition' },
    { source: 'bds', target: 'northrop', type: 'competes', strength: 0.85, description: 'Bomber competition' },
    { source: 'bca', target: 'embraer', type: 'competes', strength: 0.4, description: 'Regional jet competition' },
    
    // Regulatory relationships
    { source: 'faa', target: 'boeing', type: 'regulates', strength: 1.0, description: 'Aircraft certification authority' },
    { source: 'easa', target: 'boeing', type: 'regulates', strength: 0.9, description: 'European certification' },
    
    // Investment relationships
    { source: 'vanguard', target: 'boeing', type: 'invests', strength: 0.5, value: 8.5, description: '~8.5% ownership' },
    { source: 'blackrock', target: 'boeing', type: 'invests', strength: 0.5, value: 6.2, description: '~6.2% ownership' },
    { source: 'state-street', target: 'boeing', type: 'invests', strength: 0.4, value: 4.1, description: '~4.1% ownership' },
    { source: 'newport', target: 'boeing', type: 'invests', strength: 0.4, value: 7.8, description: '~7.8% (employee pension)' },
    
    // Executive relationships
    { source: 'ortberg', target: 'boeing', type: 'employs', strength: 1.0, description: 'CEO' },
    { source: 'kellner', target: 'boeing', type: 'employs', strength: 0.9, description: 'Chairman' },
    { source: 'west', target: 'boeing', type: 'employs', strength: 0.9, description: 'CFO' },
    
    // Joint ventures
    { source: 'boeing', target: 'ula', type: 'owns', ownership: 50, description: '50% ownership with Lockheed' },
    { source: 'lockheed', target: 'ula', type: 'owns', ownership: 50, description: '50% ownership with Boeing' },
    { source: 'ge-aerospace', target: 'cfm', type: 'owns', ownership: 50, description: '50% with Safran' },
    { source: 'safran', target: 'cfm', type: 'owns', ownership: 50, description: '50% with GE' },
    
    // Partnership relationships
    { source: 'boeing', target: 'lockheed', type: 'partners', strength: 0.6, description: 'ULA joint venture partners' },
    { source: 'spirit', target: 'airbus', type: 'supplies', strength: 0.7, description: 'Also supplies to Airbus' },
    { source: 'ge-aerospace', target: 'airbus', type: 'supplies', strength: 0.8, description: 'Engine supplier to Airbus' },
    { source: 'rolls', target: 'airbus', type: 'supplies', strength: 0.85, description: 'Engine supplier to Airbus' },
    
    // Additional competitive/supply chain
    { source: 'raytheon', target: 'boeing', type: 'supplies', strength: 0.6, description: 'Defense systems supplier' },
    { source: 'raytheon', target: 'dod', type: 'customer', strength: 0.9, description: 'Defense contractor' },
    { source: 'lockheed', target: 'dod', type: 'customer', strength: 0.95, description: 'Largest defense contractor' },
    { source: 'northrop', target: 'dod', type: 'customer', strength: 0.9, description: 'Defense contractor' },
    { source: 'gd', target: 'dod', type: 'customer', strength: 0.9, description: 'Defense contractor' },
  ]
};

// ============================================================================
// COLOR SCHEMES
// ============================================================================

export const NODE_COLORS: Record<string, string> = {
  company: '#3B82F6',
  subsidiary: '#06B6D4',
  person: '#10B981',
  fund: '#F59E0B',
  government: '#EF4444',
  organization: '#8B5CF6'
};

export const CATEGORY_COLORS: Record<string, string> = {
  aerospace: '#3B82F6',
  commercial: '#0EA5E9',
  defense: '#DC2626',
  services: '#10B981',
  finance: '#F59E0B',
  space: '#8B5CF6',
  supplier: '#06B6D4',
  customer: '#14B8A6',
  regulator: '#EF4444',
  investor: '#F59E0B',
  executive: '#10B981',
  'joint-venture': '#EC4899',
  conglomerate: '#6366F1'
};

export const LINK_COLORS: Record<string, string> = {
  owns: '#F59E0B',
  subsidiary: '#F59E0B',
  supplies: '#3B82F6',
  competes: '#EF4444',
  partners: '#10B981',
  invests: '#F59E0B',
  regulates: '#8B5CF6',
  employs: '#6B7280',
  licenses: '#EC4899',
  customer: '#14B8A6'
};

// ============================================================================
// INDUSTRY STATISTICS
// ============================================================================

export const INDUSTRY_STATS = {
  totalEntities: 47,
  topIndustries: [
    { name: 'Aerospace & Defense', count: 18 },
    { name: 'Aviation Services', count: 8 },
    { name: 'Airlines', count: 6 },
    { name: 'Financial Services', count: 4 },
    { name: 'Government', count: 4 },
  ],
  incorporationRegions: [
    { region: 'United States', percent: 72 },
    { region: 'Europe', percent: 15 },
    { region: 'Asia Pacific', percent: 8 },
    { region: 'Other', percent: 5 },
  ],
  relationshipTypes: [
    { type: 'Ownership', count: 15 },
    { type: 'Supply Chain', count: 18 },
    { type: 'Customer', count: 10 },
    { type: 'Competition', count: 8 },
    { type: 'Investment', count: 5 },
  ],
};
