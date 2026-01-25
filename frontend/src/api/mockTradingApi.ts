/**
 * Mock Trading API Service
 * 
 * Simulates a real trading backend with realistic data generation.
 * In production, replace with actual HTTP/WebSocket calls.
 * 
 * Backend Implementation Notes:
 * - Use Redis for order state caching
 * - Use TimescaleDB for time-series market data
 * - Use PostgreSQL for position/portfolio data
 * - Use Kafka for real-time event streaming
 */

import type {
  Order,
  Execution,
  Position,
  Portfolio,
  Quote,
  RiskDecomposition,
  RiskFactorExposure,
  PerformanceAttribution,
  SectorAttribution,
  SecurityAttribution,
  SectorExposure,
  OrderSide,
  OrderType,
  OrderStatus,
  TimeInForce,
  AssetClass,
} from './schemas/trading';

// ============================================================================
// REALISTIC MOCK DATA GENERATORS
// ============================================================================

const BROKERS = ['Goldman Sachs', 'Morgan Stanley', 'JP Morgan', 'Citadel', 'Two Sigma', 'Virtu', 'Jane Street'];
const VENUES = ['NYSE', 'NASDAQ', 'BATS', 'IEX', 'ARCA', 'EDGX', 'DARK-GS', 'DARK-MS', 'SIGMA-X'];
const TRADERS = ['TRADER01', 'TRADER02', 'DESK_HEAD', 'PM_ALPHA', 'PM_BETA'];

// Realistic securities with actual-like data
export const SECURITIES_MASTER: Record<string, {
  name: string;
  sector: string;
  industry: string;
  country: string;
  currency: string;
  assetClass: AssetClass;
  beta: number;
  avgVolume: number;
  marketCap: number;
}> = {
  'AAPL': { name: 'Apple Inc.', sector: 'Technology', industry: 'Consumer Electronics', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.25, avgVolume: 75000000, marketCap: 3100000000000 },
  'MSFT': { name: 'Microsoft Corp', sector: 'Technology', industry: 'Software', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.95, avgVolume: 22000000, marketCap: 2900000000000 },
  'NVDA': { name: 'NVIDIA Corp', sector: 'Technology', industry: 'Semiconductors', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.65, avgVolume: 45000000, marketCap: 3200000000000 },
  'GOOGL': { name: 'Alphabet Inc', sector: 'Technology', industry: 'Internet Services', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.10, avgVolume: 28000000, marketCap: 2100000000000 },
  'AMZN': { name: 'Amazon.com Inc', sector: 'Consumer Discretionary', industry: 'E-Commerce', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.15, avgVolume: 42000000, marketCap: 1900000000000 },
  'META': { name: 'Meta Platforms', sector: 'Technology', industry: 'Social Media', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.30, avgVolume: 18000000, marketCap: 1400000000000 },
  'TSLA': { name: 'Tesla Inc', sector: 'Consumer Discretionary', industry: 'Automobiles', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.95, avgVolume: 95000000, marketCap: 780000000000 },
  'JPM': { name: 'JPMorgan Chase', sector: 'Financials', industry: 'Banks', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.05, avgVolume: 9500000, marketCap: 580000000000 },
  'V': { name: 'Visa Inc', sector: 'Financials', industry: 'Payment Processing', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.90, avgVolume: 7200000, marketCap: 540000000000 },
  'UNH': { name: 'UnitedHealth Group', sector: 'Healthcare', industry: 'Health Insurance', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.70, avgVolume: 3800000, marketCap: 520000000000 },
  'JNJ': { name: 'Johnson & Johnson', sector: 'Healthcare', industry: 'Pharmaceuticals', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.55, avgVolume: 6500000, marketCap: 380000000000 },
  'PG': { name: 'Procter & Gamble', sector: 'Consumer Staples', industry: 'Household Products', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.45, avgVolume: 5800000, marketCap: 390000000000 },
  'XOM': { name: 'Exxon Mobil', sector: 'Energy', industry: 'Oil & Gas', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.85, avgVolume: 15000000, marketCap: 450000000000 },
  'CVX': { name: 'Chevron Corp', sector: 'Energy', industry: 'Oil & Gas', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.90, avgVolume: 8500000, marketCap: 280000000000 },
  'LLY': { name: 'Eli Lilly', sector: 'Healthcare', industry: 'Pharmaceuticals', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 0.50, avgVolume: 3200000, marketCap: 720000000000 },
  'AVGO': { name: 'Broadcom Inc', sector: 'Technology', industry: 'Semiconductors', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.15, avgVolume: 2800000, marketCap: 690000000000 },
  'AMD': { name: 'AMD Inc', sector: 'Technology', industry: 'Semiconductors', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.55, avgVolume: 48000000, marketCap: 220000000000 },
  'INTC': { name: 'Intel Corp', sector: 'Technology', industry: 'Semiconductors', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.00, avgVolume: 35000000, marketCap: 95000000000 },
  'CRM': { name: 'Salesforce Inc', sector: 'Technology', industry: 'Software', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.20, avgVolume: 5500000, marketCap: 290000000000 },
  'NFLX': { name: 'Netflix Inc', sector: 'Communication Services', industry: 'Streaming', country: 'US', currency: 'USD', assetClass: 'EQUITY', beta: 1.35, avgVolume: 5200000, marketCap: 380000000000 },
};

// Base prices for simulation
const BASE_PRICES: Record<string, number> = {
  'AAPL': 227.50, 'MSFT': 425.80, 'NVDA': 145.20, 'GOOGL': 178.30, 'AMZN': 195.60,
  'META': 585.40, 'TSLA': 248.90, 'JPM': 198.50, 'V': 285.30, 'UNH': 545.20,
  'JNJ': 158.90, 'PG': 172.40, 'XOM': 105.80, 'CVX': 148.60, 'LLY': 785.40,
  'AVGO': 168.50, 'AMD': 138.90, 'INTC': 21.50, 'CRM': 298.70, 'NFLX': 895.20,
};

// Utility functions
const randomId = () => Math.random().toString(36).substring(2, 10).toUpperCase();
const randomElement = <T>(arr: T[]): T => arr[Math.floor(Math.random() * arr.length)];
const randomBetween = (min: number, max: number) => Math.random() * (max - min) + min;
const now = () => new Date().toISOString();

// Price simulation with momentum
const priceDeltas: Record<string, number> = {};
export function simulatePrice(symbol: string): number {
  const base = BASE_PRICES[symbol] || 100;
  if (!priceDeltas[symbol]) priceDeltas[symbol] = 0;
  
  // Add some momentum
  const momentum = priceDeltas[symbol] * 0.3;
  const noise = (Math.random() - 0.5) * base * 0.002;
  priceDeltas[symbol] = momentum + noise;
  
  return Math.max(base * 0.9, Math.min(base * 1.1, base + priceDeltas[symbol]));
}

// ============================================================================
// MOCK DATA GENERATORS
// ============================================================================

let orderSequence = 1000;
let execSequence = 5000;

export function generateMockOrder(overrides?: Partial<Order>): Order {
  const symbol = randomElement(Object.keys(SECURITIES_MASTER));
  const security = SECURITIES_MASTER[symbol];
  const side = randomElement<OrderSide>(['BUY', 'SELL', 'SHORT', 'COVER']);
  const orderType = randomElement<OrderType>(['MARKET', 'LIMIT', 'VWAP', 'TWAP', 'IS', 'POV']);
  const status = randomElement<OrderStatus>(['NEW', 'PENDING', 'PARTIAL', 'FILLED', 'CANCELLED']);
  const price = simulatePrice(symbol);
  const quantity = Math.floor(randomBetween(100, 50000) / 100) * 100;
  const filledPct = status === 'FILLED' ? 1 : status === 'PARTIAL' ? randomBetween(0.1, 0.9) : 0;
  const filledQty = Math.floor(quantity * filledPct);
  
  orderSequence++;
  
  return {
    orderId: `ORD-${randomId()}`,
    clientOrderId: `CLT-${orderSequence}`,
    symbol,
    sedol: `B${randomId().substring(0, 6)}`,
    exchange: randomElement(VENUES.slice(0, 2)),
    assetClass: security.assetClass,
    side,
    orderType,
    quantity,
    filledQuantity: filledQty,
    remainingQuantity: quantity - filledQty,
    limitPrice: orderType !== 'MARKET' ? price * (side.includes('BUY') ? 1.001 : 0.999) : undefined,
    avgFillPrice: filledQty > 0 ? price * randomBetween(0.999, 1.001) : undefined,
    timeInForce: randomElement<TimeInForce>(['DAY', 'GTC', 'IOC']),
    status,
    statusMessage: status === 'FILLED' ? 'Order fully executed' : status === 'PARTIAL' ? `${Math.round(filledPct * 100)}% filled` : undefined,
    createdAt: now(),
    updatedAt: now(),
    broker: randomElement(BROKERS),
    destination: randomElement(VENUES),
    strategy: orderType !== 'MARKET' && orderType !== 'LIMIT' ? orderType : undefined,
    portfolioId: 'PORTFOLIO_MAIN',
    traderId: randomElement(TRADERS),
    complianceStatus: 'APPROVED',
    riskCheckStatus: 'PASS',
    ...overrides,
  };
}

export function generateMockExecution(order: Order): Execution {
  execSequence++;
  const price = order.avgFillPrice || simulatePrice(order.symbol);
  const quantity = Math.min(
    Math.floor(randomBetween(100, order.remainingQuantity || 1000) / 100) * 100,
    order.quantity
  );
  
  return {
    executionId: `EXE-${randomId()}`,
    orderId: order.orderId,
    symbol: order.symbol,
    side: order.side,
    quantity,
    price,
    notionalValue: quantity * price,
    executionVenue: randomElement(VENUES),
    executionTime: now(),
    tradeDate: new Date().toISOString().split('T')[0],
    settlementDate: new Date(Date.now() + 86400000).toISOString().split('T')[0],
    liquidityFlag: randomElement(['ADD', 'REMOVE', 'DARK']),
    commission: quantity * 0.005,
    fees: quantity * price * 0.00003,
    netAmount: quantity * price * (order.side.includes('BUY') ? -1 : 1),
    reportingStatus: 'REPORTED',
  };
}

export function generateMockPosition(symbol: string): Position {
  const security = SECURITIES_MASTER[symbol];
  const price = simulatePrice(symbol);
  const quantity = Math.floor(randomBetween(1000, 100000) / 100) * 100;
  const avgCost = price * randomBetween(0.85, 1.15);
  const marketValue = quantity * price;
  const costBasis = quantity * avgCost;
  const unrealizedPnL = marketValue - costBasis;
  const dayChange = price * randomBetween(-0.03, 0.03);
  
  return {
    positionId: `POS-${randomId()}`,
    portfolioId: 'PORTFOLIO_MAIN',
    symbol,
    securityName: security.name,
    assetClass: security.assetClass,
    sector: security.sector,
    industry: security.industry,
    country: security.country,
    currency: security.currency,
    quantity,
    side: quantity > 0 ? 'LONG' : 'SHORT',
    tradingQuantity: quantity,
    settlingQuantity: 0,
    marketValue,
    costBasis,
    avgCost,
    currentPrice: price,
    previousClose: price - dayChange,
    unrealizedPnL,
    unrealizedPnLPct: (unrealizedPnL / costBasis) * 100,
    realizedPnL: randomBetween(-50000, 100000),
    dayPnL: quantity * dayChange,
    dayPnLPct: (dayChange / (price - dayChange)) * 100,
    beta: security.beta,
    volatility: randomBetween(0.15, 0.45),
    var95: marketValue * randomBetween(0.02, 0.05),
    portfolioWeight: randomBetween(0.02, 0.08),
    benchmarkWeight: randomBetween(0.01, 0.06),
    activeWeight: randomBetween(-0.02, 0.03),
  };
}

export function generateMockPortfolio(): Portfolio {
  const positions = Object.keys(SECURITIES_MASTER).slice(0, 15).map(generateMockPosition);
  const nav = 250000000;
  const longValue = positions.filter(p => p.quantity > 0).reduce((sum, p) => sum + p.marketValue, 0);
  const shortValue = Math.abs(positions.filter(p => p.quantity < 0).reduce((sum, p) => sum + p.marketValue, 0));
  
  const sectorMap = new Map<string, { long: number; short: number }>();
  positions.forEach(p => {
    const current = sectorMap.get(p.sector) || { long: 0, short: 0 };
    if (p.quantity > 0) current.long += p.marketValue;
    else current.short += Math.abs(p.marketValue);
    sectorMap.set(p.sector, current);
  });
  
  const sectorExposures: SectorExposure[] = Array.from(sectorMap.entries()).map(([sector, values]) => ({
    sector,
    longWeight: (values.long / nav) * 100,
    shortWeight: (values.short / nav) * 100,
    netWeight: ((values.long - values.short) / nav) * 100,
    benchmarkWeight: randomBetween(5, 25),
    activeWeight: randomBetween(-5, 5),
    contribution: randomBetween(-0.5, 1.5),
  }));
  
  return {
    portfolioId: 'PORTFOLIO_MAIN',
    portfolioName: 'Global Alpha Fund',
    portfolioType: 'TRADING',
    currency: 'USD',
    inceptionDate: '2020-01-15',
    nav,
    cash: nav - longValue + shortValue,
    equity: longValue - shortValue,
    longValue,
    shortValue,
    grossExposure: longValue + shortValue,
    netExposure: longValue - shortValue,
    leverage: (longValue + shortValue) / nav,
    dayReturn: randomBetween(-0.02, 0.025),
    mtdReturn: randomBetween(-0.03, 0.05),
    qtdReturn: randomBetween(-0.05, 0.08),
    ytdReturn: randomBetween(-0.08, 0.15),
    oneYearReturn: randomBetween(-0.10, 0.25),
    threeYearReturn: randomBetween(0.05, 0.35),
    fiveYearReturn: randomBetween(0.15, 0.55),
    inceptionReturn: randomBetween(0.25, 0.85),
    sharpeRatio: randomBetween(0.8, 2.2),
    sortinoRatio: randomBetween(1.0, 2.8),
    informationRatio: randomBetween(0.3, 1.5),
    maxDrawdown: randomBetween(-0.15, -0.05),
    currentDrawdown: randomBetween(-0.08, 0),
    trackingError: randomBetween(0.02, 0.06),
    beta: randomBetween(0.85, 1.15),
    alpha: randomBetween(-0.02, 0.05),
    topHoldings: positions.sort((a, b) => b.marketValue - a.marketValue).slice(0, 10),
    sectorExposures,
    countryExposures: [
      { country: 'United States', countryCode: 'US', longWeight: 75, shortWeight: 5, netWeight: 70, benchmarkWeight: 65, activeWeight: 5 },
      { country: 'United Kingdom', countryCode: 'GB', longWeight: 8, shortWeight: 2, netWeight: 6, benchmarkWeight: 8, activeWeight: -2 },
      { country: 'Japan', countryCode: 'JP', longWeight: 5, shortWeight: 1, netWeight: 4, benchmarkWeight: 6, activeWeight: -2 },
      { country: 'Germany', countryCode: 'DE', longWeight: 4, shortWeight: 1, netWeight: 3, benchmarkWeight: 4, activeWeight: -1 },
    ],
    benchmark: 'SPX',
    managerId: 'PM_ALPHA',
    lastUpdated: now(),
  };
}

export function generateMockRiskDecomposition(): RiskDecomposition {
  const styleFactors: RiskFactorExposure[] = [
    { factorCategory: 'STYLE', factorName: 'Market Beta', factorId: 'BETA', portfolioExposure: 1.05, benchmarkExposure: 1.0, activeExposure: 0.05, factorReturn: 0.012, contribution: 0.0126, factorVolatility: 0.16, marginalContributionToRisk: 0.042, percentOfTotalRisk: 35 },
    { factorCategory: 'STYLE', factorName: 'Size (SMB)', factorId: 'SIZE', portfolioExposure: -0.15, benchmarkExposure: 0, activeExposure: -0.15, factorReturn: -0.005, contribution: 0.00075, factorVolatility: 0.08, marginalContributionToRisk: 0.008, percentOfTotalRisk: 6 },
    { factorCategory: 'STYLE', factorName: 'Value (HML)', factorId: 'VALUE', portfolioExposure: -0.25, benchmarkExposure: 0, activeExposure: -0.25, factorReturn: 0.003, contribution: -0.00075, factorVolatility: 0.09, marginalContributionToRisk: 0.012, percentOfTotalRisk: 8 },
    { factorCategory: 'STYLE', factorName: 'Momentum', factorId: 'MOM', portfolioExposure: 0.35, benchmarkExposure: 0, activeExposure: 0.35, factorReturn: 0.008, contribution: 0.0028, factorVolatility: 0.12, marginalContributionToRisk: 0.018, percentOfTotalRisk: 12 },
    { factorCategory: 'STYLE', factorName: 'Quality', factorId: 'QUAL', portfolioExposure: 0.20, benchmarkExposure: 0, activeExposure: 0.20, factorReturn: 0.004, contribution: 0.0008, factorVolatility: 0.06, marginalContributionToRisk: 0.006, percentOfTotalRisk: 4 },
    { factorCategory: 'STYLE', factorName: 'Low Volatility', factorId: 'LVOL', portfolioExposure: -0.10, benchmarkExposure: 0, activeExposure: -0.10, factorReturn: 0.002, contribution: -0.0002, factorVolatility: 0.05, marginalContributionToRisk: 0.003, percentOfTotalRisk: 2 },
  ];
  
  const industryFactors: RiskFactorExposure[] = [
    { factorCategory: 'INDUSTRY', factorName: 'Technology', factorId: 'TECH', portfolioExposure: 0.35, benchmarkExposure: 0.28, activeExposure: 0.07, factorReturn: 0.015, contribution: 0.00525, factorVolatility: 0.22, marginalContributionToRisk: 0.025, percentOfTotalRisk: 18 },
    { factorCategory: 'INDUSTRY', factorName: 'Healthcare', factorId: 'HLTH', portfolioExposure: 0.12, benchmarkExposure: 0.13, activeExposure: -0.01, factorReturn: 0.005, contribution: 0.0006, factorVolatility: 0.14, marginalContributionToRisk: 0.008, percentOfTotalRisk: 5 },
    { factorCategory: 'INDUSTRY', factorName: 'Financials', factorId: 'FIN', portfolioExposure: 0.10, benchmarkExposure: 0.12, activeExposure: -0.02, factorReturn: 0.008, contribution: 0.0008, factorVolatility: 0.18, marginalContributionToRisk: 0.01, percentOfTotalRisk: 7 },
    { factorCategory: 'INDUSTRY', factorName: 'Energy', factorId: 'ENRG', portfolioExposure: 0.05, benchmarkExposure: 0.04, activeExposure: 0.01, factorReturn: -0.003, contribution: -0.00015, factorVolatility: 0.25, marginalContributionToRisk: 0.006, percentOfTotalRisk: 4 },
  ];
  
  return {
    portfolioId: 'PORTFOLIO_MAIN',
    asOfDate: new Date().toISOString().split('T')[0],
    totalRisk: 0.142,
    totalVariance: 0.0202,
    systematicRisk: 0.118,
    specificRisk: 0.078,
    styleRisk: 0.065,
    industryRisk: 0.042,
    countryRisk: 0.008,
    currencyRisk: 0.003,
    factorExposures: [...styleFactors, ...industryFactors],
    var95OneDay: 1850000,
    var99OneDay: 2650000,
    var95TenDay: 5850000,
    expectedShortfall95: 2350000,
    stressScenarios: [
      { scenarioName: '2008 Financial Crisis', scenarioType: 'HISTORICAL', description: 'Replay of Sep-Nov 2008 market conditions', portfolioImpact: -28.5, dollarImpact: -71250000 },
      { scenarioName: 'COVID-19 Crash', scenarioType: 'HISTORICAL', description: 'Replay of Feb-Mar 2020 drawdown', portfolioImpact: -22.3, dollarImpact: -55750000 },
      { scenarioName: 'Tech Selloff', scenarioType: 'HYPOTHETICAL', description: 'Technology sector -30%, other sectors -10%', portfolioImpact: -18.5, dollarImpact: -46250000 },
      { scenarioName: 'Rate Shock +200bp', scenarioType: 'FACTOR_SHOCK', description: 'Parallel shift in yield curve +200bp', portfolioImpact: -12.8, dollarImpact: -32000000 },
      { scenarioName: 'USD Strength +10%', scenarioType: 'FACTOR_SHOCK', description: 'Dollar strengthens 10% vs major currencies', portfolioImpact: -4.2, dollarImpact: -10500000 },
    ],
  };
}

export function generateMockAttribution(): PerformanceAttribution {
  const sectorAttribution: SectorAttribution[] = [
    { sector: 'Technology', portfolioWeight: 35, benchmarkWeight: 28, activeWeight: 7, portfolioReturn: 4.5, benchmarkReturn: 3.8, allocationEffect: 0.28, selectionEffect: 0.25, interactionEffect: 0.05, totalEffect: 0.58 },
    { sector: 'Healthcare', portfolioWeight: 12, benchmarkWeight: 13, activeWeight: -1, portfolioReturn: 2.1, benchmarkReturn: 2.5, allocationEffect: -0.01, selectionEffect: -0.05, interactionEffect: 0.00, totalEffect: -0.06 },
    { sector: 'Financials', portfolioWeight: 10, benchmarkWeight: 12, activeWeight: -2, portfolioReturn: 3.2, benchmarkReturn: 2.8, allocationEffect: -0.06, selectionEffect: 0.04, interactionEffect: -0.01, totalEffect: -0.03 },
    { sector: 'Consumer Discretionary', portfolioWeight: 14, benchmarkWeight: 10, activeWeight: 4, portfolioReturn: 5.2, benchmarkReturn: 4.1, allocationEffect: 0.16, selectionEffect: 0.15, interactionEffect: 0.04, totalEffect: 0.35 },
    { sector: 'Energy', portfolioWeight: 5, benchmarkWeight: 4, activeWeight: 1, portfolioReturn: -1.5, benchmarkReturn: -2.0, allocationEffect: -0.02, selectionEffect: 0.03, interactionEffect: 0.01, totalEffect: 0.02 },
    { sector: 'Consumer Staples', portfolioWeight: 6, benchmarkWeight: 7, activeWeight: -1, portfolioReturn: 1.2, benchmarkReturn: 1.5, allocationEffect: -0.01, selectionEffect: -0.02, interactionEffect: 0.00, totalEffect: -0.03 },
    { sector: 'Industrials', portfolioWeight: 8, benchmarkWeight: 9, activeWeight: -1, portfolioReturn: 2.8, benchmarkReturn: 2.5, allocationEffect: -0.03, selectionEffect: 0.03, interactionEffect: 0.00, totalEffect: 0.00 },
    { sector: 'Communication Services', portfolioWeight: 10, benchmarkWeight: 8, activeWeight: 2, portfolioReturn: 3.5, benchmarkReturn: 2.9, allocationEffect: 0.06, selectionEffect: 0.06, interactionEffect: 0.01, totalEffect: 0.13 },
  ];
  
  const topContributors: SecurityAttribution[] = [
    { symbol: 'NVDA', securityName: 'NVIDIA Corp', sector: 'Technology', portfolioWeight: 8.5, benchmarkWeight: 5.2, activeWeight: 3.3, portfolioReturn: 12.5, contribution: 1.06, activeContribution: 0.41 },
    { symbol: 'META', securityName: 'Meta Platforms', sector: 'Technology', portfolioWeight: 5.2, benchmarkWeight: 2.8, activeWeight: 2.4, portfolioReturn: 8.2, contribution: 0.43, activeContribution: 0.20 },
    { symbol: 'AMZN', securityName: 'Amazon.com', sector: 'Consumer Discretionary', portfolioWeight: 6.1, benchmarkWeight: 3.5, activeWeight: 2.6, portfolioReturn: 6.8, contribution: 0.41, activeContribution: 0.18 },
    { symbol: 'LLY', securityName: 'Eli Lilly', sector: 'Healthcare', portfolioWeight: 4.2, benchmarkWeight: 1.8, activeWeight: 2.4, portfolioReturn: 5.5, contribution: 0.23, activeContribution: 0.13 },
    { symbol: 'GOOGL', securityName: 'Alphabet', sector: 'Technology', portfolioWeight: 5.8, benchmarkWeight: 4.2, activeWeight: 1.6, portfolioReturn: 4.2, contribution: 0.24, activeContribution: 0.07 },
  ];
  
  const bottomContributors: SecurityAttribution[] = [
    { symbol: 'TSLA', securityName: 'Tesla Inc', sector: 'Consumer Discretionary', portfolioWeight: 3.5, benchmarkWeight: 1.8, activeWeight: 1.7, portfolioReturn: -8.5, contribution: -0.30, activeContribution: -0.14 },
    { symbol: 'INTC', securityName: 'Intel Corp', sector: 'Technology', portfolioWeight: 2.1, benchmarkWeight: 0.5, activeWeight: 1.6, portfolioReturn: -12.2, contribution: -0.26, activeContribution: -0.20 },
    { symbol: 'XOM', securityName: 'Exxon Mobil', sector: 'Energy', portfolioWeight: 2.8, benchmarkWeight: 1.2, activeWeight: 1.6, portfolioReturn: -5.2, contribution: -0.15, activeContribution: -0.08 },
    { symbol: 'JNJ', securityName: 'Johnson & Johnson', sector: 'Healthcare', portfolioWeight: 1.5, benchmarkWeight: 1.1, activeWeight: 0.4, portfolioReturn: -3.8, contribution: -0.06, activeContribution: -0.02 },
    { symbol: 'CVX', securityName: 'Chevron', sector: 'Energy', portfolioWeight: 1.2, benchmarkWeight: 0.8, activeWeight: 0.4, portfolioReturn: -4.5, contribution: -0.05, activeContribution: -0.02 },
  ];
  
  return {
    portfolioId: 'PORTFOLIO_MAIN',
    benchmarkId: 'SPX',
    periodStart: '2026-01-01',
    periodEnd: '2026-01-27',
    portfolioReturn: 3.85,
    benchmarkReturn: 2.92,
    activeReturn: 0.93,
    allocationEffect: 0.37,
    selectionEffect: 0.49,
    interactionEffect: 0.07,
    currencyEffect: 0.00,
    sectorAttribution,
    factorAttribution: [
      { factorName: 'Market Beta', factorCategory: 'STYLE', exposure: 0.05, factorReturn: 2.8, contribution: 0.14 },
      { factorName: 'Momentum', factorCategory: 'STYLE', exposure: 0.35, factorReturn: 1.2, contribution: 0.42 },
      { factorName: 'Quality', factorCategory: 'STYLE', exposure: 0.20, factorReturn: 0.8, contribution: 0.16 },
      { factorName: 'Size', factorCategory: 'STYLE', exposure: -0.15, factorReturn: -0.5, contribution: 0.08 },
      { factorName: 'Value', factorCategory: 'STYLE', exposure: -0.25, factorReturn: 0.3, contribution: -0.08 },
    ],
    topContributors,
    bottomContributors,
  };
}

export function generateMockQuote(symbol: string): Quote {
  const price = simulatePrice(symbol);
  const security = SECURITIES_MASTER[symbol];
  const previousClose = price * randomBetween(0.97, 1.03);
  const spread = price * randomBetween(0.0001, 0.001);
  
  return {
    symbol,
    exchange: randomElement(VENUES.slice(0, 2)),
    bidPrice: price - spread / 2,
    bidSize: Math.floor(randomBetween(100, 10000) / 100) * 100,
    askPrice: price + spread / 2,
    askSize: Math.floor(randomBetween(100, 10000) / 100) * 100,
    spread,
    spreadBps: (spread / price) * 10000,
    lastPrice: price,
    lastSize: Math.floor(randomBetween(100, 5000) / 100) * 100,
    lastTime: now(),
    openPrice: previousClose * randomBetween(0.998, 1.002),
    highPrice: Math.max(price, previousClose) * randomBetween(1.001, 1.02),
    lowPrice: Math.min(price, previousClose) * randomBetween(0.98, 0.999),
    closePrice: previousClose,
    vwap: price * randomBetween(0.998, 1.002),
    volume: Math.floor(security?.avgVolume * randomBetween(0.3, 1.5)),
    dollarVolume: Math.floor(security?.avgVolume * randomBetween(0.3, 1.5) * price),
    avgVolume20d: security?.avgVolume || 10000000,
    relativeVolume: randomBetween(0.5, 2.0),
    change: price - previousClose,
    changePct: ((price - previousClose) / previousClose) * 100,
    marketState: 'OPEN',
    timestamp: now(),
  };
}

// ============================================================================
// MOCK API SERVICE CLASS
// ============================================================================

class MockTradingApi {
  private orders: Order[] = [];
  private executions: Execution[] = [];
  private positions: Position[] = [];
  private portfolio: Portfolio | null = null;
  
  constructor() {
    // Initialize with some data
    this.orders = Array.from({ length: 50 }, () => generateMockOrder());
    this.executions = this.orders
      .filter(o => o.filledQuantity > 0)
      .flatMap(o => Array.from({ length: Math.ceil(Math.random() * 3) }, () => generateMockExecution(o)));
    this.positions = Object.keys(SECURITIES_MASTER).slice(0, 15).map(s => generateMockPosition(s));
    this.portfolio = generateMockPortfolio();
  }
  
  getOrders() { return this.orders; }
  getExecutions() { return this.executions; }
  getPositions() { return this.positions; }
  getPortfolio() { return this.portfolio; }
  getRiskDecomposition() { return generateMockRiskDecomposition(); }
  getAttribution() { return generateMockAttribution(); }
  getQuote(symbol: string) { return generateMockQuote(symbol); }
  
  // Simulate real-time updates
  subscribeToUpdates(callback: (type: string, data: unknown) => void) {
    const interval = setInterval(() => {
      // Random order update
      if (Math.random() > 0.7) {
        const order = generateMockOrder();
        this.orders.unshift(order);
        if (this.orders.length > 100) this.orders.pop();
        callback('ORDER', order);
      }
      
      // Random execution
      if (Math.random() > 0.8) {
        const order = this.orders.find(o => o.status === 'PARTIAL' || o.status === 'NEW');
        if (order) {
          const execution = generateMockExecution(order);
          this.executions.unshift(execution);
          if (this.executions.length > 200) this.executions.pop();
          callback('EXECUTION', execution);
        }
      }
      
      // Position update
      if (Math.random() > 0.5) {
        const idx = Math.floor(Math.random() * this.positions.length);
        const pos = this.positions[idx];
        const priceChange = pos.currentPrice * randomBetween(-0.005, 0.005);
        pos.currentPrice += priceChange;
        pos.marketValue = pos.quantity * pos.currentPrice;
        pos.dayPnL += pos.quantity * priceChange;
        pos.unrealizedPnL = pos.marketValue - pos.costBasis;
        callback('POSITION', pos);
      }
    }, 500);
    
    return () => clearInterval(interval);
  }
}

export const mockApi = new MockTradingApi();
