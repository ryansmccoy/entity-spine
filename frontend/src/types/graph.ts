/**
 * Graph types mirroring EntitySpine's domain models
 * 
 * These TypeScript types align with:
 * - entityspine/src/entityspine/domain/enums.py (RelationshipType)
 * - entityspine/src/entityspine/domain/graph.py (Relationship, NodeRef)
 * 
 * When Python backend is available, these will be the API contract.
 */

// =============================================================================
// RELATIONSHIP TYPES (mirrors EntitySpine RelationshipType enum)
// =============================================================================

export type RelationshipType =
  // Corporate structure
  | 'parent'
  | 'subsidiary'
  | 'affiliate'
  | 'successor'
  | 'predecessor'
  // Business relationships  
  | 'customer'
  | 'supplier'
  | 'vendor'
  | 'partner'
  | 'competitor'
  // Financial relationships
  | 'investor'
  | 'investee'
  | 'lender'
  | 'borrower'
  | 'guarantor'
  | 'beneficial_owner_of'
  // Service relationships
  | 'auditor'
  | 'counsel'
  | 'underwriter'
  | 'advisor'
  // Employment/Position
  | 'officer_of'
  | 'director_of'
  | 'employed_by'
  // Industry-specific
  | 'foundry'
  | 'licensor';

// Grouped for UI display
export const RELATIONSHIP_GROUPS = {
  corporate: ['parent', 'subsidiary', 'affiliate', 'successor', 'predecessor'],
  business: ['customer', 'supplier', 'vendor', 'partner', 'competitor'],
  financial: ['investor', 'investee', 'lender', 'borrower', 'guarantor', 'beneficial_owner_of'],
  service: ['auditor', 'counsel', 'underwriter', 'advisor'],
  employment: ['officer_of', 'director_of', 'employed_by'],
  industry: ['foundry', 'licensor'],
} as const;

// =============================================================================
// ENTITY TYPES
// =============================================================================

export type EntityType =
  | 'public_company'
  | 'private_company'
  | 'subsidiary'
  | 'investor'
  | 'startup'
  | 'foundry'
  | 'equipment'
  | 'hyperscaler'
  | 'person'
  | 'government'
  | 'exchange';

export type EntityCategory =
  | 'design'
  | 'manufacturing'
  | 'equipment'
  | 'memory'
  | 'customer'
  | 'investor'
  | 'ip';

// =============================================================================
// NODE REFERENCE (mirrors EntitySpine NodeRef)
// =============================================================================

export interface NodeRef {
  node_type: string;
  node_id: string;
}

// =============================================================================
// ENTITY (Node in graph)
// =============================================================================

export interface EntityIdentifiers {
  cik?: string;
  ticker?: string;
  lei?: string;
  isin?: string;
  cusip?: string;
}

export interface EntityMetrics {
  marketCapB?: number;      // Market cap in billions USD
  revenueB?: number;        // Annual revenue in billions USD
  employees?: number;       // Employee count
  grossMargin?: number;     // Gross margin percentage
  yoyGrowth?: number;       // Year-over-year revenue growth %
  peRatio?: number;         // Price to earnings
  debtToEquity?: number;    // Debt to equity ratio
}

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
  
  // Force graph positioning (set at runtime)
  x?: number;
  y?: number;
  z?: number;
  fx?: number | null;
  fy?: number | null;
  fz?: number | null;
}

// =============================================================================
// RELATIONSHIP (Edge in graph - mirrors EntitySpine Relationship)
// =============================================================================

export interface Relationship {
  id?: string;                       // ULID
  source: string | EntityNode;       // Source node ID or object
  target: string | EntityNode;       // Target node ID or object
  type: RelationshipType;
  label?: string;                    // Display label
  subtype?: string;                  // Finer classification
  
  // Temporal validity
  validFrom?: string;                // ISO date when relationship started
  validTo?: string;                  // ISO date when relationship ended
  
  // Evidence & confidence
  confidence?: number;               // 0.0 - 1.0
  evidenceFilingId?: string;         // FK to SEC filing
  evidenceSnippet?: string;          // Short excerpt
  
  // Metadata
  metadata?: Record<string, unknown>;
}

// =============================================================================
// GRAPH DATA STRUCTURE
// =============================================================================

export interface GraphData {
  nodes: EntityNode[];
  links: Relationship[];
}

// =============================================================================
// API RESPONSE TYPES
// =============================================================================

export interface GraphQueryParams {
  entityIds?: string[];              // Specific entities to fetch
  centerEntityId?: string;           // Ego-centric graph around this entity
  depth?: number;                    // How many hops from center (default 2)
  relationshipTypes?: RelationshipType[];
  entityTypes?: EntityType[];
  minConfidence?: number;
  asOfDate?: string;                 // Point-in-time query
  includeMetrics?: boolean;
  limit?: number;
}

export interface GraphResponse {
  data: GraphData;
  totalNodes: number;
  totalEdges: number;
  truncated: boolean;
  queryTime: number;
}

// =============================================================================
// PATH FINDING (mirrors EntitySpine PathResult)
// =============================================================================

export interface PathResult {
  path: EntityNode[];
  edges: Relationship[];
  totalWeight: number;
  hops: number;
}

export interface PathFindingRequest {
  sourceId: string;
  targetId: string;
  maxHops?: number;
  allowedRelationships?: RelationshipType[];
  asOfDate?: string;
}

// =============================================================================
// NETWORK ANALYSIS (mirrors EntitySpine NetworkAnalysis)
// =============================================================================

export interface NetworkAnalysisResult {
  nodeCount: number;
  edgeCount: number;
  density: number;
  avgDegree: number;
  centralityScores: Record<string, number>;
  communities: Record<string, string[]>;
  influentialNodes: string[];
}

// =============================================================================
// UI STATE TYPES
// =============================================================================

export type SizeMetric = 'uniform' | 'marketCap' | 'revenue' | 'employees' | 'connections' | 'centrality';
export type ColorScheme = 'type' | 'category' | 'jurisdiction' | 'growth' | 'community';
export type LayoutAlgorithm = 'force' | 'hierarchical' | 'radial' | 'geographic';

export interface GraphViewState {
  colorBy: ColorScheme;
  sizeBy: SizeMetric;
  layout: LayoutAlgorithm;
  showLabels: boolean;
  showEdgeLabels: boolean;
  highlightedNodes: Set<string>;
  highlightedEdges: Set<string>;
  selectedNode: EntityNode | null;
  searchQuery: string;
  filters: GraphFilters;
}

export interface GraphFilters {
  entityTypes: EntityType[];
  relationshipTypes: RelationshipType[];
  categories: EntityCategory[];
  jurisdictions: string[];
  minMarketCap?: number;
  maxMarketCap?: number;
  minEmployees?: number;
  dateRange?: {
    start: string;
    end: string;
  };
}
