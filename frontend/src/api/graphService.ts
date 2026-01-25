/**
 * Graph Data Service
 * 
 * Provides graph data for visualization. Currently uses mock data
 * matching the semiconductor ecosystem. When Python backend is ready,
 * this will fetch from EntitySpine's GraphService API.
 * 
 * Backend endpoint would be: GET /api/graph
 * Using EntitySpine's GraphService for:
 * - get_relationships(entity_id)
 * - find_path(source_id, target_id)
 * - analyze_network(entity_ids)
 */

import { api } from './index';
import type {
  GraphData,
  GraphQueryParams,
  GraphResponse,
  PathFindingRequest,
  PathResult,
  NetworkAnalysisResult,
  EntityNode,
  Relationship,
} from '../types/graph';

// =============================================================================
// MOCK DATA - Semiconductor Ecosystem
// =============================================================================

const MOCK_NODES: EntityNode[] = [
  // === EDA TOOLS ===
  { id: 'synopsys', name: 'Synopsys', type: 'public_company', category: 'design', industry: 'EDA Software', jurisdiction: 'US', identifiers: { ticker: 'SNPS', cik: '0000883241' }, metrics: { marketCapB: 80, revenueB: 6.1, employees: 19000, grossMargin: 80, yoyGrowth: 15 } },
  { id: 'cadence', name: 'Cadence', type: 'public_company', category: 'design', industry: 'EDA Software', jurisdiction: 'US', identifiers: { ticker: 'CDNS', cik: '0000813672' }, metrics: { marketCapB: 75, revenueB: 4.1, employees: 11000, grossMargin: 89, yoyGrowth: 13 } },
  
  // === IP LICENSING ===
  { id: 'arm', name: 'ARM Holdings', type: 'public_company', category: 'ip', industry: 'IP Licensing', jurisdiction: 'GB', identifiers: { ticker: 'ARM', cik: '0001973239' }, metrics: { marketCapB: 150, revenueB: 3.2, employees: 6500, grossMargin: 96, yoyGrowth: 25 } },
  { id: 'arteris', name: 'Arteris', type: 'private_company', category: 'ip', industry: 'IP Licensing', jurisdiction: 'US', metrics: { revenueB: 0.05, employees: 200 } },
  
  // === AI CHIP STARTUPS ===
  { id: 'cerebras', name: 'Cerebras Systems', type: 'startup', category: 'design', industry: 'AI Accelerators', jurisdiction: 'US', metrics: { employees: 400, revenueB: 0.08 }, metadata: { funding: '$4.1B', product: 'Wafer-scale AI chips' } },
  { id: 'groq', name: 'Groq', type: 'startup', category: 'design', industry: 'AI Accelerators', jurisdiction: 'US', metrics: { employees: 300, revenueB: 0.03 }, metadata: { product: 'LPU inference chips' } },
  { id: 'sambanova', name: 'SambaNova', type: 'startup', category: 'design', industry: 'AI Accelerators', jurisdiction: 'US', metrics: { employees: 500, revenueB: 0.1 }, metadata: { product: 'Reconfigurable dataflow' } },
  { id: 'graphcore', name: 'Graphcore', type: 'startup', category: 'design', industry: 'AI Accelerators', jurisdiction: 'GB', metrics: { employees: 450, revenueB: 0.02 }, metadata: { product: 'IPU', status: 'Acquired by SoftBank' } },
  
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
  
  // === PACKAGING (OSAT) ===
  { id: 'ase', name: 'ASE Technology', type: 'public_company', category: 'manufacturing', industry: 'OSAT Packaging', jurisdiction: 'TW', identifiers: { ticker: 'ASX', cik: '0001132804' }, metrics: { marketCapB: 20, revenueB: 18.8, employees: 94000, grossMargin: 17, yoyGrowth: 4 } },
  { id: 'amkor', name: 'Amkor', type: 'public_company', category: 'manufacturing', industry: 'OSAT Packaging', jurisdiction: 'US', identifiers: { ticker: 'AMKR', cik: '0001047127' }, metrics: { marketCapB: 7, revenueB: 6.5, employees: 31000, grossMargin: 15, yoyGrowth: -5 } },
  
  // === MEMORY ===
  { id: 'sk_hynix', name: 'SK Hynix', type: 'public_company', category: 'memory', industry: 'DRAM & NAND', jurisdiction: 'KR', identifiers: { ticker: '000660' }, metrics: { marketCapB: 100, revenueB: 35, employees: 36000, grossMargin: 35, yoyGrowth: 32 }, metadata: { product: 'HBM leader' } },
  { id: 'micron', name: 'Micron', type: 'public_company', category: 'memory', industry: 'DRAM & NAND', jurisdiction: 'US', identifiers: { ticker: 'MU', cik: '0000723125' }, metrics: { marketCapB: 110, revenueB: 25.1, employees: 48000, grossMargin: 27, yoyGrowth: 62 } },
  
  // === HYPERSCALERS ===
  { id: 'microsoft', name: 'Microsoft', type: 'hyperscaler', category: 'customer', industry: 'Cloud & Software', jurisdiction: 'US', identifiers: { ticker: 'MSFT', cik: '0000789019' }, metrics: { marketCapB: 3100, revenueB: 245, employees: 228000, grossMargin: 70, yoyGrowth: 16 } },
  { id: 'google', name: 'Alphabet/Google', type: 'hyperscaler', category: 'customer', industry: 'Cloud & Advertising', jurisdiction: 'US', identifiers: { ticker: 'GOOGL', cik: '0001652044' }, metrics: { marketCapB: 2100, revenueB: 307, employees: 182000, grossMargin: 57, yoyGrowth: 9 } },
  { id: 'amazon', name: 'Amazon/AWS', type: 'hyperscaler', category: 'customer', industry: 'Cloud & E-Commerce', jurisdiction: 'US', identifiers: { ticker: 'AMZN', cik: '0001018724' }, metrics: { marketCapB: 1900, revenueB: 575, employees: 1540000, grossMargin: 47, yoyGrowth: 12 } },
  { id: 'meta', name: 'Meta', type: 'hyperscaler', category: 'customer', industry: 'Social Media & AI', jurisdiction: 'US', identifiers: { ticker: 'META', cik: '0001326801' }, metrics: { marketCapB: 1400, revenueB: 135, employees: 67000, grossMargin: 81, yoyGrowth: 16 } },
  
  // === PRIVATE AI COMPANIES ===
  { id: 'openai', name: 'OpenAI', type: 'private_company', category: 'customer', industry: 'AI Research', jurisdiction: 'US', metrics: { revenueB: 3.4, employees: 1500 }, metadata: { structure: 'Capped-profit' } },
  { id: 'anthropic', name: 'Anthropic', type: 'private_company', category: 'customer', industry: 'AI Research', jurisdiction: 'US', metrics: { revenueB: 0.8, employees: 800 }, metadata: { structure: 'Public Benefit Corp' } },
  
  // === INVESTORS ===
  { id: 'softbank', name: 'SoftBank', type: 'investor', category: 'investor', industry: 'Venture Capital', jurisdiction: 'JP', identifiers: { ticker: '9984' }, metrics: { marketCapB: 90, revenueB: 50, employees: 60000 } },
  { id: 'sequoia', name: 'Sequoia Capital', type: 'investor', category: 'investor', industry: 'Venture Capital', jurisdiction: 'US', metrics: { employees: 200 }, metadata: { aum: '$85B' } },
  { id: 'a16z', name: 'Andreessen Horowitz', type: 'investor', category: 'investor', industry: 'Venture Capital', jurisdiction: 'US', metrics: { employees: 500 }, metadata: { aum: '$35B' } },
  
  // === R&D / JVs ===
  { id: 'imec', name: 'IMEC', type: 'private_company', category: 'design', industry: 'R&D Consortium', jurisdiction: 'BE', metrics: { revenueB: 0.9, employees: 5500 }, metadata: { type: 'R&D consortium' } },
  { id: 'rapidus', name: 'Rapidus', type: 'private_company', category: 'manufacturing', industry: 'Semiconductor Foundry', jurisdiction: 'JP', metrics: { employees: 400 }, metadata: { type: 'JV for 2nm' } },
];

const MOCK_LINKS: Relationship[] = [
  // === FOUNDRY RELATIONSHIPS ===
  { source: 'nvidia', target: 'tsmc', type: 'foundry', label: '3nm/4nm', validFrom: '2020-01-01', metadata: { nodes: ['3nm', '4nm'], exclusive: true } },
  { source: 'amd', target: 'tsmc', type: 'foundry', label: '5nm/4nm', validFrom: '2019-01-01', metadata: { nodes: ['5nm', '4nm'] } },
  { source: 'apple', target: 'tsmc', type: 'foundry', label: '3nm', validFrom: '2014-01-01', metadata: { nodes: ['3nm'], products: ['M-series', 'A-series'] } },
  { source: 'qualcomm', target: 'tsmc', type: 'foundry', label: '4nm', validFrom: '2021-01-01', metadata: { nodes: ['4nm'] } },
  { source: 'cerebras', target: 'tsmc', type: 'foundry', label: 'Wafer-scale', validFrom: '2019-01-01', metadata: { special: 'Wafer-scale' } },
  { source: 'groq', target: 'globalfoundries', type: 'foundry', label: '14nm', validFrom: '2020-01-01', metadata: { node: '14nm' } },
  { source: 'intel', target: 'tsmc', type: 'foundry', label: 'N3B', validFrom: '2023-01-01', metadata: { note: 'Competitor using competitor!' } },
  
  // === SUPPLY CHAIN ===
  { source: 'asml', target: 'tsmc', type: 'supplier', label: 'EUV', validFrom: '2017-01-01', metadata: { product: 'EUV lithography' } },
  { source: 'asml', target: 'samsung', type: 'supplier', label: 'EUV', validFrom: '2018-01-01', metadata: { product: 'EUV lithography' } },
  { source: 'asml', target: 'intel', type: 'supplier', label: 'High-NA EUV', validFrom: '2024-01-01', metadata: { product: 'High-NA EUV' } },
  { source: 'applied_materials', target: 'tsmc', type: 'supplier', label: 'Deposition', validFrom: '2010-01-01' },
  { source: 'applied_materials', target: 'samsung', type: 'supplier', label: 'Deposition', validFrom: '2010-01-01' },
  { source: 'lam', target: 'tsmc', type: 'supplier', label: 'Etch', validFrom: '2010-01-01' },
  { source: 'lam', target: 'samsung', type: 'supplier', label: 'Etch', validFrom: '2010-01-01' },
  { source: 'kla', target: 'tsmc', type: 'supplier', label: 'Inspection', validFrom: '2010-01-01' },
  { source: 'sk_hynix', target: 'nvidia', type: 'supplier', label: 'HBM3e', validFrom: '2023-01-01', metadata: { product: 'HBM3e' } },
  { source: 'micron', target: 'nvidia', type: 'supplier', label: 'HBM3e', validFrom: '2024-01-01', metadata: { product: 'HBM3e' } },
  { source: 'broadcom', target: 'apple', type: 'supplier', label: 'WiFi/BT', validFrom: '2012-01-01', metadata: { product: 'WiFi/Bluetooth chips', revenue: '20% from Apple' } },
  { source: 'qualcomm', target: 'apple', type: 'supplier', label: '5G Modem', validFrom: '2019-01-01', validTo: '2027-01-01', metadata: { product: '5G modems', status: 'Phasing out' } },
  { source: 'ase', target: 'nvidia', type: 'supplier', label: 'CoWoS', validFrom: '2022-01-01', metadata: { service: 'CoWoS packaging' } },
  { source: 'amkor', target: 'nvidia', type: 'supplier', label: 'Packaging', validFrom: '2020-01-01', metadata: { service: 'Advanced packaging' } },
  
  // === CUSTOMER RELATIONSHIPS ===
  { source: 'microsoft', target: 'nvidia', type: 'customer', label: 'Azure AI', validFrom: '2016-01-01', metadata: { use: 'Azure AI, Copilot' } },
  { source: 'google', target: 'nvidia', type: 'customer', label: 'GCP AI', validFrom: '2016-01-01', metadata: { use: 'GCP AI' } },
  { source: 'amazon', target: 'nvidia', type: 'customer', label: 'AWS AI', validFrom: '2016-01-01', metadata: { use: 'AWS AI' } },
  { source: 'meta', target: 'nvidia', type: 'customer', label: 'AI Training', validFrom: '2018-01-01', metadata: { use: 'AI training' } },
  { source: 'openai', target: 'nvidia', type: 'customer', label: 'GPT Training', validFrom: '2020-01-01', metadata: { note: 'Via Microsoft' } },
  
  // === IP LICENSING ===
  { source: 'arm', target: 'nvidia', type: 'licensor', label: 'ARM ISA', validFrom: '2008-01-01', metadata: { ip: 'ARM architecture' } },
  { source: 'arm', target: 'qualcomm', type: 'licensor', label: 'ARM ISA', validFrom: '2006-01-01', metadata: { ip: 'ARM architecture' } },
  { source: 'arm', target: 'apple', type: 'licensor', label: 'ARM ISA', validFrom: '2008-01-01', metadata: { ip: 'ARM architecture' } },
  
  // === COMPETITION ===
  { source: 'nvidia', target: 'amd', type: 'competitor', metadata: { segment: 'GPUs, AI accelerators' } },
  { source: 'nvidia', target: 'intel', type: 'competitor', metadata: { segment: 'Data center AI' } },
  { source: 'intel', target: 'amd', type: 'competitor', metadata: { segment: 'x86 CPUs' } },
  { source: 'tsmc', target: 'samsung', type: 'competitor', metadata: { segment: 'Advanced foundry' } },
  { source: 'tsmc', target: 'intel_foundry', type: 'competitor', metadata: { segment: 'Foundry services' } },
  { source: 'nvidia', target: 'cerebras', type: 'competitor', metadata: { segment: 'AI training' } },
  { source: 'nvidia', target: 'groq', type: 'competitor', metadata: { segment: 'AI inference' } },
  
  // === OWNERSHIP & INVESTMENT ===
  { source: 'intel', target: 'intel_foundry', type: 'parent', validFrom: '2021-01-01' },
  { source: 'softbank', target: 'arm', type: 'investor', validFrom: '2016-01-01', metadata: { stake: '90%' } },
  { source: 'microsoft', target: 'openai', type: 'investor', validFrom: '2019-01-01', metadata: { investment: '$13B', stake: '49%' } },
  { source: 'google', target: 'anthropic', type: 'investor', validFrom: '2023-01-01', metadata: { investment: '$2B' } },
  { source: 'amazon', target: 'anthropic', type: 'investor', validFrom: '2023-01-01', metadata: { investment: '$4B' } },
  { source: 'sequoia', target: 'cerebras', type: 'investor', validFrom: '2019-01-01' },
  { source: 'sequoia', target: 'groq', type: 'investor', validFrom: '2020-01-01' },
  { source: 'a16z', target: 'cerebras', type: 'investor', validFrom: '2019-01-01' },
  { source: 'softbank', target: 'graphcore', type: 'investor', validFrom: '2024-01-01', metadata: { note: 'Acquired' } },
  
  // === PARTNERSHIPS ===
  { source: 'microsoft', target: 'openai', type: 'partner', validFrom: '2019-01-01', metadata: { type: 'Exclusive cloud' } },
  { source: 'imec', target: 'asml', type: 'partner', validFrom: '2010-01-01', metadata: { type: 'R&D' } },
  { source: 'imec', target: 'tsmc', type: 'partner', validFrom: '2010-01-01', metadata: { type: 'R&D' } },
  { source: 'imec', target: 'intel', type: 'partner', validFrom: '2010-01-01', metadata: { type: 'R&D' } },
  { source: 'imec', target: 'samsung', type: 'partner', validFrom: '2010-01-01', metadata: { type: 'R&D' } },
  
  // === EDA USAGE ===
  { source: 'nvidia', target: 'synopsys', type: 'customer', label: 'EDA', validFrom: '2005-01-01' },
  { source: 'nvidia', target: 'cadence', type: 'customer', label: 'EDA', validFrom: '2005-01-01' },
  { source: 'amd', target: 'synopsys', type: 'customer', label: 'EDA', validFrom: '2000-01-01' },
  { source: 'amd', target: 'cadence', type: 'customer', label: 'EDA', validFrom: '2000-01-01' },
  { source: 'apple', target: 'synopsys', type: 'customer', label: 'EDA', validFrom: '2010-01-01' },
  { source: 'apple', target: 'cadence', type: 'customer', label: 'EDA', validFrom: '2010-01-01' },
];

// =============================================================================
// SERVICE CLASS
// =============================================================================

class GraphService {
  private useMockData = true; // Toggle when backend is ready

  /**
   * Fetch graph data for visualization
   */
  async getGraph(params?: GraphQueryParams): Promise<GraphResponse> {
    if (this.useMockData) {
      return this.getMockGraph(params);
    }
    
    // When backend is ready:
    const response = await api.get<GraphResponse>('/graph', { params });
    return response.data;
  }

  /**
   * Get ego-centric graph around a specific entity
   */
  async getEntityGraph(entityId: string, depth = 2): Promise<GraphResponse> {
    if (this.useMockData) {
      return this.getMockEntityGraph(entityId, depth);
    }
    
    const response = await api.get<GraphResponse>(`/graph/entity/${entityId}`, {
      params: { depth }
    });
    return response.data;
  }

  /**
   * Find shortest path between two entities
   */
  async findPath(request: PathFindingRequest): Promise<PathResult | null> {
    if (this.useMockData) {
      return this.getMockPath(request);
    }
    
    const response = await api.post<PathResult>('/graph/path', request);
    return response.data;
  }

  /**
   * Analyze network metrics for a set of entities
   */
  async analyzeNetwork(entityIds?: string[]): Promise<NetworkAnalysisResult> {
    if (this.useMockData) {
      return this.getMockAnalysis(entityIds);
    }
    
    const response = await api.post<NetworkAnalysisResult>('/graph/analyze', { entityIds });
    return response.data;
  }

  // ===========================================================================
  // MOCK IMPLEMENTATIONS
  // ===========================================================================

  private getMockGraph(params?: GraphQueryParams): GraphResponse {
    let nodes = [...MOCK_NODES];
    let links = [...MOCK_LINKS];

    // Filter by entity types
    if (params?.entityTypes?.length) {
      nodes = nodes.filter(n => params.entityTypes!.includes(n.type));
    }

    // Filter by relationship types
    if (params?.relationshipTypes?.length) {
      links = links.filter(l => params.relationshipTypes!.includes(l.type));
    }

    // Filter by date (point-in-time)
    if (params?.asOfDate) {
      const asOf = new Date(params.asOfDate);
      links = links.filter(l => {
        const from = l.validFrom ? new Date(l.validFrom) : new Date('1900-01-01');
        const to = l.validTo ? new Date(l.validTo) : new Date('2100-01-01');
        return from <= asOf && asOf <= to;
      });
    }

    // Ensure we only include nodes that have connections
    const connectedNodeIds = new Set<string>();
    links.forEach(l => {
      connectedNodeIds.add(typeof l.source === 'string' ? l.source : l.source.id);
      connectedNodeIds.add(typeof l.target === 'string' ? l.target : l.target.id);
    });
    
    if (links.length > 0) {
      nodes = nodes.filter(n => connectedNodeIds.has(n.id));
    }

    // Apply limit
    if (params?.limit) {
      nodes = nodes.slice(0, params.limit);
    }

    return {
      data: { nodes, links },
      totalNodes: nodes.length,
      totalEdges: links.length,
      truncated: false,
      queryTime: 5,
    };
  }

  private getMockEntityGraph(entityId: string, depth: number): GraphResponse {
    const visited = new Set<string>();
    const resultNodes: EntityNode[] = [];
    const resultLinks: Relationship[] = [];

    const traverse = (nodeId: string, currentDepth: number) => {
      if (currentDepth > depth || visited.has(nodeId)) return;
      visited.add(nodeId);

      const node = MOCK_NODES.find(n => n.id === nodeId);
      if (node) {
        resultNodes.push(node);
      }

      // Find connected links
      MOCK_LINKS.forEach(link => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target.id;

        if (sourceId === nodeId || targetId === nodeId) {
          if (!resultLinks.some(l => 
            (typeof l.source === 'string' ? l.source : l.source.id) === sourceId &&
            (typeof l.target === 'string' ? l.target : l.target.id) === targetId &&
            l.type === link.type
          )) {
            resultLinks.push(link);
          }
          
          const nextId = sourceId === nodeId ? targetId : sourceId;
          traverse(nextId, currentDepth + 1);
        }
      });
    };

    traverse(entityId, 0);

    return {
      data: { nodes: resultNodes, links: resultLinks },
      totalNodes: resultNodes.length,
      totalEdges: resultLinks.length,
      truncated: false,
      queryTime: 3,
    };
  }

  private getMockPath(request: PathFindingRequest): PathResult | null {
    // Simple BFS pathfinding
    const queue: { nodeId: string; path: string[]; edges: Relationship[] }[] = [
      { nodeId: request.sourceId, path: [request.sourceId], edges: [] }
    ];
    const visited = new Set<string>([request.sourceId]);

    while (queue.length > 0) {
      const current = queue.shift()!;
      
      if (current.nodeId === request.targetId) {
        const pathNodes = current.path.map(id => 
          MOCK_NODES.find(n => n.id === id)!
        ).filter(Boolean);
        
        return {
          path: pathNodes,
          edges: current.edges,
          totalWeight: current.edges.length,
          hops: current.edges.length,
        };
      }

      if (current.path.length > (request.maxHops || 6)) continue;

      // Find neighbors
      MOCK_LINKS.forEach(link => {
        const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
        const targetId = typeof link.target === 'string' ? link.target : link.target.id;

        let nextId: string | null = null;
        if (sourceId === current.nodeId && !visited.has(targetId)) {
          nextId = targetId;
        } else if (targetId === current.nodeId && !visited.has(sourceId)) {
          nextId = sourceId;
        }

        if (nextId) {
          if (request.allowedRelationships?.length && 
              !request.allowedRelationships.includes(link.type)) {
            return;
          }
          
          visited.add(nextId);
          queue.push({
            nodeId: nextId,
            path: [...current.path, nextId],
            edges: [...current.edges, link],
          });
        }
      });
    }

    return null; // No path found
  }

  private getMockAnalysis(_entityIds?: string[]): NetworkAnalysisResult {
    // Calculate basic network metrics
    const nodeCount = MOCK_NODES.length;
    const edgeCount = MOCK_LINKS.length;
    const maxPossibleEdges = nodeCount * (nodeCount - 1) / 2;
    const density = edgeCount / maxPossibleEdges;

    // Calculate degree for each node
    const degrees: Record<string, number> = {};
    MOCK_NODES.forEach(n => degrees[n.id] = 0);
    MOCK_LINKS.forEach(l => {
      const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
      const targetId = typeof l.target === 'string' ? l.target : l.target.id;
      degrees[sourceId] = (degrees[sourceId] || 0) + 1;
      degrees[targetId] = (degrees[targetId] || 0) + 1;
    });

    const avgDegree = Object.values(degrees).reduce((a, b) => a + b, 0) / nodeCount;

    // Top 10 most connected nodes
    const sortedByDegree = Object.entries(degrees)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 10);

    const centralityScores: Record<string, number> = {};
    sortedByDegree.forEach(([id, deg]) => {
      centralityScores[id] = deg / (nodeCount - 1); // Normalized degree centrality
    });

    // Simple community detection by category
    const communities: Record<string, string[]> = {};
    MOCK_NODES.forEach(n => {
      if (!communities[n.category]) communities[n.category] = [];
      communities[n.category].push(n.id);
    });

    return {
      nodeCount,
      edgeCount,
      density,
      avgDegree,
      centralityScores,
      communities,
      influentialNodes: sortedByDegree.slice(0, 5).map(([id]) => id),
    };
  }
}

// Export singleton instance
export const graphService = new GraphService();

// Export mock data for direct use in components
export const getMockGraphData = (): GraphData => ({
  nodes: MOCK_NODES,
  links: MOCK_LINKS,
});
