import { useBrokerScores, useAlgoPerformance } from './useTradingData';
import { clsx } from 'clsx';
import { useState } from 'react';

export function BrokerScorecard() {
  const scores = useBrokerScores();

  return (
    <div className="h-full flex flex-col bg-[#1e1e2d] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <h3 className="text-sm font-semibold text-white">Broker Scorecard</h3>
        <span className="text-xs text-gray-400">Q3 2024</span>
      </div>
      
      <div className="flex-1 overflow-auto p-4">
        <div className="grid grid-cols-1 gap-3">
          {scores.sort((a, b) => b.score - a.score).map((broker, idx) => (
            <div 
              key={broker.broker}
              className="flex items-center gap-4 p-3 bg-[#252536] rounded-lg"
            >
              <div className={clsx(
                'w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold',
                idx === 0 && 'bg-yellow-500/20 text-yellow-400',
                idx === 1 && 'bg-gray-400/20 text-gray-300',
                idx === 2 && 'bg-orange-500/20 text-orange-400',
                idx > 2 && 'bg-[#2d2d43] text-gray-400'
              )}>
                #{idx + 1}
              </div>
              
              <div className="flex-1">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-semibold text-white">{broker.broker}</span>
                  <span className={clsx(
                    'text-lg font-bold',
                    broker.score >= 90 ? 'text-green-400' : broker.score >= 80 ? 'text-yellow-400' : 'text-red-400'
                  )}>
                    {broker.score.toFixed(0)}
                  </span>
                </div>
                
                <div className="flex items-center gap-4 text-[10px] text-gray-400">
                  <span>Fill: <span className="text-cyan-400">{broker.fillRate.toFixed(1)}%</span></span>
                  <span>Slip: <span className={clsx(broker.avgSlippage < 2 ? 'text-green-400' : 'text-yellow-400')}>{broker.avgSlippage.toFixed(1)}bp</span></span>
                  <span>Lat: <span className="text-purple-400">{broker.avgLatency}ms</span></span>
                  <span>Vol: <span className="text-white">${(broker.volume / 1000000).toFixed(0)}M</span></span>
                </div>
                
                <div className="mt-2 h-1.5 bg-[#2d2d43] rounded-full overflow-hidden">
                  <div 
                    className={clsx(
                      'h-full transition-all duration-500',
                      broker.score >= 90 ? 'bg-green-500' : broker.score >= 80 ? 'bg-yellow-500' : 'bg-red-500'
                    )}
                    style={{ width: `${broker.score}%` }}
                  />
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export function AlgoAnalyzer() {
  const performance = useAlgoPerformance();
  const [selectedAlgo, setSelectedAlgo] = useState('VWAP');
  
  const algos = [...new Set(performance.map(p => p.algo))];
  const filtered = performance.filter(p => p.algo === selectedAlgo);

  return (
    <div className="h-full flex flex-col bg-[#1e1e2d] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <h3 className="text-sm font-semibold text-white">Algorithm Analyzer</h3>
        <select 
          value={selectedAlgo}
          onChange={(e) => setSelectedAlgo(e.target.value)}
          className="text-xs bg-[#2d2d43] border border-[#3d3d53] rounded px-2 py-1 text-white"
        >
          {algos.map(algo => (
            <option key={algo} value={algo}>{algo}</option>
          ))}
        </select>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-[#252536] sticky top-0">
            <tr className="text-gray-400 text-left">
              <th className="px-3 py-2 font-medium">Broker</th>
              <th className="px-3 py-2 font-medium text-right">Orders</th>
              <th className="px-3 py-2 font-medium text-right">Slippage</th>
              <th className="px-3 py-2 font-medium text-right">Arrival</th>
              <th className="px-3 py-2 font-medium text-right">Part%</th>
              <th className="px-3 py-2 font-medium text-right">Fill%</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map(p => (
              <tr 
                key={`${p.algo}-${p.broker}`}
                className="border-b border-[#2d2d43] hover:bg-[#252536]"
              >
                <td className="px-3 py-2 font-semibold text-purple-400">{p.broker}</td>
                <td className="px-3 py-2 text-right text-gray-300">{p.orders}</td>
                <td className={clsx(
                  'px-3 py-2 text-right font-mono',
                  p.avgSlippage < 2 ? 'text-green-400' : p.avgSlippage < 5 ? 'text-yellow-400' : 'text-red-400'
                )}>
                  {p.avgSlippage >= 0 ? '+' : ''}{p.avgSlippage.toFixed(1)}bp
                </td>
                <td className={clsx(
                  'px-3 py-2 text-right font-mono',
                  p.arrivalCost < 3 ? 'text-green-400' : p.arrivalCost < 6 ? 'text-yellow-400' : 'text-red-400'
                )}>
                  {p.arrivalCost.toFixed(1)}bp
                </td>
                <td className="px-3 py-2 text-right text-cyan-400">
                  {p.participationRate.toFixed(1)}%
                </td>
                <td className="px-3 py-2 text-right">
                  <span className={clsx(
                    'px-2 py-0.5 rounded text-[10px] font-semibold',
                    p.fillRate >= 98 ? 'bg-green-500/20 text-green-400' : 
                    p.fillRate >= 95 ? 'bg-yellow-500/20 text-yellow-400' : 
                    'bg-red-500/20 text-red-400'
                  )}>
                    {p.fillRate.toFixed(1)}%
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        
        {/* Summary Stats */}
        <div className="p-4 border-t border-[#2d2d43]">
          <div className="grid grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-lg font-bold text-white">
                {filtered.reduce((sum, p) => sum + p.orders, 0)}
              </div>
              <div className="text-[10px] text-gray-400">Total Orders</div>
            </div>
            <div className="text-center">
              <div className={clsx(
                'text-lg font-bold',
                (filtered.reduce((sum, p) => sum + p.avgSlippage, 0) / filtered.length) < 3 ? 'text-green-400' : 'text-yellow-400'
              )}>
                {(filtered.reduce((sum, p) => sum + p.avgSlippage, 0) / filtered.length).toFixed(1)}bp
              </div>
              <div className="text-[10px] text-gray-400">Avg Slippage</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-cyan-400">
                {(filtered.reduce((sum, p) => sum + p.participationRate, 0) / filtered.length).toFixed(1)}%
              </div>
              <div className="text-[10px] text-gray-400">Avg Participation</div>
            </div>
            <div className="text-center">
              <div className="text-lg font-bold text-green-400">
                {(filtered.reduce((sum, p) => sum + p.fillRate, 0) / filtered.length).toFixed(1)}%
              </div>
              <div className="text-[10px] text-gray-400">Avg Fill Rate</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
