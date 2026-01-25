// Mock data generators for trading dashboards

export interface Order {
  id: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  qty: number;
  filled: number;
  price: number;
  avgPrice: number;
  algo: string;
  broker: string;
  status: 'Working' | 'Filled' | 'PartFill' | 'Pending' | 'Cancelled';
  pctDone: number;
  startTime: string;
  venue: string;
}

export interface Execution {
  id: string;
  time: string;
  symbol: string;
  side: 'BUY' | 'SELL';
  qty: number;
  price: number;
  venue: string;
  orderId: string;
}

export interface Position {
  symbol: string;
  qty: number;
  avgCost: number;
  lastPrice: number;
  pnl: number;
  pnlPct: number;
  dayPnl: number;
  dayPnlPct: number;
}

export interface MarketData {
  symbol: string;
  bid: number;
  ask: number;
  last: number;
  change: number;
  changePct: number;
  volume: number;
  vwap: number;
}

export interface BrokerScore {
  broker: string;
  fillRate: number;
  avgSlippage: number;
  avgLatency: number;
  volume: number;
  score: number;
}

export interface AlgoPerformance {
  algo: string;
  broker: string;
  orders: number;
  avgSlippage: number;
  arrivalCost: number;
  participationRate: number;
  fillRate: number;
}

// Sample symbols
const symbols = ['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN', 'TSLA', 'JPM', 'V', 'UNH', 'HD', 'PG', 'JNJ', 'XOM', 'CVX'];
const algos = ['VWAP', 'TWAP', 'IS', 'POV', 'Liquidity', 'Iceberg', 'Sniper'];
const brokers = ['JPM', 'MS', 'GS', 'CANT', 'BARC', 'CS', 'CITI'];
const venues = ['NYSE', 'NASDAQ', 'ARCA', 'BATS', 'IEX', 'DARK-JPM', 'DARK-MS', 'DARK-GS'];

// Base prices for symbols
const basePrices: Record<string, number> = {
  AAPL: 227.50, NVDA: 145.20, MSFT: 425.80, GOOGL: 178.30, META: 585.40,
  AMZN: 195.60, TSLA: 248.90, JPM: 215.40, V: 295.20, UNH: 548.30,
  HD: 385.60, PG: 172.40, JNJ: 158.90, XOM: 108.50, CVX: 152.30
};

function randomId(): string {
  return Math.random().toString(36).substring(2, 10).toUpperCase();
}

function randomElement<T>(arr: T[]): T {
  return arr[Math.floor(Math.random() * arr.length)];
}

function randomBetween(min: number, max: number): number {
  return Math.random() * (max - min) + min;
}

export function generateOrders(count: number): Order[] {
  const orders: Order[] = [];
  const statuses: Order['status'][] = ['Working', 'Working', 'Working', 'PartFill', 'PartFill', 'Filled', 'Pending'];
  
  for (let i = 0; i < count; i++) {
    const symbol = randomElement(symbols);
    const basePrice = basePrices[symbol];
    const qty = Math.floor(randomBetween(5000, 100000) / 100) * 100;
    const status = randomElement(statuses);
    const pctDone = status === 'Filled' ? 100 : status === 'Pending' ? 0 : Math.floor(randomBetween(10, 95));
    const filled = Math.floor(qty * pctDone / 100);
    
    orders.push({
      id: randomId(),
      symbol,
      side: Math.random() > 0.5 ? 'BUY' : 'SELL',
      qty,
      filled,
      price: basePrice,
      avgPrice: basePrice + randomBetween(-0.5, 0.5),
      algo: randomElement(algos),
      broker: randomElement(brokers),
      status,
      pctDone,
      startTime: `${9 + Math.floor(Math.random() * 7)}:${String(Math.floor(Math.random() * 60)).padStart(2, '0')}`,
      venue: randomElement(venues),
    });
  }
  
  return orders;
}

export function generateExecutions(count: number): Execution[] {
  const executions: Execution[] = [];
  const now = new Date();
  
  for (let i = 0; i < count; i++) {
    const symbol = randomElement(symbols);
    const basePrice = basePrices[symbol];
    const time = new Date(now.getTime() - i * randomBetween(5000, 30000));
    
    executions.push({
      id: randomId(),
      time: time.toLocaleTimeString('en-US', { hour12: false }),
      symbol,
      side: Math.random() > 0.5 ? 'BUY' : 'SELL',
      qty: Math.floor(randomBetween(100, 5000) / 100) * 100,
      price: basePrice + randomBetween(-0.3, 0.3),
      venue: randomElement(venues),
      orderId: randomId(),
    });
  }
  
  return executions;
}

export function generatePositions(): Position[] {
  return symbols.slice(0, 10).map(symbol => {
    const basePrice = basePrices[symbol];
    const qty = (Math.random() > 0.5 ? 1 : -1) * Math.floor(randomBetween(1000, 50000) / 100) * 100;
    const avgCost = basePrice * (1 + randomBetween(-0.05, 0.05));
    const lastPrice = basePrice;
    const pnl = (lastPrice - avgCost) * qty;
    const pnlPct = ((lastPrice / avgCost) - 1) * 100 * (qty > 0 ? 1 : -1);
    const dayPnl = randomBetween(-5000, 8000);
    const dayPnlPct = randomBetween(-2, 3);
    
    return { symbol, qty, avgCost, lastPrice, pnl, pnlPct, dayPnl, dayPnlPct };
  });
}

export function generateMarketData(): MarketData[] {
  return symbols.map(symbol => {
    const basePrice = basePrices[symbol];
    const spread = randomBetween(0.01, 0.05);
    const change = randomBetween(-5, 5);
    
    return {
      symbol,
      bid: basePrice - spread / 2,
      ask: basePrice + spread / 2,
      last: basePrice,
      change,
      changePct: (change / basePrice) * 100,
      volume: Math.floor(randomBetween(1000000, 50000000)),
      vwap: basePrice + randomBetween(-0.5, 0.5),
    };
  });
}

export function generateBrokerScores(): BrokerScore[] {
  return brokers.map(broker => ({
    broker,
    fillRate: randomBetween(85, 99),
    avgSlippage: randomBetween(0.5, 5),
    avgLatency: Math.floor(randomBetween(2, 15)),
    volume: Math.floor(randomBetween(10, 100)) * 1000000,
    score: randomBetween(75, 98),
  }));
}

export function generateAlgoPerformance(): AlgoPerformance[] {
  const results: AlgoPerformance[] = [];
  
  for (const algo of algos) {
    for (const broker of brokers.slice(0, 4)) {
      results.push({
        algo,
        broker,
        orders: Math.floor(randomBetween(50, 500)),
        avgSlippage: randomBetween(-2, 8),
        arrivalCost: randomBetween(1, 10),
        participationRate: randomBetween(5, 25),
        fillRate: randomBetween(90, 100),
      });
    }
  }
  
  return results;
}

// Updaters for real-time simulation
export function updateOrder(order: Order): Order {
  if (order.status === 'Filled' || order.status === 'Cancelled') return order;
  
  const newPct = Math.min(100, order.pctDone + randomBetween(0, 5));
  const newFilled = Math.floor(order.qty * newPct / 100);
  
  return {
    ...order,
    filled: newFilled,
    pctDone: newPct,
    avgPrice: order.avgPrice + randomBetween(-0.02, 0.02),
    status: newPct >= 100 ? 'Filled' : newPct > 0 ? 'PartFill' : order.status,
  };
}

export function updateMarketData(data: MarketData): MarketData {
  const tick = randomBetween(-0.1, 0.1);
  const newLast = data.last + tick;
  const spread = data.ask - data.bid;
  
  return {
    ...data,
    last: newLast,
    bid: newLast - spread / 2,
    ask: newLast + spread / 2,
    change: data.change + tick,
    changePct: ((data.change + tick) / data.last) * 100,
    volume: data.volume + Math.floor(randomBetween(1000, 10000)),
  };
}

export function updatePosition(pos: Position, marketData: MarketData): Position {
  const newPrice = marketData.last;
  const newPnl = (newPrice - pos.avgCost) * pos.qty;
  const newPnlPct = ((newPrice / pos.avgCost) - 1) * 100 * (pos.qty > 0 ? 1 : -1);
  
  return {
    ...pos,
    lastPrice: newPrice,
    pnl: newPnl,
    pnlPct: newPnlPct,
    dayPnl: pos.dayPnl + randomBetween(-100, 150),
    dayPnlPct: pos.dayPnlPct + randomBetween(-0.05, 0.05),
  };
}

export function generateNewExecution(symbols: string[]): Execution {
  const symbol = randomElement(symbols.length > 0 ? symbols : ['AAPL']);
  const basePrice = basePrices[symbol] || 100;
  
  return {
    id: randomId(),
    time: new Date().toLocaleTimeString('en-US', { hour12: false }),
    symbol,
    side: Math.random() > 0.5 ? 'BUY' : 'SELL',
    qty: Math.floor(randomBetween(100, 2000) / 100) * 100,
    price: basePrice + randomBetween(-0.2, 0.2),
    venue: randomElement(venues),
    orderId: randomId(),
  };
}
