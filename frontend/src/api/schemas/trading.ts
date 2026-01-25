/**
 * Trading API Schemas & Models
 * 
 * These TypeScript interfaces define the data contracts between
 * the frontend and a hypothetical Python FastAPI backend.
 * 
 * Backend Implementation Notes:
 * - Use Pydantic models mirroring these interfaces
 * - SQLAlchemy models for persistence
 * - Redis for real-time order state caching
 * - WebSocket for live updates (prices, executions, positions)
 * 
 * Example Python Pydantic Model:
 * ```python
 * from pydantic import BaseModel
 * from datetime import datetime
 * from decimal import Decimal
 * from enum import Enum
 * 
 * class OrderSide(str, Enum):
 *     BUY = "BUY"
 *     SELL = "SELL"
 *     SHORT = "SHORT"
 *     COVER = "COVER"
 * 
 * class Order(BaseModel):
 *     order_id: str
 *     symbol: str
 *     side: OrderSide
 *     quantity: int
 *     price: Decimal | None
 *     order_type: str
 *     status: str
 *     created_at: datetime
 *     # ... etc
 * ```
 */

// ============================================================================
// ENUMS & CONSTANTS
// ============================================================================

export type OrderSide = 'BUY' | 'SELL' | 'SHORT' | 'COVER';
export type OrderType = 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_LIMIT' | 'MOC' | 'LOC' | 'VWAP' | 'TWAP' | 'IS' | 'POV';
export type OrderStatus = 'NEW' | 'PENDING' | 'PARTIAL' | 'FILLED' | 'CANCELLED' | 'REJECTED' | 'EXPIRED';
export type TimeInForce = 'DAY' | 'GTC' | 'IOC' | 'FOK' | 'GTD' | 'OPG' | 'CLO';
export type AssetClass = 'EQUITY' | 'FIXED_INCOME' | 'DERIVATIVE' | 'FX' | 'COMMODITY' | 'CRYPTO';
export type PositionSide = 'LONG' | 'SHORT' | 'FLAT';

// ============================================================================
// ORDER MANAGEMENT SYSTEM (OMS) MODELS
// ============================================================================

/**
 * Order - Core order entity in OMS
 * 
 * API Endpoints:
 * - POST   /api/v1/orders           - Create new order
 * - GET    /api/v1/orders           - List orders (with filters)
 * - GET    /api/v1/orders/{id}      - Get order by ID
 * - PATCH  /api/v1/orders/{id}      - Modify order
 * - DELETE /api/v1/orders/{id}      - Cancel order
 * - WS     /ws/orders               - Real-time order updates
 */
export interface Order {
  orderId: string;                    // UUID - primary key
  clientOrderId: string;              // Client-assigned ID for tracking
  parentOrderId?: string;             // For child orders (algo slices)
  
  // Instrument
  symbol: string;                     // Bloomberg ticker or ISIN
  sedol?: string;                     // SEDOL identifier
  cusip?: string;                     // CUSIP identifier
  isin?: string;                      // ISIN identifier
  exchange: string;                   // Primary exchange (NYSE, NASDAQ, etc.)
  assetClass: AssetClass;
  
  // Order Details
  side: OrderSide;
  orderType: OrderType;
  quantity: number;                   // Total order quantity
  filledQuantity: number;             // Quantity filled so far
  remainingQuantity: number;          // Quantity remaining
  displayQuantity?: number;           // Iceberg display size
  
  // Pricing
  limitPrice?: number;                // Limit price (for LIMIT orders)
  stopPrice?: number;                 // Stop trigger price
  avgFillPrice?: number;              // Average fill price
  
  // Timing
  timeInForce: TimeInForce;
  gtdDate?: string;                   // Good-til-date (ISO 8601)
  startTime?: string;                 // Algo start time
  endTime?: string;                   // Algo end time
  
  // Status & Tracking
  status: OrderStatus;
  statusMessage?: string;             // Human-readable status
  createdAt: string;                  // ISO 8601 timestamp
  updatedAt: string;
  submittedAt?: string;
  acknowledgedAt?: string;
  
  // Routing
  broker: string;                     // Executing broker
  destination: string;                // Execution venue
  strategy?: string;                  // Algo strategy name
  
  // Algo Parameters (for algo orders)
  algoParams?: AlgoParameters;
  
  // Compliance & Risk
  portfolioId: string;                // Portfolio/account
  traderId: string;                   // Trader ID
  complianceStatus?: 'PENDING' | 'APPROVED' | 'REJECTED' | 'OVERRIDE';
  riskCheckStatus?: 'PASS' | 'FAIL' | 'WARN';
  
  // Allocation (for block trades)
  allocations?: OrderAllocation[];
}

export interface AlgoParameters {
  participationRate?: number;         // POV target rate (0-1)
  urgency?: 'LOW' | 'MEDIUM' | 'HIGH' | 'URGENT';
  priceLimit?: number;                // Max/min price for algos
  darkPoolOnly?: boolean;
  minFillSize?: number;
  maxSpread?: number;                 // Max bid-ask spread to trade
  benchmarkType?: 'ARRIVAL' | 'VWAP' | 'TWAP' | 'CLOSE' | 'OPEN';
  allowedVenues?: string[];           // Whitelist of venues
  excludedVenues?: string[];          // Blacklist of venues
}

export interface OrderAllocation {
  accountId: string;
  accountName: string;
  quantity: number;
  percentage: number;
}

// ============================================================================
// EXECUTION MODELS
// ============================================================================

/**
 * Execution - Individual fill/trade
 * 
 * API Endpoints:
 * - GET    /api/v1/executions              - List executions
 * - GET    /api/v1/executions/{id}         - Get execution by ID
 * - GET    /api/v1/orders/{id}/executions  - Executions for order
 * - WS     /ws/executions                  - Real-time execution feed
 */
export interface Execution {
  executionId: string;                // UUID
  orderId: string;                    // Parent order ID
  
  // Trade Details
  symbol: string;
  side: OrderSide;
  quantity: number;
  price: number;
  notionalValue: number;              // quantity * price
  
  // Venue & Timing
  executionVenue: string;             // Where executed (NYSE, BATS, etc.)
  executionTime: string;              // ISO 8601 microsecond precision
  tradeDate: string;                  // T date
  settlementDate: string;             // T+1/T+2 date
  
  // Counterparty
  contrabroker?: string;              // Counterparty broker
  liquidityFlag: 'ADD' | 'REMOVE' | 'AUCTION' | 'DARK';
  
  // Fees & Costs
  commission: number;
  fees: number;                       // Exchange fees, SEC fees, etc.
  netAmount: number;                  // Net cash impact
  
  // Compliance
  reportingStatus: 'PENDING' | 'REPORTED' | 'LATE';
  regulatoryFlags?: string[];         // e.g., ['SHORT_SALE', 'EXEMPT']
}

// ============================================================================
// POSITION & PORTFOLIO MODELS
// ============================================================================

/**
 * Position - Current holding in a security
 * 
 * API Endpoints:
 * - GET    /api/v1/positions                    - List all positions
 * - GET    /api/v1/positions/{symbol}           - Get position by symbol
 * - GET    /api/v1/portfolios/{id}/positions    - Positions in portfolio
 * - WS     /ws/positions                        - Real-time position updates
 */
export interface Position {
  positionId: string;
  portfolioId: string;
  
  // Security
  symbol: string;
  securityName: string;
  assetClass: AssetClass;
  sector: string;
  industry: string;
  country: string;
  currency: string;
  
  // Quantities
  quantity: number;                   // Current position (negative = short)
  side: PositionSide;
  tradingQuantity: number;            // Quantity available for trading
  settlingQuantity: number;           // Quantity in settlement
  
  // Values
  marketValue: number;                // Current market value
  costBasis: number;                  // Total cost basis
  avgCost: number;                    // Average cost per share
  currentPrice: number;               // Last price
  previousClose: number;              // Prior day close
  
  // P&L
  unrealizedPnL: number;              // Unrealized gain/loss
  unrealizedPnLPct: number;           // Unrealized return %
  realizedPnL: number;                // YTD realized P&L
  dayPnL: number;                     // Today's P&L
  dayPnLPct: number;                  // Today's return %
  
  // Risk Metrics
  beta: number;                       // Security beta
  volatility: number;                 // 30-day realized vol
  var95: number;                      // 95% VaR
  
  // Portfolio Weight
  portfolioWeight: number;            // % of portfolio
  benchmarkWeight?: number;           // Weight in benchmark
  activeWeight?: number;              // Over/underweight vs benchmark
}

/**
 * Portfolio - Collection of positions with analytics
 * 
 * API Endpoints:
 * - GET    /api/v1/portfolios                - List portfolios
 * - GET    /api/v1/portfolios/{id}           - Get portfolio details
 * - GET    /api/v1/portfolios/{id}/summary   - Portfolio summary stats
 * - GET    /api/v1/portfolios/{id}/analytics - Full analytics
 */
export interface Portfolio {
  portfolioId: string;
  portfolioName: string;
  portfolioType: 'TRADING' | 'MODEL' | 'BENCHMARK' | 'COMPOSITE';
  currency: string;
  inceptionDate: string;
  
  // Values
  nav: number;                        // Net asset value
  cash: number;                       // Cash balance
  equity: number;                     // Long + short equity
  longValue: number;                  // Long market value
  shortValue: number;                 // Short market value (abs)
  grossExposure: number;              // Long + |Short|
  netExposure: number;                // Long - |Short|
  leverage: number;                   // Gross / NAV
  
  // Performance
  dayReturn: number;
  mtdReturn: number;
  qtdReturn: number;
  ytdReturn: number;
  oneYearReturn: number;
  threeYearReturn: number;
  fiveYearReturn: number;
  inceptionReturn: number;
  
  // Risk
  sharpeRatio: number;
  sortinoRatio: number;
  informationRatio: number;
  maxDrawdown: number;
  currentDrawdown: number;
  trackingError: number;
  beta: number;
  alpha: number;
  
  // Concentration
  topHoldings: Position[];
  sectorExposures: SectorExposure[];
  countryExposures: CountryExposure[];
  
  // Metadata
  benchmark?: string;
  managerId: string;
  lastUpdated: string;
}

export interface SectorExposure {
  sector: string;
  longWeight: number;
  shortWeight: number;
  netWeight: number;
  benchmarkWeight: number;
  activeWeight: number;
  contribution: number;              // Contribution to return
}

export interface CountryExposure {
  country: string;
  countryCode: string;
  longWeight: number;
  shortWeight: number;
  netWeight: number;
  benchmarkWeight: number;
  activeWeight: number;
}

// ============================================================================
// RISK MANAGEMENT MODELS (Barra-style)
// ============================================================================

/**
 * RiskFactorExposure - Factor exposure for risk analysis
 * 
 * API Endpoints:
 * - GET    /api/v1/risk/factors                      - List risk factors
 * - GET    /api/v1/portfolios/{id}/risk/exposures    - Portfolio factor exposures
 * - GET    /api/v1/portfolios/{id}/risk/decomposition - Risk decomposition
 */
export interface RiskFactorExposure {
  factorCategory: 'STYLE' | 'INDUSTRY' | 'COUNTRY' | 'CURRENCY' | 'MACRO';
  factorName: string;
  factorId: string;
  
  portfolioExposure: number;          // Portfolio factor loading
  benchmarkExposure: number;          // Benchmark factor loading
  activeExposure: number;             // Active bet
  
  factorReturn: number;               // Factor return (period)
  contribution: number;               // Contribution to portfolio return
  
  // Risk decomposition
  factorVolatility: number;
  marginalContributionToRisk: number; // MCTR
  percentOfTotalRisk: number;
}

/**
 * RiskDecomposition - Full risk analysis
 */
export interface RiskDecomposition {
  portfolioId: string;
  asOfDate: string;
  
  // Total Risk
  totalRisk: number;                  // Annualized vol
  totalVariance: number;
  
  // Risk Components
  systematicRisk: number;             // Factor risk
  specificRisk: number;               // Idiosyncratic risk
  
  // Factor Risk Breakdown
  styleRisk: number;
  industryRisk: number;
  countryRisk: number;
  currencyRisk: number;
  
  // Marginal Risk
  factorExposures: RiskFactorExposure[];
  
  // VaR Analysis
  var95OneDay: number;
  var99OneDay: number;
  var95TenDay: number;
  expectedShortfall95: number;        // CVaR
  
  // Stress Tests
  stressScenarios: StressScenario[];
}

export interface StressScenario {
  scenarioName: string;
  scenarioType: 'HISTORICAL' | 'HYPOTHETICAL' | 'FACTOR_SHOCK';
  description: string;
  portfolioImpact: number;            // % impact
  dollarImpact: number;
  confidenceLevel?: number;
}

// ============================================================================
// PERFORMANCE ATTRIBUTION MODELS
// ============================================================================

/**
 * PerformanceAttribution - Brinson-style attribution
 * 
 * API Endpoints:
 * - GET    /api/v1/portfolios/{id}/attribution             - Attribution summary
 * - GET    /api/v1/portfolios/{id}/attribution/brinson     - Brinson attribution
 * - GET    /api/v1/portfolios/{id}/attribution/factor      - Factor attribution
 * - GET    /api/v1/portfolios/{id}/attribution/security    - Security attribution
 */
export interface PerformanceAttribution {
  portfolioId: string;
  benchmarkId: string;
  periodStart: string;
  periodEnd: string;
  
  // Summary
  portfolioReturn: number;
  benchmarkReturn: number;
  activeReturn: number;               // Excess return
  
  // Brinson Attribution
  allocationEffect: number;           // Sector allocation
  selectionEffect: number;            // Security selection
  interactionEffect: number;          // Allocation x Selection
  currencyEffect?: number;            // FX impact
  
  // Sector Attribution
  sectorAttribution: SectorAttribution[];
  
  // Factor Attribution
  factorAttribution: FactorAttribution[];
  
  // Top/Bottom Contributors
  topContributors: SecurityAttribution[];
  bottomContributors: SecurityAttribution[];
}

export interface SectorAttribution {
  sector: string;
  
  // Weights
  portfolioWeight: number;
  benchmarkWeight: number;
  activeWeight: number;
  
  // Returns
  portfolioReturn: number;
  benchmarkReturn: number;
  
  // Attribution Effects
  allocationEffect: number;
  selectionEffect: number;
  interactionEffect: number;
  totalEffect: number;
}

export interface FactorAttribution {
  factorName: string;
  factorCategory: string;
  
  exposure: number;                   // Active exposure
  factorReturn: number;
  contribution: number;               // Contribution to active return
}

export interface SecurityAttribution {
  symbol: string;
  securityName: string;
  sector: string;
  
  portfolioWeight: number;
  benchmarkWeight: number;
  activeWeight: number;
  
  portfolioReturn: number;
  contribution: number;               // Contribution to portfolio return
  activeContribution: number;         // Contribution to active return
}

// ============================================================================
// MARKET DATA MODELS
// ============================================================================

/**
 * Quote - Real-time market quote
 * 
 * API Endpoints:
 * - GET    /api/v1/quotes/{symbol}      - Get quote
 * - GET    /api/v1/quotes?symbols=...   - Batch quotes
 * - WS     /ws/quotes                   - Real-time quote stream
 */
export interface Quote {
  symbol: string;
  exchange: string;
  
  // NBBO
  bidPrice: number;
  bidSize: number;
  askPrice: number;
  askSize: number;
  spread: number;
  spreadBps: number;                  // Spread in basis points
  
  // Last Trade
  lastPrice: number;
  lastSize: number;
  lastTime: string;
  
  // Session Stats
  openPrice: number;
  highPrice: number;
  lowPrice: number;
  closePrice: number;                 // Previous close
  vwap: number;
  
  // Volume
  volume: number;
  dollarVolume: number;
  avgVolume20d: number;
  relativeVolume: number;             // Volume vs average
  
  // Change
  change: number;
  changePct: number;
  
  // Market State
  marketState: 'PRE' | 'OPEN' | 'HALT' | 'CLOSE' | 'POST';
  haltReason?: string;
  
  timestamp: string;
}

// ============================================================================
// API RESPONSE WRAPPERS
// ============================================================================

/**
 * Standard API response wrapper
 */
export interface ApiResponse<T> {
  success: boolean;
  data: T;
  error?: {
    code: string;
    message: string;
    details?: Record<string, unknown>;
  };
  meta?: {
    timestamp: string;
    requestId: string;
    pagination?: {
      page: number;
      pageSize: number;
      totalItems: number;
      totalPages: number;
    };
  };
}

/**
 * WebSocket message wrapper
 */
export interface WsMessage<T> {
  type: 'ORDER_UPDATE' | 'EXECUTION' | 'POSITION_UPDATE' | 'QUOTE' | 'ALERT' | 'HEARTBEAT';
  channel: string;
  data: T;
  sequence: number;
  timestamp: string;
}

// ============================================================================
// MOCK API CLIENT (for frontend development)
// ============================================================================

/**
 * API Client Interface
 * 
 * This interface defines what the frontend expects from the backend.
 * Implement this with actual HTTP calls in production.
 * 
 * Example Python FastAPI routes:
 * ```python
 * from fastapi import APIRouter, Depends, Query
 * from typing import List
 * 
 * router = APIRouter(prefix="/api/v1")
 * 
 * @router.get("/orders", response_model=ApiResponse[List[Order]])
 * async def list_orders(
 *     status: OrderStatus | None = None,
 *     portfolio_id: str | None = None,
 *     symbol: str | None = None,
 *     page: int = Query(1, ge=1),
 *     page_size: int = Query(50, ge=1, le=100),
 *     db: Session = Depends(get_db)
 * ):
 *     # Implementation
 *     pass
 * 
 * @router.post("/orders", response_model=ApiResponse[Order])
 * async def create_order(
 *     order: OrderCreate,
 *     db: Session = Depends(get_db),
 *     user: User = Depends(get_current_user)
 * ):
 *     # Validate order
 *     # Run compliance checks
 *     # Submit to execution venue
 *     pass
 * ```
 */
export interface TradingApiClient {
  // Orders
  getOrders(filters?: OrderFilters): Promise<ApiResponse<Order[]>>;
  getOrder(orderId: string): Promise<ApiResponse<Order>>;
  createOrder(order: CreateOrderRequest): Promise<ApiResponse<Order>>;
  modifyOrder(orderId: string, modifications: ModifyOrderRequest): Promise<ApiResponse<Order>>;
  cancelOrder(orderId: string, reason?: string): Promise<ApiResponse<void>>;
  
  // Executions
  getExecutions(filters?: ExecutionFilters): Promise<ApiResponse<Execution[]>>;
  getOrderExecutions(orderId: string): Promise<ApiResponse<Execution[]>>;
  
  // Positions
  getPositions(portfolioId?: string): Promise<ApiResponse<Position[]>>;
  getPosition(symbol: string, portfolioId?: string): Promise<ApiResponse<Position>>;
  
  // Portfolios
  getPortfolios(): Promise<ApiResponse<Portfolio[]>>;
  getPortfolio(portfolioId: string): Promise<ApiResponse<Portfolio>>;
  getPortfolioAnalytics(portfolioId: string): Promise<ApiResponse<PortfolioAnalytics>>;
  
  // Risk
  getRiskDecomposition(portfolioId: string): Promise<ApiResponse<RiskDecomposition>>;
  getFactorExposures(portfolioId: string): Promise<ApiResponse<RiskFactorExposure[]>>;
  
  // Attribution
  getAttribution(portfolioId: string, period: string): Promise<ApiResponse<PerformanceAttribution>>;
  
  // Market Data
  getQuote(symbol: string): Promise<ApiResponse<Quote>>;
  getQuotes(symbols: string[]): Promise<ApiResponse<Quote[]>>;
  
  // WebSocket
  subscribeOrders(callback: (message: WsMessage<Order>) => void): () => void;
  subscribeExecutions(callback: (message: WsMessage<Execution>) => void): () => void;
  subscribeQuotes(symbols: string[], callback: (message: WsMessage<Quote>) => void): () => void;
}

// Request/Filter types
export interface OrderFilters {
  status?: OrderStatus[];
  portfolioId?: string;
  symbol?: string;
  side?: OrderSide;
  fromDate?: string;
  toDate?: string;
  page?: number;
  pageSize?: number;
}

export interface ExecutionFilters {
  orderId?: string;
  symbol?: string;
  fromDate?: string;
  toDate?: string;
  page?: number;
  pageSize?: number;
}

export interface CreateOrderRequest {
  symbol: string;
  side: OrderSide;
  quantity: number;
  orderType: OrderType;
  limitPrice?: number;
  stopPrice?: number;
  timeInForce: TimeInForce;
  portfolioId: string;
  broker?: string;
  strategy?: string;
  algoParams?: AlgoParameters;
  allocations?: OrderAllocation[];
}

export interface ModifyOrderRequest {
  quantity?: number;
  limitPrice?: number;
  stopPrice?: number;
  timeInForce?: TimeInForce;
}

export interface PortfolioAnalytics {
  portfolio: Portfolio;
  positions: Position[];
  riskDecomposition: RiskDecomposition;
  attribution?: PerformanceAttribution;
}
