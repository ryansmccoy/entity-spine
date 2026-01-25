import { useOrders, useExecutions } from './useTradingData';
import { clsx } from 'clsx';

export function OrderBlotter() {
  const { orders, flashingIds } = useOrders(20);

  return (
    <div className="h-full flex flex-col bg-[#1e1e2d] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <h3 className="text-sm font-semibold text-white">Order Blotter</h3>
        <div className="flex items-center gap-2">
          <span className="text-xs text-green-400">● Live</span>
          <span className="text-xs text-gray-400">{orders.length} orders</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-[#252536] sticky top-0">
            <tr className="text-gray-400 text-left">
              <th className="px-3 py-2 font-medium">ID</th>
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Side</th>
              <th className="px-3 py-2 font-medium text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-right">Filled</th>
              <th className="px-3 py-2 font-medium text-right">Avg Px</th>
              <th className="px-3 py-2 font-medium">Algo</th>
              <th className="px-3 py-2 font-medium">Broker</th>
              <th className="px-3 py-2 font-medium">Status</th>
              <th className="px-3 py-2 font-medium">Progress</th>
            </tr>
          </thead>
          <tbody>
            {orders.map(order => (
              <tr 
                key={order.id}
                className={clsx(
                  'border-b border-[#2d2d43] hover:bg-[#252536] transition-colors',
                  flashingIds.has(order.id) && 'bg-yellow-500/20'
                )}
              >
                <td className="px-3 py-2 font-mono text-gray-300">{order.id}</td>
                <td className="px-3 py-2 font-semibold text-white">{order.symbol}</td>
                <td className={clsx('px-3 py-2 font-semibold', order.side === 'BUY' ? 'text-green-400' : 'text-red-400')}>
                  {order.side}
                </td>
                <td className="px-3 py-2 text-right text-gray-300">{order.qty.toLocaleString()}</td>
                <td className={clsx(
                  'px-3 py-2 text-right',
                  flashingIds.has(order.id) ? 'text-yellow-300 font-semibold' : 'text-gray-300'
                )}>
                  {order.filled.toLocaleString()}
                </td>
                <td className="px-3 py-2 text-right font-mono text-gray-300">${order.avgPrice.toFixed(2)}</td>
                <td className="px-3 py-2 text-cyan-400">{order.algo}</td>
                <td className="px-3 py-2 text-purple-400">{order.broker}</td>
                <td className="px-3 py-2">
                  <span className={clsx(
                    'px-2 py-0.5 rounded text-[10px] font-semibold',
                    order.status === 'Filled' && 'bg-green-500/20 text-green-400',
                    order.status === 'Working' && 'bg-blue-500/20 text-blue-400',
                    order.status === 'PartFill' && 'bg-yellow-500/20 text-yellow-400',
                    order.status === 'Pending' && 'bg-gray-500/20 text-gray-400',
                    order.status === 'Cancelled' && 'bg-red-500/20 text-red-400',
                  )}>
                    {order.status}
                  </span>
                </td>
                <td className="px-3 py-2 w-32">
                  <div className="flex items-center gap-2">
                    <div className="flex-1 h-1.5 bg-[#2d2d43] rounded-full overflow-hidden">
                      <div 
                        className={clsx(
                          'h-full transition-all duration-300',
                          order.status === 'Filled' ? 'bg-green-500' : 'bg-blue-500'
                        )}
                        style={{ width: `${order.pctDone}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-gray-400 w-8">{order.pctDone}%</span>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function ExecutionFeed() {
  const { executions, newExecutionId } = useExecutions(30);

  return (
    <div className="h-full flex flex-col bg-[#1e1e2d] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <h3 className="text-sm font-semibold text-white">Execution Feed</h3>
        <div className="flex items-center gap-2">
          <span className="animate-pulse text-xs text-green-400">● Streaming</span>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs">
          <thead className="bg-[#252536] sticky top-0">
            <tr className="text-gray-400 text-left">
              <th className="px-3 py-2 font-medium">Time</th>
              <th className="px-3 py-2 font-medium">Symbol</th>
              <th className="px-3 py-2 font-medium">Side</th>
              <th className="px-3 py-2 font-medium text-right">Qty</th>
              <th className="px-3 py-2 font-medium text-right">Price</th>
              <th className="px-3 py-2 font-medium">Venue</th>
            </tr>
          </thead>
          <tbody>
            {executions.map(exec => (
              <tr 
                key={exec.id}
                className={clsx(
                  'border-b border-[#2d2d43] transition-all duration-500',
                  exec.id === newExecutionId ? 'bg-green-500/30 animate-pulse' : 'hover:bg-[#252536]'
                )}
              >
                <td className="px-3 py-1.5 font-mono text-gray-400">{exec.time}</td>
                <td className="px-3 py-1.5 font-semibold text-white">{exec.symbol}</td>
                <td className={clsx('px-3 py-1.5 font-semibold', exec.side === 'BUY' ? 'text-green-400' : 'text-red-400')}>
                  {exec.side}
                </td>
                <td className="px-3 py-1.5 text-right text-gray-300">{exec.qty.toLocaleString()}</td>
                <td className="px-3 py-1.5 text-right font-mono text-gray-300">${exec.price.toFixed(2)}</td>
                <td className="px-3 py-1.5 text-cyan-400">{exec.venue}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
