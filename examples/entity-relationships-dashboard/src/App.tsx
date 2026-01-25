/**
 * Entity Relationships Dashboard
 * Bloomberg/FactSet style entity profile with 3D relationship graph
 */

import { useState, useRef, useCallback, useMemo, useEffect } from 'react';
import ForceGraph3D, { ForceGraphMethods } from 'react-force-graph-3d';
import * as THREE from 'three';
import {
  Building2,
  TrendingUp,
  TrendingDown,
  Globe,
  Phone,
  MapPin,
  Users,
  FileText,
  ChevronDown,
  ChevronRight,
  ExternalLink,
  Star,
  DollarSign,
  BarChart3,
  PieChart,
  Clock,
  Search,
  Filter,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  Maximize2,
  Minimize2,
  Network,
  List,
  GitBranch,
  Hash,
  X,
  Info,
  Link2,
  Briefcase,
} from 'lucide-react';
import clsx from 'clsx';
import {
  BOEING_PROFILE,
  BOEING_HIERARCHY,
  BOEING_ECOSYSTEM,
  NODE_COLORS,
  CATEGORY_COLORS,
  LINK_COLORS,
  INDUSTRY_STATS,
  EntityNode,
  RelationshipLink,
  HierarchyEntity,
} from './data';

// ============================================================================
// SUB-COMPONENTS
// ============================================================================

// Collapsible Section
function Section({ 
  title, 
  icon: Icon, 
  children, 
  defaultOpen = true,
  className = '',
}: {
  title: string;
  icon: React.ElementType;
  children: React.ReactNode;
  defaultOpen?: boolean;
  className?: string;
}) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  
  return (
    <div className={clsx('card rounded-xl overflow-hidden', className)}>
      <div 
        className="card-header flex items-center justify-between px-4 py-2.5 cursor-pointer hover:bg-gray-800/50 transition-colors"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-2">
          <Icon className="w-4 h-4 text-gray-400" />
          <h3 className="font-semibold text-white text-sm">{title}</h3>
        </div>
        {isOpen ? (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronRight className="w-4 h-4 text-gray-400" />
        )}
      </div>
      {isOpen && <div className="p-4">{children}</div>}
    </div>
  );
}

// Metric Row
function MetricRow({ label, value, change }: { label: string; value: string | number; change?: number }) {
  return (
    <div className="flex justify-between items-center py-1.5 text-sm border-b border-gray-700/50 last:border-0">
      <span className="text-gray-400">{label}</span>
      <div className="flex items-center gap-2">
        <span className="font-medium text-white">{value}</span>
        {change !== undefined && (
          <span className={clsx('text-xs', change >= 0 ? 'text-green-400' : 'text-red-400')}>
            {change >= 0 ? '+' : ''}{change.toFixed(1)}%
          </span>
        )}
      </div>
    </div>
  );
}

// Identifier Badge
function IdentifierBadge({ scheme, value }: { scheme: string; value: string }) {
  const colors: Record<string, string> = {
    CIK: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
    LEI: 'bg-green-500/20 text-green-400 border-green-500/30',
    EIN: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
    DUNS: 'bg-orange-500/20 text-orange-400 border-orange-500/30',
    ISIN: 'bg-cyan-500/20 text-cyan-400 border-cyan-500/30',
    CUSIP: 'bg-pink-500/20 text-pink-400 border-pink-500/30',
  };
  
  return (
    <span className={clsx(
      'inline-flex items-center gap-1 px-2 py-0.5 rounded text-xs font-medium border',
      colors[scheme] || 'bg-gray-500/20 text-gray-400 border-gray-500/30'
    )}>
      <span className="font-bold">{scheme}:</span>
      <span className="font-mono">{value}</span>
    </span>
  );
}

// Hierarchy Tree Node
function HierarchyTreeNode({ 
  entity, 
  level = 0,
  expanded,
  onToggle,
}: { 
  entity: HierarchyEntity; 
  level?: number;
  expanded: Record<string, boolean>;
  onToggle: (id: string) => void;
}) {
  const hasChildren = entity.children && entity.children.length > 0;
  const isExpanded = expanded[entity.id] ?? (level < 2);
  
  const relationshipColor: Record<string, string> = {
    'Parent': 'bg-purple-500/20 text-purple-400',
    'Subsidiary': 'bg-blue-500/20 text-blue-400',
    'Related Entity': 'bg-orange-500/20 text-orange-400',
    'Integrated': 'bg-green-500/20 text-green-400',
    'Jointly Owned': 'bg-yellow-500/20 text-yellow-400',
  };
  
  return (
    <div className={clsx(level > 0 && 'ml-5')}>
      <div className={clsx(
        'flex items-center gap-2 py-1.5 px-2 rounded-lg hover:bg-gray-800/50 group border-l-2 transition-colors',
        level === 0 ? 'border-purple-500' : 'border-gray-600'
      )}>
        {hasChildren ? (
          <button
            onClick={() => onToggle(entity.id)}
            className="p-0.5 hover:bg-gray-700 rounded"
          >
            {isExpanded ? (
              <ChevronDown className="w-3.5 h-3.5 text-gray-400" />
            ) : (
              <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
            )}
          </button>
        ) : (
          <span className="w-4.5" />
        )}
        
        <div className="w-3 h-px bg-gray-600" />
        
        <div className="flex-1 min-w-0">
          <span className="font-medium text-white text-sm truncate">{entity.name}</span>
        </div>
        
        <span className={clsx(
          'text-xs px-2 py-0.5 rounded font-medium whitespace-nowrap',
          relationshipColor[entity.relationship] || 'bg-gray-500/20 text-gray-400'
        )}>
          {entity.relationship}
        </span>
        
        <span className="text-xs text-gray-500 w-28 truncate hidden lg:block">
          {entity.incorporation || 'N/A'}
        </span>
        
        <span className="text-xs text-gray-500 w-24 truncate hidden xl:block">
          {entity.industry || 'N/A'}
        </span>
      </div>
      
      {hasChildren && isExpanded && (
        <div className="border-l border-gray-700 ml-2.5">
          {entity.children!.map((child) => (
            <HierarchyTreeNode
              key={child.id}
              entity={child}
              level={level + 1}
              expanded={expanded}
              onToggle={onToggle}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

export default function App() {
  // State
  const [activeView, setActiveView] = useState<'dashboard' | 'graph' | 'hierarchy'>('dashboard');
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<RelationshipLink>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [hierarchyExpanded, setHierarchyExpanded] = useState<Record<string, boolean>>({ boeing: true });
  const [isGraphFullscreen, setIsGraphFullscreen] = useState(false);
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<Set<string>>(new Set(['company', 'subsidiary', 'person', 'fund', 'government', 'organization']));
  
  const fgRef = useRef<ForceGraphMethods>();
  const profile = BOEING_PROFILE;
  
  // Mock price
  const currentPrice = 127.64;
  const priceChange = -3.83;
  const priceChangePercent = -2.91;

  // Filter nodes
  const filteredData = useMemo(() => {
    const query = searchQuery.toLowerCase();
    const filteredNodes = BOEING_ECOSYSTEM.nodes.filter(node => {
      const matchesSearch = !query || 
        node.name.toLowerCase().includes(query) ||
        node.id.toLowerCase().includes(query) ||
        (node.description?.toLowerCase().includes(query));
      const matchesType = selectedTypes.has(node.type);
      return matchesSearch && matchesType;
    });
    
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = BOEING_ECOSYSTEM.links.filter(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });
    
    return { nodes: filteredNodes, links: filteredLinks };
  }, [searchQuery, selectedTypes]);

  // Node connections
  const nodeConnections = useMemo(() => {
    const connections: Record<string, number> = {};
    filteredData.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      connections[sourceId] = (connections[sourceId] || 0) + 1;
      connections[targetId] = (connections[targetId] || 0) + 1;
    });
    return connections;
  }, [filteredData]);

  // Get node size
  const getNodeSize = useCallback((node: EntityNode) => {
    const baseSize = 5;
    const maxSize = 18;
    if (node.marketCap) {
      const maxCap = Math.max(...BOEING_ECOSYSTEM.nodes.map(n => n.marketCap || 0));
      return baseSize + (node.marketCap / maxCap) * (maxSize - baseSize);
    }
    const conns = nodeConnections[node.id] || 0;
    const maxConns = Math.max(...Object.values(nodeConnections), 1);
    return baseSize + (conns / maxConns) * (maxSize - baseSize);
  }, [nodeConnections]);

  // Handle node click
  const handleNodeClick = useCallback((node: EntityNode) => {
    setSelectedNode(node);
    
    const connectedNodes = new Set<string>([node.id]);
    const connectedLinks = new Set<RelationshipLink>();
    
    BOEING_ECOSYSTEM.links.forEach(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      
      if (sourceId === node.id || targetId === node.id) {
        connectedNodes.add(sourceId);
        connectedNodes.add(targetId);
        connectedLinks.add(link);
      }
    });
    
    setHighlightNodes(connectedNodes);
    setHighlightLinks(connectedLinks);
    
    if (fgRef.current) {
      const distance = 200;
      const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
      fgRef.current.cameraPosition(
        { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
        { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
        1500
      );
    }
  }, []);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
  }, []);

  // Reset camera
  const resetCamera = useCallback(() => {
    if (fgRef.current) {
      fgRef.current.cameraPosition({ x: 0, y: 0, z: 600 }, { x: 0, y: 0, z: 0 }, 1000);
    }
    clearSelection();
  }, [clearSelection]);

  // Format currency
  const formatCurrency = (value: number) => {
    if (value >= 1e12) return `$${(value / 1e12).toFixed(2)}T`;
    if (value >= 1e9) return `$${(value / 1e9).toFixed(2)}B`;
    if (value >= 1e6) return `$${(value / 1e6).toFixed(2)}M`;
    return `$${value.toLocaleString()}`;
  };

  // Get relationships for node
  const getNodeRelationships = useCallback((node: EntityNode) => {
    return BOEING_ECOSYSTEM.links.filter(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      return sourceId === node.id || targetId === node.id;
    }).map(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      const isSource = sourceId === node.id;
      const otherId = isSource ? targetId : sourceId;
      const otherNode = BOEING_ECOSYSTEM.nodes.find(n => n.id === otherId);
      return { ...link, direction: isSource ? 'outgoing' : 'incoming', otherNode };
    });
  }, []);

  // Hierarchy toggle
  const toggleHierarchyExpanded = useCallback((id: string) => {
    setHierarchyExpanded(prev => ({ ...prev, [id]: !prev[id] }));
  }, []);

  // Count hierarchy entities
  const countEntities = (entity: HierarchyEntity): number => {
    let count = 1;
    if (entity.children) {
      entity.children.forEach(child => count += countEntities(child));
    }
    return count;
  };

  // ============================================================================
  // RENDER
  // ============================================================================

  return (
    <div className="h-full w-full flex flex-col bg-slate-950">
      {/* Header */}
      <header className="flex-shrink-0 border-b border-gray-800 bg-slate-900/80 backdrop-blur">
        <div className="flex items-center justify-between px-4 py-3">
          <div className="flex items-center gap-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-blue-500 to-blue-600 text-white font-bold">
              B
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-white">{profile.primaryName}</h1>
                <span className="text-blue-400 font-semibold">({profile.listings[0].ticker}:NYSE)</span>
                <Star className="w-4 h-4 text-gray-500 hover:text-yellow-400 cursor-pointer" />
              </div>
              <div className="flex items-center gap-3 text-sm">
                <span className="text-gray-400">{profile.sector} • {profile.industry}</span>
                <span className="px-1.5 py-0.5 rounded bg-green-500/20 text-green-400 text-xs">Active</span>
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-6">
            {/* Price */}
            <div className="text-right">
              <div className="text-2xl font-bold text-white">${currentPrice.toFixed(2)}</div>
              <div className={clsx('flex items-center justify-end gap-1', priceChange >= 0 ? 'text-green-400' : 'text-red-400')}>
                {priceChange >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                <span>{priceChange >= 0 ? '+' : ''}{priceChange.toFixed(2)} ({priceChangePercent.toFixed(2)}%)</span>
              </div>
            </div>
            
            {/* View Toggles */}
            <div className="flex gap-1 bg-gray-800 rounded-lg p-1">
              <button
                onClick={() => setActiveView('dashboard')}
                className={clsx(
                  'px-3 py-1.5 rounded text-sm font-medium transition-colors',
                  activeView === 'dashboard' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                )}
              >
                Dashboard
              </button>
              <button
                onClick={() => setActiveView('graph')}
                className={clsx(
                  'px-3 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-1.5',
                  activeView === 'graph' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                )}
              >
                <Network className="w-4 h-4" />
                3D Graph
              </button>
              <button
                onClick={() => setActiveView('hierarchy')}
                className={clsx(
                  'px-3 py-1.5 rounded text-sm font-medium transition-colors flex items-center gap-1.5',
                  activeView === 'hierarchy' ? 'bg-blue-600 text-white' : 'text-gray-400 hover:text-white'
                )}
              >
                <GitBranch className="w-4 h-4" />
                Hierarchy
              </button>
            </div>
          </div>
        </div>
        
        {/* Identifiers Bar */}
        <div className="flex items-center gap-2 px-4 py-2 border-t border-gray-800/50">
          {profile.identifiers.slice(0, 6).map((id) => (
            <IdentifierBadge key={id.scheme} scheme={id.scheme} value={id.value} />
          ))}
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {activeView === 'dashboard' && (
          <div className="h-full overflow-auto p-4">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
              {/* Left Column - Company Info */}
              <div className="lg:col-span-2 space-y-4">
                {/* Quick Stats */}
                <div className="grid grid-cols-5 gap-3">
                  {[
                    { label: 'Market Cap', value: formatCurrency(profile.financials.marketCap) },
                    { label: 'Revenue', value: formatCurrency(profile.financials.revenue) },
                    { label: 'Employees', value: profile.employees.toLocaleString() },
                    { label: '52W Range', value: `$${profile.keyStats['52WeekLow']} - $${profile.keyStats['52WeekHigh']}` },
                    { label: 'Inst. Ownership', value: `${profile.keyStats.institutionalOwnership}%` },
                  ].map((stat) => (
                    <div key={stat.label} className="card rounded-lg p-3">
                      <div className="text-xs text-gray-400">{stat.label}</div>
                      <div className="font-semibold text-white mt-0.5">{stat.value}</div>
                    </div>
                  ))}
                </div>
                
                {/* Business Description */}
                <Section title="Business Description" icon={FileText}>
                  <p className="text-sm text-gray-300 leading-relaxed">{profile.description}</p>
                </Section>
                
                {/* Mini Graph Preview */}
                <Section title="Entity Relationships Preview" icon={Network}>
                  <div className="h-64 bg-gray-900 rounded-lg overflow-hidden relative">
                    <ForceGraph3D
                      graphData={{ nodes: filteredData.nodes.slice(0, 20), links: filteredData.links.slice(0, 30) }}
                      nodeId="id"
                      nodeLabel={(node: EntityNode) => node.name}
                      nodeColor={(node: EntityNode) => CATEGORY_COLORS[node.category || ''] || NODE_COLORS[node.type]}
                      nodeVal={(node: EntityNode) => getNodeSize(node) * 0.7}
                      linkColor={(link: RelationshipLink) => LINK_COLORS[link.type] || '#6B7280'}
                      linkWidth={1}
                      backgroundColor="#0f172a"
                      width={undefined}
                      height={256}
                      enableNavigationControls={false}
                    />
                    <button
                      onClick={() => setActiveView('graph')}
                      className="absolute bottom-3 right-3 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white text-xs rounded-lg flex items-center gap-1"
                    >
                      <Maximize2 className="w-3 h-3" />
                      Open Full Graph
                    </button>
                  </div>
                </Section>
                
                {/* Corporate Structure Summary */}
                <Section title="Corporate Structure" icon={Building2}>
                  <div className="flex items-center justify-between mb-3">
                    <span className="text-sm text-gray-400">
                      Total Entities: <span className="text-blue-400 font-medium">{countEntities(BOEING_HIERARCHY)}</span>
                    </span>
                    <button
                      onClick={() => setActiveView('hierarchy')}
                      className="text-xs text-blue-400 hover:underline"
                    >
                      View Full Hierarchy →
                    </button>
                  </div>
                  <div className="grid grid-cols-3 gap-4">
                    {INDUSTRY_STATS.relationshipTypes.slice(0, 3).map((rel) => (
                      <div key={rel.type} className="text-center p-3 bg-gray-800/50 rounded-lg">
                        <div className="text-xl font-bold text-white">{rel.count}</div>
                        <div className="text-xs text-gray-400">{rel.type}</div>
                      </div>
                    ))}
                  </div>
                </Section>
              </div>
              
              {/* Right Column - Stats */}
              <div className="space-y-4">
                <Section title="Key Statistics" icon={BarChart3}>
                  <div className="space-y-0">
                    <MetricRow label="52 Week High" value={`$${profile.keyStats['52WeekHigh']}`} />
                    <MetricRow label="52 Week Low" value={`$${profile.keyStats['52WeekLow']}`} />
                    <MetricRow label="Avg Volume (3M)" value={profile.keyStats.avgVolume.toLocaleString()} />
                    <MetricRow label="Shares Outstanding" value={`${(profile.keyStats.sharesOutstanding / 1e6).toFixed(1)}M`} />
                    <MetricRow label="Float" value={`${profile.keyStats.floatPercent}%`} />
                    <MetricRow label="Dividend Yield" value={`${profile.keyStats.dividendYield}%`} />
                  </div>
                </Section>
                
                <Section title="Financial Metrics" icon={DollarSign}>
                  <div className="space-y-0">
                    <MetricRow label="Revenue" value={formatCurrency(profile.financials.revenue)} />
                    <MetricRow label="Net Income" value={formatCurrency(profile.financials.netIncome)} />
                    <MetricRow label="Total Assets" value={formatCurrency(profile.financials.totalAssets)} />
                    <MetricRow label="Total Debt" value={formatCurrency(profile.financials.totalDebt)} />
                    <MetricRow label="Cash" value={formatCurrency(profile.financials.cash)} />
                  </div>
                </Section>
                
                <Section title="Corporate Info" icon={Building2}>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-start gap-2">
                      <MapPin className="w-4 h-4 text-gray-400 mt-0.5" />
                      <span className="text-gray-300">{profile.headquarters}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Globe className="w-4 h-4 text-gray-400" />
                      <a href={profile.website} className="text-blue-400 hover:underline">{profile.website}</a>
                    </div>
                    <div className="flex items-center justify-between text-gray-400">
                      <span>Founded</span>
                      <span className="text-white">{profile.founded}</span>
                    </div>
                    <div className="flex items-center justify-between text-gray-400">
                      <span>Incorporation</span>
                      <span className="text-white">{profile.incorporation}</span>
                    </div>
                    <div className="flex items-center justify-between text-gray-400">
                      <span>Fiscal Year End</span>
                      <span className="text-white">{profile.fiscalYearEnd}</span>
                    </div>
                  </div>
                </Section>
                
                <Section title="Industry Classification" icon={List}>
                  <div className="space-y-2 text-sm">
                    <div className="flex items-center justify-between text-gray-400">
                      <span>Sector</span>
                      <span className="text-white">{profile.sector}</span>
                    </div>
                    <div className="flex items-center justify-between text-gray-400">
                      <span>Industry</span>
                      <span className="text-white">{profile.industry}</span>
                    </div>
                    <div className="flex items-center justify-between text-gray-400">
                      <span>SIC Code</span>
                      <span className="text-white">{profile.sicCode}</span>
                    </div>
                    <div className="flex items-center justify-between text-gray-400">
                      <span>NAICS Code</span>
                      <span className="text-white">{profile.naicsCode}</span>
                    </div>
                  </div>
                </Section>
              </div>
            </div>
          </div>
        )}

        {activeView === 'graph' && (
          <div className={clsx('relative', isGraphFullscreen ? 'fixed inset-0 z-50' : 'h-full')}>
            {/* Graph Canvas */}
            <ForceGraph3D
              ref={fgRef}
              graphData={filteredData}
              nodeId="id"
              nodeLabel=""
              nodeColor={(node: EntityNode) => {
                if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) {
                  return '#374151';
                }
                return CATEGORY_COLORS[node.category || ''] || NODE_COLORS[node.type];
              }}
              nodeVal={(node: EntityNode) => getNodeSize(node)}
              nodeOpacity={0.9}
              linkSource="source"
              linkTarget="target"
              linkColor={(link: RelationshipLink) => {
                if (highlightLinks.size > 0 && !highlightLinks.has(link)) {
                  return 'rgba(75, 85, 99, 0.2)';
                }
                return LINK_COLORS[link.type] || '#6B7280';
              }}
              linkWidth={(link: RelationshipLink) => highlightLinks.has(link) ? 2 : (link.strength || 0.5) * 1.5}
              linkOpacity={0.6}
              linkDirectionalParticles={(link: RelationshipLink) => highlightLinks.has(link) ? 4 : 0}
              linkDirectionalParticleWidth={2}
              linkDirectionalParticleSpeed={0.005}
              onNodeClick={handleNodeClick}
              onBackgroundClick={clearSelection}
              backgroundColor="#030712"
              nodeThreeObject={(node: EntityNode) => {
                const size = getNodeSize(node);
                const color = CATEGORY_COLORS[node.category || ''] || NODE_COLORS[node.type];
                const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
                
                const group = new THREE.Group();
                
                const geometry = new THREE.SphereGeometry(size, 16, 16);
                const material = new THREE.MeshLambertMaterial({
                  color: isHighlighted ? color : '#374151',
                  transparent: true,
                  opacity: isHighlighted ? 0.9 : 0.3
                });
                const sphere = new THREE.Mesh(geometry, material);
                group.add(sphere);
                
                if (isHighlighted && highlightNodes.has(node.id)) {
                  const glowGeometry = new THREE.SphereGeometry(size * 1.4, 16, 16);
                  const glowMaterial = new THREE.MeshBasicMaterial({
                    color: color,
                    transparent: true,
                    opacity: 0.2
                  });
                  const glow = new THREE.Mesh(glowGeometry, glowMaterial);
                  group.add(glow);
                }
                
                const canvas = document.createElement('canvas');
                const context = canvas.getContext('2d')!;
                canvas.width = 256;
                canvas.height = 64;
                context.fillStyle = isHighlighted ? 'white' : 'rgba(255,255,255,0.3)';
                context.font = 'bold 24px Arial';
                context.textAlign = 'center';
                context.fillText(node.name.length > 20 ? node.name.substring(0, 18) + '...' : node.name, 128, 40);
                
                const texture = new THREE.CanvasTexture(canvas);
                const spriteMaterial = new THREE.SpriteMaterial({ map: texture, transparent: true });
                const sprite = new THREE.Sprite(spriteMaterial);
                sprite.scale.set(60, 15, 1);
                sprite.position.set(0, size + 12, 0);
                group.add(sprite);
                
                return group;
              }}
              cooldownTicks={100}
              d3AlphaDecay={0.02}
              d3VelocityDecay={0.3}
            />
            
            {/* Graph Controls */}
            <div className="absolute top-4 left-4 flex flex-col gap-2 z-10">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search entities..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 w-64 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
              
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={clsx(
                  "flex items-center gap-2 px-4 py-2 rounded-lg transition-colors",
                  showFilters ? "bg-blue-600 text-white" : "bg-gray-900/90 backdrop-blur border border-gray-700 text-gray-300 hover:bg-gray-800"
                )}
              >
                <Filter className="w-4 h-4" />
                <span>Filters</span>
              </button>
              
              <div className="flex gap-2">
                <button
                  onClick={() => fgRef.current?.cameraPosition({ x: 0, y: 0, z: (fgRef.current.cameraPosition() as {z:number}).z * 0.8 })}
                  className="p-2 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-800"
                  title="Zoom In"
                >
                  <ZoomIn className="w-4 h-4" />
                </button>
                <button
                  onClick={() => fgRef.current?.cameraPosition({ x: 0, y: 0, z: (fgRef.current.cameraPosition() as {z:number}).z * 1.2 })}
                  className="p-2 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-800"
                  title="Zoom Out"
                >
                  <ZoomOut className="w-4 h-4" />
                </button>
                <button
                  onClick={resetCamera}
                  className="p-2 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-800"
                  title="Reset View"
                >
                  <RotateCcw className="w-4 h-4" />
                </button>
                <button
                  onClick={() => setIsGraphFullscreen(!isGraphFullscreen)}
                  className="p-2 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-800"
                  title={isGraphFullscreen ? "Exit Fullscreen" : "Fullscreen"}
                >
                  {isGraphFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
                </button>
              </div>
            </div>
            
            {/* Filters Panel */}
            {showFilters && (
              <div className="absolute top-4 left-72 w-64 bg-gray-900/95 backdrop-blur border border-gray-700 rounded-lg p-4 z-10">
                <h3 className="text-sm font-semibold text-white mb-3">Filter by Type</h3>
                <div className="space-y-2">
                  {['company', 'subsidiary', 'person', 'fund', 'government', 'organization'].map(type => (
                    <label key={type} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedTypes.has(type)}
                        onChange={(e) => {
                          const newTypes = new Set(selectedTypes);
                          if (e.target.checked) newTypes.add(type);
                          else newTypes.delete(type);
                          setSelectedTypes(newTypes);
                        }}
                        className="rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500"
                      />
                      <span className="text-sm text-gray-300 capitalize">{type}</span>
                      <span
                        className="w-3 h-3 rounded-full ml-auto"
                        style={{ backgroundColor: NODE_COLORS[type] || '#6B7280' }}
                      />
                    </label>
                  ))}
                </div>
              </div>
            )}
            
            {/* Legend */}
            <div className="absolute bottom-4 left-4 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg p-3 z-10">
              <h4 className="text-xs font-semibold text-gray-400 mb-2">Relationship Types</h4>
              <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                {Object.entries(LINK_COLORS).slice(0, 6).map(([type, color]) => (
                  <div key={type} className="flex items-center gap-2">
                    <div className="w-4 h-0.5" style={{ backgroundColor: color }} />
                    <span className="text-xs text-gray-400 capitalize">{type}</span>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Selected Node Panel */}
            {selectedNode && (
              <div className="absolute top-4 right-4 w-80 bg-gray-900/95 backdrop-blur border border-gray-700 rounded-lg overflow-hidden z-10">
                <div className="flex items-center justify-between p-3 border-b border-gray-700">
                  <h3 className="font-semibold text-white">{selectedNode.name}</h3>
                  <button onClick={clearSelection} className="p-1 hover:bg-gray-700 rounded">
                    <X className="w-4 h-4 text-gray-400" />
                  </button>
                </div>
                <div className="p-3 space-y-3 max-h-96 overflow-y-auto">
                  {selectedNode.description && (
                    <p className="text-sm text-gray-400">{selectedNode.description}</p>
                  )}
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div>
                      <span className="text-gray-500">Type</span>
                      <div className="text-white capitalize">{selectedNode.type}</div>
                    </div>
                    {selectedNode.headquarters && (
                      <div>
                        <span className="text-gray-500">HQ</span>
                        <div className="text-white">{selectedNode.headquarters}</div>
                      </div>
                    )}
                    {selectedNode.marketCap && (
                      <div>
                        <span className="text-gray-500">Market Cap</span>
                        <div className="text-white">{formatCurrency(selectedNode.marketCap)}</div>
                      </div>
                    )}
                    {selectedNode.revenue && (
                      <div>
                        <span className="text-gray-500">Revenue</span>
                        <div className="text-white">{formatCurrency(selectedNode.revenue)}</div>
                      </div>
                    )}
                    {selectedNode.employees && (
                      <div>
                        <span className="text-gray-500">Employees</span>
                        <div className="text-white">{selectedNode.employees.toLocaleString()}</div>
                      </div>
                    )}
                    {selectedNode.ticker && (
                      <div>
                        <span className="text-gray-500">Ticker</span>
                        <div className="text-white">{selectedNode.ticker}</div>
                      </div>
                    )}
                  </div>
                  
                  <div>
                    <h4 className="text-xs font-semibold text-gray-400 mb-2">Relationships ({getNodeRelationships(selectedNode).length})</h4>
                    <div className="space-y-1.5 max-h-40 overflow-y-auto">
                      {getNodeRelationships(selectedNode).slice(0, 10).map((rel, i) => (
                        <div key={i} className="flex items-center gap-2 text-xs">
                          <span className="px-1.5 py-0.5 rounded capitalize" style={{ backgroundColor: LINK_COLORS[rel.type] + '30', color: LINK_COLORS[rel.type] }}>
                            {rel.type}
                          </span>
                          <span className="text-gray-500">{rel.direction === 'outgoing' ? '→' : '←'}</span>
                          <span className="text-gray-300 truncate">{rel.otherNode?.name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {activeView === 'hierarchy' && (
          <div className="h-full overflow-auto p-4">
            <div className="max-w-5xl mx-auto space-y-4">
              {/* Header */}
              <div className="flex items-center justify-between">
                <div>
                  <h2 className="text-lg font-bold text-white">Corporate Hierarchy</h2>
                  <p className="text-sm text-gray-400">Total Entities: {countEntities(BOEING_HIERARCHY)}</p>
                </div>
                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      const getAllIds = (entity: HierarchyEntity): string[] => {
                        const ids = [entity.id];
                        if (entity.children) {
                          entity.children.forEach(child => ids.push(...getAllIds(child)));
                        }
                        return ids;
                      };
                      setHierarchyExpanded(Object.fromEntries(getAllIds(BOEING_HIERARCHY).map(id => [id, true])));
                    }}
                    className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg"
                  >
                    Expand All
                  </button>
                  <button
                    onClick={() => setHierarchyExpanded({ boeing: true })}
                    className="px-3 py-1.5 text-xs bg-gray-800 hover:bg-gray-700 text-gray-300 rounded-lg"
                  >
                    Collapse All
                  </button>
                </div>
              </div>
              
              {/* Statistics */}
              <div className="grid grid-cols-4 gap-4">
                {INDUSTRY_STATS.incorporationRegions.map((reg) => (
                  <div key={reg.region} className="card rounded-lg p-3">
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-gray-400">{reg.region}</span>
                      <span className="text-sm font-semibold text-white">{reg.percent}%</span>
                    </div>
                    <div className="h-1.5 bg-gray-700 rounded-full overflow-hidden">
                      <div className="h-full bg-blue-500 rounded-full" style={{ width: `${reg.percent}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              
              {/* Tree Header */}
              <div className="flex items-center gap-2 px-2 py-2 bg-amber-900/20 border-b border-amber-700/50 text-xs font-medium text-amber-300/80 rounded-t-lg">
                <span className="flex-1">Entity Name</span>
                <span className="w-24 text-center">Relationship</span>
                <span className="w-28 hidden lg:block">Incorporation</span>
                <span className="w-24 hidden xl:block">Industry</span>
              </div>
              
              {/* Tree */}
              <div className="card rounded-lg p-4 max-h-[600px] overflow-y-auto">
                <HierarchyTreeNode 
                  entity={BOEING_HIERARCHY} 
                  expanded={hierarchyExpanded} 
                  onToggle={toggleHierarchyExpanded}
                />
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Footer */}
      <footer className="flex-shrink-0 px-4 py-2 border-t border-gray-800 bg-slate-900/50">
        <div className="flex items-center justify-between text-xs text-gray-500">
          <div className="flex items-center gap-4">
            <span>Source: EntitySpine</span>
            <span>Entity ID: {profile.entityId}</span>
          </div>
          <div className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            <span>Last updated: {new Date().toLocaleString()}</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
