/**
 * EntityMiniGraph - Embeddable 3D Entity Relationship Graph
 * 
 * A compact, embeddable version of the entity graph that can be placed
 * inside other pages (Dashboard, Research, etc.) with real-time updates.
 */

import { useCallback, useMemo, useRef, useState, useEffect } from 'react';
import ForceGraph3D from 'react-force-graph-3d';
import * as THREE from 'three';
import { clsx } from 'clsx';
import {
  EntityNode,
  RelationshipLink,
  GraphData,
  SEMICONDUCTOR_ECOSYSTEM,
  NODE_TYPE_COLORS,
  CATEGORY_COLORS,
  LINK_COLORS,
  getNodeColor,
  getNodeRelationships,
  getConnectionCounts,
  filterGraphData,
  ColorMode,
} from './graphData';
import { Search, X, ExternalLink } from 'lucide-react';

interface EntityMiniGraphProps {
  /** Height of the graph container */
  height?: number;
  /** Initial node to focus on */
  focusNodeId?: string;
  /** Callback when a node is selected */
  onNodeSelect?: (node: EntityNode | null) => void;
  /** Whether to show the detail panel */
  showDetailPanel?: boolean;
  /** Custom class name */
  className?: string;
}

export function EntityMiniGraph({
  height = 400,
  focusNodeId,
  onNodeSelect,
  showDetailPanel = true,
  className,
}: EntityMiniGraphProps) {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null);
  const [graphData] = useState<GraphData>(SEMICONDUCTOR_ECOSYSTEM);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [colorBy, setColorBy] = useState<ColorMode>('type');
  const [sizeBy] = useState<'uniform' | 'marketCap' | 'revenue' | 'employees' | 'connections'>('marketCap');
  const [highlightLinks, setHighlightLinks] = useState<Set<RelationshipLink>>(new Set());
  const [highlightNodes, setHighlightNodes] = useState<Set<EntityNode>>(new Set());

  // Calculate connection counts
  const connectionCounts = useMemo(() => getConnectionCounts(graphData.links), [graphData.links]);

  // Filter data
  const filteredData = useMemo(() => {
    return filterGraphData(graphData, { searchQuery });
  }, [graphData, searchQuery]);

  // Get node size
  const getNodeSize = useCallback((node: EntityNode): number => {
    const baseSize = 3;
    const maxSize = 12;
    
    switch (sizeBy) {
      case 'uniform':
        return 4;
      case 'marketCap': {
        const cap = node.metrics?.marketCapB || 1;
        return Math.min(maxSize, baseSize + Math.log10(cap) * 2.5);
      }
      case 'revenue': {
        const rev = node.metrics?.revenueB || 0.1;
        return Math.min(maxSize, baseSize + Math.log10(rev + 1) * 3);
      }
      case 'employees': {
        const emp = node.metrics?.employees || 100;
        return Math.min(maxSize, baseSize + Math.log10(emp) * 1.5);
      }
      case 'connections': {
        const conn = connectionCounts[node.id] || 1;
        return Math.min(maxSize, baseSize + conn);
      }
      default:
        return 4;
    }
  }, [sizeBy, connectionCounts]);

  // Handle node click
  const handleNodeClick = useCallback((node: EntityNode) => {
    setSelectedNode(node);
    onNodeSelect?.(node);
    
    // Zoom to node
    const distance = 150;
    const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
    
    fgRef.current?.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      node as { x: number; y: number; z: number },
      1500
    );
    
    // Highlight connected
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
  }, [filteredData, onNodeSelect]);

  // Focus on initial node
  useEffect(() => {
    if (focusNodeId) {
      const node = graphData.nodes.find(n => n.id === focusNodeId);
      if (node) {
        setTimeout(() => handleNodeClick(node), 500);
      }
    }
  }, [focusNodeId, graphData.nodes, handleNodeClick]);

  // Custom node rendering
  const nodeThreeObject = useCallback((nodeObj: object) => {
    const node = nodeObj as EntityNode;
    const isSelected = selectedNode?.id === node.id;
    const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node);
    
    const group = new THREE.Group();
    const nodeSize = isSelected ? getNodeSize(node) * 1.3 : getNodeSize(node);
    
    const geometry = new THREE.SphereGeometry(nodeSize);
    const color = getNodeColor(node, colorBy);
    const material = new THREE.MeshLambertMaterial({
      color,
      transparent: !isHighlighted,
      opacity: isHighlighted ? 1 : 0.3,
    });
    const sphere = new THREE.Mesh(geometry, material);
    group.add(sphere);
    
    if (isSelected) {
      const glowGeometry = new THREE.SphereGeometry(nodeSize * 1.4);
      const glowMaterial = new THREE.MeshBasicMaterial({
        color,
        transparent: true,
        opacity: 0.2,
      });
      group.add(new THREE.Mesh(glowGeometry, glowMaterial));
    }
    
    return group;
  }, [selectedNode, highlightNodes, getNodeSize, colorBy]);

  // Get link color
  const getLinkColor = useCallback((link: RelationshipLink) => {
    const isHighlighted = highlightLinks.size === 0 || highlightLinks.has(link);
    const baseColor = LINK_COLORS[link.type] || '#999999';
    return isHighlighted ? baseColor : '#333333';
  }, [highlightLinks]);

  // Clear selection
  const clearSelection = useCallback(() => {
    setSelectedNode(null);
    setHighlightNodes(new Set());
    setHighlightLinks(new Set());
    onNodeSelect?.(null);
  }, [onNodeSelect]);

  return (
    <div className={clsx('bg-[#1e1e2d] rounded-lg overflow-hidden flex flex-col', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-white">Entity Graph</span>
          <span className="text-xs text-gray-400">
            {filteredData.nodes.length} entities
          </span>
        </div>
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search..."
              className="w-28 pl-7 pr-2 py-1 bg-[#1e1e2d] border border-[#3d3d53] rounded text-xs text-white placeholder:text-gray-500 focus:outline-none focus:border-blue-500"
            />
          </div>
          
          {/* Color By */}
          <select
            value={colorBy}
            onChange={(e) => setColorBy(e.target.value as ColorMode)}
            className="bg-[#1e1e2d] border border-[#3d3d53] rounded px-2 py-1 text-xs text-white focus:outline-none"
          >
            <option value="type">By Type</option>
            <option value="category">By Category</option>
          </select>
          
          {/* Expand */}
          <a
            href="/graph"
            target="_blank"
            className="p-1 hover:bg-[#3d3d53] rounded"
            title="Open full graph"
          >
            <ExternalLink className="h-3.5 w-3.5 text-gray-400" />
          </a>
        </div>
      </div>
      
      {/* Main content */}
      <div className="flex-1 flex" style={{ height: height - 40 }}>
        {/* Graph */}
        <div className="flex-1 relative">
          <ForceGraph3D
            ref={fgRef}
            graphData={filteredData}
            nodeId="id"
            nodeThreeObject={nodeThreeObject}
            nodeThreeObjectExtend={false}
            linkColor={(link) => getLinkColor(link as RelationshipLink)}
            linkWidth={(link) => highlightLinks.has(link as RelationshipLink) ? 2 : 0.5}
            linkOpacity={0.6}
            linkDirectionalArrowLength={3}
            linkDirectionalArrowRelPos={1}
            linkCurvature={0.15}
            linkDirectionalParticles={(link) => highlightLinks.has(link as RelationshipLink) ? 3 : 0}
            linkDirectionalParticleWidth={1.5}
            linkDirectionalParticleSpeed={0.006}
            onNodeClick={(node) => handleNodeClick(node as EntityNode)}
            onBackgroundClick={clearSelection}
            backgroundColor="#1e1e2d"
            showNavInfo={false}
            width={showDetailPanel && selectedNode ? undefined : undefined}
          />
          
          {/* Mini Legend */}
          <div className="absolute bottom-2 left-2 bg-[#252536]/90 rounded p-2 text-[10px]">
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
              {Object.entries(colorBy === 'type' ? NODE_TYPE_COLORS : CATEGORY_COLORS).slice(0, 6).map(([key, color]) => (
                <div key={key} className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full" style={{ backgroundColor: color }} />
                  <span className="text-gray-400 capitalize">{key.replace('_', ' ')}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
        
        {/* Detail Panel */}
        {showDetailPanel && selectedNode && (
          <div className="w-56 bg-[#252536] border-l border-[#2d2d43] overflow-y-auto">
            <div className="p-3">
              {/* Header */}
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h3 className="text-sm font-bold text-white">{selectedNode.name}</h3>
                  {selectedNode.identifiers?.ticker && (
                    <span className="text-xs text-cyan-400">{selectedNode.identifiers.ticker}</span>
                  )}
                </div>
                <button onClick={clearSelection} className="text-gray-400 hover:text-white">
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
              
              {/* Type badges */}
              <div className="flex flex-wrap gap-1 mb-3">
                <span 
                  className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                  style={{ backgroundColor: NODE_TYPE_COLORS[selectedNode.type], color: '#000' }}
                >
                  {selectedNode.type.replace('_', ' ')}
                </span>
                <span 
                  className="px-1.5 py-0.5 rounded text-[10px] font-medium"
                  style={{ backgroundColor: CATEGORY_COLORS[selectedNode.category], color: '#000' }}
                >
                  {selectedNode.category}
                </span>
              </div>
              
              {/* Industry */}
              {selectedNode.industry && (
                <div className="text-xs text-gray-400 mb-3">{selectedNode.industry}</div>
              )}
              
              {/* Metrics */}
              {selectedNode.metrics && (
                <div className="grid grid-cols-2 gap-1.5 mb-3">
                  {selectedNode.metrics.marketCapB && (
                    <div className="bg-[#1e1e2d] rounded p-1.5">
                      <div className="text-[9px] text-gray-500">Mkt Cap</div>
                      <div className="text-xs font-bold text-green-400">
                        ${selectedNode.metrics.marketCapB >= 1000 
                          ? (selectedNode.metrics.marketCapB / 1000).toFixed(1) + 'T' 
                          : selectedNode.metrics.marketCapB + 'B'}
                      </div>
                    </div>
                  )}
                  {selectedNode.metrics.revenueB && (
                    <div className="bg-[#1e1e2d] rounded p-1.5">
                      <div className="text-[9px] text-gray-500">Revenue</div>
                      <div className="text-xs font-bold text-blue-400">
                        ${selectedNode.metrics.revenueB.toFixed(1)}B
                      </div>
                    </div>
                  )}
                  {selectedNode.metrics.employees && (
                    <div className="bg-[#1e1e2d] rounded p-1.5">
                      <div className="text-[9px] text-gray-500">Employees</div>
                      <div className="text-xs font-bold text-purple-400">
                        {(selectedNode.metrics.employees / 1000).toFixed(0)}K
                      </div>
                    </div>
                  )}
                  {selectedNode.metrics.yoyGrowth !== undefined && (
                    <div className="bg-[#1e1e2d] rounded p-1.5">
                      <div className="text-[9px] text-gray-500">YoY</div>
                      <div className={clsx(
                        'text-xs font-bold',
                        selectedNode.metrics.yoyGrowth >= 0 ? 'text-green-400' : 'text-red-400'
                      )}>
                        {selectedNode.metrics.yoyGrowth > 0 ? '+' : ''}{selectedNode.metrics.yoyGrowth}%
                      </div>
                    </div>
                  )}
                </div>
              )}
              
              {/* Relationships */}
              <div className="text-[10px]">
                <div className="text-gray-500 font-semibold mb-1">RELATIONSHIPS</div>
                {Object.entries(getNodeRelationships(selectedNode, filteredData)).map(([type, rels]) => (
                  <div key={type} className="mb-1.5">
                    <div className="flex items-center gap-1 mb-0.5" style={{ color: LINK_COLORS[type as keyof typeof LINK_COLORS] }}>
                      <span className="w-2 h-0.5" style={{ backgroundColor: LINK_COLORS[type as keyof typeof LINK_COLORS] }} />
                      <span className="capitalize">{type}</span>
                      <span className="text-gray-500">({rels.length})</span>
                    </div>
                    <div className="space-y-0.5 ml-3">
                      {rels.slice(0, 3).map((rel, i) => (
                        <button
                          key={i}
                          onClick={() => handleNodeClick(rel.node)}
                          className="block w-full text-left bg-[#1e1e2d] hover:bg-[#3d3d53] rounded px-1.5 py-0.5 text-gray-300 truncate"
                        >
                          {rel.direction === 'in' ? '← ' : '→ '}{rel.node.name}
                        </button>
                      ))}
                      {rels.length > 3 && (
                        <span className="text-gray-500 ml-1.5">+{rels.length - 3} more</span>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
