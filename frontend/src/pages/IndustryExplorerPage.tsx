/**
 * Industry Explorer Page
 * 
 * Bloomberg Terminal-style industry explorer with:
 * - Global map showing company locations
 * - Interactive knowledge graph
 * - Industry dashboard with floating panels
 * - All views connected for seamless exploration
 * 
 * Layout modes:
 * - Dashboard: Map + Industry panels + Mini graph
 * - Graph: Full 3D graph with filters
 * - Split: Map + Graph side by side
 */

import { useState, useCallback, useMemo } from 'react';
import { getMockGraphData } from '../api/graphService';
import { GlobalMap } from '../components/graph/GlobalMap';
import { IndustryDashboard } from '../components/graph/IndustryDashboard';
import type { EntityNode, GraphData, GraphFilters } from '../types/graph';

// Layout modes
type LayoutMode = 'dashboard' | 'graph' | 'split' | 'map';

// Mini versions of components for dashboard layout
function MiniGraph({ 
  data, 
  onNodeClick,
  highlightedNodes 
}: { 
  data: GraphData; 
  onNodeClick: (node: EntityNode) => void;
  highlightedNodes: Set<string>;
}) {
  // Simple 2D representation for the mini view
  return (
    <div className="w-full h-full bg-gray-900 rounded-lg relative overflow-hidden">
      <svg className="w-full h-full" viewBox="0 0 400 300">
        {/* Draw edges */}
        {data.links.slice(0, 50).map((link, i) => {
          const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
          const targetId = typeof link.target === 'string' ? link.target : link.target.id;
          const sourceIdx = data.nodes.findIndex(n => n.id === sourceId);
          const targetIdx = data.nodes.findIndex(n => n.id === targetId);
          
          if (sourceIdx === -1 || targetIdx === -1) return null;
          
          // Simple circular layout
          const angle1 = (sourceIdx / data.nodes.length) * Math.PI * 2;
          const angle2 = (targetIdx / data.nodes.length) * Math.PI * 2;
          const x1 = 200 + Math.cos(angle1) * 120;
          const y1 = 150 + Math.sin(angle1) * 100;
          const x2 = 200 + Math.cos(angle2) * 120;
          const y2 = 150 + Math.sin(angle2) * 100;
          
          return (
            <line
              key={i}
              x1={x1}
              y1={y1}
              x2={x2}
              y2={y2}
              stroke="#374151"
              strokeWidth={0.5}
              opacity={0.3}
            />
          );
        })}
        
        {/* Draw nodes */}
        {data.nodes.map((node, i) => {
          const angle = (i / data.nodes.length) * Math.PI * 2;
          const x = 200 + Math.cos(angle) * 120;
          const y = 150 + Math.sin(angle) * 100;
          const isHighlighted = highlightedNodes.size === 0 || highlightedNodes.has(node.id);
          
          return (
            <g key={node.id}>
              <circle
                cx={x}
                cy={y}
                r={isHighlighted ? 6 : 4}
                fill={getNodeColor(node.type)}
                opacity={isHighlighted ? 1 : 0.3}
                className="cursor-pointer hover:opacity-100"
                onClick={() => onNodeClick(node)}
              />
            </g>
          );
        })}
      </svg>
      
      {/* Overlay message */}
      <div className="absolute bottom-2 right-2 text-xs text-gray-500">
        Click to explore in full graph →
      </div>
    </div>
  );
}

function getNodeColor(type: string): string {
  const colors: Record<string, string> = {
    public_company: '#4CAF50',
    private_company: '#9E9E9E',
    subsidiary: '#795548',
    investor: '#FFC107',
    startup: '#E91E63',
    foundry: '#2196F3',
    equipment: '#FF5722',
    hyperscaler: '#9C27B0',
  };
  return colors[type] || '#666';
}

export default function IndustryExplorerPage() {
  // Data
  const [graphData] = useState<GraphData>(getMockGraphData());
  
  // UI state
  const [layoutMode, setLayoutMode] = useState<LayoutMode>('dashboard');
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [selectedCountry, setSelectedCountry] = useState<string | null>(null);
  const [selectedIndustry, setSelectedIndustry] = useState<string | null>(null);
  const [highlightedNodes, setHighlightedNodes] = useState<Set<string>>(new Set());
  const [mapMetric, setMapMetric] = useState<'marketCap' | 'count' | 'revenue'>('marketCap');
  
  // Filters (reserved for advanced filtering)
  const [_filters, _setFilters] = useState<GraphFilters>({
    entityTypes: [],
    relationshipTypes: [],
    categories: [],
    jurisdictions: [],
  });
  void _filters;

  // Filter data based on selections
  const filteredData = useMemo(() => {
    let nodes = graphData.nodes;
    let links = graphData.links;

    // Filter by country
    if (selectedCountry) {
      nodes = nodes.filter(n => n.jurisdiction === selectedCountry);
    }

    // Filter by industry
    if (selectedIndustry) {
      nodes = nodes.filter(n => n.industry === selectedIndustry);
    }

    // Filter links to only include visible nodes
    const nodeIds = new Set(nodes.map(n => n.id));
    links = links.filter(l => {
      const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
      const targetId = typeof l.target === 'string' ? l.target : l.target.id;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });

    return { nodes, links };
  }, [graphData, selectedCountry, selectedIndustry]);

  // Handlers
  const handleNodeSelect = useCallback((node: EntityNode) => {
    setSelectedNode(node);
    setHighlightedNodes(new Set([node.id]));
  }, []);

  const handleCountryClick = useCallback((code: string) => {
    setSelectedCountry(prev => prev === code ? null : code);
    setSelectedNode(null);
  }, []);

  const handleIndustrySelect = useCallback((industry: string | null) => {
    setSelectedIndustry(industry);
    setSelectedNode(null);
  }, []);

  const handleFilterChange = useCallback((newFilters: Record<string, unknown>) => {
    _setFilters(prev => ({ ...prev, ...newFilters }));
  }, []);

  const clearAllSelections = useCallback(() => {
    setSelectedNode(null);
    setSelectedCountry(null);
    setSelectedIndustry(null);
    setHighlightedNodes(new Set());
  }, []);

  return (
    <div className="h-screen flex flex-col bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-4 py-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold flex items-center gap-2">
              <span>🌐</span> Industry Explorer
            </h1>
            
            {/* Active filters badges */}
            <div className="flex items-center gap-2">
              {selectedCountry && (
                <span className="bg-blue-600 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                  🌍 {selectedCountry}
                  <button onClick={() => setSelectedCountry(null)} className="hover:text-red-300">×</button>
                </span>
              )}
              {selectedIndustry && (
                <span className="bg-purple-600 text-xs px-2 py-1 rounded-full flex items-center gap-1">
                  🏭 {selectedIndustry}
                  <button onClick={() => setSelectedIndustry(null)} className="hover:text-red-300">×</button>
                </span>
              )}
              {(selectedCountry || selectedIndustry) && (
                <button
                  onClick={clearAllSelections}
                  className="text-xs text-gray-400 hover:text-white"
                >
                  Clear all
                </button>
              )}
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Stats */}
            <div className="text-sm text-gray-400 mr-4">
              {filteredData.nodes.length} entities • {filteredData.links.length} relationships
            </div>
            
            {/* Layout mode switcher */}
            <div className="flex bg-gray-700 rounded-lg p-0.5">
              {[
                { mode: 'dashboard' as const, icon: '📊', label: 'Dashboard' },
                { mode: 'map' as const, icon: '🗺️', label: 'Map' },
                { mode: 'split' as const, icon: '⬛', label: 'Split' },
                { mode: 'graph' as const, icon: '🔗', label: 'Graph' },
              ].map(({ mode, icon, label }) => (
                <button
                  key={mode}
                  onClick={() => setLayoutMode(mode)}
                  className={`px-3 py-1.5 rounded text-sm flex items-center gap-1 transition-colors ${
                    layoutMode === mode
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-400 hover:text-white'
                  }`}
                  title={label}
                >
                  {icon} <span className="hidden md:inline">{label}</span>
                </button>
              ))}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {layoutMode === 'dashboard' && (
          <DashboardLayout
            graphData={filteredData}
            onNodeSelect={handleNodeSelect}
            onCountryClick={handleCountryClick}
            onIndustrySelect={handleIndustrySelect}
            onFilterChange={handleFilterChange}
            selectedNode={selectedNode}
            selectedCountry={selectedCountry}
            selectedIndustry={selectedIndustry}
            highlightedNodes={highlightedNodes}
            mapMetric={mapMetric}
            setMapMetric={setMapMetric}
            setLayoutMode={setLayoutMode}
          />
        )}

        {layoutMode === 'map' && (
          <MapLayout
            graphData={filteredData}
            onNodeSelect={handleNodeSelect}
            onCountryClick={handleCountryClick}
            selectedNode={selectedNode}
            selectedCountry={selectedCountry}
            mapMetric={mapMetric}
            setMapMetric={setMapMetric}
          />
        )}

        {layoutMode === 'split' && (
          <SplitLayout
            graphData={filteredData}
            onNodeSelect={handleNodeSelect}
            onCountryClick={handleCountryClick}
            selectedNode={selectedNode}
            selectedCountry={selectedCountry}
            highlightedNodes={highlightedNodes}
            mapMetric={mapMetric}
            setMapMetric={setMapMetric}
          />
        )}

        {layoutMode === 'graph' && (
          <div className="h-full flex items-center justify-center text-gray-500">
            <div className="text-center">
              <div className="text-6xl mb-4">🔗</div>
              <p>Full 3D Graph View</p>
              <p className="text-sm">Go to <a href="/graph" className="text-blue-400 hover:underline">/graph</a> for the full experience</p>
            </div>
          </div>
        )}
      </div>

      {/* Selected Entity Detail Panel (floating) */}
      {selectedNode && (
        <EntityDetailPanel
          node={selectedNode}
          graphData={filteredData}
          onClose={() => setSelectedNode(null)}
          onNodeSelect={handleNodeSelect}
        />
      )}
    </div>
  );
}

// =============================================================================
// LAYOUT COMPONENTS
// =============================================================================

interface DashboardLayoutProps {
  graphData: GraphData;
  onNodeSelect: (node: EntityNode) => void;
  onCountryClick: (code: string) => void;
  onIndustrySelect: (industry: string | null) => void;
  onFilterChange: (filters: Record<string, unknown>) => void;
  selectedNode: EntityNode | null;
  selectedCountry: string | null;
  selectedIndustry: string | null;
  highlightedNodes: Set<string>;
  mapMetric: 'marketCap' | 'count' | 'revenue';
  setMapMetric: (m: 'marketCap' | 'count' | 'revenue') => void;
  setLayoutMode: (mode: LayoutMode) => void;
}

function DashboardLayout({
  graphData,
  onNodeSelect,
  onCountryClick,
  onIndustrySelect,
  onFilterChange,
  selectedCountry,
  selectedIndustry,
  highlightedNodes,
  mapMetric,
  setMapMetric,
  setLayoutMode,
}: DashboardLayoutProps) {
  return (
    <div className="h-full grid grid-cols-12 gap-2 p-2">
      {/* Left: Map + Mini Graph */}
      <div className="col-span-8 flex flex-col gap-2">
        {/* Global Map */}
        <div className="flex-1 bg-gray-800 rounded-lg overflow-hidden relative">
          <div className="absolute top-2 left-2 z-10 flex gap-2">
            <select
              value={mapMetric}
              onChange={e => setMapMetric(e.target.value as typeof mapMetric)}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs"
            >
              <option value="marketCap">Size: Market Cap</option>
              <option value="count">Size: Company Count</option>
              <option value="revenue">Size: Revenue</option>
            </select>
          </div>
          <GlobalMap
            nodes={graphData.nodes}
            onCountryClick={onCountryClick}
            onNodeClick={onNodeSelect}
            selectedCountry={selectedCountry}
            colorMetric={mapMetric}
          />
        </div>

        {/* Mini Graph */}
        <div className="h-48 bg-gray-800 rounded-lg p-2">
          <div className="flex items-center justify-between mb-1">
            <h3 className="text-sm font-medium text-gray-400">Knowledge Graph Preview</h3>
            <button
              onClick={() => setLayoutMode('graph')}
              className="text-xs text-blue-400 hover:text-blue-300"
            >
              Open Full Graph →
            </button>
          </div>
          <MiniGraph
            data={graphData}
            onNodeClick={onNodeSelect}
            highlightedNodes={highlightedNodes}
          />
        </div>
      </div>

      {/* Right: Industry Dashboard */}
      <div className="col-span-4 bg-gray-800 rounded-lg overflow-hidden">
        <IndustryDashboard
          graphData={graphData}
          onNodeSelect={onNodeSelect}
          onFilterChange={onFilterChange}
          selectedIndustry={selectedIndustry}
          onIndustrySelect={onIndustrySelect}
        />
      </div>
    </div>
  );
}

interface MapLayoutProps {
  graphData: GraphData;
  onNodeSelect: (node: EntityNode) => void;
  onCountryClick: (code: string) => void;
  selectedNode: EntityNode | null;
  selectedCountry: string | null;
  mapMetric: 'marketCap' | 'count' | 'revenue';
  setMapMetric: (m: 'marketCap' | 'count' | 'revenue') => void;
}

function MapLayout({
  graphData,
  onNodeSelect,
  onCountryClick,
  selectedCountry,
  mapMetric,
  setMapMetric,
}: MapLayoutProps) {
  return (
    <div className="h-full p-2">
      <div className="h-full bg-gray-800 rounded-lg overflow-hidden relative">
        <div className="absolute top-4 left-4 z-10 flex gap-2">
          <select
            value={mapMetric}
            onChange={e => setMapMetric(e.target.value as typeof mapMetric)}
            className="bg-gray-700 border border-gray-600 rounded px-3 py-2 text-sm"
          >
            <option value="marketCap">Size by Market Cap</option>
            <option value="count">Size by Company Count</option>
            <option value="revenue">Size by Revenue</option>
          </select>
        </div>
        
        {/* Country company list */}
        {selectedCountry && (
          <div className="absolute top-4 right-4 z-10 w-72 max-h-96 bg-gray-800 border border-gray-600 rounded-lg overflow-hidden">
            <div className="p-3 border-b border-gray-700 font-semibold">
              Companies in {selectedCountry}
            </div>
            <div className="max-h-80 overflow-y-auto">
              {graphData.nodes
                .filter(n => n.jurisdiction === selectedCountry)
                .sort((a, b) => (b.metrics?.marketCapB || 0) - (a.metrics?.marketCapB || 0))
                .map(node => (
                  <button
                    key={node.id}
                    onClick={() => onNodeSelect(node)}
                    className="w-full flex items-center justify-between p-2 hover:bg-gray-700 text-left"
                  >
                    <div>
                      <div className="font-medium">{node.name}</div>
                      <div className="text-xs text-gray-400">{node.industry}</div>
                    </div>
                    {node.metrics?.marketCapB && (
                      <div className="text-green-400 text-sm">${node.metrics.marketCapB}B</div>
                    )}
                  </button>
                ))}
            </div>
          </div>
        )}
        
        <GlobalMap
          nodes={graphData.nodes}
          onCountryClick={onCountryClick}
          onNodeClick={onNodeSelect}
          selectedCountry={selectedCountry}
          colorMetric={mapMetric}
        />
      </div>
    </div>
  );
}

interface SplitLayoutProps {
  graphData: GraphData;
  onNodeSelect: (node: EntityNode) => void;
  onCountryClick: (code: string) => void;
  selectedNode: EntityNode | null;
  selectedCountry: string | null;
  highlightedNodes: Set<string>;
  mapMetric: 'marketCap' | 'count' | 'revenue';
  setMapMetric: (m: 'marketCap' | 'count' | 'revenue') => void;
}

function SplitLayout({
  graphData,
  onNodeSelect,
  onCountryClick,
  selectedCountry,
  highlightedNodes,
  mapMetric,
  setMapMetric,
}: SplitLayoutProps) {
  return (
    <div className="h-full grid grid-cols-2 gap-2 p-2">
      {/* Left: Map */}
      <div className="bg-gray-800 rounded-lg overflow-hidden relative">
        <div className="absolute top-2 left-2 z-10">
          <select
            value={mapMetric}
            onChange={e => setMapMetric(e.target.value as typeof mapMetric)}
            className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs"
          >
            <option value="marketCap">Market Cap</option>
            <option value="count">Count</option>
            <option value="revenue">Revenue</option>
          </select>
        </div>
        <GlobalMap
          nodes={graphData.nodes}
          onCountryClick={onCountryClick}
          onNodeClick={onNodeSelect}
          selectedCountry={selectedCountry}
          colorMetric={mapMetric}
        />
      </div>

      {/* Right: Mini Graph */}
      <div className="bg-gray-800 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-400 mb-2">Entity Network</h3>
        <div className="h-[calc(100%-2rem)]">
          <MiniGraph
            data={graphData}
            onNodeClick={onNodeSelect}
            highlightedNodes={highlightedNodes}
          />
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// ENTITY DETAIL PANEL
// =============================================================================

interface EntityDetailPanelProps {
  node: EntityNode;
  graphData: GraphData;
  onClose: () => void;
  onNodeSelect: (node: EntityNode) => void;
}

function EntityDetailPanel({ node, graphData, onClose, onNodeSelect }: EntityDetailPanelProps) {
  // Find relationships
  const relationships = useMemo(() => {
    const rels: Array<{ type: string; node: EntityNode; direction: 'in' | 'out' }> = [];
    
    graphData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      
      if (sourceId === node.id) {
        const targetNode = graphData.nodes.find(n => n.id === targetId);
        if (targetNode) rels.push({ type: link.type, node: targetNode, direction: 'out' });
      } else if (targetId === node.id) {
        const sourceNode = graphData.nodes.find(n => n.id === sourceId);
        if (sourceNode) rels.push({ type: link.type, node: sourceNode, direction: 'in' });
      }
    });
    
    return rels;
  }, [node, graphData]);

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-[70vh] bg-gray-800 border border-gray-600 rounded-lg shadow-2xl overflow-hidden z-50">
      {/* Header */}
      <div className="bg-gray-700 p-3 flex items-start justify-between">
        <div>
          <h3 className="font-bold text-lg">{node.name}</h3>
          <div className="flex items-center gap-2 mt-1">
            <span
              className="px-2 py-0.5 rounded text-xs"
              style={{ backgroundColor: getNodeColor(node.type) }}
            >
              {node.type.replace('_', ' ')}
            </span>
            {node.identifiers?.ticker && (
              <span className="text-xs text-gray-400">${node.identifiers.ticker}</span>
            )}
          </div>
        </div>
        <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">×</button>
      </div>

      {/* Content */}
      <div className="p-3 overflow-y-auto max-h-[50vh]">
        {/* Industry & Location */}
        <div className="flex items-center gap-2 mb-3 text-sm">
          <span className="bg-gray-700 px-2 py-1 rounded">{node.industry}</span>
          {node.jurisdiction && (
            <span className="bg-gray-700 px-2 py-1 rounded">
              {getFlagEmoji(node.jurisdiction)} {node.jurisdiction}
            </span>
          )}
        </div>

        {/* Metrics */}
        {node.metrics && (
          <div className="grid grid-cols-2 gap-2 mb-3">
            {node.metrics.marketCapB && (
              <div className="bg-gray-700 rounded p-2">
                <div className="text-xs text-gray-400">Market Cap</div>
                <div className="text-lg font-bold text-green-400">
                  ${node.metrics.marketCapB >= 1000 
                    ? (node.metrics.marketCapB / 1000).toFixed(1) + 'T'
                    : node.metrics.marketCapB + 'B'}
                </div>
              </div>
            )}
            {node.metrics.revenueB && (
              <div className="bg-gray-700 rounded p-2">
                <div className="text-xs text-gray-400">Revenue</div>
                <div className="text-lg font-bold text-blue-400">${node.metrics.revenueB}B</div>
              </div>
            )}
            {node.metrics.employees && (
              <div className="bg-gray-700 rounded p-2">
                <div className="text-xs text-gray-400">Employees</div>
                <div className="text-lg font-bold text-purple-400">
                  {(node.metrics.employees / 1000).toFixed(0)}K
                </div>
              </div>
            )}
            {node.metrics.yoyGrowth !== undefined && (
              <div className="bg-gray-700 rounded p-2">
                <div className="text-xs text-gray-400">YoY Growth</div>
                <div className={`text-lg font-bold ${node.metrics.yoyGrowth >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                  {node.metrics.yoyGrowth > 0 ? '+' : ''}{node.metrics.yoyGrowth}%
                </div>
              </div>
            )}
          </div>
        )}

        {/* Relationships */}
        <div>
          <h4 className="text-sm font-medium text-gray-400 mb-2">
            Relationships ({relationships.length})
          </h4>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {relationships.slice(0, 10).map((rel, i) => (
              <button
                key={i}
                onClick={() => onNodeSelect(rel.node)}
                className="w-full flex items-center gap-2 bg-gray-700 hover:bg-gray-600 rounded p-2 text-sm text-left"
              >
                <span className="text-gray-500">
                  {rel.direction === 'in' ? '←' : '→'}
                </span>
                <span className="capitalize text-xs text-gray-400 w-16">{rel.type}</span>
                <span className="flex-1 truncate">{rel.node.name}</span>
              </button>
            ))}
            {relationships.length > 10 && (
              <div className="text-xs text-gray-500 text-center py-1">
                +{relationships.length - 10} more
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Footer actions */}
      <div className="p-3 border-t border-gray-700 flex gap-2">
        <button className="flex-1 bg-blue-600 hover:bg-blue-700 rounded py-2 text-sm">
          View Filings
        </button>
        <button className="flex-1 bg-gray-700 hover:bg-gray-600 rounded py-2 text-sm">
          Explore Graph
        </button>
      </div>
    </div>
  );
}

function getFlagEmoji(code: string): string {
  const flags: Record<string, string> = {
    US: '🇺🇸', GB: '🇬🇧', TW: '🇹🇼', KR: '🇰🇷', JP: '🇯🇵',
    NL: '🇳🇱', BE: '🇧🇪', DE: '🇩🇪', CN: '🇨🇳',
  };
  return flags[code] || '🌍';
}
