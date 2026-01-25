/**
 * EntityGraphPage - 3D Interactive Entity Relationship Graph
 * 
 * Visualizes the semiconductor industry ecosystem with:
 * - 3D force-directed graph layout
 * - Node colors by entity type/category
 * - Edge colors by relationship type
 * - Click to select and view entity details
 * - Search and filter capabilities
 * - Zoom, pan, rotate controls
 */

import { useCallback, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';

// =============================================================================
// TYPES
// =============================================================================

interface EntityNode {
  id: string;
  name: string;
  type: 'public_company' | 'private_company' | 'subsidiary' | 'investor' | 'startup' | 'foundry' | 'equipment' | 'hyperscaler';
  category: 'design' | 'manufacturing' | 'equipment' | 'memory' | 'customer' | 'investor' | 'ip';
  industry?: string;
  jurisdiction?: string;
  identifiers?: {
    cik?: string;
    ticker?: string;
    lei?: string;
  };
  // Financial metrics for visualization
  metrics?: {
    marketCapB?: number;    // Market cap in billions USD
    revenueB?: number;      // Annual revenue in billions USD
    employees?: number;     // Employee count
    grossMargin?: number;   // Gross margin percentage
    yoyGrowth?: number;     // Year-over-year revenue growth %
  };
  metadata?: Record<string, unknown>;
  // Force graph properties
  x?: number;
  y?: number;
  z?: number;
  fx?: number | null;
  fy?: number | null;
  fz?: number | null;
}

interface RelationshipLink {
  source: string | EntityNode;
  target: string | EntityNode;
  type: 'parent' | 'subsidiary' | 'customer' | 'supplier' | 'foundry' | 'competitor' | 'investor' | 'partner' | 'licensor';
  label?: string;
  metadata?: Record<string, unknown>;
}

interface GraphData {
  nodes: EntityNode[];
  links: RelationshipLink[];
}

type SizeMetric = 'uniform' | 'marketCap' | 'revenue' | 'employees' | 'connections';

// =============================================================================
// SEMICONDUCTOR ECOSYSTEM DATA
// =============================================================================

const SEMICONDUCTOR_ECOSYSTEM: GraphData = {
  nodes: [
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
  ],
  
  links: [
    // === FOUNDRY RELATIONSHIPS ===
    { source: 'nvidia', target: 'tsmc', type: 'foundry', label: '3nm/4nm', metadata: { nodes: ['3nm', '4nm'], exclusive: true } },
    { source: 'amd', target: 'tsmc', type: 'foundry', label: '5nm/4nm', metadata: { nodes: ['5nm', '4nm'] } },
    { source: 'apple', target: 'tsmc', type: 'foundry', label: '3nm', metadata: { nodes: ['3nm'], products: ['M-series', 'A-series'] } },
    { source: 'qualcomm', target: 'tsmc', type: 'foundry', label: '4nm', metadata: { nodes: ['4nm'] } },
    { source: 'cerebras', target: 'tsmc', type: 'foundry', label: 'Wafer-scale', metadata: { special: 'Wafer-scale' } },
    { source: 'groq', target: 'globalfoundries', type: 'foundry', label: '14nm', metadata: { node: '14nm' } },
    { source: 'intel', target: 'tsmc', type: 'foundry', label: 'N3B', metadata: { note: 'Competitor using competitor!' } },
    
    // === SUPPLY CHAIN ===
    { source: 'asml', target: 'tsmc', type: 'supplier', label: 'EUV', metadata: { product: 'EUV lithography' } },
    { source: 'asml', target: 'samsung', type: 'supplier', label: 'EUV', metadata: { product: 'EUV lithography' } },
    { source: 'asml', target: 'intel', type: 'supplier', label: 'High-NA EUV', metadata: { product: 'High-NA EUV' } },
    { source: 'applied_materials', target: 'tsmc', type: 'supplier', label: 'Deposition' },
    { source: 'applied_materials', target: 'samsung', type: 'supplier', label: 'Deposition' },
    { source: 'lam', target: 'tsmc', type: 'supplier', label: 'Etch' },
    { source: 'lam', target: 'samsung', type: 'supplier', label: 'Etch' },
    { source: 'kla', target: 'tsmc', type: 'supplier', label: 'Inspection' },
    { source: 'sk_hynix', target: 'nvidia', type: 'supplier', label: 'HBM3e', metadata: { product: 'HBM3e' } },
    { source: 'micron', target: 'nvidia', type: 'supplier', label: 'HBM3e', metadata: { product: 'HBM3e' } },
    { source: 'broadcom', target: 'apple', type: 'supplier', label: 'WiFi/BT', metadata: { product: 'WiFi/Bluetooth chips', revenue: '20% from Apple' } },
    { source: 'qualcomm', target: 'apple', type: 'supplier', label: '5G Modem', metadata: { product: '5G modems', status: 'Phasing out' } },
    { source: 'ase', target: 'nvidia', type: 'supplier', label: 'CoWoS', metadata: { service: 'CoWoS packaging' } },
    { source: 'amkor', target: 'nvidia', type: 'supplier', label: 'Packaging', metadata: { service: 'Advanced packaging' } },
    
    // === CUSTOMER RELATIONSHIPS ===
    { source: 'microsoft', target: 'nvidia', type: 'customer', label: 'Azure AI', metadata: { use: 'Azure AI, Copilot' } },
    { source: 'google', target: 'nvidia', type: 'customer', label: 'GCP AI', metadata: { use: 'GCP AI' } },
    { source: 'amazon', target: 'nvidia', type: 'customer', label: 'AWS AI', metadata: { use: 'AWS AI' } },
    { source: 'meta', target: 'nvidia', type: 'customer', label: 'AI Training', metadata: { use: 'AI training' } },
    { source: 'openai', target: 'nvidia', type: 'customer', label: 'GPT Training', metadata: { note: 'Via Microsoft' } },
    
    // === IP LICENSING ===
    { source: 'arm', target: 'nvidia', type: 'licensor', label: 'ARM ISA', metadata: { ip: 'ARM architecture' } },
    { source: 'arm', target: 'qualcomm', type: 'licensor', label: 'ARM ISA', metadata: { ip: 'ARM architecture' } },
    { source: 'arm', target: 'apple', type: 'licensor', label: 'ARM ISA', metadata: { ip: 'ARM architecture' } },
    
    // === COMPETITION ===
    { source: 'nvidia', target: 'amd', type: 'competitor', metadata: { segment: 'GPUs, AI accelerators' } },
    { source: 'nvidia', target: 'intel', type: 'competitor', metadata: { segment: 'Data center AI' } },
    { source: 'intel', target: 'amd', type: 'competitor', metadata: { segment: 'x86 CPUs' } },
    { source: 'tsmc', target: 'samsung', type: 'competitor', metadata: { segment: 'Advanced foundry' } },
    { source: 'tsmc', target: 'intel_foundry', type: 'competitor', metadata: { segment: 'Foundry services' } },
    { source: 'nvidia', target: 'cerebras', type: 'competitor', metadata: { segment: 'AI training' } },
    { source: 'nvidia', target: 'groq', type: 'competitor', metadata: { segment: 'AI inference' } },
    
    // === OWNERSHIP & INVESTMENT ===
    { source: 'intel', target: 'intel_foundry', type: 'parent' },
    { source: 'softbank', target: 'arm', type: 'investor', metadata: { stake: '90%' } },
    { source: 'microsoft', target: 'openai', type: 'investor', metadata: { investment: '$13B', stake: '49%' } },
    { source: 'google', target: 'anthropic', type: 'investor', metadata: { investment: '$2B' } },
    { source: 'amazon', target: 'anthropic', type: 'investor', metadata: { investment: '$4B' } },
    { source: 'sequoia', target: 'cerebras', type: 'investor' },
    { source: 'sequoia', target: 'groq', type: 'investor' },
    { source: 'a16z', target: 'cerebras', type: 'investor' },
    { source: 'softbank', target: 'graphcore', type: 'investor', metadata: { note: 'Acquired' } },
    
    // === PARTNERSHIPS ===
    { source: 'microsoft', target: 'openai', type: 'partner', metadata: { type: 'Exclusive cloud' } },
    { source: 'imec', target: 'asml', type: 'partner', metadata: { type: 'R&D' } },
    { source: 'imec', target: 'tsmc', type: 'partner', metadata: { type: 'R&D' } },
    { source: 'imec', target: 'intel', type: 'partner', metadata: { type: 'R&D' } },
    { source: 'imec', target: 'samsung', type: 'partner', metadata: { type: 'R&D' } },
    
    // === EDA USAGE ===
    { source: 'nvidia', target: 'synopsys', type: 'customer' },
    { source: 'nvidia', target: 'cadence', type: 'customer' },
    { source: 'amd', target: 'synopsys', type: 'customer' },
    { source: 'amd', target: 'cadence', type: 'customer' },
    { source: 'apple', target: 'synopsys', type: 'customer' },
    { source: 'apple', target: 'cadence', type: 'customer' },
  ],
};

// =============================================================================
// COLOR SCHEMES
// =============================================================================

const NODE_COLORS: Record<string, string> = {
  public_company: '#4CAF50',  // Green
  private_company: '#9E9E9E', // Gray
  subsidiary: '#795548',      // Brown
  investor: '#FFC107',        // Amber
  startup: '#E91E63',         // Pink
  foundry: '#2196F3',         // Blue
  equipment: '#FF5722',       // Deep Orange
  hyperscaler: '#9C27B0',     // Purple
};

const CATEGORY_COLORS: Record<string, string> = {
  design: '#4CAF50',
  manufacturing: '#2196F3',
  equipment: '#FF5722',
  memory: '#00BCD4',
  customer: '#9C27B0',
  investor: '#FFC107',
  ip: '#FF9800',
};

const LINK_COLORS: Record<string, string> = {
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
// COMPONENT
// =============================================================================

export default function EntityGraphPage() {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const [graphData] = useState<GraphData>(SEMICONDUCTOR_ECOSYSTEM);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<EntityNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [colorBy, setColorBy] = useState<'type' | 'category'>('type');
  const [sizeBy, setSizeBy] = useState<SizeMetric>('marketCap');
  const [showLabels, setShowLabels] = useState(true);
  const [showEdgeLabels, setShowEdgeLabels] = useState(true);
  const [filterType, setFilterType] = useState<string>('all');
  const [highlightLinks, setHighlightLinks] = useState<Set<RelationshipLink>>(new Set());
  const [highlightNodes, setHighlightNodes] = useState<Set<EntityNode>>(new Set());

  // Calculate connection counts for each node
  const connectionCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    graphData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      counts[sourceId] = (counts[sourceId] || 0) + 1;
      counts[targetId] = (counts[targetId] || 0) + 1;
    });
    return counts;
  }, [graphData.links]);

  // Get node size based on selected metric
  const getNodeSize = useCallback((node: EntityNode): number => {
    const baseSize = 4;
    const maxSize = 20;
    
    switch (sizeBy) {
      case 'uniform':
        return 6;
      case 'marketCap': {
        const cap = node.metrics?.marketCapB || 1;
        // Log scale for market cap (ranges from ~1B to ~3000B)
        return Math.min(maxSize, baseSize + Math.log10(cap) * 4);
      }
      case 'revenue': {
        const rev = node.metrics?.revenueB || 0.1;
        // Log scale for revenue
        return Math.min(maxSize, baseSize + Math.log10(rev + 1) * 5);
      }
      case 'employees': {
        const emp = node.metrics?.employees || 100;
        // Log scale for employees
        return Math.min(maxSize, baseSize + Math.log10(emp) * 2.5);
      }
      case 'connections': {
        const conn = connectionCounts[node.id] || 1;
        return Math.min(maxSize, baseSize + conn * 1.5);
      }
      default:
        return 6;
    }
  }, [sizeBy, connectionCounts]);

  // Filter data based on search and type filter
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    let links = graphData.links;
    
    // Filter by type
    if (filterType !== 'all') {
      nodes = nodes.filter(n => n.type === filterType || n.category === filterType);
      const nodeIds = new Set(nodes.map(n => n.id));
      links = links.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        return nodeIds.has(sourceId) && nodeIds.has(targetId);
      });
    }
    
    // Filter by search
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      nodes = nodes.filter(n => 
        n.name.toLowerCase().includes(query) ||
        n.id.toLowerCase().includes(query) ||
        n.identifiers?.ticker?.toLowerCase().includes(query)
      );
      const nodeIds = new Set(nodes.map(n => n.id));
      links = links.filter(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        return nodeIds.has(sourceId) || nodeIds.has(targetId);
      });
      
      // Include connected nodes
      links.forEach(l => {
        const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
        const targetId = typeof l.target === 'string' ? l.target : l.target.id;
        nodeIds.add(sourceId);
        nodeIds.add(targetId);
      });
      nodes = graphData.nodes.filter(n => nodeIds.has(n.id));
    }
    
    return { nodes, links };
  }, [graphData, searchQuery, filterType]);

  // Handle node click
  const handleNodeClick = useCallback((node: EntityNode) => {
    setSelectedNode(node);
    
    // Zoom to node
    const distance = 200;
    const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
    
    fgRef.current?.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      node as { x: number; y: number; z: number },
      2000
    );
    
    // Highlight connected nodes and links
    const connectedNodes = new Set<EntityNode>();
    const connectedLinks = new Set<RelationshipLink>();
    
    filteredData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      
      if (sourceId === node.id || targetId === node.id) {
        connectedLinks.add(link);
        const connectedNode = filteredData.nodes.find(
          n => n.id === (sourceId === node.id ? targetId : sourceId)
        );
        if (connectedNode) connectedNodes.add(connectedNode);
      }
    });
    
    connectedNodes.add(node);
    setHighlightNodes(connectedNodes);
    setHighlightLinks(connectedLinks);
  }, [filteredData]);

  // Handle node hover
  const handleNodeHover = useCallback((node: EntityNode | null) => {
    setHoveredNode(node);
    document.body.style.cursor = node ? 'pointer' : 'default';
  }, []);

  // Get node color
  const getNodeColor = useCallback((node: EntityNode) => {
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node);
    const baseColor = colorBy === 'type' ? NODE_COLORS[node.type] : CATEGORY_COLORS[node.category];
    return isHighlighted ? baseColor : '#333333';
  }, [colorBy, highlightNodes]);

  // Get link color
  const getLinkColor = useCallback((link: RelationshipLink) => {
    const isHighlighted = highlightLinks.size === 0 || highlightLinks.has(link);
    const baseColor = LINK_COLORS[link.type] || '#999999';
    return isHighlighted ? baseColor : '#222222';
  }, [highlightLinks]);

  // Custom node rendering
  const nodeThreeObject = useCallback((nodeObj: object) => {
    const node = nodeObj as EntityNode;
    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoveredNode?.id === node.id;
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node);
    
    const group = new THREE.Group();
    
    // Dynamic size based on selected metric
    const baseNodeSize = getNodeSize(node);
    const nodeSize = isSelected ? baseNodeSize * 1.5 : isHovered ? baseNodeSize * 1.2 : baseNodeSize;
    
    // Sphere for node
    const geometry = new THREE.SphereGeometry(nodeSize);
    const material = new THREE.MeshLambertMaterial({
      color: getNodeColor(node),
      transparent: !isHighlighted,
      opacity: isHighlighted ? 1 : 0.3,
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);
    
    // Glow effect for selected node
    if (isSelected) {
      const glowGeometry = new THREE.SphereGeometry(nodeSize * 1.5);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: getNodeColor(node),
        transparent: true,
        opacity: 0.2,
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      group.add(glow);
    }
    
    // Label with name and industry
    if (showLabels && isHighlighted) {
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d')!;
      canvas.width = 512;
      canvas.height = 96;
      
      context.fillStyle = 'rgba(0, 0, 0, 0.85)';
      context.roundRect(0, 0, 512, 96, 8);
      context.fill();
      
      // Company name
      context.font = 'bold 28px Arial';
      context.fillStyle = '#ffffff';
      context.textAlign = 'center';
      context.fillText(node.name, 256, 35);
      
      // Industry/category subtitle
      const subtitle = node.industry || node.category;
      context.font = '20px Arial';
      context.fillStyle = '#9ca3af';
      context.fillText(subtitle, 256, 65);
      
      // Metric badge if available
      if (sizeBy !== 'uniform' && node.metrics) {
        let metricText = '';
        switch (sizeBy) {
          case 'marketCap':
            if (node.metrics.marketCapB) metricText = `$${node.metrics.marketCapB >= 1000 ? (node.metrics.marketCapB / 1000).toFixed(1) + 'T' : node.metrics.marketCapB + 'B'}`;
            break;
          case 'revenue':
            if (node.metrics.revenueB) metricText = `$${node.metrics.revenueB.toFixed(1)}B rev`;
            break;
          case 'employees':
            if (node.metrics.employees) metricText = `${(node.metrics.employees / 1000).toFixed(0)}K employees`;
            break;
        }
        if (metricText) {
          context.font = 'bold 18px Arial';
          context.fillStyle = '#60a5fa';
          context.fillText(metricText, 256, 85);
        }
      }
      
      const texture = new THREE.CanvasTexture(canvas);
      const spriteMaterial = new THREE.SpriteMaterial({ map: texture });
      const sprite = new THREE.Sprite(spriteMaterial);
      sprite.scale.set(60, 12, 1);
      sprite.position.set(0, nodeSize + 8, 0);
      group.add(sprite);
    }
    
    return group;
  }, [selectedNode, hoveredNode, highlightNodes, getNodeColor, getNodeSize, showLabels, sizeBy]);

  // Reset view
  const resetView = useCallback(() => {
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
    setSearchQuery('');
    setFilterType('all');
    fgRef.current?.cameraPosition({ x: 0, y: 0, z: 500 }, { x: 0, y: 0, z: 0 }, 1000);
  }, []);

  // Get relationship count for selected node
  const getNodeRelationships = useCallback((node: EntityNode) => {
    const relationships: Record<string, Array<{ node: EntityNode; link: RelationshipLink; direction: 'in' | 'out' }>> = {};
    
    filteredData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      
      if (sourceId === node.id) {
        const targetNode = filteredData.nodes.find(n => n.id === targetId);
        if (targetNode) {
          if (!relationships[link.type]) relationships[link.type] = [];
          relationships[link.type].push({ node: targetNode, link, direction: 'out' });
        }
      } else if (targetId === node.id) {
        const sourceNode = filteredData.nodes.find(n => n.id === sourceId);
        if (sourceNode) {
          if (!relationships[link.type]) relationships[link.type] = [];
          relationships[link.type].push({ node: sourceNode, link, direction: 'in' });
        }
      }
    });
    
    return relationships;
  }, [filteredData]);

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold">🔗 Entity Relationship Graph</h1>
          <span className="text-sm text-gray-400">
            {filteredData.nodes.length} entities • {filteredData.links.length} relationships
          </span>
        </div>
        
        <div className="flex items-center gap-3 flex-wrap">
          {/* Search */}
          <input
            type="text"
            placeholder="Search entities..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm w-40 focus:outline-none focus:border-blue-500"
          />
          
          {/* Filter by type */}
          <select
            value={filterType}
            onChange={(e) => setFilterType(e.target.value)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="all">All Types</option>
            <optgroup label="Entity Type">
              <option value="public_company">Public Companies</option>
              <option value="private_company">Private Companies</option>
              <option value="startup">Startups</option>
              <option value="foundry">Foundries</option>
              <option value="equipment">Equipment</option>
              <option value="hyperscaler">Hyperscalers</option>
              <option value="investor">Investors</option>
            </optgroup>
            <optgroup label="Category">
              <option value="design">Design</option>
              <option value="manufacturing">Manufacturing</option>
              <option value="memory">Memory</option>
              <option value="customer">Customers</option>
            </optgroup>
          </select>
          
          {/* Color by */}
          <select
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value as 'type' | 'category')}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="type">Color by Type</option>
            <option value="category">Color by Category</option>
          </select>
          
          {/* Size by metric */}
          <select
            value={sizeBy}
            onChange={(e) => setSizeBy(e.target.value as SizeMetric)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500"
          >
            <option value="uniform">Uniform Size</option>
            <option value="marketCap">Size by Market Cap</option>
            <option value="revenue">Size by Revenue</option>
            <option value="employees">Size by Employees</option>
            <option value="connections">Size by Connections</option>
          </select>
          
          {/* Toggle labels */}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showLabels}
              onChange={(e) => setShowLabels(e.target.checked)}
              className="rounded"
            />
            Labels
          </label>
          
          {/* Toggle edge labels */}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showEdgeLabels}
              onChange={(e) => setShowEdgeLabels(e.target.checked)}
              className="rounded"
            />
            Edge Labels
          </label>
          
          {/* Reset button */}
          <button
            onClick={resetView}
            className="bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-sm"
          >
            Reset View
          </button>
        </div>
      </header>
      
      {/* Main content */}
      <div className="flex-1 flex">
        {/* 3D Graph */}
        <div className="flex-1 relative">
          <ForceGraph3D
            ref={fgRef}
            graphData={filteredData}
            nodeId="id"
            nodeLabel={(node) => {
              const n = node as EntityNode;
              return `${n.name}\n${n.type}`;
            }}
            nodeThreeObject={nodeThreeObject}
            nodeThreeObjectExtend={false}
            linkColor={(link) => getLinkColor(link as RelationshipLink)}
            linkWidth={(link) => highlightLinks.has(link as RelationshipLink) ? 3 : 1}
            linkOpacity={0.7}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.15}
            linkLabel={showEdgeLabels ? (link) => {
              const l = link as RelationshipLink;
              return l.label || l.type;
            } : undefined}
            linkDirectionalParticles={(link) => highlightLinks.has(link as RelationshipLink) ? 4 : 0}
            linkDirectionalParticleWidth={2}
            linkDirectionalParticleSpeed={0.005}
            onNodeClick={(node) => handleNodeClick(node as EntityNode)}
            onNodeHover={(node) => handleNodeHover(node as EntityNode | null)}
            onBackgroundClick={() => {
              setSelectedNode(null);
              setHighlightNodes(new Set());
              setHighlightLinks(new Set());
            }}
            backgroundColor="#111827"
            showNavInfo={false}
          />
          
          {/* Legend */}
          <div className="absolute bottom-4 left-4 bg-gray-800/90 rounded-lg p-3 text-sm max-w-xs">
            <h3 className="font-semibold mb-2">
              {colorBy === 'type' ? 'Entity Types' : 'Categories'}
            </h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {Object.entries(colorBy === 'type' ? NODE_COLORS : CATEGORY_COLORS).map(([key, color]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                  <span className="capitalize text-xs">{key.replace('_', ' ')}</span>
                </div>
              ))}
            </div>
            
            <h3 className="font-semibold mt-3 mb-2">Relationships</h3>
            <div className="grid grid-cols-2 gap-x-4 gap-y-1">
              {Object.entries(LINK_COLORS).map(([key, color]) => (
                <div key={key} className="flex items-center gap-2">
                  <span className="w-4 h-0.5" style={{ backgroundColor: color }} />
                  <span className="capitalize text-xs">{key}</span>
                </div>
              ))}
            </div>
            
            {sizeBy !== 'uniform' && (
              <>
                <h3 className="font-semibold mt-3 mb-1">Node Size</h3>
                <p className="text-xs text-gray-400">
                  {sizeBy === 'marketCap' && 'Sized by market capitalization'}
                  {sizeBy === 'revenue' && 'Sized by annual revenue'}
                  {sizeBy === 'employees' && 'Sized by employee count'}
                  {sizeBy === 'connections' && 'Sized by # of connections'}
                </p>
              </>
            )}
          </div>
          
          {/* Controls hint */}
          <div className="absolute bottom-4 right-4 bg-gray-800/90 rounded-lg p-3 text-xs text-gray-400">
            <p>🖱️ Drag to rotate • Scroll to zoom</p>
            <p>Click node to select • Click background to deselect</p>
            <p className="mt-1 text-blue-400">Particles flow along selected relationships</p>
          </div>
        </div>
        
        {/* Details panel */}
        {selectedNode && (
          <div className="w-96 bg-gray-800 border-l border-gray-700 overflow-y-auto">
            <div className="p-4">
              {/* Entity header */}
              <div className="flex items-start justify-between mb-4">
                <div>
                  <h2 className="text-xl font-bold">{selectedNode.name}</h2>
                  <div className="flex items-center gap-2 mt-1">
                    <span 
                      className="px-2 py-0.5 rounded text-xs font-medium"
                      style={{ backgroundColor: NODE_COLORS[selectedNode.type], color: '#000' }}
                    >
                      {selectedNode.type.replace('_', ' ')}
                    </span>
                    <span 
                      className="px-2 py-0.5 rounded text-xs font-medium"
                      style={{ backgroundColor: CATEGORY_COLORS[selectedNode.category], color: '#000' }}
                    >
                      {selectedNode.category}
                    </span>
                  </div>
                </div>
                <button 
                  onClick={() => {
                    setSelectedNode(null);
                    setHighlightNodes(new Set());
                    setHighlightLinks(new Set());
                  }}
                  className="text-gray-400 hover:text-white"
                >
                  ✕
                </button>
              </div>
              
              {/* Industry */}
              {selectedNode.industry && (
                <div className="mb-4">
                  <span className="inline-block bg-gray-700 text-gray-300 px-3 py-1 rounded-full text-sm">
                    {selectedNode.industry}
                  </span>
                </div>
              )}
              
              {/* Financial Metrics */}
              {selectedNode.metrics && Object.keys(selectedNode.metrics).length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-gray-400 mb-2">FINANCIAL METRICS</h3>
                  <div className="grid grid-cols-2 gap-2">
                    {selectedNode.metrics.marketCapB && (
                      <div className="bg-gray-700 rounded p-3">
                        <div className="text-xs text-gray-400">Market Cap</div>
                        <div className="text-lg font-bold text-green-400">
                          ${selectedNode.metrics.marketCapB >= 1000 
                            ? (selectedNode.metrics.marketCapB / 1000).toFixed(1) + 'T' 
                            : selectedNode.metrics.marketCapB + 'B'}
                        </div>
                      </div>
                    )}
                    {selectedNode.metrics.revenueB && (
                      <div className="bg-gray-700 rounded p-3">
                        <div className="text-xs text-gray-400">Revenue</div>
                        <div className="text-lg font-bold text-blue-400">
                          ${selectedNode.metrics.revenueB.toFixed(1)}B
                        </div>
                      </div>
                    )}
                    {selectedNode.metrics.employees && (
                      <div className="bg-gray-700 rounded p-3">
                        <div className="text-xs text-gray-400">Employees</div>
                        <div className="text-lg font-bold text-purple-400">
                          {(selectedNode.metrics.employees / 1000).toFixed(0)}K
                        </div>
                      </div>
                    )}
                    {selectedNode.metrics.grossMargin && (
                      <div className="bg-gray-700 rounded p-3">
                        <div className="text-xs text-gray-400">Gross Margin</div>
                        <div className="text-lg font-bold text-yellow-400">
                          {selectedNode.metrics.grossMargin}%
                        </div>
                      </div>
                    )}
                    {selectedNode.metrics.yoyGrowth !== undefined && (
                      <div className="bg-gray-700 rounded p-3 col-span-2">
                        <div className="text-xs text-gray-400">YoY Growth</div>
                        <div className={`text-lg font-bold ${selectedNode.metrics.yoyGrowth >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          {selectedNode.metrics.yoyGrowth > 0 ? '+' : ''}{selectedNode.metrics.yoyGrowth}%
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Identifiers */}
              {selectedNode.identifiers && Object.keys(selectedNode.identifiers).length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-gray-400 mb-2">IDENTIFIERS</h3>
                  <div className="bg-gray-700 rounded p-3 space-y-1">
                    {selectedNode.identifiers.ticker && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">Ticker</span>
                        <span className="font-mono">{selectedNode.identifiers.ticker}</span>
                      </div>
                    )}
                    {selectedNode.identifiers.cik && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">CIK</span>
                        <span className="font-mono">{selectedNode.identifiers.cik}</span>
                      </div>
                    )}
                    {selectedNode.identifiers.lei && (
                      <div className="flex justify-between">
                        <span className="text-gray-400">LEI</span>
                        <span className="font-mono text-xs">{selectedNode.identifiers.lei}</span>
                      </div>
                    )}
                  </div>
                </div>
              )}
              
              {/* Jurisdiction */}
              {selectedNode.jurisdiction && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-gray-400 mb-2">JURISDICTION</h3>
                  <div className="bg-gray-700 rounded p-3">
                    <span className="text-lg">{getFlagEmoji(selectedNode.jurisdiction)}</span>
                    <span className="ml-2">{getCountryName(selectedNode.jurisdiction)}</span>
                  </div>
                </div>
              )}
              
              {/* Metadata */}
              {selectedNode.metadata && Object.keys(selectedNode.metadata).length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-semibold text-gray-400 mb-2">ADDITIONAL INFO</h3>
                  <div className="bg-gray-700 rounded p-3 space-y-1">
                    {Object.entries(selectedNode.metadata).map(([key, value]) => (
                      <div key={key} className="flex justify-between">
                        <span className="text-gray-400 capitalize">{key.replace(/([A-Z])/g, ' $1')}</span>
                        <span>{String(value)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              
              {/* Relationships */}
              <div className="mb-4">
                <h3 className="text-sm font-semibold text-gray-400 mb-2">RELATIONSHIPS</h3>
                {Object.entries(getNodeRelationships(selectedNode)).map(([type, rels]) => (
                  <div key={type} className="mb-3">
                    <div 
                      className="flex items-center gap-2 mb-1"
                      style={{ color: LINK_COLORS[type] }}
                    >
                      <span className="w-3 h-0.5" style={{ backgroundColor: LINK_COLORS[type] }} />
                      <span className="capitalize font-medium">{type}</span>
                      <span className="text-gray-500 text-sm">({rels.length})</span>
                    </div>
                    <div className="space-y-1 ml-5">
                      {rels.map(({ node, direction }, i) => (
                        <button
                          key={i}
                          onClick={() => handleNodeClick(node)}
                          className="block w-full text-left bg-gray-700 hover:bg-gray-600 rounded px-2 py-1 text-sm"
                        >
                          <span className="text-gray-400">{direction === 'in' ? '← ' : '→ '}</span>
                          {node.name}
                          {node.identifiers?.ticker && (
                            <span className="text-gray-500 ml-1">({node.identifiers.ticker})</span>
                          )}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Actions */}
              <div className="pt-4 border-t border-gray-700 space-y-2">
                <button className="w-full bg-blue-600 hover:bg-blue-700 rounded py-2 text-sm">
                  View SEC Filings →
                </button>
                <button className="w-full bg-gray-700 hover:bg-gray-600 rounded py-2 text-sm">
                  Export Relationships
                </button>
                <button className="w-full bg-gray-700 hover:bg-gray-600 rounded py-2 text-sm">
                  Find Path To...
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// Helper functions
function getFlagEmoji(countryCode: string): string {
  const flags: Record<string, string> = {
    US: '🇺🇸', GB: '🇬🇧', TW: '🇹🇼', KR: '🇰🇷', JP: '🇯🇵',
    NL: '🇳🇱', BE: '🇧🇪', DE: '🇩🇪', CN: '🇨🇳',
  };
  return flags[countryCode] || '🌍';
}

function getCountryName(countryCode: string): string {
  const names: Record<string, string> = {
    US: 'United States', GB: 'United Kingdom', TW: 'Taiwan', KR: 'South Korea',
    JP: 'Japan', NL: 'Netherlands', BE: 'Belgium', DE: 'Germany', CN: 'China',
  };
  return names[countryCode] || countryCode;
}
