/**
 * Graph Filter Sidebar Component
 * 
 * Provides comprehensive filtering for the entity graph:
 * - Entity type filters
 * - Relationship type filters
 * - Category filters
 * - Jurisdiction filters
 * - Metric range filters (market cap, employees)
 * - Date range for temporal queries
 */

import { useState } from 'react';
import type { GraphFilters, EntityType, RelationshipType, EntityCategory } from '../../types/graph';
import { RELATIONSHIP_GROUPS } from '../../types/graph';

interface FilterSidebarProps {
  filters: GraphFilters;
  onFiltersChange: (filters: GraphFilters) => void;
  isOpen: boolean;
  onClose: () => void;
  availableJurisdictions: string[];
}

const ENTITY_TYPES: { value: EntityType; label: string; color: string }[] = [
  { value: 'public_company', label: 'Public Company', color: '#4CAF50' },
  { value: 'private_company', label: 'Private Company', color: '#9E9E9E' },
  { value: 'subsidiary', label: 'Subsidiary', color: '#795548' },
  { value: 'investor', label: 'Investor', color: '#FFC107' },
  { value: 'startup', label: 'Startup', color: '#E91E63' },
  { value: 'foundry', label: 'Foundry', color: '#2196F3' },
  { value: 'equipment', label: 'Equipment', color: '#FF5722' },
  { value: 'hyperscaler', label: 'Hyperscaler', color: '#9C27B0' },
];

const CATEGORIES: { value: EntityCategory; label: string; color: string }[] = [
  { value: 'design', label: 'Design', color: '#4CAF50' },
  { value: 'manufacturing', label: 'Manufacturing', color: '#2196F3' },
  { value: 'equipment', label: 'Equipment', color: '#FF5722' },
  { value: 'memory', label: 'Memory', color: '#00BCD4' },
  { value: 'customer', label: 'Customer', color: '#9C27B0' },
  { value: 'investor', label: 'Investor', color: '#FFC107' },
  { value: 'ip', label: 'IP', color: '#FF9800' },
];

const RELATIONSHIP_TYPE_LABELS: Record<RelationshipType, string> = {
  parent: 'Parent',
  subsidiary: 'Subsidiary',
  affiliate: 'Affiliate',
  successor: 'Successor',
  predecessor: 'Predecessor',
  customer: 'Customer',
  supplier: 'Supplier',
  vendor: 'Vendor',
  partner: 'Partner',
  competitor: 'Competitor',
  investor: 'Investor',
  investee: 'Investee',
  lender: 'Lender',
  borrower: 'Borrower',
  guarantor: 'Guarantor',
  beneficial_owner_of: 'Beneficial Owner',
  auditor: 'Auditor',
  counsel: 'Counsel',
  underwriter: 'Underwriter',
  advisor: 'Advisor',
  officer_of: 'Officer',
  director_of: 'Director',
  employed_by: 'Employee',
  foundry: 'Foundry',
  licensor: 'Licensor',
};

const RELATIONSHIP_COLORS: Record<string, string> = {
  corporate: '#795548',
  business: '#4CAF50',
  financial: '#FFC107',
  service: '#00BCD4',
  employment: '#9C27B0',
  industry: '#FF5722',
};

export function FilterSidebar({
  filters,
  onFiltersChange,
  isOpen,
  onClose,
  availableJurisdictions,
}: FilterSidebarProps) {
  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(['entityTypes', 'relationshipTypes'])
  );

  const toggleSection = (section: string) => {
    setExpandedSections(prev => {
      const next = new Set(prev);
      if (next.has(section)) {
        next.delete(section);
      } else {
        next.add(section);
      }
      return next;
    });
  };

  const toggleEntityType = (type: EntityType) => {
    const current = filters.entityTypes || [];
    const updated = current.includes(type)
      ? current.filter(t => t !== type)
      : [...current, type];
    onFiltersChange({ ...filters, entityTypes: updated });
  };

  const toggleRelationshipType = (type: RelationshipType) => {
    const current = filters.relationshipTypes || [];
    const updated = current.includes(type)
      ? current.filter(t => t !== type)
      : [...current, type];
    onFiltersChange({ ...filters, relationshipTypes: updated });
  };

  const toggleCategory = (category: EntityCategory) => {
    const current = filters.categories || [];
    const updated = current.includes(category)
      ? current.filter(c => c !== category)
      : [...current, category];
    onFiltersChange({ ...filters, categories: updated });
  };

  const toggleJurisdiction = (jurisdiction: string) => {
    const current = filters.jurisdictions || [];
    const updated = current.includes(jurisdiction)
      ? current.filter(j => j !== jurisdiction)
      : [...current, jurisdiction];
    onFiltersChange({ ...filters, jurisdictions: updated });
  };

  const clearAllFilters = () => {
    onFiltersChange({
      entityTypes: [],
      relationshipTypes: [],
      categories: [],
      jurisdictions: [],
    });
  };

  const hasActiveFilters = 
    (filters.entityTypes?.length || 0) > 0 ||
    (filters.relationshipTypes?.length || 0) > 0 ||
    (filters.categories?.length || 0) > 0 ||
    (filters.jurisdictions?.length || 0) > 0 ||
    filters.minMarketCap !== undefined ||
    filters.maxMarketCap !== undefined;

  if (!isOpen) return null;

  return (
    <div className="w-72 bg-gray-800 border-r border-gray-700 flex flex-col h-full overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 border-b border-gray-700">
        <h2 className="font-semibold flex items-center gap-2">
          <span>🔍</span> Filters
          {hasActiveFilters && (
            <span className="bg-blue-500 text-xs px-2 py-0.5 rounded-full">
              Active
            </span>
          )}
        </h2>
        <div className="flex items-center gap-2">
          {hasActiveFilters && (
            <button
              onClick={clearAllFilters}
              className="text-xs text-gray-400 hover:text-white"
            >
              Clear all
            </button>
          )}
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-white p-1"
          >
            ✕
          </button>
        </div>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* Entity Types */}
        <div>
          <button
            onClick={() => toggleSection('entityTypes')}
            className="flex items-center justify-between w-full text-sm font-medium text-gray-300 hover:text-white mb-2"
          >
            <span>Entity Types</span>
            <span>{expandedSections.has('entityTypes') ? '▼' : '▶'}</span>
          </button>
          {expandedSections.has('entityTypes') && (
            <div className="space-y-1 ml-1">
              {ENTITY_TYPES.map(({ value, label, color }) => (
                <label
                  key={value}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-700 p-1 rounded"
                >
                  <input
                    type="checkbox"
                    checked={filters.entityTypes?.includes(value) ?? false}
                    onChange={() => toggleEntityType(value)}
                    className="rounded border-gray-600"
                  />
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-gray-300">{label}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Categories */}
        <div>
          <button
            onClick={() => toggleSection('categories')}
            className="flex items-center justify-between w-full text-sm font-medium text-gray-300 hover:text-white mb-2"
          >
            <span>Categories</span>
            <span>{expandedSections.has('categories') ? '▼' : '▶'}</span>
          </button>
          {expandedSections.has('categories') && (
            <div className="space-y-1 ml-1">
              {CATEGORIES.map(({ value, label, color }) => (
                <label
                  key={value}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-700 p-1 rounded"
                >
                  <input
                    type="checkbox"
                    checked={filters.categories?.includes(value) ?? false}
                    onChange={() => toggleCategory(value)}
                    className="rounded border-gray-600"
                  />
                  <span
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: color }}
                  />
                  <span className="text-gray-300">{label}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Relationship Types */}
        <div>
          <button
            onClick={() => toggleSection('relationshipTypes')}
            className="flex items-center justify-between w-full text-sm font-medium text-gray-300 hover:text-white mb-2"
          >
            <span>Relationship Types</span>
            <span>{expandedSections.has('relationshipTypes') ? '▼' : '▶'}</span>
          </button>
          {expandedSections.has('relationshipTypes') && (
            <div className="space-y-3 ml-1">
              {Object.entries(RELATIONSHIP_GROUPS).map(([group, types]) => (
                <div key={group}>
                  <div
                    className="text-xs font-medium mb-1 flex items-center gap-1"
                    style={{ color: RELATIONSHIP_COLORS[group] || '#999' }}
                  >
                    <span
                      className="w-2 h-2 rounded-full"
                      style={{ backgroundColor: RELATIONSHIP_COLORS[group] || '#999' }}
                    />
                    {group.charAt(0).toUpperCase() + group.slice(1)}
                  </div>
                  <div className="space-y-1 ml-3">
                    {types.map(type => (
                      <label
                        key={type}
                        className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-700 p-1 rounded"
                      >
                        <input
                          type="checkbox"
                          checked={filters.relationshipTypes?.includes(type as RelationshipType) ?? false}
                          onChange={() => toggleRelationshipType(type as RelationshipType)}
                          className="rounded border-gray-600"
                        />
                        <span className="text-gray-300">
                          {RELATIONSHIP_TYPE_LABELS[type as RelationshipType] || type}
                        </span>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Jurisdictions */}
        <div>
          <button
            onClick={() => toggleSection('jurisdictions')}
            className="flex items-center justify-between w-full text-sm font-medium text-gray-300 hover:text-white mb-2"
          >
            <span>Jurisdictions</span>
            <span>{expandedSections.has('jurisdictions') ? '▼' : '▶'}</span>
          </button>
          {expandedSections.has('jurisdictions') && (
            <div className="space-y-1 ml-1">
              {availableJurisdictions.map(j => (
                <label
                  key={j}
                  className="flex items-center gap-2 text-sm cursor-pointer hover:bg-gray-700 p-1 rounded"
                >
                  <input
                    type="checkbox"
                    checked={filters.jurisdictions?.includes(j) ?? false}
                    onChange={() => toggleJurisdiction(j)}
                    className="rounded border-gray-600"
                  />
                  <span className="text-gray-300">{getJurisdictionDisplay(j)}</span>
                </label>
              ))}
            </div>
          )}
        </div>

        {/* Market Cap Range */}
        <div>
          <button
            onClick={() => toggleSection('metrics')}
            className="flex items-center justify-between w-full text-sm font-medium text-gray-300 hover:text-white mb-2"
          >
            <span>Metrics</span>
            <span>{expandedSections.has('metrics') ? '▼' : '▶'}</span>
          </button>
          {expandedSections.has('metrics') && (
            <div className="space-y-3 ml-1">
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Min Market Cap ($B)
                </label>
                <input
                  type="number"
                  value={filters.minMarketCap ?? ''}
                  onChange={e => onFiltersChange({
                    ...filters,
                    minMarketCap: e.target.value ? Number(e.target.value) : undefined,
                  })}
                  placeholder="0"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Max Market Cap ($B)
                </label>
                <input
                  type="number"
                  value={filters.maxMarketCap ?? ''}
                  onChange={e => onFiltersChange({
                    ...filters,
                    maxMarketCap: e.target.value ? Number(e.target.value) : undefined,
                  })}
                  placeholder="∞"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm"
                />
              </div>
              <div>
                <label className="text-xs text-gray-400 block mb-1">
                  Min Employees
                </label>
                <input
                  type="number"
                  value={filters.minEmployees ?? ''}
                  onChange={e => onFiltersChange({
                    ...filters,
                    minEmployees: e.target.value ? Number(e.target.value) : undefined,
                  })}
                  placeholder="0"
                  className="w-full bg-gray-700 border border-gray-600 rounded px-2 py-1 text-sm"
                />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Footer with apply hint */}
      <div className="p-3 border-t border-gray-700 text-xs text-gray-500">
        Filters apply immediately
      </div>
    </div>
  );
}

function getJurisdictionDisplay(code: string): string {
  const flags: Record<string, string> = {
    US: '🇺🇸 United States',
    GB: '🇬🇧 United Kingdom',
    TW: '🇹🇼 Taiwan',
    KR: '🇰🇷 South Korea',
    JP: '🇯🇵 Japan',
    NL: '🇳🇱 Netherlands',
    BE: '🇧🇪 Belgium',
    DE: '🇩🇪 Germany',
    CN: '🇨🇳 China',
  };
  return flags[code] || `🌍 ${code}`;
}

export default FilterSidebar;
