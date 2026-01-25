import { useMarketData, usePositions } from './useTradingData';
import { clsx } from 'clsx';

export function MarketDataPanel() {
  const { marketData, flashingSymbols } = useMarketData();

  return (
    <div className="h-full flex flex-col bg-[#1e1e2d] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <h3 className="text-sm font-semibold text-white">Market Data</h3>
        <span className="text-xs text-green-400">● Real-time</span>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-[#252536] sticky top-0">
            <tr className="text-gray-400 text-left">
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium text-right">Bid</th>
              <th className="px-3 py-2 font-medium text-right">Ask</th>
              <th className="px-3 py-2 font-medium text-right">Last</th>
              <th className="px-3 py-2 font-medium text-right">Chg</th>
              <th className="px-3 py-2 font-medium text-right">Vol</th>
            </tr>
          </thead>
          <tbody>
            {marketData.map(md => {
              const flash = flashingSymbols.get(md.symbol);
              return (
                <tr 
                  key={md.symbol}
                  className={clsx(
                    'border-b border-[#2d2d43] transition-colors duration-150',
                    flash === 'up' && 'bg-green-500/20',
                    flash === 'down' && 'bg-red-500/20',
                    !flash && 'hover:bg-[#252536]'
                  )}
                >
                  <td className="px-3 py-1.5 font-semibold text-white">{md.symbol}</td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono',
                    flash === 'up' ? 'text-green-400' : flash === 'down' ? 'text-red-400' : 'text-blue-400'
                  )}>
                    {md.bid.toFixed(2)}
                  </td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono',
                    flash === 'up' ? 'text-green-400' : flash === 'down' ? 'text-red-400' : 'text-red-400'
                  )}>
                    {md.ask.toFixed(2)}
                  </td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono font-semibold',
                    flash === 'up' ? 'text-green-400' : flash === 'down' ? 'text-red-400' : 'text-white'
                  )}>
                    {md.last.toFixed(2)}
                  </td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono',
                    md.change >= 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {md.change >= 0 ? '+' : ''}{md.change.toFixed(2)} ({md.changePct.toFixed(2)}%)
                  </td>
                  <td className="px-3 py-1.5 text-right text-gray-400">
                    {(md.volume / 1000000).toFixed(1)}M
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function PositionsPanel() {
  const { positions, flashingSymbols } = usePositions();
  
  const totalPnl = positions.reduce((sum, p) => sum + p.pnl, 0);
  const totalDayPnl = positions.reduce((sum, p) => sum + p.dayPnl, 0);

  return (
    <div className="h-full flex flex-col bg-[#1e1e2d] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <h3 className="text-sm font-semibold text-white">Positions</h3>
        <div className="flex items-center gap-4">
          <span className={clsx('text-xs font-mono', totalDayPnl >= 0 ? 'text-green-400' : 'text-red-400')}>
            Day: {totalDayPnl >= 0 ? '+' : ''}${(totalDayPnl / 1000).toFixed(1)}K
          </span>
          <span className={clsx('text-xs font-mono', totalPnl >= 0 ? 'text-green-400' : 'text-red-400')}>
            Total: {totalPnl >= 0 ? '+' : ''}${(totalPnl / 1000).toFixed(1)}K
          </span>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-[#252536] sticky top-0">
            <tr className="text-gray-400 text-left">
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-right">Avg Cost</th>
              <th className="px-3 py-2 font-medium text-right">Last</th>
              <th className="px-3 py-2 font-medium text-right">P&L</th>
              <th className="px-3 py-2 font-medium text-right">Day P&L</th>
            </tr>
          </thead>
          <tbody>
            {positions.map(pos => {
              const flash = flashingSymbols.get(pos.symbol);
              return (
                <tr 
                  key={pos.symbol}
                  className={clsx(
                    'border-b border-[#2d2d43] transition-colors duration-150',
                    flash === 'up' && 'bg-green-500/20',
                    flash === 'down' && 'bg-red-500/20',
                    !flash && 'hover:bg-[#252536]'
                  )}
                >
                  <td className="px-3 py-1.5 font-semibold text-white">{pos.symbol}</td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono',
                    pos.qty > 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {pos.qty > 0 ? '+' : ''}{pos.qty.toLocaleString()}
                  </td>
                  <td className="px-3 py-1.5 text-right font-mono text-gray-300">
                    ${pos.avgCost.toFixed(2)}
                  </td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono font-semibold',
                    flash === 'up' ? 'text-green-400' : flash === 'down' ? 'text-red-400' : 'text-white'
                  )}>
                    ${pos.lastPrice.toFixed(2)}
                  </td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono',
                    pos.pnl >= 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {pos.pnl >= 0 ? '+' : ''}${(pos.pnl / 1000).toFixed(1)}K ({pos.pnlPct.toFixed(1)}%)
                  </td>
                  <td className={clsx(
                    'px-3 py-1.5 text-right font-mono',
                    pos.dayPnl >= 0 ? 'text-green-400' : 'text-red-400'
                  )}>
                    {pos.dayPnl >= 0 ? '+' : ''}${pos.dayPnl.toFixed(0)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
