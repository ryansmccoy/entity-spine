import { useState, useEffect } from 'react';
import { clsx } from 'clsx';
import {
  Search,
  FileText,
  TrendingUp,
  TrendingDown,
  Clock,
  Building2,
  BarChart3,
  Bookmark,
  Share2,
  ChevronRight,
  ExternalLink,
  Network,
} from 'lucide-react';
import { EntityMiniGraph } from '../components/graph';

// Mock research data
interface ResearchNote {
  id: string;
  title: string;
  analyst: string;
  firm: string;
  date: string;
  rating: 'Buy' | 'Hold' | 'Sell' | 'Outperform' | 'Underperform';
  targetPrice: number;
  currentPrice: number;
  symbol: string;
  sector: string;
  summary: string;
  isNew: boolean;
}

interface CompanyData {
  symbol: string;
  name: string;
  price: number;
  change: number;
  changePct: number;
  marketCap: string;
  pe: number;
  eps: number;
  avgRating: string;
  avgTarget: number;
  analystCount: number;
}

const mockNotes: ResearchNote[] = [
  {
    id: '1',
    title: 'Apple: Services Revenue Continues to Impress',
    analyst: 'John Smith',
    firm: 'Morgan Stanley',
    date: '2 hours ago',
    rating: 'Outperform',
    targetPrice: 245,
    currentPrice: 227.50,
    symbol: 'AAPL',
    sector: 'Technology',
    summary: 'Services segment grew 18% YoY, now representing 24% of total revenue. iPhone replacement cycle remains strong heading into 2025.',
    isNew: true,
  },
  {
    id: '2',
    title: 'NVIDIA: Data Center Dominance Unmatched',
    analyst: 'Sarah Chen',
    firm: 'Goldman Sachs',
    date: '4 hours ago',
    rating: 'Buy',
    targetPrice: 180,
    currentPrice: 145.20,
    symbol: 'NVDA',
    sector: 'Technology',
    summary: 'Blackwell architecture poised to capture 85%+ of AI training market. Raising estimates on stronger-than-expected enterprise adoption.',
    isNew: true,
  },
  {
    id: '3',
    title: 'Microsoft: Azure Growth Decelerating',
    analyst: 'Michael Brown',
    firm: 'JP Morgan',
    date: '6 hours ago',
    rating: 'Hold',
    targetPrice: 420,
    currentPrice: 425.80,
    symbol: 'MSFT',
    sector: 'Technology',
    summary: 'Azure growth slowed to 28% vs 31% in prior quarter. Competition from AWS and Google Cloud intensifying. Maintaining neutral stance.',
    isNew: false,
  },
  {
    id: '4',
    title: 'Tesla: Margin Pressures Persist',
    analyst: 'Emily Davis',
    firm: 'Barclays',
    date: '1 day ago',
    rating: 'Underperform',
    targetPrice: 200,
    currentPrice: 248.90,
    symbol: 'TSLA',
    sector: 'Consumer Discretionary',
    summary: 'Price cuts continue to erode margins. Cybertruck ramp slower than expected. Autonomous timeline remains uncertain.',
    isNew: false,
  },
  {
    id: '5',
    title: 'Amazon: AWS Reacceleration in Sight',
    analyst: 'David Wilson',
    firm: 'Citi',
    date: '1 day ago',
    rating: 'Buy',
    targetPrice: 225,
    currentPrice: 195.60,
    symbol: 'AMZN',
    sector: 'Consumer Discretionary',
    summary: 'Optimization headwinds subsiding. GenAI workloads driving new growth vector. E-commerce margins improving.',
    isNew: false,
  },
];

const mockCompanies: CompanyData[] = [
  { symbol: 'AAPL', name: 'Apple Inc.', price: 227.50, change: 2.35, changePct: 1.04, marketCap: '3.51T', pe: 29.8, eps: 7.63, avgRating: 'Buy', avgTarget: 238, analystCount: 42 },
  { symbol: 'NVDA', name: 'NVIDIA Corp', price: 145.20, change: 5.80, changePct: 4.16, marketCap: '3.58T', pe: 65.2, eps: 2.23, avgRating: 'Strong Buy', avgTarget: 175, analystCount: 48 },
  { symbol: 'MSFT', name: 'Microsoft Corp', price: 425.80, change: -1.20, changePct: -0.28, marketCap: '3.16T', pe: 35.4, eps: 12.02, avgRating: 'Buy', avgTarget: 450, analystCount: 45 },
  { symbol: 'GOOGL', name: 'Alphabet Inc', price: 178.30, change: 1.45, changePct: 0.82, marketCap: '2.19T', pe: 25.1, eps: 7.10, avgRating: 'Buy', avgTarget: 195, analystCount: 52 },
  { symbol: 'META', name: 'Meta Platforms', price: 585.40, change: 8.20, changePct: 1.42, marketCap: '1.48T', pe: 28.6, eps: 20.47, avgRating: 'Buy', avgTarget: 620, analystCount: 55 },
];

function RatingBadge({ rating }: { rating: ResearchNote['rating'] }) {
  const colors = {
    'Buy': 'bg-green-500/20 text-green-400',
    'Outperform': 'bg-green-500/20 text-green-400',
    'Hold': 'bg-yellow-500/20 text-yellow-400',
    'Underperform': 'bg-orange-500/20 text-orange-400',
    'Sell': 'bg-red-500/20 text-red-400',
  };
  
  return (
    <span className={clsx('px-2 py-0.5 rounded text-[10px] font-semibold', colors[rating])}>
      {rating}
    </span>
  );
}

export default function ResearchPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNote, setSelectedNote] = useState<ResearchNote | null>(null);
  const [flashingSymbols, setFlashingSymbols] = useState<Set<string>>(new Set());
  const [companies, setCompanies] = useState(mockCompanies);

  // Simulate real-time price updates
  useEffect(() => {
    const interval = setInterval(() => {
      setCompanies(prev => prev.map(company => {
        if (Math.random() > 0.6) {
          const change = (Math.random() - 0.5) * 2;
          const newPrice = company.price + change;
          setFlashingSymbols(s => new Set([...s, company.symbol]));
          setTimeout(() => {
            setFlashingSymbols(s => {
              const newSet = new Set(s);
              newSet.delete(company.symbol);
              return newSet;
            });
          }, 300);
          return {
            ...company,
            price: newPrice,
            change: company.change + change,
            changePct: ((company.change + change) / newPrice) * 100,
          };
        }
        return company;
      }));
    }, 500);

    return () => clearInterval(interval);
  }, []);

  const filteredNotes = mockNotes.filter(note =>
    note.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
    note.symbol.toLowerCase().includes(searchQuery.toLowerCase()) ||
    note.firm.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="h-[calc(100vh-130px)] flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600">
            <FileText className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Research Hub</h1>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Analyst notes, ratings & company intelligence
            </p>
          </div>
        </div>

        {/* Search */}
        <div className="relative w-96">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search notes, symbols, firms..."
            className="w-full pl-10 pr-4 py-2 bg-[#252536] border border-[#3d3d53] rounded-lg text-sm text-white placeholder:text-gray-500 focus:outline-none focus:border-purple-500"
          />
        </div>

        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-400">{filteredNotes.length} notes</span>
          <span className="animate-pulse h-2 w-2 rounded-full bg-green-500" />
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 grid grid-cols-12 gap-4">
        {/* Left: Company Watchlist */}
        <div className="col-span-3 bg-[#1e1e2d] rounded-lg overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
            <h3 className="text-sm font-semibold text-white">Watchlist</h3>
            <span className="text-xs text-green-400">● Live</span>
          </div>
          <div className="flex-1 overflow-auto">
            {companies.map(company => (
              <div 
                key={company.symbol}
                className={clsx(
                  'px-4 py-3 border-b border-[#2d2d43] cursor-pointer transition-colors',
                  flashingSymbols.has(company.symbol) && (company.change >= 0 ? 'bg-green-500/20' : 'bg-red-500/20'),
                  !flashingSymbols.has(company.symbol) && 'hover:bg-[#252536]'
                )}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-white">{company.symbol}</span>
                  <span className={clsx(
                    'font-mono font-semibold',
                    flashingSymbols.has(company.symbol) && company.change >= 0 && 'text-green-400',
                    flashingSymbols.has(company.symbol) && company.change < 0 && 'text-red-400',
                    !flashingSymbols.has(company.symbol) && 'text-white'
                  )}>
                    ${company.price.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-xs">
                  <span className="text-gray-400 truncate mr-2">{company.name}</span>
                  <span className={clsx(
                    'font-mono',
                    company.change >= 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {company.change >= 0 ? '+' : ''}{company.change.toFixed(2)} ({company.changePct.toFixed(2)}%)
                  </span>
                </div>
                <div className="flex items-center gap-3 mt-2 text-[10px]">
                  <span className="text-gray-500">P/E: <span className="text-gray-300">{company.pe}</span></span>
                  <span className="text-gray-500">MCap: <span className="text-gray-300">{company.marketCap}</span></span>
                  <span className={clsx(
                    'px-1.5 py-0.5 rounded',
                    company.avgRating.includes('Buy') ? 'bg-green-500/20 text-green-400' : 'bg-yellow-500/20 text-yellow-400'
                  )}>
                    {company.avgRating}
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Center: Research Notes Feed */}
        <div className="col-span-5 bg-[#1e1e2d] rounded-lg overflow-hidden flex flex-col">
          <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
            <h3 className="text-sm font-semibold text-white">Latest Research</h3>
            <div className="flex items-center gap-2">
              <span className="text-[10px] px-2 py-0.5 bg-blue-500/20 text-blue-400 rounded">
                {filteredNotes.filter(n => n.isNew).length} New
              </span>
            </div>
          </div>
          <div className="flex-1 overflow-auto">
            {filteredNotes.map(note => (
              <div 
                key={note.id}
                onClick={() => setSelectedNote(note)}
                className={clsx(
                  'px-4 py-3 border-b border-[#2d2d43] cursor-pointer transition-colors',
                  selectedNote?.id === note.id ? 'bg-purple-500/10 border-l-2 border-l-purple-500' : 'hover:bg-[#252536]',
                  note.isNew && 'bg-blue-500/5'
                )}
              >
                <div className="flex items-start gap-3">
                  <div className="flex-shrink-0 mt-1">
                    <div className="h-8 w-8 rounded bg-[#252536] flex items-center justify-center">
                      <span className="text-xs font-bold text-white">{note.symbol}</span>
                    </div>
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      {note.isNew && (
                        <span className="h-2 w-2 rounded-full bg-blue-500 animate-pulse" />
                      )}
                      <h4 className="text-sm font-semibold text-white truncate">{note.title}</h4>
                    </div>
                    <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
                      <span>{note.firm}</span>
                      <span>•</span>
                      <span>{note.analyst}</span>
                      <span>•</span>
                      <Clock className="h-3 w-3" />
                      <span>{note.date}</span>
                    </div>
                    <div className="flex items-center gap-3">
                      <RatingBadge rating={note.rating} />
                      <span className="text-xs text-gray-400">
                        Target: <span className="text-white font-mono">${note.targetPrice}</span>
                      </span>
                      <span className={clsx(
                        'text-xs',
                        note.targetPrice > note.currentPrice ? 'text-green-400' : 'text-red-400'
                      )}>
                        ({note.targetPrice > note.currentPrice ? '+' : ''}{((note.targetPrice / note.currentPrice - 1) * 100).toFixed(1)}%)
                      </span>
                    </div>
                  </div>
                  <ChevronRight className="h-4 w-4 text-gray-500 flex-shrink-0" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Note Detail */}
        <div className="col-span-4 bg-[#1e1e2d] rounded-lg overflow-hidden flex flex-col">
          {selectedNote ? (
            <>
              <div className="px-4 py-3 bg-[#252536] border-b border-[#2d2d43]">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-lg font-bold text-white">{selectedNote.symbol}</span>
                  <div className="flex items-center gap-2">
                    <button className="p-1.5 hover:bg-[#2d2d43] rounded">
                      <Bookmark className="h-4 w-4 text-gray-400" />
                    </button>
                    <button className="p-1.5 hover:bg-[#2d2d43] rounded">
                      <Share2 className="h-4 w-4 text-gray-400" />
                    </button>
                    <button className="p-1.5 hover:bg-[#2d2d43] rounded">
                      <ExternalLink className="h-4 w-4 text-gray-400" />
                    </button>
                  </div>
                </div>
                <h3 className="text-sm font-semibold text-white mb-2">{selectedNote.title}</h3>
                <div className="flex items-center gap-2 text-xs text-gray-400">
                  <Building2 className="h-3 w-3" />
                  <span>{selectedNote.firm}</span>
                  <span>•</span>
                  <span>{selectedNote.analyst}</span>
                </div>
              </div>

              <div className="flex-1 overflow-auto p-4">
                {/* Rating & Price Target */}
                <div className="grid grid-cols-2 gap-4 mb-4">
                  <div className="bg-[#252536] rounded-lg p-3">
                    <div className="text-[10px] text-gray-400 mb-1">Rating</div>
                    <RatingBadge rating={selectedNote.rating} />
                  </div>
                  <div className="bg-[#252536] rounded-lg p-3">
                    <div className="text-[10px] text-gray-400 mb-1">Price Target</div>
                    <div className="flex items-center gap-2">
                      <span className="text-lg font-bold text-white">${selectedNote.targetPrice}</span>
                      <span className={clsx(
                        'text-xs',
                        selectedNote.targetPrice > selectedNote.currentPrice ? 'text-green-400' : 'text-red-400'
                      )}>
                        {selectedNote.targetPrice > selectedNote.currentPrice ? (
                          <TrendingUp className="h-4 w-4" />
                        ) : (
                          <TrendingDown className="h-4 w-4" />
                        )}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Current Price */}
                <div className="bg-[#252536] rounded-lg p-3 mb-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="text-[10px] text-gray-400 mb-1">Current Price</div>
                      <div className="text-xl font-bold text-white">${selectedNote.currentPrice.toFixed(2)}</div>
                    </div>
                    <div className="text-right">
                      <div className="text-[10px] text-gray-400 mb-1">Upside/Downside</div>
                      <div className={clsx(
                        'text-xl font-bold',
                        selectedNote.targetPrice > selectedNote.currentPrice ? 'text-green-400' : 'text-red-400'
                      )}>
                        {selectedNote.targetPrice > selectedNote.currentPrice ? '+' : ''}
                        {((selectedNote.targetPrice / selectedNote.currentPrice - 1) * 100).toFixed(1)}%
                      </div>
                    </div>
                  </div>
                </div>

                {/* Summary */}
                <div className="mb-4">
                  <div className="text-[10px] text-gray-400 mb-2 uppercase tracking-wider">Key Takeaways</div>
                  <p className="text-sm text-gray-300 leading-relaxed">{selectedNote.summary}</p>
                </div>

                {/* Sector */}
                <div className="flex items-center gap-2 text-xs">
                  <BarChart3 className="h-3 w-3 text-gray-500" />
                  <span className="text-gray-400">Sector:</span>
                  <span className="text-cyan-400">{selectedNote.sector}</span>
                </div>
              </div>

              {/* Actions */}
              <div className="px-4 py-3 bg-[#252536] border-t border-[#2d2d43] flex items-center gap-2">
                <button className="flex-1 px-4 py-2 bg-green-500 hover:bg-green-600 text-white text-xs font-semibold rounded transition-colors">
                  Add to Watchlist
                </button>
                <button className="flex-1 px-4 py-2 bg-[#2d2d43] hover:bg-[#3d3d53] text-white text-xs font-semibold rounded transition-colors">
                  Create Alert
                </button>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">
              <div className="text-center">
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-30" />
                <p className="text-sm">Select a research note to view details</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Entity Relationship Graph */}
      <div className="bg-[#1e1e2d] rounded-lg overflow-hidden">
        <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
          <div className="flex items-center gap-2">
            <Network className="h-4 w-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-white">Entity Relationships</h3>
          </div>
          <a
            href="/graph"
            className="flex items-center gap-1 text-[10px] font-medium text-purple-400 hover:text-purple-300"
          >
            Full Graph
            <ExternalLink className="h-3 w-3" />
          </a>
        </div>
        <EntityMiniGraph height={280} showDetailPanel={false} />
      </div>
    </div>
  );
}
