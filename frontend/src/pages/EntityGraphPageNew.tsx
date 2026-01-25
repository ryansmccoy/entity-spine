/**
 * EntityGraphPage - 3D Interactive Entity Relationship Graph
 * 
 * Progressive feature implementation:
 * 
 * MAIN VIEW (Levels 1-3):
 * - 3D force-directed graph layout
 * - Dynamic node sizing by metrics
 * - Color coding by type/category
 * - Filter sidebar
 * - Time slider for temporal queries
 * - Analytics panel
 * 
 * TABS (Levels 4-5):
 * - 🤖 AI Assistant - Natural language graph exploration
 * - ⏳ Timeline - (Future) Animated history playback
 * - 🌌 Multi-verse - (Future) Scenario comparison
 * 
 * Data Strategy:
 * - Currently uses mock data embedded in graphService
 * - When Python backend ready, will fetch from EntitySpine's GraphService API
 * - Types in types/graph.ts mirror EntitySpine domain models
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';

import { graphService, getMockGraphData } from '../api/graphService';
import { FilterSidebar } from '../components/graph/FilterSidebar';
import { TimeSlider } from '../components/graph/TimeSlider';
import { AnalyticsPanel } from '../components/graph/AnalyticsPanel';
import { AIAssistant } from '../components/graph/AIAssistant';

import type {
  GraphData,
  EntityNode,
  Relationship,
  GraphFilters,
  NetworkAnalysisResult,
  SizeMetric,
  ColorScheme,
  PathResult,
} from '../types/graph';

// =============================================================================
// COLOR SCHEMES
// =============================================================================

const NODE_COLORS: Record<string, string> = {
  public_company: '#4CAF50',
  private_company: '#9E9E9E',
  subsidiary: '#795548',
  investor: '#FFC107',
  startup: '#E91E63',
  foundry: '#2196F3',
  equipment: '#FF5722',
  hyperscaler: '#9C27B0',
  person: '#00BCD4',
  government: '#607D8B',
  exchange: '#3F51B5',
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
  affiliate: '#9E9E9E',
};

// =============================================================================
// TABS DEFINITION
// =============================================================================

type TabId = 'graph' | 'ai' | 'timeline' | 'multiverse';

interface Tab {
  id: TabId;
  label: string;
  icon: string;
  level: number;
  available: boolean;
}

const TABS: Tab[] = [
  { id: 'graph', label: 'Graph', icon: '🔗', level: 1, available: true },
  { id: 'ai', label: 'AI Assistant', icon: '🤖', level: 4, available: true },
  { id: 'timeline', label: 'Timeline', icon: '⏳', level: 4, available: false },
  { id: 'multiverse', label: 'Multi-verse', icon: '🌌', level: 5, available: false },
];

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function EntityGraphPage() {
  // Graph reference
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);

  // Data state
  const [graphData, _setGraphData] = useState<GraphData>(getMockGraphData());
  const [analysis, setAnalysis] = useState<NetworkAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  // Reserved for future data updates from backend
  void _setGraphData;

  // Selection state
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [hoveredNode, setHoveredNode] = useState<EntityNode | null>(null);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<Relationship>>(new Set());
  const [pathResult, setPathResult] = useState<PathResult | null>(null);

  // UI state
  const [activeTab, setActiveTab] = useState<TabId>('graph');
  const [showFilters, setShowFilters] = useState(false);
  const [showAnalytics, setShowAnalytics] = useState(false);
  const [showTimeline, setShowTimeline] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  
  // View settings
  const [colorBy, setColorBy] = useState<ColorScheme>('type');
  const [sizeBy, setSizeBy] = useState<SizeMetric>('marketCap');
  const [showLabels, _setShowLabels] = useState(true);
  const [showEdgeLabels, _setShowEdgeLabels] = useState(true);
  
  // Reserved for future view settings UI
  void _setShowLabels;
  void _setShowEdgeLabels;

  // Filters
  const [filters, setFilters] = useState<GraphFilters>({
    entityTypes: [],
    relationshipTypes: [],
    categories: [],
    jurisdictions: [],
  });

  // Time state
  const [currentDate, setCurrentDate] = useState(new Date());
  const [isPlaying, setIsPlaying] = useState(false);
  const minDate = new Date('2015-01-01');
  const maxDate = new Date('2026-12-31');

  // Load analysis on mount
  useEffect(() => {
    const loadAnalysis = async () => {
      try {
        const result = await graphService.analyzeNetwork();
        setAnalysis(result);
      } catch (error) {
        console.error('Failed to load analysis:', error);
      }
    };
    loadAnalysis();
  }, []);

  // Available jurisdictions from data
  const availableJurisdictions = useMemo(() => {
    const jurisdictions = new Set<string>();
    graphData.nodes.forEach(n => {
      if (n.jurisdiction) jurisdictions.add(n.jurisdiction);
    });
    return Array.from(jurisdictions).sort();
  }, [graphData.nodes]);

  // Calculate connection counts
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

  // Filter data
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    let links = graphData.links;

    // Filter by entity types
    if (filters.entityTypes.length > 0) {
      nodes = nodes.filter(n => filters.entityTypes.includes(n.type));
    }

    // Filter by categories
    if (filters.categories.length > 0) {
      nodes = nodes.filter(n => filters.categories.includes(n.category));
    }

    // Filter by jurisdictions
    if (filters.jurisdictions.length > 0) {
      nodes = nodes.filter(n => n.jurisdiction && filters.jurisdictions.includes(n.jurisdiction));
    }

    // Filter by market cap
    if (filters.minMarketCap !== undefined) {
      nodes = nodes.filter(n => (n.metrics?.marketCapB || 0) >= filters.minMarketCap!);
    }
    if (filters.maxMarketCap !== undefined) {
      nodes = nodes.filter(n => (n.metrics?.marketCapB || Infinity) <= filters.maxMarketCap!);
    }

    // Filter by employees
    if (filters.minEmployees !== undefined) {
      nodes = nodes.filter(n => (n.metrics?.employees || 0) >= filters.minEmployees!);
    }

    // Filter by relationship types
    if (filters.relationshipTypes.length > 0) {
      links = links.filter(l => filters.relationshipTypes.includes(l.type));
    }

    // Search filter
    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      nodes = nodes.filter(n =>
        n.name.toLowerCase().includes(query) ||
        n.id.toLowerCase().includes(query) ||
        n.identifiers?.ticker?.toLowerCase().includes(query)
      );
    }

    // Only include links where both nodes exist
    const nodeIds = new Set(nodes.map(n => n.id));
    links = links.filter(l => {
      const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
      const targetId = typeof l.target === 'string' ? l.target : l.target.id;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });

    // Time filter
    if (showTimeline) {
      links = links.filter(l => {
        const from = l.validFrom ? new Date(l.validFrom) : new Date('1900-01-01');
        const to = l.validTo ? new Date(l.validTo) : new Date('2100-01-01');
        return from <= currentDate && currentDate <= to;
      });
    }

    return { nodes, links };
  }, [graphData, filters, searchQuery, showTimeline, currentDate]);

  // Get node size
  const getNodeSize = useCallback((node: EntityNode): number => {
    const baseSize = 4;
    const maxSize = 20;

    switch (sizeBy) {
      case 'uniform':
        return 6;
      case 'marketCap': {
        const cap = node.metrics?.marketCapB || 1;
        return Math.min(maxSize, baseSize + Math.log10(cap) * 4);
      }
      case 'revenue': {
        const rev = node.metrics?.revenueB || 0.1;
        return Math.min(maxSize, baseSize + Math.log10(rev + 1) * 5);
      }
      case 'employees': {
        const emp = node.metrics?.employees || 100;
        return Math.min(maxSize, baseSize + Math.log10(emp) * 2.5);
      }
      case 'connections': {
        const conn = connectionCounts[node.id] || 1;
        return Math.min(maxSize, baseSize + conn * 1.5);
      }
      case 'centrality': {
        const score = analysis?.centralityScores[node.id] || 0;
        return Math.min(maxSize, baseSize + score * 20);
      }
      default:
        return 6;
    }
  }, [sizeBy, connectionCounts, analysis]);

  // Get node color
  const getNodeColor = useCallback((node: EntityNode): string => {
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
    
    let baseColor: string;
    switch (colorBy) {
      case 'type':
        baseColor = NODE_COLORS[node.type] || '#666';
        break;
      case 'category':
        baseColor = CATEGORY_COLORS[node.category] || '#666';
        break;
      case 'jurisdiction':
        baseColor = getJurisdictionColor(node.jurisdiction || 'unknown');
        break;
      case 'growth': {
        const growth = node.metrics?.yoyGrowth || 0;
        baseColor = growth > 20 ? '#4CAF50' : growth > 0 ? '#8BC34A' : growth > -10 ? '#FFC107' : '#F44336';
        break;
      }
      default:
        baseColor = NODE_COLORS[node.type] || '#666';
    }

    return isHighlighted ? baseColor : '#333333';
  }, [colorBy, highlightNodes]);

  // Get link color
  const getLinkColor = useCallback((link: Relationship): string => {
    const isHighlighted = highlightLinks.size === 0 || highlightLinks.has(link);
    const baseColor = LINK_COLORS[link.type] || '#666';
    return isHighlighted ? baseColor : '#222222';
  }, [highlightLinks]);

  // Handle node click
  const handleNodeClick = useCallback((node: EntityNode) => {
    setSelectedNode(node);
    setPathResult(null);

    // Zoom to node
    const distance = 200;
    const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);

    fgRef.current?.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      node as { x: number; y: number; z: number },
      2000
    );

    // Highlight connected nodes
    const connectedNodes = new Set<string>([node.id]);
    const connectedLinks = new Set<Relationship>();

    filteredData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;

      if (sourceId === node.id || targetId === node.id) {
        connectedLinks.add(link);
        connectedNodes.add(sourceId === node.id ? targetId : sourceId);
      }
    });

    setHighlightNodes(connectedNodes);
    setHighlightLinks(connectedLinks);
  }, [filteredData]);

  // Handle hover
  const handleNodeHover = useCallback((node: EntityNode | null) => {
    setHoveredNode(node);
    document.body.style.cursor = node ? 'pointer' : 'default';
  }, []);

  // Reset view
  const resetView = useCallback(() => {
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
    setSearchQuery('');
    setPathResult(null);
    fgRef.current?.cameraPosition({ x: 0, y: 0, z: 500 }, { x: 0, y: 0, z: 0 }, 1000);
  }, []);

  // Find path between two nodes
  const handleFindPath = useCallback(async (sourceId: string, targetId: string) => {
    setIsLoading(true);
    try {
      const result = await graphService.findPath({ sourceId, targetId, maxHops: 6 });
      setPathResult(result);

      if (result) {
        // Highlight path
        const pathNodeIds = new Set(result.path.map(n => n.id));
        setHighlightNodes(pathNodeIds);
        setHighlightLinks(new Set(result.edges));
      }
    } catch (error) {
      console.error('Path finding failed:', error);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Handle AI assistant actions
  const handleHighlightNodes = useCallback((nodeIds: string[]) => {
    setHighlightNodes(new Set(nodeIds));
  }, []);

  const handleZoomToNode = useCallback((nodeId: string) => {
    const node = filteredData.nodes.find(n => n.id === nodeId);
    if (node) handleNodeClick(node);
  }, [filteredData.nodes, handleNodeClick]);

  const handleFilterChange = useCallback((newFilters: Record<string, unknown>) => {
    setFilters(prev => ({
      ...prev,
      ...newFilters,
    }));
  }, []);

  // Get relationships for selected node
  const getNodeRelationships = useCallback((node: EntityNode) => {
    const relationships: Record<string, Array<{ node: EntityNode; link: Relationship; direction: 'in' | 'out' }>> = {};

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

  // Custom node rendering
  const nodeThreeObject = useCallback((nodeObj: object) => {
    const node = nodeObj as EntityNode;
    const isSelected = selectedNode?.id === node.id;
    const isHovered = hoveredNode?.id === node.id;
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
    const isOnPath = pathResult?.path.some(p => p.id === node.id);

    const group = new THREE.Group();

    const baseNodeSize = getNodeSize(node);
    const nodeSize = isSelected ? baseNodeSize * 1.5 : isHovered ? baseNodeSize * 1.2 : baseNodeSize;

    // Sphere for node
    const geometry = new THREE.SphereGeometry(nodeSize);
    const material = new THREE.MeshLambertMaterial({
      color: isOnPath ? '#FFD700' : getNodeColor(node),
      transparent: !isHighlighted,
      opacity: isHighlighted ? 1 : 0.3,
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);

    // Glow for selected/path nodes
    if (isSelected || isOnPath) {
      const glowGeometry = new THREE.SphereGeometry(nodeSize * 1.5);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color: isOnPath ? '#FFD700' : getNodeColor(node),
        transparent: true,
        opacity: 0.2,
      });
      const glow = new THREE.Mesh(glowGeometry, glowMaterial);
      group.add(glow);
    }

    // Label
    if (showLabels && isHighlighted) {
      const canvas = document.createElement('canvas');
      const context = canvas.getContext('2d')!;
      canvas.width = 512;
      canvas.height = 96;

      context.fillStyle = 'rgba(0, 0, 0, 0.85)';
      context.roundRect(0, 0, 512, 96, 8);
      context.fill();

      context.font = 'bold 28px Arial';
      context.fillStyle = '#ffffff';
      context.textAlign = 'center';
      context.fillText(node.name, 256, 35);

      const subtitle = node.industry || node.category;
      context.font = '20px Arial';
      context.fillStyle = '#9ca3af';
      context.fillText(subtitle, 256, 65);

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
  }, [selectedNode, hoveredNode, highlightNodes, getNodeColor, getNodeSize, showLabels, sizeBy, pathResult]);

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* Header with Tabs */}
      <header className="bg-gray-800 border-b border-gray-700">
        {/* Tab bar */}
        <div className="flex items-center px-4 py-2 gap-1 border-b border-gray-700">
          {TABS.map(tab => (
            <button
              key={tab.id}
              onClick={() => tab.available && setActiveTab(tab.id)}
              disabled={!tab.available}
              className={`px-4 py-2 rounded-t text-sm font-medium transition-colors ${
                activeTab === tab.id
                  ? 'bg-gray-700 text-white'
                  : tab.available
                  ? 'text-gray-400 hover:text-white hover:bg-gray-700/50'
                  : 'text-gray-600 cursor-not-allowed'
              }`}
            >
              <span className="mr-1">{tab.icon}</span>
              {tab.label}
              {!tab.available && <span className="ml-1 text-xs text-gray-500">(Soon)</span>}
            </button>
          ))}
        </div>

        {/* Controls bar (only for graph tab) */}
        {activeTab === 'graph' && (
          <div className="px-4 py-2 flex items-center justify-between flex-wrap gap-2">
            <div className="flex items-center gap-3">
              <h1 className="text-lg font-bold flex items-center gap-2">
                🔗 Entity Graph
              </h1>
              <span className="text-sm text-gray-400">
                {filteredData.nodes.length} entities • {filteredData.links.length} relationships
              </span>
            </div>

            <div className="flex items-center gap-2 flex-wrap">
              {/* Search */}
              <input
                type="text"
                placeholder="Search..."
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                className="bg-gray-700 border border-gray-600 rounded px-3 py-1.5 text-sm w-36 focus:outline-none focus:border-blue-500"
              />

              {/* Color by */}
              <select
                value={colorBy}
                onChange={e => setColorBy(e.target.value as ColorScheme)}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm"
              >
                <option value="type">Color: Type</option>
                <option value="category">Color: Category</option>
                <option value="jurisdiction">Color: Country</option>
                <option value="growth">Color: Growth</option>
              </select>

              {/* Size by */}
              <select
                value={sizeBy}
                onChange={e => setSizeBy(e.target.value as SizeMetric)}
                className="bg-gray-700 border border-gray-600 rounded px-2 py-1.5 text-sm"
              >
                <option value="uniform">Size: Uniform</option>
                <option value="marketCap">Size: Market Cap</option>
                <option value="revenue">Size: Revenue</option>
                <option value="employees">Size: Employees</option>
                <option value="connections">Size: Connections</option>
                <option value="centrality">Size: Centrality</option>
              </select>

              {/* Toggle buttons */}
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`px-3 py-1.5 rounded text-sm ${showFilters ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
              >
                🔍 Filters
              </button>

              <button
                onClick={() => setShowTimeline(!showTimeline)}
                className={`px-3 py-1.5 rounded text-sm ${showTimeline ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
              >
                ⏱️ Timeline
              </button>

              <button
                onClick={() => setShowAnalytics(!showAnalytics)}
                className={`px-3 py-1.5 rounded text-sm ${showAnalytics ? 'bg-blue-600' : 'bg-gray-700 hover:bg-gray-600'}`}
              >
                📊 Analytics
              </button>

              <button
                onClick={resetView}
                className="bg-gray-700 hover:bg-gray-600 px-3 py-1.5 rounded text-sm"
              >
                Reset
              </button>
            </div>
          </div>
        )}
      </header>

      {/* Main Content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Filter Sidebar */}
        {activeTab === 'graph' && (
          <FilterSidebar
            filters={filters}
            onFiltersChange={setFilters}
            isOpen={showFilters}
            onClose={() => setShowFilters(false)}
            availableJurisdictions={availableJurisdictions}
          />
        )}

        {/* Main Panel */}
        <div className="flex-1 flex flex-col">
          {activeTab === 'graph' && (
            <>
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
                  linkColor={(link) => getLinkColor(link as Relationship)}
                  linkWidth={(link) => highlightLinks.has(link as Relationship) ? 3 : 1}
                  linkOpacity={0.7}
                  linkDirectionalArrowLength={4}
                  linkDirectionalArrowRelPos={1}
                  linkCurvature={0.15}
                  linkLabel={showEdgeLabels ? (link) => {
                    const l = link as Relationship;
                    return l.label || l.type;
                  } : undefined}
                  linkDirectionalParticles={(link) => highlightLinks.has(link as Relationship) ? 4 : 0}
                  linkDirectionalParticleWidth={2}
                  linkDirectionalParticleSpeed={0.005}
                  onNodeClick={(node) => handleNodeClick(node as EntityNode)}
                  onNodeHover={(node) => handleNodeHover(node as EntityNode | null)}
                  onBackgroundClick={() => {
                    setSelectedNode(null);
                    setHighlightNodes(new Set());
                    setHighlightLinks(new Set());
                    setPathResult(null);
                  }}
                  backgroundColor="#111827"
                  showNavInfo={false}
                />

                {/* Legend */}
                <div className="absolute bottom-4 left-4 bg-gray-800/90 rounded-lg p-3 text-sm max-w-xs">
                  <h3 className="font-semibold mb-2">{colorBy === 'type' ? 'Entity Types' : colorBy === 'category' ? 'Categories' : 'Legend'}</h3>
                  <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                    {Object.entries(colorBy === 'type' ? NODE_COLORS : colorBy === 'category' ? CATEGORY_COLORS : NODE_COLORS)
                      .slice(0, 8)
                      .map(([key, color]) => (
                        <div key={key} className="flex items-center gap-2">
                          <span className="w-3 h-3 rounded-full" style={{ backgroundColor: color }} />
                          <span className="capitalize text-xs">{key.replace('_', ' ')}</span>
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
                        {sizeBy === 'centrality' && 'Sized by network centrality'}
                      </p>
                    </>
                  )}
                </div>

                {/* Path Result */}
                {pathResult && (
                  <div className="absolute top-4 left-4 bg-gray-800/95 rounded-lg p-3 max-w-sm">
                    <h3 className="font-semibold text-yellow-400 mb-2">🛤️ Path Found ({pathResult.hops} hops)</h3>
                    <div className="flex flex-wrap items-center gap-1 text-sm">
                      {pathResult.path.map((node, i) => (
                        <span key={node.id} className="flex items-center">
                          <button
                            onClick={() => handleNodeClick(node)}
                            className="bg-gray-700 hover:bg-gray-600 px-2 py-0.5 rounded"
                          >
                            {node.name}
                          </button>
                          {i < pathResult.path.length - 1 && (
                            <span className="mx-1 text-gray-500">→</span>
                          )}
                        </span>
                      ))}
                    </div>
                    <button
                      onClick={() => setPathResult(null)}
                      className="mt-2 text-xs text-gray-400 hover:text-white"
                    >
                      Clear path
                    </button>
                  </div>
                )}

                {/* Controls hint */}
                <div className="absolute bottom-4 right-4 bg-gray-800/90 rounded-lg p-3 text-xs text-gray-400">
                  <p>🖱️ Drag to rotate • Scroll to zoom</p>
                  <p>Click node to select • Click background to deselect</p>
                </div>
              </div>

              {/* Time Slider */}
              {showTimeline && (
                <TimeSlider
                  minDate={minDate}
                  maxDate={maxDate}
                  currentDate={currentDate}
                  onChange={setCurrentDate}
                  isPlaying={isPlaying}
                  onPlayToggle={() => setIsPlaying(!isPlaying)}
                />
              )}
            </>
          )}

          {activeTab === 'ai' && (
            <AIAssistant
              graphData={filteredData}
              onHighlightNodes={handleHighlightNodes}
              onZoomToNode={handleZoomToNode}
              onFilterChange={handleFilterChange}
              onFindPath={handleFindPath}
              selectedNode={selectedNode}
            />
          )}
        </div>

        {/* Right Panel: Analytics or Details */}
        {activeTab === 'graph' && showAnalytics && (
          <div className="w-80 bg-gray-800 border-l border-gray-700">
            <AnalyticsPanel
              graphData={filteredData}
              analysis={analysis}
              onNodeSelect={handleZoomToNode}
              isLoading={isLoading}
            />
          </div>
        )}

        {/* Right Panel: Entity Details */}
        {activeTab === 'graph' && selectedNode && !showAnalytics && (
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
                      {rels.slice(0, 5).map(({ node, direction }, i) => (
                        <button
                          key={i}
                          onClick={() => handleNodeClick(node)}
                          className="block w-full text-left bg-gray-700 hover:bg-gray-600 rounded px-2 py-1 text-sm"
                        >
                          <span className="text-gray-400">{direction === 'in' ? '← ' : '→ '}</span>
                          {node.name}
                        </button>
                      ))}
                      {rels.length > 5 && (
                        <span className="text-xs text-gray-500 ml-2">+{rels.length - 5} more</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              {/* Actions */}
              <div className="pt-4 border-t border-gray-700 space-y-2">
                <button className="w-full bg-blue-600 hover:bg-blue-700 rounded py-2 text-sm">
                  View SEC Filings →
                </button>
                <button
                  onClick={() => setActiveTab('ai')}
                  className="w-full bg-purple-600 hover:bg-purple-700 rounded py-2 text-sm"
                >
                  🤖 Ask AI About This Entity
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

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

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

function getJurisdictionColor(jurisdiction: string): string {
  const colors: Record<string, string> = {
    US: '#3B82F6',
    GB: '#EF4444',
    TW: '#10B981',
    KR: '#F59E0B',
    JP: '#EC4899',
    NL: '#FF5722',
    BE: '#FFC107',
    DE: '#9E9E9E',
    CN: '#DC2626',
  };
  return colors[jurisdiction] || '#666';
}
