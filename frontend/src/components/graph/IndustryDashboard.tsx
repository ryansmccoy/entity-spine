/**
 * Industry Dashboard Component
 * 
 * Bloomberg Terminal-style dashboard with floating panels showing:
 * - Industry breakdown and metrics
 * - Supply chain flow visualization
 * - Key financial metrics
 * - Market sentiment/momentum
 * - Competitor analysis
 * 
 * All connected to the knowledge graph for interactive exploration.
 */

import { useState, useMemo, useCallback } from 'react';
import type { EntityNode, Relationship, GraphData } from '../../types/graph';

interface IndustryDashboardProps {
  graphData: GraphData;
  onNodeSelect: (node: EntityNode) => void;
  onFilterChange: (filters: Record<string, unknown>) => void;
  selectedIndustry: string | null;
  onIndustrySelect: (industry: string | null) => void;
}

// Industry definitions with emoji and color
const INDUSTRIES: Record<string, { label: string; emoji: string; color: string }> = {
  'EDA Software': { label: 'EDA Tools', emoji: '🛠️', color: '#8B5CF6' },
  'IP Licensing': { label: 'IP/Licensing', emoji: '📜', color: '#F59E0B' },
  'AI Accelerators': { label: 'AI Chips', emoji: '🤖', color: '#EC4899' },
  'GPUs & AI': { label: 'GPUs', emoji: '🎮', color: '#10B981' },
  'CPUs & GPUs': { label: 'CPUs', emoji: '💻', color: '#3B82F6' },
  'CPUs & Foundry': { label: 'IDM', emoji: '🏭', color: '#6366F1' },
  'Mobile Chips': { label: 'Mobile', emoji: '📱', color: '#14B8A6' },
  'Consumer Electronics': { label: 'Consumer', emoji: '🍎', color: '#64748B' },
  'Networking & Storage': { label: 'Networking', emoji: '🌐', color: '#0EA5E9' },
  'Semiconductor Foundry': { label: 'Foundry', emoji: '⚙️', color: '#2196F3' },
  'Lithography': { label: 'Lithography', emoji: '🔬', color: '#FF5722' },
  'Deposition & Etch': { label: 'Deposition', emoji: '🧪', color: '#FF7043' },
  'Etch & Deposition': { label: 'Etch', emoji: '⚡', color: '#FF8A65' },
  'Inspection & Metrology': { label: 'Inspection', emoji: '🔍', color: '#FFAB91' },
  'OSAT Packaging': { label: 'Packaging', emoji: '📦', color: '#795548' },
  'DRAM & NAND': { label: 'Memory', emoji: '💾', color: '#00BCD4' },
  'Cloud & Software': { label: 'Cloud', emoji: '☁️', color: '#9C27B0' },
  'Cloud & Advertising': { label: 'Cloud/Ad', emoji: '📊', color: '#AB47BC' },
  'Cloud & E-Commerce': { label: 'Cloud/E-Com', emoji: '🛒', color: '#BA68C8' },
  'Social Media & AI': { label: 'Social/AI', emoji: '👥', color: '#CE93D8' },
  'AI Research': { label: 'AI Research', emoji: '🧠', color: '#E91E63' },
  'Venture Capital': { label: 'VC/PE', emoji: '💰', color: '#FFC107' },
  'R&D Consortium': { label: 'R&D', emoji: '🔬', color: '#607D8B' },
};

export function IndustryDashboard({
  graphData,
  onNodeSelect,
  onFilterChange: _onFilterChange,
  selectedIndustry,
  onIndustrySelect,
}: IndustryDashboardProps) {
  // Reserved for advanced filtering features
  void _onFilterChange;
  const [expandedPanel, setExpandedPanel] = useState<string | null>('overview');
  const [sortBy, setSortBy] = useState<'marketCap' | 'revenue' | 'employees' | 'growth'>('marketCap');

  // Aggregate industry data
  const industryData = useMemo(() => {
    const byIndustry: Record<string, {
      industry: string;
      companies: EntityNode[];
      totalMarketCap: number;
      totalRevenue: number;
      totalEmployees: number;
      avgGrowth: number;
      info: typeof INDUSTRIES[string];
    }> = {};

    graphData.nodes.forEach(node => {
      const industry = node.industry || 'Other';
      if (!byIndustry[industry]) {
        byIndustry[industry] = {
          industry,
          companies: [],
          totalMarketCap: 0,
          totalRevenue: 0,
          totalEmployees: 0,
          avgGrowth: 0,
          info: INDUSTRIES[industry] || { label: industry, emoji: '🏢', color: '#666' },
        };
      }

      byIndustry[industry].companies.push(node);
      byIndustry[industry].totalMarketCap += node.metrics?.marketCapB || 0;
      byIndustry[industry].totalRevenue += node.metrics?.revenueB || 0;
      byIndustry[industry].totalEmployees += node.metrics?.employees || 0;
    });

    // Calculate average growth
    Object.values(byIndustry).forEach(ind => {
      const growths = ind.companies
        .filter(c => c.metrics?.yoyGrowth !== undefined)
        .map(c => c.metrics!.yoyGrowth!);
      ind.avgGrowth = growths.length > 0
        ? growths.reduce((a, b) => a + b, 0) / growths.length
        : 0;
    });

    return Object.values(byIndustry).sort((a, b) => b.totalMarketCap - a.totalMarketCap);
  }, [graphData.nodes]);

  // Supply chain analysis
  const supplyChainData = useMemo(() => {
    const flows: Array<{
      from: string;
      to: string;
      type: string;
      count: number;
      companies: Array<{ source: string; target: string }>;
    }> = [];

    const flowMap: Record<string, typeof flows[0]> = {};

    graphData.links.forEach(link => {
      if (!['supplier', 'customer', 'foundry'].includes(link.type)) return;

      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;

      const sourceNode = graphData.nodes.find(n => n.id === sourceId);
      const targetNode = graphData.nodes.find(n => n.id === targetId);

      if (!sourceNode?.industry || !targetNode?.industry) return;

      const key = `${sourceNode.industry}→${targetNode.industry}`;
      if (!flowMap[key]) {
        flowMap[key] = {
          from: sourceNode.industry,
          to: targetNode.industry,
          type: link.type,
          count: 0,
          companies: [],
        };
      }
      flowMap[key].count++;
      flowMap[key].companies.push({ source: sourceNode.name, target: targetNode.name });
    });

    return Object.values(flowMap).sort((a, b) => b.count - a.count).slice(0, 10);
  }, [graphData]);

  // Market metrics
  const marketMetrics = useMemo(() => {
    const metrics = {
      totalMarketCap: 0,
      totalRevenue: 0,
      totalEmployees: 0,
      avgGrowth: 0,
      publicCompanies: 0,
      privateCompanies: 0,
      topGainer: null as EntityNode | null,
      topLoser: null as EntityNode | null,
    };

    let growthCount = 0;
    let maxGrowth = -Infinity;
    let minGrowth = Infinity;

    graphData.nodes.forEach(node => {
      metrics.totalMarketCap += node.metrics?.marketCapB || 0;
      metrics.totalRevenue += node.metrics?.revenueB || 0;
      metrics.totalEmployees += node.metrics?.employees || 0;

      if (node.type === 'public_company') metrics.publicCompanies++;
      else metrics.privateCompanies++;

      if (node.metrics?.yoyGrowth !== undefined) {
        metrics.avgGrowth += node.metrics.yoyGrowth;
        growthCount++;

        if (node.metrics.yoyGrowth > maxGrowth) {
          maxGrowth = node.metrics.yoyGrowth;
          metrics.topGainer = node;
        }
        if (node.metrics.yoyGrowth < minGrowth) {
          minGrowth = node.metrics.yoyGrowth;
          metrics.topLoser = node;
        }
      }
    });

    if (growthCount > 0) {
      metrics.avgGrowth /= growthCount;
    }

    return metrics;
  }, [graphData.nodes]);

  // Toggle panel expansion
  const togglePanel = useCallback((panelId: string) => {
    setExpandedPanel(prev => prev === panelId ? null : panelId);
  }, []);

  return (
    <div className="h-full bg-gray-900 text-white overflow-y-auto">
      {/* Header */}
      <div className="sticky top-0 bg-gray-800 border-b border-gray-700 p-3 z-10">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-bold flex items-center gap-2">
            <span>📈</span> Industry Dashboard
          </h2>
          <div className="flex items-center gap-2">
            <select
              value={sortBy}
              onChange={e => setSortBy(e.target.value as typeof sortBy)}
              className="bg-gray-700 border border-gray-600 rounded px-2 py-1 text-xs"
            >
              <option value="marketCap">Sort: Market Cap</option>
              <option value="revenue">Sort: Revenue</option>
              <option value="employees">Sort: Employees</option>
              <option value="growth">Sort: Growth</option>
            </select>
          </div>
        </div>
      </div>

      <div className="p-3 space-y-3">
        {/* Market Overview Panel */}
        <DashboardPanel
          title="Market Overview"
          emoji="🌍"
          isExpanded={expandedPanel === 'overview'}
          onToggle={() => togglePanel('overview')}
        >
          <div className="grid grid-cols-4 gap-2 mb-3">
            <MetricCard
              label="Total Market Cap"
              value={`$${formatLargeNumber(marketMetrics.totalMarketCap)}T`}
              color="text-green-400"
            />
            <MetricCard
              label="Total Revenue"
              value={`$${formatLargeNumber(marketMetrics.totalRevenue / 1000)}T`}
              color="text-blue-400"
            />
            <MetricCard
              label="Total Employees"
              value={formatLargeNumber(marketMetrics.totalEmployees / 1000000) + 'M'}
              color="text-purple-400"
            />
            <MetricCard
              label="Avg Growth"
              value={`${marketMetrics.avgGrowth >= 0 ? '+' : ''}${marketMetrics.avgGrowth.toFixed(1)}%`}
              color={marketMetrics.avgGrowth >= 0 ? 'text-green-400' : 'text-red-400'}
            />
          </div>

          <div className="grid grid-cols-2 gap-2">
            {marketMetrics.topGainer && (
              <button
                onClick={() => onNodeSelect(marketMetrics.topGainer!)}
                className="bg-green-900/30 border border-green-700/50 rounded p-2 text-left hover:bg-green-900/50"
              >
                <div className="text-xs text-green-400">🚀 Top Gainer</div>
                <div className="font-bold">{marketMetrics.topGainer.name}</div>
                <div className="text-green-400 text-sm">
                  +{marketMetrics.topGainer.metrics?.yoyGrowth}% YoY
                </div>
              </button>
            )}
            {marketMetrics.topLoser && (
              <button
                onClick={() => onNodeSelect(marketMetrics.topLoser!)}
                className="bg-red-900/30 border border-red-700/50 rounded p-2 text-left hover:bg-red-900/50"
              >
                <div className="text-xs text-red-400">📉 Biggest Decline</div>
                <div className="font-bold">{marketMetrics.topLoser.name}</div>
                <div className="text-red-400 text-sm">
                  {marketMetrics.topLoser.metrics?.yoyGrowth}% YoY
                </div>
              </button>
            )}
          </div>
        </DashboardPanel>

        {/* Industry Breakdown Panel */}
        <DashboardPanel
          title="Industry Breakdown"
          emoji="🏭"
          isExpanded={expandedPanel === 'industries'}
          onToggle={() => togglePanel('industries')}
          badge={industryData.length.toString()}
        >
          <div className="space-y-1">
            {industryData.map(ind => (
              <button
                key={ind.industry}
                onClick={() => onIndustrySelect(selectedIndustry === ind.industry ? null : ind.industry)}
                className={`w-full flex items-center gap-2 p-2 rounded text-left transition-colors ${
                  selectedIndustry === ind.industry
                    ? 'bg-blue-600'
                    : 'bg-gray-800 hover:bg-gray-700'
                }`}
              >
                <span className="text-lg">{ind.info.emoji}</span>
                <div className="flex-1 min-w-0">
                  <div className="font-medium truncate">{ind.info.label}</div>
                  <div className="text-xs text-gray-400">
                    {ind.companies.length} companies
                  </div>
                </div>
                <div className="text-right text-sm">
                  <div className="text-green-400 font-medium">
                    ${formatLargeNumber(ind.totalMarketCap)}B
                  </div>
                  <div className={`text-xs ${ind.avgGrowth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                    {ind.avgGrowth >= 0 ? '+' : ''}{ind.avgGrowth.toFixed(1)}%
                  </div>
                </div>
                {/* Progress bar */}
                <div className="w-16 h-2 bg-gray-700 rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full"
                    style={{
                      width: `${(ind.totalMarketCap / industryData[0].totalMarketCap) * 100}%`,
                      backgroundColor: ind.info.color,
                    }}
                  />
                </div>
              </button>
            ))}
          </div>
        </DashboardPanel>

        {/* Supply Chain Flow Panel */}
        <DashboardPanel
          title="Supply Chain Flows"
          emoji="🔄"
          isExpanded={expandedPanel === 'supply'}
          onToggle={() => togglePanel('supply')}
          badge={supplyChainData.length.toString()}
        >
          <div className="space-y-2">
            {supplyChainData.map((flow, i) => {
              const fromInfo = INDUSTRIES[flow.from] || { emoji: '🏢', label: flow.from, color: '#666' };
              const toInfo = INDUSTRIES[flow.to] || { emoji: '🏢', label: flow.to, color: '#666' };
              
              return (
                <div
                  key={i}
                  className="bg-gray-800 rounded p-2 hover:bg-gray-750"
                >
                  <div className="flex items-center gap-2 text-sm">
                    <span
                      className="px-2 py-0.5 rounded text-xs"
                      style={{ backgroundColor: fromInfo.color }}
                    >
                      {fromInfo.emoji} {fromInfo.label}
                    </span>
                    <span className="text-gray-500">→</span>
                    <span
                      className="px-2 py-0.5 rounded text-xs"
                      style={{ backgroundColor: toInfo.color }}
                    >
                      {toInfo.emoji} {toInfo.label}
                    </span>
                    <span className="ml-auto text-gray-400">
                      {flow.count} connections
                    </span>
                  </div>
                  <div className="mt-1 text-xs text-gray-500 truncate">
                    {flow.companies.slice(0, 2).map(c => `${c.source}→${c.target}`).join(', ')}
                    {flow.companies.length > 2 && ` +${flow.companies.length - 2} more`}
                  </div>
                </div>
              );
            })}
          </div>
        </DashboardPanel>

        {/* Top Companies Panel */}
        <DashboardPanel
          title="Top Companies by Market Cap"
          emoji="🏆"
          isExpanded={expandedPanel === 'top'}
          onToggle={() => togglePanel('top')}
        >
          <div className="space-y-1">
            {graphData.nodes
              .filter(n => n.metrics?.marketCapB)
              .sort((a, b) => (b.metrics?.marketCapB || 0) - (a.metrics?.marketCapB || 0))
              .slice(0, 10)
              .map((node, i) => (
                <button
                  key={node.id}
                  onClick={() => onNodeSelect(node)}
                  className="w-full flex items-center gap-2 p-2 bg-gray-800 hover:bg-gray-700 rounded text-left"
                >
                  <span className="w-5 text-gray-500 text-sm">{i + 1}.</span>
                  <div className="flex-1">
                    <div className="font-medium">{node.name}</div>
                    <div className="text-xs text-gray-400">{node.industry}</div>
                  </div>
                  <div className="text-right">
                    <div className="text-green-400 font-bold">
                      ${node.metrics?.marketCapB && node.metrics.marketCapB >= 1000
                        ? (node.metrics.marketCapB / 1000).toFixed(1) + 'T'
                        : (node.metrics?.marketCapB || 0) + 'B'}
                    </div>
                    {node.metrics?.yoyGrowth !== undefined && (
                      <div className={`text-xs ${node.metrics.yoyGrowth >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                        {node.metrics.yoyGrowth >= 0 ? '+' : ''}{node.metrics.yoyGrowth}%
                      </div>
                    )}
                  </div>
                </button>
              ))}
          </div>
        </DashboardPanel>

        {/* Relationship Heatmap Panel */}
        <DashboardPanel
          title="Relationship Distribution"
          emoji="🔗"
          isExpanded={expandedPanel === 'relationships'}
          onToggle={() => togglePanel('relationships')}
        >
          <RelationshipHeatmap links={graphData.links} />
        </DashboardPanel>
      </div>
    </div>
  );
}

// Sub-components

interface DashboardPanelProps {
  title: string;
  emoji: string;
  isExpanded: boolean;
  onToggle: () => void;
  badge?: string;
  children: React.ReactNode;
}

function DashboardPanel({ title, emoji, isExpanded, onToggle, badge, children }: DashboardPanelProps) {
  return (
    <div className="bg-gray-800 rounded-lg border border-gray-700 overflow-hidden">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-3 hover:bg-gray-750 transition-colors"
      >
        <div className="flex items-center gap-2">
          <span>{emoji}</span>
          <span className="font-semibold">{title}</span>
          {badge && (
            <span className="bg-blue-600 text-xs px-2 py-0.5 rounded-full">{badge}</span>
          )}
        </div>
        <span className="text-gray-400">{isExpanded ? '▼' : '▶'}</span>
      </button>
      {isExpanded && (
        <div className="p-3 pt-0 border-t border-gray-700">
          {children}
        </div>
      )}
    </div>
  );
}

interface MetricCardProps {
  label: string;
  value: string;
  color: string;
}

function MetricCard({ label, value, color }: MetricCardProps) {
  return (
    <div className="bg-gray-700 rounded p-2 text-center">
      <div className={`text-xl font-bold ${color}`}>{value}</div>
      <div className="text-xs text-gray-400">{label}</div>
    </div>
  );
}

function RelationshipHeatmap({ links }: { links: Relationship[] }) {
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    links.forEach(l => {
      counts[l.type] = (counts[l.type] || 0) + 1;
    });
    return Object.entries(counts).sort(([, a], [, b]) => b - a);
  }, [links]);

  const maxCount = typeCounts[0]?.[1] || 1;

  const typeColors: Record<string, string> = {
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

  return (
    <div className="space-y-2">
      {typeCounts.map(([type, count]) => (
        <div key={type} className="flex items-center gap-2">
          <div className="w-20 text-sm capitalize truncate">{type}</div>
          <div className="flex-1 bg-gray-700 rounded-full h-4 overflow-hidden">
            <div
              className="h-full rounded-full transition-all"
              style={{
                width: `${(count / maxCount) * 100}%`,
                backgroundColor: typeColors[type] || '#666',
              }}
            />
          </div>
          <div className="w-8 text-right text-sm text-gray-400">{count}</div>
        </div>
      ))}
    </div>
  );
}

function formatLargeNumber(num: number): string {
  if (num >= 1000) return (num / 1000).toFixed(1);
  if (num >= 1) return num.toFixed(0);
  return num.toFixed(2);
}

export default IndustryDashboard;
