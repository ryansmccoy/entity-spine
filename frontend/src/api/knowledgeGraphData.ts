/**
 * Knowledge Graph Data Manager
 * 
 * Loads and manages entity, relationship, and metrics data.
 * Uses embedded JSON data (can be migrated to API/SQLite later).
 * 
 * Data structure:
 * - entities: Company/entity definitions
 * - relationships: Connections between entities
 * - metrics: Financial metrics (time-series)
 */

import type { EntityNode, Relationship, GraphData, EntityMetrics } from '../types/graph';

// =============================================================================
// TYPE DEFINITIONS (extend base types with JSON structure)
// =============================================================================

interface EntityJson {
  id: string;
  name: string;
  type: string;
  category: string;
  industry: string;
  sector?: string;
  jurisdiction: string;
  identifiers?: Record<string, string>;
  founded?: string;
  ipoDate?: string;
  headquarters?: {
    city: string;
    state?: string;
    country: string;
  };
  description?: string;
  tags?: string[];
  parentId?: string;
}

interface RelationshipJson {
  id: string;
  sourceId: string;
  targetId: string;
  type: string;
  label?: string;
  validFrom?: string;
  validTo?: string;
  value?: number;
  valueCurrency?: string;
  percentage?: number;
  metadata?: Record<string, unknown>;
}

interface MetricsJson {
  entityId: string;
  periodType: string;
  periodEnd: string;
  fiscalYear: number;
  fiscalQuarter?: number;
  valuation?: {
    marketCapB?: number;
    enterpriseValueB?: number;
    valuationB?: number;  // For private companies
  };
  incomeStatement?: {
    revenueB?: number;
    grossProfitB?: number;
    operatingIncomeB?: number;
    netIncomeB?: number;
  };
  margins?: {
    grossMargin?: number;
    operatingMargin?: number;
    netMargin?: number;
  };
  growth?: {
    revenueGrowthYoy?: number;
    epsGrowthYoy?: number;
  };
  balanceSheet?: {
    cashB?: number;
    totalDebtB?: number;
  };
  ratios?: {
    peRatio?: number | null;
    psRatio?: number;
    evToEbitda?: number;
  };
  operational?: {
    employees?: number;
    rndSpendB?: number;
    capexB?: number;
  };
  [key: string]: unknown;  // Allow industry-specific fields
}

// =============================================================================
// DATA TRANSFORMATION
// =============================================================================

/**
 * Transform JSON entity to EntityNode for graph visualization
 */
function transformEntity(json: EntityJson, metrics?: MetricsJson): EntityNode {
  // Get latest metrics if available
  const entityMetrics: EntityMetrics | undefined = metrics ? {
    marketCapB: metrics.valuation?.marketCapB ?? metrics.valuation?.valuationB,
    revenueB: metrics.incomeStatement?.revenueB,
    employees: metrics.operational?.employees,
    grossMargin: metrics.margins?.grossMargin,
    yoyGrowth: metrics.growth?.revenueGrowthYoy,
    peRatio: metrics.ratios?.peRatio ?? undefined,
  } : undefined;

  return {
    id: json.id,
    name: json.name,
    type: json.type as EntityNode['type'],
    category: json.category as EntityNode['category'],
    industry: json.industry,
    jurisdiction: json.jurisdiction,
    identifiers: json.identifiers ? {
      cik: json.identifiers.cik,
      ticker: json.identifiers.ticker,
      lei: json.identifiers.lei,
      isin: json.identifiers.isin,
    } : undefined,
    metrics: entityMetrics,
    metadata: {
      description: json.description,
      founded: json.founded,
      ipoDate: json.ipoDate,
      headquarters: json.headquarters,
      tags: json.tags,
      sector: json.sector,
    },
  };
}

/**
 * Transform JSON relationship to Relationship for graph visualization
 */
function transformRelationship(json: RelationshipJson): Relationship {
  return {
    id: json.id,
    source: json.sourceId,
    target: json.targetId,
    type: json.type as Relationship['type'],
    label: json.label,
    validFrom: json.validFrom,
    validTo: json.validTo,
    confidence: json.percentage ? json.percentage / 100 : undefined,
    metadata: {
      ...json.metadata,
      value: json.value,
      valueCurrency: json.valueCurrency,
      percentage: json.percentage,
    },
  };
}

// =============================================================================
// DATA MANAGER CLASS
// =============================================================================

class KnowledgeGraphDataManager {
  private entities: Map<string, EntityJson> = new Map();
  private relationships: RelationshipJson[] = [];
  private metrics: Map<string, MetricsJson[]> = new Map();
  private _initialized = false;
  private loadPromise: Promise<void> | null = null;

  constructor() {
    // Don't load in constructor - use async init
  }

  /**
   * Initialize by loading data from JSON files
   * Call this once at app startup
   */
  async init(): Promise<void> {
    if (this._initialized) return;
    if (this.loadPromise) return this.loadPromise;
    
    this.loadPromise = this.loadData();
    await this.loadPromise;
  }

  private async loadData(): Promise<void> {
    try {
      // Fetch JSON files at runtime
      const [entitiesRes, relationshipsRes, metricsRes] = await Promise.all([
        fetch('/data/entities.json'),
        fetch('/data/relationships.json'),
        fetch('/data/metrics.json'),
      ]);

      const entitiesData = await entitiesRes.json();
      const relationshipsData = await relationshipsRes.json();
      const metricsData = await metricsRes.json();

      // Load entities
      const entityList = entitiesData.entities as EntityJson[];
      entityList.forEach((e: EntityJson) => this.entities.set(e.id, e));

      // Load relationships
      this.relationships = relationshipsData.relationships as RelationshipJson[];

      // Load metrics (group by entity)
      const metricsList = metricsData.metrics as MetricsJson[];
      metricsList.forEach((m: MetricsJson) => {
        if (!this.metrics.has(m.entityId)) {
          this.metrics.set(m.entityId, []);
        }
        this.metrics.get(m.entityId)!.push(m);
      });

      this._initialized = true;
      console.log(`[KnowledgeGraph] Loaded ${this.entities.size} entities, ${this.relationships.length} relationships, ${this.metrics.size} metric series`);
    } catch (error) {
      console.error('[KnowledgeGraph] Failed to load data:', error);
      // Fall back to empty data
      this._initialized = true;
    }
  }

  get initialized(): boolean {
    return this._initialized;
  }

  /**
   * Get full graph data for visualization
   */
  getGraphData(): GraphData {
    const nodes: EntityNode[] = [];
    
    this.entities.forEach((entity, id) => {
      // Get latest metrics for this entity
      const entityMetrics = this.metrics.get(id);
      const latestMetrics = entityMetrics?.sort((a, b) => 
        new Date(b.periodEnd).getTime() - new Date(a.periodEnd).getTime()
      )[0];
      
      nodes.push(transformEntity(entity, latestMetrics));
    });

    const links = this.relationships
      .filter(r => this.entities.has(r.sourceId) && this.entities.has(r.targetId))
      .map(transformRelationship);

    return { nodes, links };
  }

  /**
   * Get entity by ID
   */
  getEntity(id: string): EntityNode | null {
    const entity = this.entities.get(id);
    if (!entity) return null;
    
    const metrics = this.getLatestMetrics(id);
    return transformEntity(entity, metrics);
  }

  /**
   * Get entities by filter
   */
  getEntities(filter?: {
    type?: string;
    category?: string;
    jurisdiction?: string;
    industry?: string;
  }): EntityNode[] {
    const result: EntityNode[] = [];
    
    this.entities.forEach((entity, id) => {
      // Apply filters
      if (filter?.type && entity.type !== filter.type) return;
      if (filter?.category && entity.category !== filter.category) return;
      if (filter?.jurisdiction && entity.jurisdiction !== filter.jurisdiction) return;
      if (filter?.industry && entity.industry !== filter.industry) return;
      
      const metrics = this.getLatestMetrics(id);
      result.push(transformEntity(entity, metrics));
    });
    
    return result;
  }

  /**
   * Get relationships for an entity
   */
  getRelationships(entityId: string, direction: 'all' | 'outgoing' | 'incoming' = 'all'): Relationship[] {
    return this.relationships
      .filter(r => {
        if (direction === 'outgoing') return r.sourceId === entityId;
        if (direction === 'incoming') return r.targetId === entityId;
        return r.sourceId === entityId || r.targetId === entityId;
      })
      .map(transformRelationship);
  }

  /**
   * Get relationships by type
   */
  getRelationshipsByType(type: string): Relationship[] {
    return this.relationships
      .filter(r => r.type === type)
      .map(transformRelationship);
  }

  /**
   * Get latest metrics for an entity
   */
  getLatestMetrics(entityId: string): MetricsJson | undefined {
    const entityMetrics = this.metrics.get(entityId);
    if (!entityMetrics || entityMetrics.length === 0) return undefined;
    
    return entityMetrics.sort((a, b) => 
      new Date(b.periodEnd).getTime() - new Date(a.periodEnd).getTime()
    )[0];
  }

  /**
   * Get metrics time series for an entity
   */
  getMetricsTimeSeries(entityId: string): MetricsJson[] {
    return this.metrics.get(entityId) || [];
  }

  /**
   * Get supply chain for an entity (upstream suppliers)
   */
  getSupplyChain(entityId: string, depth = 2): GraphData {
    const visited = new Set<string>();
    const nodes: EntityNode[] = [];
    const links: Relationship[] = [];
    
    const traverse = (id: string, currentDepth: number) => {
      if (currentDepth > depth || visited.has(id)) return;
      visited.add(id);
      
      const entity = this.getEntity(id);
      if (entity) nodes.push(entity);
      
      // Find suppliers (this entity is the target)
      const suppliers = this.relationships.filter(
        r => r.targetId === id && ['supplier', 'foundry', 'supplies_memory', 'supplies_equipment', 'licensor'].includes(r.type)
      );
      
      suppliers.forEach(rel => {
        links.push(transformRelationship(rel));
        traverse(rel.sourceId, currentDepth + 1);
      });
    };
    
    traverse(entityId, 0);
    return { nodes, links };
  }

  /**
   * Get customers for an entity (downstream)
   */
  getCustomers(entityId: string): GraphData {
    const nodes: EntityNode[] = [];
    const links: Relationship[] = [];
    
    // Find customers (this entity is the source)
    const customerRels = this.relationships.filter(
      r => r.sourceId === entityId && r.type === 'customer'
    );
    
    // Also find where this entity is a supplier
    const asSupplierRels = this.relationships.filter(
      r => r.targetId === entityId && ['supplier', 'foundry', 'supplies_memory'].includes(r.type)
    );
    
    const entityIds = new Set<string>();
    
    [...customerRels, ...asSupplierRels].forEach(rel => {
      links.push(transformRelationship(rel));
      entityIds.add(rel.sourceId);
      entityIds.add(rel.targetId);
    });
    
    entityIds.forEach(id => {
      const entity = this.getEntity(id);
      if (entity) nodes.push(entity);
    });
    
    return { nodes, links };
  }

  /**
   * Find path between two entities
   */
  findPath(sourceId: string, targetId: string, maxDepth = 5): {
    path: string[];
    relationships: Relationship[];
  } | null {
    const visited = new Set<string>();
    const queue: { id: string; path: string[]; rels: Relationship[] }[] = [
      { id: sourceId, path: [sourceId], rels: [] }
    ];
    
    while (queue.length > 0) {
      const current = queue.shift()!;
      
      if (current.id === targetId) {
        return { path: current.path, relationships: current.rels };
      }
      
      if (current.path.length > maxDepth || visited.has(current.id)) continue;
      visited.add(current.id);
      
      // Get all connected entities
      const connections = this.relationships.filter(
        r => r.sourceId === current.id || r.targetId === current.id
      );
      
      connections.forEach(rel => {
        const nextId = rel.sourceId === current.id ? rel.targetId : rel.sourceId;
        if (!visited.has(nextId)) {
          queue.push({
            id: nextId,
            path: [...current.path, nextId],
            rels: [...current.rels, transformRelationship(rel)],
          });
        }
      });
    }
    
    return null;
  }

  /**
   * Get industry statistics
   */
  getIndustryStats(): {
    industry: string;
    count: number;
    totalMarketCapB: number;
    totalRevenueB: number;
    avgGrowth: number;
  }[] {
    const byIndustry = new Map<string, {
      count: number;
      marketCaps: number[];
      revenues: number[];
      growths: number[];
    }>();
    
    this.entities.forEach((entity, id) => {
      const industry = entity.industry;
      if (!byIndustry.has(industry)) {
        byIndustry.set(industry, { count: 0, marketCaps: [], revenues: [], growths: [] });
      }
      
      const stats = byIndustry.get(industry)!;
      stats.count++;
      
      const metrics = this.getLatestMetrics(id);
      if (metrics) {
        if (metrics.valuation?.marketCapB) stats.marketCaps.push(metrics.valuation.marketCapB);
        if (metrics.incomeStatement?.revenueB) stats.revenues.push(metrics.incomeStatement.revenueB);
        if (metrics.growth?.revenueGrowthYoy) stats.growths.push(metrics.growth.revenueGrowthYoy);
      }
    });
    
    return Array.from(byIndustry.entries()).map(([industry, stats]) => ({
      industry,
      count: stats.count,
      totalMarketCapB: stats.marketCaps.reduce((a, b) => a + b, 0),
      totalRevenueB: stats.revenues.reduce((a, b) => a + b, 0),
      avgGrowth: stats.growths.length > 0
        ? stats.growths.reduce((a, b) => a + b, 0) / stats.growths.length
        : 0,
    })).sort((a, b) => b.totalMarketCapB - a.totalMarketCapB);
  }

  /**
   * Get jurisdiction statistics
   */
  getJurisdictionStats(): {
    jurisdiction: string;
    count: number;
    totalMarketCapB: number;
    companies: string[];
  }[] {
    const byJurisdiction = new Map<string, {
      count: number;
      marketCapB: number;
      companies: string[];
    }>();
    
    this.entities.forEach((entity, id) => {
      const jurisdiction = entity.jurisdiction;
      if (!byJurisdiction.has(jurisdiction)) {
        byJurisdiction.set(jurisdiction, { count: 0, marketCapB: 0, companies: [] });
      }
      
      const stats = byJurisdiction.get(jurisdiction)!;
      stats.count++;
      stats.companies.push(entity.name);
      
      const metrics = this.getLatestMetrics(id);
      if (metrics?.valuation?.marketCapB) {
        stats.marketCapB += metrics.valuation.marketCapB;
      }
    });
    
    return Array.from(byJurisdiction.entries()).map(([jurisdiction, stats]) => ({
      jurisdiction,
      count: stats.count,
      totalMarketCapB: stats.marketCapB,
      companies: stats.companies,
    })).sort((a, b) => b.totalMarketCapB - a.totalMarketCapB);
  }

  /**
   * Search entities by name or ticker
   */
  search(query: string): EntityNode[] {
    const lowerQuery = query.toLowerCase();
    const results: EntityNode[] = [];
    
    this.entities.forEach((entity, id) => {
      const nameMatch = entity.name.toLowerCase().includes(lowerQuery);
      const tickerMatch = entity.identifiers?.ticker?.toLowerCase() === lowerQuery;
      const idMatch = entity.id.toLowerCase().includes(lowerQuery);
      
      if (nameMatch || tickerMatch || idMatch) {
        const metrics = this.getLatestMetrics(id);
        results.push(transformEntity(entity, metrics));
      }
    });
    
    return results;
  }

  /**
   * Get summary statistics
   */
  getSummary(): {
    totalEntities: number;
    totalRelationships: number;
    totalMarketCapT: number;
    totalRevenueT: number;
    byType: Record<string, number>;
    byCategory: Record<string, number>;
    byRelationType: Record<string, number>;
  } {
    let totalMarketCap = 0;
    let totalRevenue = 0;
    const byType: Record<string, number> = {};
    const byCategory: Record<string, number> = {};
    
    this.entities.forEach((entity, id) => {
      byType[entity.type] = (byType[entity.type] || 0) + 1;
      byCategory[entity.category] = (byCategory[entity.category] || 0) + 1;
      
      const metrics = this.getLatestMetrics(id);
      if (metrics?.valuation?.marketCapB) totalMarketCap += metrics.valuation.marketCapB;
      if (metrics?.incomeStatement?.revenueB) totalRevenue += metrics.incomeStatement.revenueB;
    });
    
    const byRelationType: Record<string, number> = {};
    this.relationships.forEach(r => {
      byRelationType[r.type] = (byRelationType[r.type] || 0) + 1;
    });
    
    return {
      totalEntities: this.entities.size,
      totalRelationships: this.relationships.length,
      totalMarketCapT: totalMarketCap / 1000,
      totalRevenueT: totalRevenue / 1000,
      byType,
      byCategory,
      byRelationType,
    };
  }
}

// Export singleton instance
export const knowledgeGraph = new KnowledgeGraphDataManager();

// Export for direct access
export { KnowledgeGraphDataManager };
export type { EntityJson, RelationshipJson, MetricsJson };
