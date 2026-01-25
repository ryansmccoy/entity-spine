import { usePipelines } from './useTradingData';
import { clsx } from 'clsx';
import { Database, ArrowRight, CheckCircle, Loader2, Clock } from 'lucide-react';

export function PipelineMonitor() {
  const pipelines = usePipelines();

  return (
    <div className="h-full flex flex-col bg-[#1e1e2d] rounded-lg overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-[#252536] border-b border-[#2d2d43]">
        <div className="flex items-center gap-2">
          <Database className="h-4 w-4 text-cyan-400" />
          <h3 className="text-sm font-semibold text-white">Pipeline Monitor</h3>
        </div>
        <span className="text-xs text-gray-400">Bronze → Silver → Gold</span>
      </div>
      
      <div className="flex-1 overflow-auto p-4 space-y-4">
        {pipelines.map(pipeline => (
          <div key={pipeline.id} className="bg-[#252536] rounded-lg p-4">
            <div className="flex items-center justify-between mb-3">
              <div>
                <h4 className="font-semibold text-white">{pipeline.name}</h4>
                <div className="flex items-center gap-3 text-[10px] text-gray-400 mt-1">
                  <span>Last: {pipeline.lastRun}</span>
                  <span>Next: {pipeline.nextRun}</span>
                </div>
              </div>
              <div className="flex items-center gap-2">
                {pipeline.stages.some(s => s.status === 'running') ? (
                  <span className="flex items-center gap-1 text-xs text-blue-400">
                    <Loader2 className="h-3 w-3 animate-spin" />
                    Running
                  </span>
                ) : pipeline.stages.every(s => s.status === 'completed') ? (
                  <span className="flex items-center gap-1 text-xs text-green-400">
                    <CheckCircle className="h-3 w-3" />
                    Complete
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-xs text-gray-400">
                    <Clock className="h-3 w-3" />
                    Idle
                  </span>
                )}
              </div>
            </div>
            
            {/* Pipeline Stages */}
            <div className="flex items-center gap-2">
              {pipeline.stages.map((stage, idx) => (
                <div key={stage.name} className="flex items-center gap-2 flex-1">
                  <div className={clsx(
                    'flex-1 rounded-lg p-3 border transition-all',
                    stage.status === 'completed' && 'bg-green-500/10 border-green-500/30',
                    stage.status === 'running' && 'bg-blue-500/10 border-blue-500/30',
                    stage.status === 'idle' && 'bg-[#2d2d43] border-[#3d3d53]',
                    stage.status === 'error' && 'bg-red-500/10 border-red-500/30',
                  )}>
                    <div className="flex items-center justify-between mb-2">
                      <span className={clsx(
                        'text-xs font-semibold',
                        stage.name === 'Bronze' && 'text-orange-400',
                        stage.name === 'Silver' && 'text-gray-300',
                        stage.name === 'Gold' && 'text-yellow-400',
                      )}>
                        {stage.name}
                      </span>
                      {stage.status === 'running' && (
                        <Loader2 className="h-3 w-3 text-blue-400 animate-spin" />
                      )}
                      {stage.status === 'completed' && (
                        <CheckCircle className="h-3 w-3 text-green-400" />
                      )}
                    </div>
                    
                    {/* Progress bar */}
                    <div className="h-1.5 bg-[#1e1e2d] rounded-full overflow-hidden mb-2">
                      <div 
                        className={clsx(
                          'h-full transition-all duration-500',
                          stage.status === 'completed' && 'bg-green-500',
                          stage.status === 'running' && 'bg-blue-500',
                          stage.status === 'idle' && 'bg-gray-600',
                        )}
                        style={{ width: `${stage.progress}%` }}
                      />
                    </div>
                    
                    <div className="flex justify-between text-[10px] text-gray-400">
                      <span>{stage.records.toLocaleString()} rows</span>
                      <span>{stage.duration}</span>
                    </div>
                  </div>
                  
                  {idx < pipeline.stages.length - 1 && (
                    <ArrowRight className="h-4 w-4 text-gray-500 flex-shrink-0" />
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
        
        {/* Overall Stats */}
        <div className="grid grid-cols-3 gap-4 pt-4 border-t border-[#2d2d43]">
          <div className="bg-orange-500/10 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-orange-400">
              {pipelines.reduce((sum, p) => sum + (p.stages[0]?.records || 0), 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-gray-400">Bronze Records</div>
          </div>
          <div className="bg-gray-400/10 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-gray-300">
              {pipelines.reduce((sum, p) => sum + (p.stages[1]?.records || 0), 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-gray-400">Silver Records</div>
          </div>
          <div className="bg-yellow-500/10 rounded-lg p-3 text-center">
            <div className="text-xl font-bold text-yellow-400">
              {pipelines.reduce((sum, p) => sum + (p.stages[2]?.records || 0), 0).toLocaleString()}
            </div>
            <div className="text-[10px] text-gray-400">Gold Records</div>
          </div>
        </div>
      </div>
    </div>
  );
}
