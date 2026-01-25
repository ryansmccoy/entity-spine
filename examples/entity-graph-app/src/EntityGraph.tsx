import { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import ForceGraph3D, { ForceGraphMethods } from 'react-force-graph-3d';
import * as THREE from 'three';
import { Search, Filter, ZoomIn, ZoomOut, RotateCcw, Info, X, Building2, Users, DollarSign, Link2, Globe, Hash, Briefcase, ChevronDown } from 'lucide-react';
import clsx from 'clsx';

// ============================================================================
// TYPES
// ============================================================================

interface EntityNode {
  id: string;
  name: string;
  type: 'company' | 'person' | 'fund' | 'government' | 'organization';
  category?: string;
  description?: string;
  marketCap?: number;
  revenue?: number;
  employees?: number;
  founded?: number;
  headquarters?: string;
  cik?: string;
  lei?: string;
  ticker?: string;
  industry?: string;
  sector?: string;
  website?: string;
  // Graph properties
  x?: number;
  y?: number;
  z?: number;
  vx?: number;
  vy?: number;
  vz?: number;
  fx?: number | null;
  fy?: number | null;
  fz?: number | null;
}

interface RelationshipLink {
  source: string | EntityNode;
  target: string | EntityNode;
  type: 'owns' | 'supplies' | 'competes' | 'partners' | 'invests' | 'regulates' | 'employs' | 'licenses';
  strength?: number;
  value?: number;
  description?: string;
}

interface GraphData {
  nodes: EntityNode[];
  links: RelationshipLink[];
}

type SizeMetric = 'marketCap' | 'revenue' | 'employees' | 'connections';

// ============================================================================
// SAMPLE DATA - SEMICONDUCTOR ECOSYSTEM
// ============================================================================

const SEMICONDUCTOR_ECOSYSTEM: GraphData = {
  nodes: [
    // Major Chip Companies
    { id: 'nvidia', name: 'NVIDIA Corporation', type: 'company', category: 'chip_designer', description: 'Leading GPU and AI chip designer', marketCap: 3200000000000, revenue: 60900000000, employees: 29600, founded: 1993, headquarters: 'Santa Clara, CA', ticker: 'NVDA', cik: '0001045810', industry: 'Semiconductors', sector: 'Technology', website: 'nvidia.com' },
    { id: 'amd', name: 'Advanced Micro Devices', type: 'company', category: 'chip_designer', description: 'CPU and GPU designer', marketCap: 225000000000, revenue: 22680000000, employees: 26000, founded: 1969, headquarters: 'Santa Clara, CA', ticker: 'AMD', cik: '0000002488', industry: 'Semiconductors', sector: 'Technology', website: 'amd.com' },
    { id: 'intel', name: 'Intel Corporation', type: 'company', category: 'idm', description: 'Integrated device manufacturer', marketCap: 108000000000, revenue: 54228000000, employees: 124800, founded: 1968, headquarters: 'Santa Clara, CA', ticker: 'INTC', cik: '0000050863', industry: 'Semiconductors', sector: 'Technology', website: 'intel.com' },
    { id: 'qualcomm', name: 'Qualcomm Inc', type: 'company', category: 'chip_designer', description: 'Mobile processor designer', marketCap: 188000000000, revenue: 35820000000, employees: 51000, founded: 1985, headquarters: 'San Diego, CA', ticker: 'QCOM', cik: '0000804328', industry: 'Semiconductors', sector: 'Technology', website: 'qualcomm.com' },
    { id: 'broadcom', name: 'Broadcom Inc', type: 'company', category: 'chip_designer', description: 'Infrastructure semiconductor solutions', marketCap: 774000000000, revenue: 35819000000, employees: 20000, founded: 1961, headquarters: 'San Jose, CA', ticker: 'AVGO', cik: '0001730168', industry: 'Semiconductors', sector: 'Technology', website: 'broadcom.com' },
    
    // Foundries
    { id: 'tsmc', name: 'Taiwan Semiconductor', type: 'company', category: 'foundry', description: 'World\'s largest chip foundry', marketCap: 890000000000, revenue: 69300000000, employees: 73090, founded: 1987, headquarters: 'Hsinchu, Taiwan', ticker: 'TSM', industry: 'Semiconductors', sector: 'Technology', website: 'tsmc.com' },
    { id: 'samsung_semi', name: 'Samsung Semiconductor', type: 'company', category: 'foundry', description: 'Major foundry and memory producer', marketCap: 320000000000, revenue: 52740000000, employees: 120000, founded: 1974, headquarters: 'Hwaseong, South Korea', industry: 'Semiconductors', sector: 'Technology', website: 'samsung.com/semiconductor' },
    { id: 'globalfoundries', name: 'GlobalFoundries', type: 'company', category: 'foundry', description: 'Specialty chip foundry', marketCap: 27000000000, revenue: 7392000000, employees: 13000, founded: 2009, headquarters: 'Malta, NY', ticker: 'GFS', cik: '0001709048', industry: 'Semiconductors', sector: 'Technology', website: 'globalfoundries.com' },
    
    // Equipment Makers
    { id: 'asml', name: 'ASML Holding', type: 'company', category: 'equipment', description: 'EUV lithography monopoly', marketCap: 356000000000, revenue: 27559000000, employees: 42795, founded: 1984, headquarters: 'Veldhoven, Netherlands', ticker: 'ASML', industry: 'Semiconductor Equipment', sector: 'Technology', website: 'asml.com' },
    { id: 'lam', name: 'Lam Research', type: 'company', category: 'equipment', description: 'Etch and deposition equipment', marketCap: 116000000000, revenue: 17428000000, employees: 17300, founded: 1980, headquarters: 'Fremont, CA', ticker: 'LRCX', cik: '0000707549', industry: 'Semiconductor Equipment', sector: 'Technology', website: 'lamresearch.com' },
    { id: 'applied', name: 'Applied Materials', type: 'company', category: 'equipment', description: 'Semiconductor equipment leader', marketCap: 166000000000, revenue: 26517000000, employees: 34000, founded: 1967, headquarters: 'Santa Clara, CA', ticker: 'AMAT', cik: '0000006951', industry: 'Semiconductor Equipment', sector: 'Technology', website: 'appliedmaterials.com' },
    { id: 'klac', name: 'KLA Corporation', type: 'company', category: 'equipment', description: 'Process control and inspection', marketCap: 100000000000, revenue: 9654000000, employees: 15000, founded: 1975, headquarters: 'Milpitas, CA', ticker: 'KLAC', cik: '0000319201', industry: 'Semiconductor Equipment', sector: 'Technology', website: 'kla.com' },
    
    // EDA & IP
    { id: 'synopsys', name: 'Synopsys Inc', type: 'company', category: 'eda', description: 'EDA tools and IP provider', marketCap: 85000000000, revenue: 5840000000, employees: 19000, founded: 1986, headquarters: 'Sunnyvale, CA', ticker: 'SNPS', cik: '0000883241', industry: 'Software', sector: 'Technology', website: 'synopsys.com' },
    { id: 'cadence', name: 'Cadence Design', type: 'company', category: 'eda', description: 'EDA and design services', marketCap: 80000000000, revenue: 4090000000, employees: 10700, founded: 1988, headquarters: 'San Jose, CA', ticker: 'CDNS', cik: '0000813672', industry: 'Software', sector: 'Technology', website: 'cadence.com' },
    { id: 'arm', name: 'Arm Holdings', type: 'company', category: 'ip', description: 'CPU architecture licensor', marketCap: 153000000000, revenue: 2679000000, employees: 6409, founded: 1990, headquarters: 'Cambridge, UK', ticker: 'ARM', industry: 'Semiconductors', sector: 'Technology', website: 'arm.com' },
    
    // Tech Giants (Chip Customers & Designers)
    { id: 'apple', name: 'Apple Inc', type: 'company', category: 'tech_giant', description: 'Consumer electronics, designs own chips', marketCap: 3440000000000, revenue: 383285000000, employees: 161000, founded: 1976, headquarters: 'Cupertino, CA', ticker: 'AAPL', cik: '0000320193', industry: 'Consumer Electronics', sector: 'Technology', website: 'apple.com' },
    { id: 'google', name: 'Alphabet (Google)', type: 'company', category: 'tech_giant', description: 'Cloud and AI, designs TPU chips', marketCap: 2100000000000, revenue: 307394000000, employees: 182381, founded: 1998, headquarters: 'Mountain View, CA', ticker: 'GOOGL', cik: '0001652044', industry: 'Internet Services', sector: 'Technology', website: 'google.com' },
    { id: 'microsoft', name: 'Microsoft Corporation', type: 'company', category: 'tech_giant', description: 'Software and cloud, developing custom chips', marketCap: 3150000000000, revenue: 211915000000, employees: 221000, founded: 1975, headquarters: 'Redmond, WA', ticker: 'MSFT', cik: '0000789019', industry: 'Software', sector: 'Technology', website: 'microsoft.com' },
    { id: 'amazon', name: 'Amazon.com', type: 'company', category: 'tech_giant', description: 'E-commerce and cloud, designs Graviton chips', marketCap: 1950000000000, revenue: 574785000000, employees: 1525000, founded: 1994, headquarters: 'Seattle, WA', ticker: 'AMZN', cik: '0001018724', industry: 'E-commerce', sector: 'Consumer Cyclical', website: 'amazon.com' },
    { id: 'meta', name: 'Meta Platforms', type: 'company', category: 'tech_giant', description: 'Social media, AI chip development', marketCap: 1280000000000, revenue: 134902000000, employees: 67317, founded: 2004, headquarters: 'Menlo Park, CA', ticker: 'META', cik: '0001326801', industry: 'Internet Services', sector: 'Technology', website: 'meta.com' },
    { id: 'tesla', name: 'Tesla Inc', type: 'company', category: 'tech_giant', description: 'EVs, designs FSD and Dojo chips', marketCap: 780000000000, revenue: 96773000000, employees: 140473, founded: 2003, headquarters: 'Austin, TX', ticker: 'TSLA', cik: '0001318605', industry: 'Automotive', sector: 'Consumer Cyclical', website: 'tesla.com' },
    
    // Memory
    { id: 'micron', name: 'Micron Technology', type: 'company', category: 'memory', description: 'DRAM and NAND memory', marketCap: 112000000000, revenue: 21440000000, employees: 48000, founded: 1978, headquarters: 'Boise, ID', ticker: 'MU', cik: '0000723125', industry: 'Semiconductors', sector: 'Technology', website: 'micron.com' },
    { id: 'skhynix', name: 'SK Hynix', type: 'company', category: 'memory', description: 'Memory chip manufacturer', marketCap: 95000000000, revenue: 26800000000, employees: 29000, founded: 1983, headquarters: 'Icheon, South Korea', industry: 'Semiconductors', sector: 'Technology', website: 'skhynix.com' },
    { id: 'westerndigital', name: 'Western Digital', type: 'company', category: 'memory', description: 'Storage solutions and NAND', marketCap: 23000000000, revenue: 12317000000, employees: 51000, founded: 1970, headquarters: 'San Jose, CA', ticker: 'WDC', cik: '0000106040', industry: 'Data Storage', sector: 'Technology', website: 'westerndigital.com' },
    
    // Investors
    { id: 'softbank', name: 'SoftBank Group', type: 'fund', category: 'investor', description: 'Major tech investor, owned ARM', marketCap: 85000000000, revenue: 46000000000, employees: 60000, founded: 1981, headquarters: 'Tokyo, Japan', industry: 'Investment', sector: 'Financial Services', website: 'softbank.jp' },
    { id: 'blackrock', name: 'BlackRock Inc', type: 'fund', category: 'investor', description: 'World\'s largest asset manager', marketCap: 115000000000, revenue: 17859000000, employees: 19800, founded: 1988, headquarters: 'New York, NY', ticker: 'BLK', cik: '0001364742', industry: 'Asset Management', sector: 'Financial Services', website: 'blackrock.com' },
    { id: 'vanguard', name: 'Vanguard Group', type: 'fund', category: 'investor', description: 'Major index fund provider', employees: 19000, founded: 1975, headquarters: 'Malvern, PA', industry: 'Asset Management', sector: 'Financial Services', website: 'vanguard.com' },
    
    // Government/Regulatory
    { id: 'chips_act', name: 'CHIPS Act Program', type: 'government', category: 'policy', description: 'US semiconductor subsidy program', founded: 2022, headquarters: 'Washington, DC' },
    { id: 'commerce_dept', name: 'US Commerce Dept', type: 'government', category: 'regulator', description: 'Export controls on chips', headquarters: 'Washington, DC', website: 'commerce.gov' },
    
    // Key People
    { id: 'jensen_huang', name: 'Jensen Huang', type: 'person', category: 'executive', description: 'CEO & Co-founder of NVIDIA' },
    { id: 'lisa_su', name: 'Lisa Su', type: 'person', category: 'executive', description: 'CEO of AMD' },
    { id: 'pat_gelsinger', name: 'Pat Gelsinger', type: 'person', category: 'executive', description: 'CEO of Intel' },
    { id: 'morris_chang', name: 'Morris Chang', type: 'person', category: 'executive', description: 'Founder of TSMC' },
    { id: 'tim_cook', name: 'Tim Cook', type: 'person', category: 'executive', description: 'CEO of Apple' },
    { id: 'satya_nadella', name: 'Satya Nadella', type: 'person', category: 'executive', description: 'CEO of Microsoft' },
    { id: 'sundar_pichai', name: 'Sundar Pichai', type: 'person', category: 'executive', description: 'CEO of Alphabet' },
    { id: 'elon_musk', name: 'Elon Musk', type: 'person', category: 'executive', description: 'CEO of Tesla' },
    
    // Additional Semiconductor Companies
    { id: 'marvell', name: 'Marvell Technology', type: 'company', category: 'chip_designer', description: 'Data infrastructure semiconductors', marketCap: 77000000000, revenue: 5507000000, employees: 8200, founded: 1995, headquarters: 'Wilmington, DE', ticker: 'MRVL', cik: '0001877522', industry: 'Semiconductors', sector: 'Technology', website: 'marvell.com' },
    { id: 'analog', name: 'Analog Devices', type: 'company', category: 'analog', description: 'Analog and mixed-signal semiconductors', marketCap: 110000000000, revenue: 12306000000, employees: 26000, founded: 1965, headquarters: 'Wilmington, MA', ticker: 'ADI', cik: '0000006281', industry: 'Semiconductors', sector: 'Technology', website: 'analog.com' },
    { id: 'txn', name: 'Texas Instruments', type: 'company', category: 'analog', description: 'Analog chips and embedded processors', marketCap: 177000000000, revenue: 17519000000, employees: 34000, founded: 1951, headquarters: 'Dallas, TX', ticker: 'TXN', cik: '0000097476', industry: 'Semiconductors', sector: 'Technology', website: 'ti.com' },
    { id: 'nxp', name: 'NXP Semiconductors', type: 'company', category: 'automotive', description: 'Automotive and IoT chips', marketCap: 62000000000, revenue: 13276000000, employees: 34500, founded: 2006, headquarters: 'Eindhoven, Netherlands', ticker: 'NXPI', cik: '0001413447', industry: 'Semiconductors', sector: 'Technology', website: 'nxp.com' },
    { id: 'onsemi', name: 'onsemi', type: 'company', category: 'automotive', description: 'Power and sensing semiconductors', marketCap: 30000000000, revenue: 8253000000, employees: 33900, founded: 1999, headquarters: 'Scottsdale, AZ', ticker: 'ON', cik: '0001141197', industry: 'Semiconductors', sector: 'Technology', website: 'onsemi.com' },
  ],
  links: [
    // Manufacturing Relationships (Foundry)
    { source: 'nvidia', target: 'tsmc', type: 'supplies', strength: 1.0, description: 'TSMC manufactures NVIDIA GPUs' },
    { source: 'amd', target: 'tsmc', type: 'supplies', strength: 1.0, description: 'TSMC manufactures AMD CPUs/GPUs' },
    { source: 'apple', target: 'tsmc', type: 'supplies', strength: 1.0, description: 'TSMC manufactures Apple Silicon' },
    { source: 'qualcomm', target: 'tsmc', type: 'supplies', strength: 0.8, description: 'TSMC manufactures Snapdragon' },
    { source: 'qualcomm', target: 'samsung_semi', type: 'supplies', strength: 0.2, description: 'Samsung also manufactures Snapdragon' },
    { source: 'broadcom', target: 'tsmc', type: 'supplies', strength: 0.9, description: 'TSMC manufactures Broadcom chips' },
    { source: 'marvell', target: 'tsmc', type: 'supplies', strength: 0.9, description: 'TSMC manufactures Marvell chips' },
    { source: 'google', target: 'tsmc', type: 'supplies', strength: 0.8, description: 'TSMC manufactures Google TPUs' },
    { source: 'amazon', target: 'tsmc', type: 'supplies', strength: 0.7, description: 'TSMC manufactures AWS Graviton' },
    { source: 'intel', target: 'tsmc', type: 'supplies', strength: 0.3, description: 'Intel outsources some chips to TSMC' },
    
    // Equipment Supply Chain
    { source: 'asml', target: 'tsmc', type: 'supplies', strength: 1.0, description: 'ASML supplies EUV machines to TSMC' },
    { source: 'asml', target: 'samsung_semi', type: 'supplies', strength: 0.9, description: 'ASML supplies to Samsung' },
    { source: 'asml', target: 'intel', type: 'supplies', strength: 0.8, description: 'ASML supplies to Intel' },
    { source: 'lam', target: 'tsmc', type: 'supplies', strength: 0.9, description: 'Lam supplies etch equipment' },
    { source: 'applied', target: 'tsmc', type: 'supplies', strength: 0.9, description: 'Applied supplies deposition equipment' },
    { source: 'klac', target: 'tsmc', type: 'supplies', strength: 0.9, description: 'KLA supplies inspection equipment' },
    
    // EDA/IP Licensing
    { source: 'arm', target: 'apple', type: 'licenses', strength: 0.9, description: 'Apple licenses ARM architecture' },
    { source: 'arm', target: 'qualcomm', type: 'licenses', strength: 1.0, description: 'Qualcomm licenses ARM for Snapdragon' },
    { source: 'arm', target: 'nvidia', type: 'licenses', strength: 0.7, description: 'NVIDIA licenses ARM for Grace CPU' },
    { source: 'arm', target: 'samsung_semi', type: 'licenses', strength: 0.8, description: 'Samsung licenses ARM' },
    { source: 'arm', target: 'amazon', type: 'licenses', strength: 0.8, description: 'Amazon licenses ARM for Graviton' },
    { source: 'synopsys', target: 'nvidia', type: 'supplies', strength: 0.8, description: 'Synopsys provides EDA tools' },
    { source: 'synopsys', target: 'apple', type: 'supplies', strength: 0.8, description: 'Synopsys provides EDA to Apple' },
    { source: 'cadence', target: 'nvidia', type: 'supplies', strength: 0.8, description: 'Cadence provides EDA tools' },
    { source: 'cadence', target: 'amd', type: 'supplies', strength: 0.8, description: 'Cadence provides EDA to AMD' },
    
    // Competition
    { source: 'nvidia', target: 'amd', type: 'competes', strength: 0.9, description: 'GPU competition' },
    { source: 'nvidia', target: 'intel', type: 'competes', strength: 0.7, description: 'AI chip competition' },
    { source: 'amd', target: 'intel', type: 'competes', strength: 1.0, description: 'CPU competition' },
    { source: 'tsmc', target: 'samsung_semi', type: 'competes', strength: 0.8, description: 'Foundry competition' },
    { source: 'tsmc', target: 'intel', type: 'competes', strength: 0.5, description: 'Intel Foundry Services competition' },
    { source: 'synopsys', target: 'cadence', type: 'competes', strength: 0.9, description: 'EDA market competition' },
    { source: 'micron', target: 'skhynix', type: 'competes', strength: 0.9, description: 'Memory competition' },
    { source: 'micron', target: 'samsung_semi', type: 'competes', strength: 0.9, description: 'Memory competition' },
    { source: 'google', target: 'microsoft', type: 'competes', strength: 0.8, description: 'Cloud and AI competition' },
    { source: 'google', target: 'amazon', type: 'competes', strength: 0.8, description: 'Cloud competition' },
    
    // Customer Relationships
    { source: 'nvidia', target: 'microsoft', type: 'supplies', strength: 0.9, description: 'GPUs for Azure AI' },
    { source: 'nvidia', target: 'google', type: 'supplies', strength: 0.8, description: 'GPUs for Google Cloud' },
    { source: 'nvidia', target: 'amazon', type: 'supplies', strength: 0.8, description: 'GPUs for AWS' },
    { source: 'nvidia', target: 'meta', type: 'supplies', strength: 0.9, description: 'GPUs for Meta AI' },
    { source: 'nvidia', target: 'tesla', type: 'supplies', strength: 0.6, description: 'Training GPUs for Tesla' },
    { source: 'qualcomm', target: 'apple', type: 'supplies', strength: 0.3, description: '5G modems for iPhone' },
    { source: 'micron', target: 'nvidia', type: 'supplies', strength: 0.8, description: 'HBM memory for GPUs' },
    { source: 'skhynix', target: 'nvidia', type: 'supplies', strength: 0.9, description: 'HBM memory for GPUs' },
    
    // Investment Relationships
    { source: 'softbank', target: 'arm', type: 'invests', strength: 0.9, description: 'SoftBank majority owner of ARM' },
    { source: 'blackrock', target: 'nvidia', type: 'invests', strength: 0.5, description: 'Major institutional investor' },
    { source: 'blackrock', target: 'apple', type: 'invests', strength: 0.5, description: 'Major institutional investor' },
    { source: 'vanguard', target: 'nvidia', type: 'invests', strength: 0.5, description: 'Major institutional investor' },
    { source: 'vanguard', target: 'microsoft', type: 'invests', strength: 0.5, description: 'Major institutional investor' },
    
    // Government/Regulatory
    { source: 'chips_act', target: 'intel', type: 'invests', strength: 0.9, description: '$8.5B CHIPS Act funding' },
    { source: 'chips_act', target: 'tsmc', type: 'invests', strength: 0.7, description: 'CHIPS Act funding for Arizona fab' },
    { source: 'chips_act', target: 'samsung_semi', type: 'invests', strength: 0.6, description: 'CHIPS Act funding for Texas fab' },
    { source: 'chips_act', target: 'globalfoundries', type: 'invests', strength: 0.5, description: 'CHIPS Act funding' },
    { source: 'commerce_dept', target: 'nvidia', type: 'regulates', strength: 0.7, description: 'Export controls on AI chips' },
    { source: 'commerce_dept', target: 'asml', type: 'regulates', strength: 0.8, description: 'Export controls on EUV' },
    
    // Leadership
    { source: 'jensen_huang', target: 'nvidia', type: 'employs', strength: 1.0, description: 'CEO & Co-founder' },
    { source: 'lisa_su', target: 'amd', type: 'employs', strength: 1.0, description: 'CEO' },
    { source: 'pat_gelsinger', target: 'intel', type: 'employs', strength: 1.0, description: 'CEO' },
    { source: 'morris_chang', target: 'tsmc', type: 'employs', strength: 0.5, description: 'Founder (retired)' },
    { source: 'tim_cook', target: 'apple', type: 'employs', strength: 1.0, description: 'CEO' },
    { source: 'satya_nadella', target: 'microsoft', type: 'employs', strength: 1.0, description: 'CEO' },
    { source: 'sundar_pichai', target: 'google', type: 'employs', strength: 1.0, description: 'CEO' },
    { source: 'elon_musk', target: 'tesla', type: 'employs', strength: 1.0, description: 'CEO' },
    
    // Partnership
    { source: 'nvidia', target: 'microsoft', type: 'partners', strength: 0.8, description: 'AI partnership' },
    { source: 'arm', target: 'nvidia', type: 'partners', strength: 0.6, description: 'Technology partnership' },
    { source: 'intel', target: 'microsoft', type: 'partners', strength: 0.7, description: 'Long-standing partnership' },
    { source: 'google', target: 'broadcom', type: 'partners', strength: 0.7, description: 'Custom chip development' },
    { source: 'amazon', target: 'marvell', type: 'partners', strength: 0.6, description: 'Custom chip development' },
  ]
};

// ============================================================================
// COLOR SCHEMES
// ============================================================================

const NODE_COLORS: Record<EntityNode['type'], string> = {
  company: '#3B82F6',    // Blue
  person: '#10B981',     // Green
  fund: '#F59E0B',       // Amber
  government: '#EF4444', // Red
  organization: '#8B5CF6' // Purple
};

const CATEGORY_COLORS: Record<string, string> = {
  chip_designer: '#3B82F6',
  foundry: '#06B6D4',
  equipment: '#8B5CF6',
  eda: '#EC4899',
  ip: '#F97316',
  tech_giant: '#10B981',
  memory: '#6366F1',
  analog: '#14B8A6',
  automotive: '#84CC16',
  investor: '#F59E0B',
  policy: '#EF4444',
  regulator: '#DC2626',
  executive: '#10B981',
  idm: '#0EA5E9'
};

const LINK_COLORS: Record<RelationshipLink['type'], string> = {
  owns: '#F59E0B',
  supplies: '#3B82F6',
  competes: '#EF4444',
  partners: '#10B981',
  invests: '#F59E0B',
  regulates: '#8B5CF6',
  employs: '#6B7280',
  licenses: '#EC4899'
};

// ============================================================================
// COMPONENT
// ============================================================================

export default function EntityGraph() {
  const fgRef = useRef<ForceGraphMethods>();
  const [graphData] = useState<GraphData>(SEMICONDUCTOR_ECOSYSTEM);
  const [selectedNode, setSelectedNode] = useState<EntityNode | null>(null);
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set());
  const [highlightLinks, setHighlightLinks] = useState<Set<RelationshipLink>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [showFilters, setShowFilters] = useState(false);
  const [selectedTypes, setSelectedTypes] = useState<Set<EntityNode['type']>>(new Set(['company', 'person', 'fund', 'government', 'organization']));
  const [selectedCategories, setSelectedCategories] = useState<Set<string>>(new Set());
  const [sizeMetric, setSizeMetric] = useState<SizeMetric>('marketCap');
  const [showSizeDropdown, setShowSizeDropdown] = useState(false);
  
  // Get unique categories
  const allCategories = useMemo(() => {
    const cats = new Set<string>();
    graphData.nodes.forEach(node => {
      if (node.category) cats.add(node.category);
    });
    return Array.from(cats).sort();
  }, [graphData]);
  
  // Initialize selected categories
  useEffect(() => {
    if (selectedCategories.size === 0) {
      setSelectedCategories(new Set(allCategories));
    }
  }, [allCategories, selectedCategories.size]);

  // Filter nodes based on search and type filters
  const filteredData = useMemo(() => {
    const query = searchQuery.toLowerCase();
    const filteredNodes = graphData.nodes.filter(node => {
      const matchesSearch = !query || 
        node.name.toLowerCase().includes(query) ||
        node.id.toLowerCase().includes(query) ||
        (node.description?.toLowerCase().includes(query)) ||
        (node.ticker?.toLowerCase().includes(query));
      const matchesType = selectedTypes.has(node.type);
      const matchesCategory = !node.category || selectedCategories.has(node.category);
      return matchesSearch && matchesType && matchesCategory;
    });
    
    const nodeIds = new Set(filteredNodes.map(n => n.id));
    const filteredLinks = graphData.links.filter(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      return nodeIds.has(sourceId) && nodeIds.has(targetId);
    });
    
    return { nodes: filteredNodes, links: filteredLinks };
  }, [graphData, searchQuery, selectedTypes, selectedCategories]);

  // Calculate node connections for sizing
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

  // Get node size based on selected metric
  const getNodeSize = useCallback((node: EntityNode) => {
    const baseSize = 6;
    const maxSize = 20;
    
    switch (sizeMetric) {
      case 'marketCap': {
        if (!node.marketCap) return baseSize;
        const maxCap = Math.max(...graphData.nodes.map(n => n.marketCap || 0));
        return baseSize + (node.marketCap / maxCap) * (maxSize - baseSize);
      }
      case 'revenue': {
        if (!node.revenue) return baseSize;
        const maxRev = Math.max(...graphData.nodes.map(n => n.revenue || 0));
        return baseSize + (node.revenue / maxRev) * (maxSize - baseSize);
      }
      case 'employees': {
        if (!node.employees) return baseSize;
        const maxEmp = Math.max(...graphData.nodes.map(n => n.employees || 0));
        return baseSize + (node.employees / maxEmp) * (maxSize - baseSize);
      }
      case 'connections': {
        const conns = nodeConnections[node.id] || 0;
        const maxConns = Math.max(...Object.values(nodeConnections), 1);
        return baseSize + (conns / maxConns) * (maxSize - baseSize);
      }
      default:
        return baseSize;
    }
  }, [sizeMetric, graphData.nodes, nodeConnections]);

  // Handle node click
  const handleNodeClick = useCallback((node: EntityNode) => {
    setSelectedNode(node);
    
    // Highlight connected nodes and links
    const connectedNodes = new Set<string>([node.id]);
    const connectedLinks = new Set<RelationshipLink>();
    
    graphData.links.forEach(link => {
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
    
    // Zoom to node
    if (fgRef.current) {
      const distance = 200;
      const distRatio = 1 + distance / Math.hypot(node.x || 0, node.y || 0, node.z || 0);
      fgRef.current.cameraPosition(
        { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
        { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
        1500
      );
    }
  }, [graphData.links]);

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

  // Get relationships for selected node
  const getNodeRelationships = useCallback((node: EntityNode) => {
    return graphData.links.filter(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      return sourceId === node.id || targetId === node.id;
    }).map(link => {
      const sourceId = typeof link.source === 'string' ? link.source : link.source.id;
      const targetId = typeof link.target === 'string' ? link.target : link.target.id;
      const isSource = sourceId === node.id;
      const otherId = isSource ? targetId : sourceId;
      const otherNode = graphData.nodes.find(n => n.id === otherId);
      return {
        ...link,
        direction: isSource ? 'outgoing' : 'incoming',
        otherNode
      };
    });
  }, [graphData]);

  return (
    <div className="relative w-full h-full bg-gray-950">
      {/* Graph Canvas */}
      <ForceGraph3D
        ref={fgRef}
        graphData={filteredData}
        nodeId="id"
        nodeLabel=""
        nodeColor={(node: EntityNode) => {
          if (highlightNodes.size > 0 && !highlightNodes.has(node.id)) {
            return '#374151'; // Dimmed
          }
          return node.category ? (CATEGORY_COLORS[node.category] || NODE_COLORS[node.type]) : NODE_COLORS[node.type];
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
        linkWidth={(link: RelationshipLink) => {
          if (highlightLinks.has(link)) return 2;
          return (link.strength || 0.5) * 1.5;
        }}
        linkOpacity={0.6}
        linkDirectionalParticles={(link: RelationshipLink) => highlightLinks.has(link) ? 4 : 0}
        linkDirectionalParticleWidth={2}
        linkDirectionalParticleSpeed={0.005}
        onNodeClick={handleNodeClick}
        onBackgroundClick={clearSelection}
        backgroundColor="#030712"
        nodeThreeObject={(node: EntityNode) => {
          const size = getNodeSize(node);
          const color = node.category ? (CATEGORY_COLORS[node.category] || NODE_COLORS[node.type]) : NODE_COLORS[node.type];
          const isHighlighted = highlightNodes.size === 0 || highlightNodes.has(node.id);
          
          // Create group
          const group = new THREE.Group();
          
          // Main sphere
          const geometry = new THREE.SphereGeometry(size, 16, 16);
          const material = new THREE.MeshLambertMaterial({
            color: isHighlighted ? color : '#374151',
            transparent: true,
            opacity: isHighlighted ? 0.9 : 0.3
          });
          const sphere = new THREE.Mesh(geometry, material);
          group.add(sphere);
          
          // Glow effect for highlighted nodes
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
          
          // Label sprite
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

      {/* Controls Panel */}
      <div className="absolute top-4 left-4 flex flex-col gap-2 z-10">
        {/* Search */}
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
        
        {/* Filter Toggle */}
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
        
        {/* Size Metric Dropdown */}
        <div className="relative">
          <button
            onClick={() => setShowSizeDropdown(!showSizeDropdown)}
            className="flex items-center justify-between gap-2 px-4 py-2 w-full bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-800"
          >
            <span>Size: {sizeMetric === 'marketCap' ? 'Market Cap' : sizeMetric === 'revenue' ? 'Revenue' : sizeMetric === 'employees' ? 'Employees' : 'Connections'}</span>
            <ChevronDown className="w-4 h-4" />
          </button>
          {showSizeDropdown && (
            <div className="absolute top-full left-0 mt-1 w-full bg-gray-900 border border-gray-700 rounded-lg overflow-hidden z-20">
              {(['marketCap', 'revenue', 'employees', 'connections'] as SizeMetric[]).map(metric => (
                <button
                  key={metric}
                  onClick={() => { setSizeMetric(metric); setShowSizeDropdown(false); }}
                  className={clsx(
                    "w-full px-4 py-2 text-left hover:bg-gray-800 transition-colors",
                    sizeMetric === metric ? "bg-blue-600 text-white" : "text-gray-300"
                  )}
                >
                  {metric === 'marketCap' ? 'Market Cap' : metric === 'revenue' ? 'Revenue' : metric === 'employees' ? 'Employees' : 'Connections'}
                </button>
              ))}
            </div>
          )}
        </div>
        
        {/* Camera Controls */}
        <div className="flex gap-2">
          <button
            onClick={() => fgRef.current?.cameraPosition({ x: 0, y: 0, z: fgRef.current.cameraPosition().z * 0.8 })}
            className="p-2 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg text-gray-300 hover:bg-gray-800"
            title="Zoom In"
          >
            <ZoomIn className="w-4 h-4" />
          </button>
          <button
            onClick={() => fgRef.current?.cameraPosition({ x: 0, y: 0, z: fgRef.current.cameraPosition().z * 1.2 })}
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
        </div>
      </div>

      {/* Filters Panel */}
      {showFilters && (
        <div className="absolute top-4 left-72 w-64 bg-gray-900/95 backdrop-blur border border-gray-700 rounded-lg p-4 z-10">
          <h3 className="text-white font-semibold mb-3">Entity Types</h3>
          <div className="space-y-2 mb-4">
            {(['company', 'person', 'fund', 'government', 'organization'] as const).map(type => (
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
                  className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500"
                />
                <span className="flex items-center gap-2 text-gray-300">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: NODE_COLORS[type] }} />
                  {type.charAt(0).toUpperCase() + type.slice(1)}
                </span>
              </label>
            ))}
          </div>
          
          <h3 className="text-white font-semibold mb-3">Categories</h3>
          <div className="space-y-2 max-h-48 overflow-y-auto">
            {allCategories.map(category => (
              <label key={category} className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  checked={selectedCategories.has(category)}
                  onChange={(e) => {
                    const newCats = new Set(selectedCategories);
                    if (e.target.checked) newCats.add(category);
                    else newCats.delete(category);
                    setSelectedCategories(newCats);
                  }}
                  className="w-4 h-4 rounded border-gray-600 bg-gray-800 text-blue-500 focus:ring-blue-500"
                />
                <span className="flex items-center gap-2 text-gray-300 text-sm">
                  <span className="w-3 h-3 rounded-full" style={{ backgroundColor: CATEGORY_COLORS[category] || '#6B7280' }} />
                  {category.replace(/_/g, ' ')}
                </span>
              </label>
            ))}
          </div>
        </div>
      )}

      {/* Legend */}
      <div className="absolute bottom-4 left-4 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg p-4 z-10">
        <h3 className="text-white font-semibold mb-2 text-sm">Relationship Types</h3>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
          {Object.entries(LINK_COLORS).map(([type, color]) => (
            <div key={type} className="flex items-center gap-2">
              <div className="w-6 h-0.5" style={{ backgroundColor: color }} />
              <span className="text-gray-400 capitalize">{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Stats */}
      <div className="absolute bottom-4 right-4 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg px-4 py-2 z-10">
        <div className="text-gray-400 text-sm">
          <span className="text-white font-semibold">{filteredData.nodes.length}</span> entities · 
          <span className="text-white font-semibold ml-1">{filteredData.links.length}</span> relationships
        </div>
      </div>

      {/* Selected Node Panel */}
      {selectedNode && (
        <div className="absolute top-4 right-4 w-80 max-h-[calc(100vh-2rem)] overflow-y-auto bg-gray-900/95 backdrop-blur border border-gray-700 rounded-lg z-10">
          <div className="sticky top-0 bg-gray-900 border-b border-gray-700 p-4 flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2">
                <span 
                  className="w-3 h-3 rounded-full" 
                  style={{ backgroundColor: selectedNode.category ? (CATEGORY_COLORS[selectedNode.category] || NODE_COLORS[selectedNode.type]) : NODE_COLORS[selectedNode.type] }} 
                />
                <h2 className="text-white font-semibold">{selectedNode.name}</h2>
              </div>
              <p className="text-gray-400 text-sm mt-1">{selectedNode.type.charAt(0).toUpperCase() + selectedNode.type.slice(1)} · {selectedNode.category?.replace(/_/g, ' ')}</p>
            </div>
            <button onClick={clearSelection} className="p-1 text-gray-400 hover:text-white">
              <X className="w-5 h-5" />
            </button>
          </div>
          
          <div className="p-4 space-y-4">
            {selectedNode.description && (
              <p className="text-gray-300 text-sm">{selectedNode.description}</p>
            )}
            
            {/* Financial Info */}
            {(selectedNode.marketCap || selectedNode.revenue) && (
              <div className="grid grid-cols-2 gap-3">
                {selectedNode.marketCap && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center gap-1 text-gray-400 text-xs mb-1">
                      <DollarSign className="w-3 h-3" />
                      Market Cap
                    </div>
                    <div className="text-white font-semibold">{formatCurrency(selectedNode.marketCap)}</div>
                  </div>
                )}
                {selectedNode.revenue && (
                  <div className="bg-gray-800/50 rounded-lg p-3">
                    <div className="flex items-center gap-1 text-gray-400 text-xs mb-1">
                      <Briefcase className="w-3 h-3" />
                      Revenue
                    </div>
                    <div className="text-white font-semibold">{formatCurrency(selectedNode.revenue)}</div>
                  </div>
                )}
              </div>
            )}
            
            {/* Company Details */}
            <div className="space-y-2 text-sm">
              {selectedNode.employees && (
                <div className="flex items-center gap-2 text-gray-300">
                  <Users className="w-4 h-4 text-gray-500" />
                  <span>{selectedNode.employees.toLocaleString()} employees</span>
                </div>
              )}
              {selectedNode.headquarters && (
                <div className="flex items-center gap-2 text-gray-300">
                  <Building2 className="w-4 h-4 text-gray-500" />
                  <span>{selectedNode.headquarters}</span>
                </div>
              )}
              {selectedNode.founded && (
                <div className="flex items-center gap-2 text-gray-300">
                  <Info className="w-4 h-4 text-gray-500" />
                  <span>Founded {selectedNode.founded}</span>
                </div>
              )}
              {selectedNode.website && (
                <div className="flex items-center gap-2 text-gray-300">
                  <Globe className="w-4 h-4 text-gray-500" />
                  <a href={`https://${selectedNode.website}`} target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">
                    {selectedNode.website}
                  </a>
                </div>
              )}
            </div>
            
            {/* Identifiers */}
            {(selectedNode.ticker || selectedNode.cik || selectedNode.lei) && (
              <div className="space-y-2">
                <h3 className="text-white font-semibold text-sm flex items-center gap-2">
                  <Hash className="w-4 h-4" />
                  Identifiers
                </h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  {selectedNode.ticker && (
                    <div className="bg-gray-800/50 rounded px-2 py-1">
                      <span className="text-gray-500">Ticker:</span>
                      <span className="text-white ml-1">{selectedNode.ticker}</span>
                    </div>
                  )}
                  {selectedNode.cik && (
                    <div className="bg-gray-800/50 rounded px-2 py-1">
                      <span className="text-gray-500">CIK:</span>
                      <span className="text-white ml-1">{selectedNode.cik}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
            
            {/* Relationships */}
            <div className="space-y-2">
              <h3 className="text-white font-semibold text-sm flex items-center gap-2">
                <Link2 className="w-4 h-4" />
                Relationships ({getNodeRelationships(selectedNode).length})
              </h3>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {getNodeRelationships(selectedNode).map((rel, i) => (
                  <div 
                    key={i} 
                    className="flex items-center gap-2 text-sm bg-gray-800/30 rounded px-2 py-1 cursor-pointer hover:bg-gray-800/50"
                    onClick={() => rel.otherNode && handleNodeClick(rel.otherNode)}
                  >
                    <span 
                      className="w-2 h-2 rounded-full flex-shrink-0" 
                      style={{ backgroundColor: LINK_COLORS[rel.type] }}
                    />
                    <span className="text-gray-400 capitalize flex-shrink-0">{rel.type}</span>
                    <span className="text-gray-500">{rel.direction === 'outgoing' ? '→' : '←'}</span>
                    <span className="text-gray-300 truncate">{rel.otherNode?.name || 'Unknown'}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Title */}
      <div className="absolute top-4 left-1/2 -translate-x-1/2 bg-gray-900/90 backdrop-blur border border-gray-700 rounded-lg px-6 py-3 z-10">
        <h1 className="text-white font-bold text-xl">Entity Relationship Graph</h1>
        <p className="text-gray-400 text-sm text-center">Semiconductor Ecosystem</p>
      </div>
    </div>
  );
}
