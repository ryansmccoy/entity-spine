/**
 * Global Map Component
 * 
 * World map visualization showing company locations by jurisdiction.
 * Features:
 * - Interactive country markers
 * - Marker size by market cap or company count
 * - Hover tooltips with company details
 * - Click to filter graph by jurisdiction
 * - Heat map overlay by industry concentration
 */

import { memo, useState, useMemo } from 'react';
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from 'react-simple-maps';
import type { EntityNode } from '../../types/graph';

// World topology for the map
const GEO_URL = 'https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json';

// Country coordinates for markers
const COUNTRY_COORDS: Record<string, [number, number]> = {
  US: [-95.7, 37.1],
  GB: [-1.2, 52.2],
  TW: [121.0, 23.7],
  KR: [127.8, 36.0],
  JP: [138.3, 36.2],
  NL: [5.3, 52.1],
  BE: [4.5, 50.5],
  DE: [10.5, 51.2],
  CN: [104.2, 35.9],
  IE: [-7.7, 53.4],
  SG: [103.8, 1.4],
  CH: [8.2, 46.8],
  FR: [2.2, 46.2],
  IL: [35.0, 31.5],
  CA: [-106.3, 56.1],
  AU: [133.8, -25.3],
  IN: [78.9, 20.6],
};

const COUNTRY_NAMES: Record<string, string> = {
  US: 'United States',
  GB: 'United Kingdom',
  TW: 'Taiwan',
  KR: 'South Korea',
  JP: 'Japan',
  NL: 'Netherlands',
  BE: 'Belgium',
  DE: 'Germany',
  CN: 'China',
  IE: 'Ireland',
  SG: 'Singapore',
  CH: 'Switzerland',
  FR: 'France',
  IL: 'Israel',
  CA: 'Canada',
  AU: 'Australia',
  IN: 'India',
};

interface GlobalMapProps {
  nodes: EntityNode[];
  onCountryClick: (countryCode: string) => void;
  onNodeClick: (node: EntityNode) => void;
  selectedCountry: string | null;
  colorMetric: 'marketCap' | 'count' | 'revenue';
}

interface CountryData {
  code: string;
  name: string;
  companies: EntityNode[];
  totalMarketCap: number;
  totalRevenue: number;
  coords: [number, number];
}

function GlobalMapComponent({
  nodes,
  onCountryClick,
  onNodeClick: _onNodeClick,
  selectedCountry,
  colorMetric,
}: GlobalMapProps) {
  // Reserved for future drill-down into specific company
  void _onNodeClick;
  const [hoveredCountry, setHoveredCountry] = useState<string | null>(null);
  const [tooltipContent, setTooltipContent] = useState<CountryData | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Aggregate data by country
  const countryData = useMemo(() => {
    const byCountry: Record<string, CountryData> = {};

    nodes.forEach(node => {
      const code = node.jurisdiction || 'unknown';
      if (!COUNTRY_COORDS[code]) return;

      if (!byCountry[code]) {
        byCountry[code] = {
          code,
          name: COUNTRY_NAMES[code] || code,
          companies: [],
          totalMarketCap: 0,
          totalRevenue: 0,
          coords: COUNTRY_COORDS[code],
        };
      }

      byCountry[code].companies.push(node);
      byCountry[code].totalMarketCap += node.metrics?.marketCapB || 0;
      byCountry[code].totalRevenue += node.metrics?.revenueB || 0;
    });

    return Object.values(byCountry);
  }, [nodes]);

  // Calculate marker sizes
  const maxValue = useMemo(() => {
    return Math.max(
      ...countryData.map(c =>
        colorMetric === 'count'
          ? c.companies.length
          : colorMetric === 'marketCap'
          ? c.totalMarketCap
          : c.totalRevenue
      )
    );
  }, [countryData, colorMetric]);

  const getMarkerSize = (data: CountryData): number => {
    const value =
      colorMetric === 'count'
        ? data.companies.length
        : colorMetric === 'marketCap'
        ? data.totalMarketCap
        : data.totalRevenue;

    const normalized = value / maxValue;
    return 8 + normalized * 30; // 8-38px range
  };

  const getMarkerColor = (data: CountryData): string => {
    const isSelected = selectedCountry === data.code;
    const isHovered = hoveredCountry === data.code;

    if (isSelected) return '#3B82F6';
    if (isHovered) return '#60A5FA';

    // Color by dominant industry
    const industries = data.companies.reduce((acc, c) => {
      const ind = c.category;
      acc[ind] = (acc[ind] || 0) + 1;
      return acc;
    }, {} as Record<string, number>);

    const dominant = Object.entries(industries).sort(([, a], [, b]) => b - a)[0]?.[0];

    const colors: Record<string, string> = {
      design: '#4CAF50',
      manufacturing: '#2196F3',
      equipment: '#FF5722',
      memory: '#00BCD4',
      customer: '#9C27B0',
      investor: '#FFC107',
      ip: '#FF9800',
    };

    return colors[dominant] || '#6B7280';
  };

  const handleMarkerHover = (
    data: CountryData | null,
    event?: React.MouseEvent
  ) => {
    setHoveredCountry(data?.code || null);
    setTooltipContent(data);
    if (event) {
      setTooltipPos({ x: event.clientX, y: event.clientY });
    }
  };

  return (
    <div className="relative w-full h-full bg-gray-900 rounded-lg overflow-hidden">
      <ComposableMap
        projection="geoMercator"
        projectionConfig={{
          scale: 140,
          center: [0, 30],
        }}
        style={{ width: '100%', height: '100%' }}
      >
        <ZoomableGroup>
          {/* Base map */}
          <Geographies geography={GEO_URL}>
            {({ geographies }) =>
              geographies.map(geo => {
                const isHighlighted = countryData.some(
                  c => c.name === geo.properties.name
                );
                return (
                  <Geography
                    key={geo.rsmKey}
                    geography={geo}
                    fill={isHighlighted ? '#374151' : '#1F2937'}
                    stroke="#4B5563"
                    strokeWidth={0.5}
                    style={{
                      default: { outline: 'none' },
                      hover: { fill: isHighlighted ? '#4B5563' : '#374151', outline: 'none' },
                      pressed: { outline: 'none' },
                    }}
                  />
                );
              })
            }
          </Geographies>

          {/* Company markers */}
          {countryData.map(data => (
            <Marker
              key={data.code}
              coordinates={data.coords}
              onMouseEnter={e => handleMarkerHover(data, e)}
              onMouseLeave={() => handleMarkerHover(null)}
              onClick={() => onCountryClick(data.code)}
              style={{ cursor: 'pointer' }}
            >
              {/* Glow effect */}
              <circle
                r={getMarkerSize(data) + 4}
                fill={getMarkerColor(data)}
                opacity={0.2}
              />
              {/* Main marker */}
              <circle
                r={getMarkerSize(data)}
                fill={getMarkerColor(data)}
                opacity={0.8}
                stroke="#fff"
                strokeWidth={selectedCountry === data.code ? 2 : 1}
              />
              {/* Country code label */}
              <text
                textAnchor="middle"
                y={4}
                style={{
                  fontFamily: 'system-ui',
                  fill: '#fff',
                  fontSize: getMarkerSize(data) > 15 ? '10px' : '8px',
                  fontWeight: 'bold',
                }}
              >
                {data.code}
              </text>
            </Marker>
          ))}
        </ZoomableGroup>
      </ComposableMap>

      {/* Tooltip */}
      {tooltipContent && (
        <div
          className="fixed z-50 bg-gray-800 border border-gray-600 rounded-lg p-3 shadow-xl pointer-events-none"
          style={{
            left: tooltipPos.x + 15,
            top: tooltipPos.y - 10,
            maxWidth: '280px',
          }}
        >
          <div className="flex items-center gap-2 mb-2">
            <span className="text-xl">{getFlagEmoji(tooltipContent.code)}</span>
            <h4 className="font-bold text-white">{tooltipContent.name}</h4>
          </div>

          <div className="grid grid-cols-3 gap-2 text-center mb-2">
            <div className="bg-gray-700 rounded p-1">
              <div className="text-lg font-bold text-blue-400">
                {tooltipContent.companies.length}
              </div>
              <div className="text-xs text-gray-400">Companies</div>
            </div>
            <div className="bg-gray-700 rounded p-1">
              <div className="text-lg font-bold text-green-400">
                ${formatNumber(tooltipContent.totalMarketCap)}B
              </div>
              <div className="text-xs text-gray-400">Market Cap</div>
            </div>
            <div className="bg-gray-700 rounded p-1">
              <div className="text-lg font-bold text-purple-400">
                ${formatNumber(tooltipContent.totalRevenue)}B
              </div>
              <div className="text-xs text-gray-400">Revenue</div>
            </div>
          </div>

          <div className="text-xs text-gray-300">
            <strong>Top Companies:</strong>
            <div className="mt-1 space-y-0.5">
              {tooltipContent.companies
                .sort((a, b) => (b.metrics?.marketCapB || 0) - (a.metrics?.marketCapB || 0))
                .slice(0, 4)
                .map(c => (
                  <div key={c.id} className="flex justify-between">
                    <span>{c.name}</span>
                    <span className="text-gray-400">
                      {c.metrics?.marketCapB ? `$${c.metrics.marketCapB}B` : '-'}
                    </span>
                  </div>
                ))}
            </div>
          </div>

          <div className="mt-2 text-xs text-blue-400">Click to filter</div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-gray-800/90 rounded p-2 text-xs">
        <div className="text-gray-400 mb-1">Marker Size: {colorMetric === 'count' ? 'Company Count' : colorMetric === 'marketCap' ? 'Market Cap' : 'Revenue'}</div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-green-500" />
            <span>Design</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-blue-500" />
            <span>Manufacturing</span>
          </div>
          <div className="flex items-center gap-1">
            <div className="w-2 h-2 rounded-full bg-orange-500" />
            <span>Equipment</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function getFlagEmoji(countryCode: string): string {
  const flags: Record<string, string> = {
    US: '🇺🇸', GB: '🇬🇧', TW: '🇹🇼', KR: '🇰🇷', JP: '🇯🇵',
    NL: '🇳🇱', BE: '🇧🇪', DE: '🇩🇪', CN: '🇨🇳', IE: '🇮🇪',
    SG: '🇸🇬', CH: '🇨🇭', FR: '🇫🇷', IL: '🇮🇱', CA: '🇨🇦',
    AU: '🇦🇺', IN: '🇮🇳',
  };
  return flags[countryCode] || '🌍';
}

function formatNumber(num: number): string {
  if (num >= 1000) return (num / 1000).toFixed(1) + 'T';
  if (num >= 1) return num.toFixed(0);
  return num.toFixed(1);
}

export const GlobalMap = memo(GlobalMapComponent);
export default GlobalMap;
