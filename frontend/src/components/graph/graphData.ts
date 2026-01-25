/**
 * Shared Entity Graph Types & Data
 * 
 * Centralized types and mock data for the entity relationship graph.
 * Used by both EntityGraphPage and embedded graph components.
 */

// =============================================================================
// TYPES
// =============================================================================

export interface EntityNode {
  id: string;
  name: string;
  type: EntityType;
  category: EntityCategory;
  industry?: string;
  jurisdiction?: string;
  identifiers?: EntityIdentifiers;
  metrics?: EntityMetrics;
  metadata?: Record<string, unknown>;
  // Force graph positioning
  x?: number;
  y?: number;
  z?: number;
  fx?: number | null;
  fy?: number | null;
  fz?: number | null;
}

export type EntityType = 
  | 'public_company' 
  | 'private_company' 
  | 'subsidiary' 
  | 'investor' 
  | 'startup' 
  | 'foundry' 
  | 'equipment' 
  | 'hyperscaler';

export type EntityCategory = 
  | 'design' 
  | 'manufacturing' 
  | 'equipment' 
  | 'memory' 
  | 'customer' 
  | 'investor' 
  | 'ip';

export interface EntityIdentifiers {
  cik?: string;
  ticker?: string;
  lei?: string;
}

export interface EntityMetrics {
  marketCapB?: number;
  revenueB?: number;
  employees?: number;
  grossMargin?: number;
  yoyGrowth?: number;
}

export interface RelationshipLink {
  source: string | EntityNode;
  target: string | EntityNode;
  type: RelationshipType;
  label?: string;
  metadata?: Record<string, unknown>;
}

export type RelationshipType = 
  | 'parent' 
  | 'subsidiary' 
  | 'customer' 
  | 'supplier' 
  | 'foundry' 
  | 'competitor' 
  | 'investor' 
  | 'partner' 
  | 'licensor';

export interface GraphData {
  nodes: EntityNode[];
  links: RelationshipLink[];
}

export type SizeMetric = 'uniform' | 'marketCap' | 'revenue' | 'employees' | 'connections';
export type ColorMode = 'type' | 'category';

export interface GraphFilters {
  entityTypes: EntityType[];
  categories: EntityCategory[];
  relationshipTypes: RelationshipType[];
  jurisdictions: string[];
  searchQuery: string;
}

// =============================================================================
// COLOR SCHEMES
// =============================================================================

export const NODE_TYPE_COLORS: Record<EntityType, string> = {
  public_company: '#4CAF50',
  private_company: '#9E9E9E',
  subsidiary: '#795548',
  investor: '#FFC107',
  startup: '#E91E63',
  foundry: '#2196F3',
  equipment: '#FF5722',
  hyperscaler: '#9C27B0',
};

export const CATEGORY_COLORS: Record<EntityCategory, string> = {
  design: '#4CAF50',
  manufacturing: '#2196F3',
  equipment: '#FF5722',
  memory: '#00BCD4',
  customer: '#9C27B0',
  investor: '#FFC107',
  ip: '#FF9800',
};

export const LINK_COLORS: Record<RelationshipType, string> = {
  parent: '#795548',
  subsidiary: '#795548',
  customer: '#9C27B0',
  supplier: '#4CAF50',
  foundry: '#2196F3',
  competitor: '#F44336',
  investor: '#FFC107',
  partner: '#00BCD4',
  licensor: '#FF9800',
};

// =============================================================================
// SEMICONDUCTOR ECOSYSTEM DATA
// =============================================================================

export const SEMICONDUCTOR_ECOSYSTEM: GraphData = {
  nodes: [
    // === EDA TOOLS ===
    { id: 'synopsys', name: 'Synopsys', type: 'public_company', category: 'design', industry: 'EDA Software', jurisdiction: 'US', identifiers: { ticker: 'SNPS', cik: '0000883241' }, metrics: { marketCapB: 80, revenueB: 6.1, employees: 19000, grossMargin: 80, yoyGrowth: 15 } },
    { id: 'cadence', name: 'Cadence', type: 'public_company', category: 'design', industry: 'EDA Software', jurisdiction: 'US', identifiers: { ticker: 'CDNS', cik: '0000813672' }, metrics: { marketCapB: 75, revenueB: 4.1, employees: 11000, grossMargin: 89, yoyGrowth: 13 } },
    
    // === IP LICENSING ===
    { id: 'arm', name: 'ARM Holdings', type: 'public_company', category: 'ip', industry: 'IP Licensing', jurisdiction: 'GB', identifiers: { ticker: 'ARM', cik: '0001973239' }, metrics: { marketCapB: 150, revenueB: 3.2, employees: 6500, grossMargin: 96, yoyGrowth: 25 } },
    
    // === AI CHIP STARTUPS ===
    { id: 'cerebras', name: 'Cerebras Systems', type: 'startup', category: 'design', industry: 'AI Accelerators', jurisdiction: 'US', metrics: { employees: 400, revenueB: 0.08 }, metadata: { funding: '$4.1B', product: 'Wafer-scale AI chips' } },
    { id: 'groq', name: 'Groq', type: 'startup', category: 'design', industry: 'AI Accelerators', jurisdiction: 'US', metrics: { employees: 300, revenueB: 0.03 }, metadata: { product: 'LPU inference chips' } },
    { id: 'sambanova', name: 'SambaNova', type: 'startup', category: 'design', industry: 'AI Accelerators', jurisdiction: 'US', metrics: { employees: 500, revenueB: 0.1 }, metadata: { product: 'Reconfigurable dataflow' } },
    
    // === PUBLIC CHIP COMPANIES ===
    { id: 'nvidia', name: 'NVIDIA', type: 'public_company', category: 'design', industry: 'GPUs & AI', jurisdiction: 'US', identifiers: { ticker: 'NVDA', cik: '0001045810' }, metrics: { marketCapB: 3000, revenueB: 60.9, employees: 29600, grossMargin: 75, yoyGrowth: 126 } },
    { id: 'amd', name: 'AMD', type: 'public_company', category: 'design', industry: 'CPUs & GPUs', jurisdiction: 'US', identifiers: { ticker: 'AMD', cik: '0000002488' }, metrics: { marketCapB: 220, revenueB: 22.7, employees: 26000, grossMargin: 51, yoyGrowth: 4 } },
    { id: 'intel', name: 'Intel', type: 'public_company', category: 'design', industry: 'CPUs & Foundry', jurisdiction: 'US', identifiers: { ticker: 'INTC', cik: '0000050863' }, metrics: { marketCapB: 100, revenueB: 54.2, employees: 124800, grossMargin: 41, yoyGrowth: -14 } },
    { id: 'qualcomm', name: 'Qualcomm', type: 'public_company', category: 'design', industry: 'Mobile Chips', jurisdiction: 'US', identifiers: { ticker: 'QCOM', cik: '0000804328' }, metrics: { marketCapB: 190, revenueB: 38.6, employees: 51000, grossMargin: 56, yoyGrowth: -6 } },
    { id: 'apple', name: 'Apple', type: 'public_company', category: 'design', industry: 'Consumer Electronics', jurisdiction: 'US', identifiers: { ticker: 'AAPL', cik: '0000320193' }, metrics: { marketCapB: 3400, revenueB: 383, employees: 161000, grossMargin: 46, yoyGrowth: -3 } },
    { id: 'broadcom', name: 'Broadcom', type: 'public_company', category: 'design', industry: 'Networking & Storage', jurisdiction: 'US', identifiers: { ticker: 'AVGO', cik: '0001730168' }, metrics: { marketCapB: 700, revenueB: 35.8, employees: 20000, grossMargin: 75, yoyGrowth: 8 } },
    
    // === FOUNDRIES ===
    { id: 'tsmc', name: 'TSMC', type: 'foundry', category: 'manufacturing', industry: 'Semiconductor Foundry', jurisdiction: 'TW', identifiers: { ticker: 'TSM', cik: '0001046179' }, metrics: { marketCapB: 950, revenueB: 69.3, employees: 76000, grossMargin: 54, yoyGrowth: 26 }, metadata: { marketShare: '54%' } },
    { id: 'samsung', name: 'Samsung Foundry', type: 'foundry', category: 'manufacturing', industry: 'Semiconductor Foundry', jurisdiction: 'KR', identifiers: { ticker: '005930' }, metrics: { marketCapB: 350, revenueB: 15, employees: 270000, grossMargin: 45 }, metadata: { marketShare: '17%' } },
    { id: 'globalfoundries', name: 'GlobalFoundries', type: 'foundry', category: 'manufacturing', industry: 'Semiconductor Foundry', jurisdiction: 'US', identifiers: { ticker: 'GFS', cik: '0001840706' }, metrics: { marketCapB: 25, revenueB: 7.4, employees: 13000, grossMargin: 26, yoyGrowth: -9 } },
    { id: 'intel_foundry', name: 'Intel Foundry Services', type: 'subsidiary', category: 'manufacturing', industry: 'Semiconductor Foundry', jurisdiction: 'US', metrics: { revenueB: 0.9, employees: 15000 } },
    
    // === EQUIPMENT ===
    { id: 'asml', name: 'ASML', type: 'equipment', category: 'equipment', industry: 'Lithography', jurisdiction: 'NL', identifiers: { ticker: 'ASML', cik: '0000937966' }, metrics: { marketCapB: 360, revenueB: 27.6, employees: 42000, grossMargin: 51, yoyGrowth: 30 }, metadata: { product: 'EUV lithography (monopoly)' } },
    { id: 'applied_materials', name: 'Applied Materials', type: 'equipment', category: 'equipment', industry: 'Deposition & Etch', jurisdiction: 'US', identifiers: { ticker: 'AMAT', cik: '0000006951' }, metrics: { marketCapB: 155, revenueB: 26.5, employees: 34000, grossMargin: 47, yoyGrowth: 3 } },
    { id: 'lam', name: 'Lam Research', type: 'equipment', category: 'equipment', industry: 'Etch & Deposition', jurisdiction: 'US', identifiers: { ticker: 'LRCX', cik: '0000707549' }, metrics: { marketCapB: 110, revenueB: 14.9, employees: 17500, grossMargin: 48, yoyGrowth: -14 } },
    { id: 'kla', name: 'KLA', type: 'equipment', category: 'equipment', industry: 'Inspection & Metrology', jurisdiction: 'US', identifiers: { ticker: 'KLAC', cik: '0000319201' }, metrics: { marketCapB: 95, revenueB: 9.7, employees: 15000, grossMargin: 60, yoyGrowth: -5 } },
    
    // === MEMORY ===
    { id: 'sk_hynix', name: 'SK Hynix', type: 'public_company', category: 'memory', industry: 'DRAM & NAND', jurisdiction: 'KR', identifiers: { ticker: '000660' }, metrics: { marketCapB: 100, revenueB: 35, employees: 36000, grossMargin: 35, yoyGrowth: 32 }, metadata: { product: 'HBM leader' } },
    { id: 'micron', name: 'Micron', type: 'public_company', category: 'memory', industry: 'DRAM & NAND', jurisdiction: 'US', identifiers: { ticker: 'MU', cik: '0000723125' }, metrics: { marketCapB: 110, revenueB: 25.1, employees: 48000, grossMargin: 27, yoyGrowth: 62 } },
    
    // === HYPERSCALERS ===
    { id: 'microsoft', name: 'Microsoft', type: 'hyperscaler', category: 'customer', industry: 'Cloud & Software', jurisdiction: 'US', identifiers: { ticker: 'MSFT', cik: '0000789019' }, metrics: { marketCapB: 3100, revenueB: 245, employees: 228000, grossMargin: 70, yoyGrowth: 16 } },
    { id: 'google', name: 'Alphabet/Google', type: 'hyperscaler', category: 'customer', industry: 'Cloud & Advertising', jurisdiction: 'US', identifiers: { ticker: 'GOOGL', cik: '0001652044' }, metrics: { marketCapB: 2100, revenueB: 307, employees: 182000, grossMargin: 57, yoyGrowth: 9 } },
    { id: 'amazon', name: 'Amazon/AWS', type: 'hyperscaler', category: 'customer', industry: 'Cloud & E-Commerce', jurisdiction: 'US', identifiers: { ticker: 'AMZN', cik: '0001018724' }, metrics: { marketCapB: 1900, revenueB: 575, employees: 1540000, grossMargin: 47, yoyGrowth: 12 } },
    { id: 'meta', name: 'Meta', type: 'hyperscaler', category: 'customer', industry: 'Social Media & AI', jurisdiction: 'US', identifiers: { ticker: 'META', cik: '0001326801' }, metrics: { marketCapB: 1400, revenueB: 135, employees: 67000, grossMargin: 81, yoyGrowth: 16 } },
    
    // === INVESTORS ===
    { id: 'softbank', name: 'SoftBank', type: 'investor', category: 'investor', industry: 'Venture Capital', jurisdiction: 'JP', identifiers: { ticker: '9984' }, metrics: { marketCapB: 90, revenueB: 50, employees: 60000 } },
    { id: 'sequoia', name: 'Sequoia Capital', type: 'investor', category: 'investor', industry: 'Venture Capital', jurisdiction: 'US', metrics: { employees: 200 }, metadata: { aum: '$85B' } },
    { id: 'a16z', name: 'Andreessen Horowitz', type: 'investor', category: 'investor', industry: 'Venture Capital', jurisdiction: 'US', metrics: { employees: 500 }, metadata: { aum: '$35B' } },
  ],
  
  links: [
    // === FOUNDRY RELATIONSHIPS ===
    { source: 'nvidia', target: 'tsmc', type: 'foundry', label: '3nm/4nm' },
    { source: 'amd', target: 'tsmc', type: 'foundry', label: '5nm/4nm' },
    { source: 'apple', target: 'tsmc', type: 'foundry', label: '3nm' },
    { source: 'qualcomm', target: 'tsmc', type: 'foundry', label: '4nm' },
    { source: 'cerebras', target: 'tsmc', type: 'foundry', label: 'Wafer-scale' },
    { source: 'groq', target: 'globalfoundries', type: 'foundry', label: '14nm' },
    { source: 'intel', target: 'tsmc', type: 'foundry', label: 'N3B' },
    
    // === SUPPLY CHAIN ===
    { source: 'asml', target: 'tsmc', type: 'supplier', label: 'EUV' },
    { source: 'asml', target: 'samsung', type: 'supplier', label: 'EUV' },
    { source: 'asml', target: 'intel', type: 'supplier', label: 'High-NA EUV' },
    { source: 'applied_materials', target: 'tsmc', type: 'supplier', label: 'Deposition' },
    { source: 'lam', target: 'tsmc', type: 'supplier', label: 'Etch' },
    { source: 'kla', target: 'tsmc', type: 'supplier', label: 'Inspection' },
    { source: 'sk_hynix', target: 'nvidia', type: 'supplier', label: 'HBM3e' },
    { source: 'micron', target: 'nvidia', type: 'supplier', label: 'HBM3e' },
    { source: 'broadcom', target: 'apple', type: 'supplier', label: 'WiFi/BT' },
    { source: 'qualcomm', target: 'apple', type: 'supplier', label: '5G Modem' },
    
    // === CUSTOMER RELATIONSHIPS ===
    { source: 'microsoft', target: 'nvidia', type: 'customer', label: 'Azure AI' },
    { source: 'google', target: 'nvidia', type: 'customer', label: 'GCP AI' },
    { source: 'amazon', target: 'nvidia', type: 'customer', label: 'AWS AI' },
    { source: 'meta', target: 'nvidia', type: 'customer', label: 'AI Training' },
    
    // === IP LICENSING ===
    { source: 'arm', target: 'nvidia', type: 'licensor', label: 'ARM ISA' },
    { source: 'arm', target: 'qualcomm', type: 'licensor', label: 'ARM ISA' },
    { source: 'arm', target: 'apple', type: 'licensor', label: 'ARM ISA' },
    
    // === COMPETITION ===
    { source: 'nvidia', target: 'amd', type: 'competitor' },
    { source: 'nvidia', target: 'intel', type: 'competitor' },
    { source: 'intel', target: 'amd', type: 'competitor' },
    { source: 'tsmc', target: 'samsung', type: 'competitor' },
    { source: 'tsmc', target: 'intel_foundry', type: 'competitor' },
    { source: 'nvidia', target: 'cerebras', type: 'competitor' },
    { source: 'nvidia', target: 'groq', type: 'competitor' },
    
    // === OWNERSHIP & INVESTMENT ===
    { source: 'intel', target: 'intel_foundry', type: 'parent' },
    { source: 'softbank', target: 'arm', type: 'investor', metadata: { stake: '90%' } },
    { source: 'sequoia', target: 'cerebras', type: 'investor' },
    { source: 'sequoia', target: 'groq', type: 'investor' },
    { source: 'a16z', target: 'cerebras', type: 'investor' },
    
    // === PARTNERSHIPS ===
    { source: 'microsoft', target: 'nvidia', type: 'partner', label: 'AI Cloud' },
    
    // === EDA USAGE ===
    { source: 'nvidia', target: 'synopsys', type: 'customer' },
    { source: 'nvidia', target: 'cadence', type: 'customer' },
    { source: 'amd', target: 'synopsys', type: 'customer' },
    { source: 'apple', target: 'cadence', type: 'customer' },
  ],
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

export function getNodeColor(node: EntityNode, colorBy: ColorMode): string {
  return colorBy === 'type' ? NODE_TYPE_COLORS[node.type] : CATEGORY_COLORS[node.category];
}

export function getLinkColor(link: RelationshipLink): string {
  return LINK_COLORS[link.type] || '#999999';
}

export function getFlagEmoji(countryCode: string): string {
  const flags: Record<string, string> = {
    US: '🇺🇸', GB: '🇬🇧', TW: '🇹🇼', KR: '🇰🇷', JP: '🇯🇵',
    NL: '🇳🇱', BE: '🇧🇪', DE: '🇩🇪', CN: '🇨🇳',
  };
  return flags[countryCode] || '🌍';
}

export function getCountryName(countryCode: string): string {
  const names: Record<string, string> = {
    US: 'United States', GB: 'United Kingdom', TW: 'Taiwan', KR: 'South Korea',
    JP: 'Japan', NL: 'Netherlands', BE: 'Belgium', DE: 'Germany', CN: 'China',
  };
  return names[countryCode] || countryCode;
}

export function filterGraphData(
  data: GraphData,
  filters: Partial<GraphFilters>
): GraphData {
  let nodes = data.nodes;
  let links = data.links;
  
  // Filter by entity types
  if (filters.entityTypes && filters.entityTypes.length > 0) {
    nodes = nodes.filter(n => filters.entityTypes!.includes(n.type));
  }
  
  // Filter by categories
  if (filters.categories && filters.categories.length > 0) {
    nodes = nodes.filter(n => filters.categories!.includes(n.category));
  }
  
  // Filter by jurisdictions
  if (filters.jurisdictions && filters.jurisdictions.length > 0) {
    nodes = nodes.filter(n => n.jurisdiction && filters.jurisdictions!.includes(n.jurisdiction));
  }
  
  // Filter by search query
  if (filters.searchQuery) {
    const query = filters.searchQuery.toLowerCase();
    const matchingNodes = nodes.filter(n => 
      n.name.toLowerCase().includes(query) ||
      n.id.toLowerCase().includes(query) ||
      n.identifiers?.ticker?.toLowerCase().includes(query)
    );
    
    // Include connected nodes
    const matchingIds = new Set(matchingNodes.map(n => n.id));
    links.forEach(l => {
      const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
      const targetId = typeof l.target === 'string' ? l.target : l.target.id;
      if (matchingIds.has(sourceId) || matchingIds.has(targetId)) {
        matchingIds.add(sourceId);
        matchingIds.add(targetId);
      }
    });
    nodes = data.nodes.filter(n => matchingIds.has(n.id));
  }
  
  // Filter links to only include nodes that passed filters
  const nodeIds = new Set(nodes.map(n => n.id));
  links = links.filter(l => {
    const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
    const targetId = typeof l.target === 'string' ? l.target : l.target.id;
    return nodeIds.has(sourceId) && nodeIds.has(targetId);
  });
  
  // Filter by relationship types
  if (filters.relationshipTypes && filters.relationshipTypes.length > 0) {
    links = links.filter(l => filters.relationshipTypes!.includes(l.type));
  }
  
  return { nodes, links };
}

export function getConnectionCounts(links: RelationshipLink[]): Record<string, number> {
  const counts: Record<string, number> = {};
  links.forEach(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;
    counts[sourceId] = (counts[sourceId] || 0) + 1;
    counts[targetId] = (counts[targetId] || 0) + 1;
  });
  return counts;
}

export function getNodeRelationships(
  node: EntityNode, 
  data: GraphData
): Record<RelationshipType, Array<{ node: EntityNode; direction: 'in' | 'out'; label?: string }>> {
  const relationships: Record<string, Array<{ node: EntityNode; direction: 'in' | 'out'; label?: string }>> = {};
  
  data.links.forEach(link => {
    const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
    const targetId = typeof link.target === 'string' ? link.target : link.target.id;
    
    if (sourceId === node.id) {
      const targetNode = data.nodes.find(n => n.id === targetId);
      if (targetNode) {
        if (!relationships[link.type]) relationships[link.type] = [];
        relationships[link.type].push({ node: targetNode, direction: 'out', label: link.label });
      }
    } else if (targetId === node.id) {
      const sourceNode = data.nodes.find(n => n.id === sourceId);
      if (sourceNode) {
        if (!relationships[link.type]) relationships[link.type] = [];
        relationships[link.type].push({ node: sourceNode, direction: 'in', label: link.label });
      }
    }
  });
  
  return relationships as Record<RelationshipType, Array<{ node: EntityNode; direction: 'in' | 'out'; label?: string }>>;
}
