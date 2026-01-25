/**
 * EntitySpine API Client
 * 
 * Connects the frontend dashboard to the EntitySpine backend API.
 */

// Configuration
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

// Types matching the backend schemas
export interface EntityResponse {
  entity_id: string;
  primary_name: string;
  entity_type: string;
  status: string;
  source_system: string;
  source_id: string | null;
  cik: string | null;
  ticker: string | null;
  created_at: string | null;
  updated_at: string | null;
  metadata: Record<string, unknown>;
}

export interface ResolutionResponse {
  query: string;
  status: string;
  entity: EntityResponse | null;
  confidence: number;
  match_reason: string | null;
  tier: string;
  warnings: string[];
  elapsed_ms: number | null;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  depth: number;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface NetworkResponse {
  center_id: string;
  center_name: string | null;
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
  edge_count: number;
}

export interface SubsidiaryResponse {
  id: string;
  name: string;
  type: string;
}

export interface OfficerResponse {
  id: string;
  name: string;
  title: string | null;
  role_type: string;
  is_current: boolean;
  start_date: string | null;
  end_date: string | null;
}

export interface SearchResponse {
  query: string;
  results: EntityResponse[];
  total: number;
  limit: number;
  offset: number;
  elapsed_ms: number | null;
}

export interface HealthResponse {
  status: string;
  database: string;
  entities_count: number;
}

// API Client class
class EntitySpineAPI {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    return response.json();
  }

  // Health & Info
  async health(): Promise<HealthResponse> {
    return this.fetch('/health');
  }

  async info(): Promise<{ name: string; version: string; tier: string }> {
    return this.fetch('/info');
  }

  // Resolution
  async resolve(query: string, options?: { asOf?: string; mic?: string }): Promise<ResolutionResponse> {
    const params = new URLSearchParams();
    if (options?.asOf) params.set('as_of', options.asOf);
    if (options?.mic) params.set('mic', options.mic);
    const qs = params.toString() ? `?${params}` : '';
    return this.fetch(`/resolve/${encodeURIComponent(query)}${qs}`);
  }

  async batchResolve(queries: string[]): Promise<{ results: Record<string, ResolutionResponse> }> {
    return this.fetch('/resolve/batch', {
      method: 'POST',
      body: JSON.stringify({ queries }),
    });
  }

  // Entities
  async getEntityById(entityId: string): Promise<EntityResponse> {
    return this.fetch(`/entities/${entityId}`);
  }

  async getEntityByCik(cik: string): Promise<EntityResponse> {
    return this.fetch(`/entities/cik/${cik}`);
  }

  async getEntityByTicker(ticker: string, mic?: string): Promise<EntityResponse> {
    const qs = mic ? `?mic=${mic}` : '';
    return this.fetch(`/entities/ticker/${ticker}${qs}`);
  }

  // Search
  async search(query: string, options?: { limit?: number; offset?: number; entityType?: string }): Promise<SearchResponse> {
    const params = new URLSearchParams({ q: query });
    if (options?.limit) params.set('limit', String(options.limit));
    if (options?.offset) params.set('offset', String(options.offset));
    if (options?.entityType) params.set('entity_type', options.entityType);
    return this.fetch(`/search?${params}`);
  }

  // Graph
  async getNetwork(entityId: string, maxDepth: number = 2): Promise<NetworkResponse> {
    return this.fetch(`/graph/network/${entityId}?max_depth=${maxDepth}`);
  }

  async getSubsidiaries(entityId: string): Promise<{ parent_id: string; subsidiaries: SubsidiaryResponse[]; count: number }> {
    return this.fetch(`/graph/subsidiaries/${entityId}`);
  }

  async getOfficers(entityId: string, currentOnly: boolean = true): Promise<{ company_id: string; officers: OfficerResponse[]; count: number }> {
    return this.fetch(`/graph/officers/${entityId}?current_only=${currentOnly}`);
  }

  async findPath(sourceId: string, targetId: string, maxDepth: number = 5): Promise<{
    source: string;
    target: string;
    found: boolean;
    path: Array<{ id: string; name: string; relationship: string | null }>;
    distance: number;
  }> {
    return this.fetch(`/graph/path?source=${sourceId}&target=${targetId}&max_depth=${maxDepth}`);
  }

  // Conversion
  async convert(value: string, fromScheme: string, toScheme: string): Promise<{
    from_scheme: string;
    from_value: string;
    to_scheme: string;
    to_value: string | null;
    entity_id: string;
    entity_name: string;
  }> {
    return this.fetch(`/convert?value=${encodeURIComponent(value)}&from_scheme=${fromScheme}&to_scheme=${toScheme}`);
  }
}

// Export singleton instance
export const api = new EntitySpineAPI();

// Export class for custom configuration
export { EntitySpineAPI };

// Helper to check API connectivity
export async function checkAPIConnection(): Promise<boolean> {
  try {
    const health = await api.health();
    return health.status === 'healthy';
  } catch {
    return false;
  }
}
