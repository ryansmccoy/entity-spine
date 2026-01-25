/**
 * Graph Analytics Panel Component
 * 
 * Displays network analysis metrics:
 * - Node/edge counts
 * - Network density
 * - Centrality scores
 * - Community detection results
 * - Influential nodes
 */

import { useMemo } from 'react';
import type { GraphData, NetworkAnalysisResult } from '../../types/graph';

interface AnalyticsPanelProps {
  graphData: GraphData;
  analysis: NetworkAnalysisResult | null;
  onNodeSelect: (nodeId: string) => void;
  isLoading?: boolean;
}

export function AnalyticsPanel({
  graphData,
  analysis,
  onNodeSelect,
  isLoading = false,
}: AnalyticsPanelProps) {
  // Calculate basic stats from current graph
  const basicStats = useMemo(() => {
    const nodeCount = graphData.nodes.length;
    const edgeCount = graphData.links.length;
    const maxPossibleEdges = nodeCount * (nodeCount - 1) / 2;
    const density = maxPossibleEdges > 0 ? (edgeCount / maxPossibleEdges) : 0;

    // Calculate degrees
    const degrees: Record<string, number> = {};
    graphData.nodes.forEach(n => degrees[n.id] = 0);
    graphData.links.forEach(l => {
      const sourceId = typeof l.source === 'string' ? l.source : l.source.id;
      const targetId = typeof l.target === 'string' ? l.target : l.target.id;
      degrees[sourceId] = (degrees[sourceId] || 0) + 1;
      degrees[targetId] = (degrees[targetId] || 0) + 1;
    });

    const avgDegree = nodeCount > 0
      ? Object.values(degrees).reduce((a, b) => a + b, 0) / nodeCount
      : 0;

    // Top connected nodes
    const topConnected = Object.entries(degrees)
      .sort(([, a], [, b]) => b - a)
      .slice(0, 5)
      .map(([id, degree]) => ({
        id,
        name: graphData.nodes.find(n => n.id === id)?.name || id,
        degree,
      }));

    // Relationship type distribution
    const relTypeCounts: Record<string, number> = {};
    graphData.links.forEach(l => {
      relTypeCounts[l.type] = (relTypeCounts[l.type] || 0) + 1;
    });

    // Entity type distribution
    const entityTypeCounts: Record<string, number> = {};
    graphData.nodes.forEach(n => {
      entityTypeCounts[n.type] = (entityTypeCounts[n.type] || 0) + 1;
    });

    return {
      nodeCount,
      edgeCount,
      density,
      avgDegree,
      topConnected,
      relTypeCounts,
      entityTypeCounts,
    };
  }, [graphData]);

  if (isLoading) {
    return (
      <div className="p-4 text-center text-gray-400">
        <div className="animate-spin text-2xl mb-2">⏳</div>
        Analyzing network...
      </div>
    );
  }

  return (
    <div className="p-4 space-y-5 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-center gap-2">
        <span className="text-xl">📊</span>
        <h2 className="font-semibold">Network Analytics</h2>
      </div>

      {/* Basic Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="bg-gray-700 rounded-lg p-3">
          <div className="text-2xl font-bold text-blue-400">{basicStats.nodeCount}</div>
          <div className="text-xs text-gray-400">Entities</div>
        </div>
        <div className="bg-gray-700 rounded-lg p-3">
          <div className="text-2xl font-bold text-green-400">{basicStats.edgeCount}</div>
          <div className="text-xs text-gray-400">Relationships</div>
        </div>
        <div className="bg-gray-700 rounded-lg p-3">
          <div className="text-2xl font-bold text-purple-400">
            {(basicStats.density * 100).toFixed(1)}%
          </div>
          <div className="text-xs text-gray-400">Density</div>
        </div>
        <div className="bg-gray-700 rounded-lg p-3">
          <div className="text-2xl font-bold text-yellow-400">
            {basicStats.avgDegree.toFixed(1)}
          </div>
          <div className="text-xs text-gray-400">Avg Connections</div>
        </div>
      </div>

      {/* Most Connected Entities */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">🏆 Most Connected</h3>
        <div className="space-y-1">
          {basicStats.topConnected.map((node, i) => (
            <button
              key={node.id}
              onClick={() => onNodeSelect(node.id)}
              className="w-full flex items-center justify-between bg-gray-700 hover:bg-gray-600 rounded px-3 py-2 text-sm transition-colors"
            >
              <div className="flex items-center gap-2">
                <span className="text-gray-500 w-4">{i + 1}.</span>
                <span>{node.name}</span>
              </div>
              <span className="text-blue-400 font-medium">{node.degree}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Relationship Distribution */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">🔗 Relationship Types</h3>
        <div className="space-y-2">
          {Object.entries(basicStats.relTypeCounts)
            .sort(([, a], [, b]) => b - a)
            .map(([type, count]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(count / basicStats.edgeCount) * 100}%`,
                      backgroundColor: getRelationshipColor(type),
                    }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-20 text-right capitalize">
                  {type}
                </span>
                <span className="text-xs font-medium w-8">{count}</span>
              </div>
            ))}
        </div>
      </div>

      {/* Entity Type Distribution */}
      <div>
        <h3 className="text-sm font-medium text-gray-400 mb-2">🏢 Entity Types</h3>
        <div className="space-y-2">
          {Object.entries(basicStats.entityTypeCounts)
            .sort(([, a], [, b]) => b - a)
            .map(([type, count]) => (
              <div key={type} className="flex items-center gap-2">
                <div className="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${(count / basicStats.nodeCount) * 100}%`,
                      backgroundColor: getEntityTypeColor(type),
                    }}
                  />
                </div>
                <span className="text-xs text-gray-400 w-24 text-right capitalize">
                  {type.replace('_', ' ')}
                </span>
                <span className="text-xs font-medium w-8">{count}</span>
              </div>
            ))}
        </div>
      </div>

      {/* Advanced Analysis (if available) */}
      {analysis && (
        <>
          <div className="border-t border-gray-700 pt-4">
            <h3 className="text-sm font-medium text-gray-400 mb-2">🎯 Centrality Scores</h3>
            <div className="space-y-1">
              {Object.entries(analysis.centralityScores)
                .slice(0, 5)
                .map(([nodeId, score]) => {
                  const node = graphData.nodes.find(n => n.id === nodeId);
                  return (
                    <button
                      key={nodeId}
                      onClick={() => onNodeSelect(nodeId)}
                      className="w-full flex items-center justify-between bg-gray-700 hover:bg-gray-600 rounded px-3 py-2 text-sm"
                    >
                      <span>{node?.name || nodeId}</span>
                      <span className="text-purple-400">{(score * 100).toFixed(1)}%</span>
                    </button>
                  );
                })}
            </div>
          </div>

          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-2">🏘️ Communities</h3>
            <div className="space-y-2">
              {Object.entries(analysis.communities).map(([community, members]) => (
                <div key={community} className="bg-gray-700 rounded p-2">
                  <div className="text-xs font-medium text-gray-300 mb-1 capitalize">
                    {community} ({members.length})
                  </div>
                  <div className="flex flex-wrap gap-1">
                    {members.slice(0, 5).map(id => {
                      const node = graphData.nodes.find(n => n.id === id);
                      return (
                        <button
                          key={id}
                          onClick={() => onNodeSelect(id)}
                          className="text-xs bg-gray-600 hover:bg-gray-500 px-2 py-0.5 rounded"
                        >
                          {node?.name || id}
                        </button>
                      );
                    })}
                    {members.length > 5 && (
                      <span className="text-xs text-gray-500">+{members.length - 5} more</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

function getRelationshipColor(type: string): string {
  const colors: Record<string, string> = {
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
  return colors[type] || '#666';
}

function getEntityTypeColor(type: string): string {
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

export default AnalyticsPanel;
