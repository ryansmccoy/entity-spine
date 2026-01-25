import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Entity {
  entity_id: string;
  primary_name: string;
  entity_type: string;
  jurisdiction?: string;
  source_system: string;
  source_id?: string;
  created_at: string;
  updated_at: string;
}

export interface IdentifierClaim {
  claim_id: string;
  entity_id: string;
  scheme: string;
  identifier: string;
  source_system: string;
  confidence: number;
  valid_from?: string;
  valid_to?: string;
}

export interface Relationship {
  relationship_id: string;
  from_entity_id: string;
  relationship_type: string;
  to_entity_id: string;
  source_system: string;
  confidence: number;
  start_date?: string;
  end_date?: string;
}

export interface SearchResult {
  entity: Entity;
  score: number;
  match_reason?: string;
}

export interface GraphNode {
  id: string;
  name: string;
  type: string;
  val: number;
}

export interface GraphLink {
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}

class EntitySpineAPI {
  // Health check
  async health() {
    const response = await api.get('/health');
    return response.data;
  }

  // Info
  async info() {
    const response = await api.get('/');
    return response.data;
  }

  // Search entities
  async searchEntities(query: string, limit: number = 10): Promise<SearchResult[]> {
    const response = await api.get('/search', {
      params: { q: query, limit },
    });
    return response.data.results;
  }

  // Get entity by ID
  async getEntity(entityId: string): Promise<Entity> {
    const response = await api.get(`/entities/${entityId}`);
    return response.data.entity;
  }

  // Get entity by identifier
  async getEntityByIdentifier(scheme: string, identifier: string): Promise<Entity> {
    const response = await api.get('/resolve', {
      params: { scheme, identifier },
    });
    return response.data.entity;
  }

  // Batch resolution
  async batchResolve(identifiers: Array<{ scheme: string; identifier: string }>) {
    const response = await api.post('/batch-resolve', { identifiers });
    return response.data.results;
  }

  // Get entity relationships
  async getEntityRelationships(entityId: string) {
    const response = await api.get(`/entities/${entityId}/relationships`);
    return response.data;
  }

  // Get entity network (knowledge graph)
  async getEntityNetwork(entityId: string, depth: number = 2): Promise<GraphData> {
    const response = await api.get(`/entities/${entityId}/network`, {
      params: { depth },
    });
    return response.data;
  }

  // Get entity identifiers
  async getEntityIdentifiers(entityId: string): Promise<IdentifierClaim[]> {
    const response = await api.get(`/entities/${entityId}/identifiers`);
    return response.data.identifiers;
  }

  // Database stats
  async getDatabaseStats() {
    const response = await api.get('/stats');
    return response.data;
  }

  // Load SEC data
  async loadSECData() {
    const response = await api.post('/admin/load-sec-data');
    return response.data;
  }
}

export default new EntitySpineAPI();
