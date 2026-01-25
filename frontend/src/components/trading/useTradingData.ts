import { useState, useEffect } from 'react';
import {
  Order,
  Execution,
  Position,
  MarketData,
  BrokerScore,
  AlgoPerformance,
  generateOrders,
  generateExecutions,
  generatePositions,
  generateMarketData,
  generateBrokerScores,
  generateAlgoPerformance,
  updateOrder,
  updateMarketData,
  updatePosition,
  generateNewExecution,
} from './mockData';

export function useOrders(initialCount = 15) {
  const [orders, setOrders] = useState<Order[]>(() => generateOrders(initialCount));
  const [flashingIds, setFlashingIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    const interval = setInterval(() => {
      setOrders(prev => {
        const updated = prev.map(order => {
          if (Math.random() > 0.7) {
            const newOrder = updateOrder(order);
            if (newOrder.filled !== order.filled) {
              setFlashingIds(ids => new Set([...ids, order.id]));
              setTimeout(() => {
                setFlashingIds(ids => {
                  const newIds = new Set(ids);
                  newIds.delete(order.id);
                  return newIds;
                });
              }, 500);
            }
            return newOrder;
          }
          return order;
        });
        return updated;
      });
    }, 800);

    return () => clearInterval(interval);
  }, []);

  return { orders, flashingIds };
}

export function useExecutions(initialCount = 20) {
  const [executions, setExecutions] = useState<Execution[]>(() => generateExecutions(initialCount));
  const [newExecutionId, setNewExecutionId] = useState<string | null>(null);

  useEffect(() => {
    const interval = setInterval(() => {
      if (Math.random() > 0.5) {
        const newExec = generateNewExecution(['AAPL', 'NVDA', 'MSFT', 'GOOGL', 'META', 'AMZN']);
        setExecutions(prev => [newExec, ...prev.slice(0, 49)]);
        setNewExecutionId(newExec.id);
        setTimeout(() => setNewExecutionId(null), 800);
      }
    }, 600);

    return () => clearInterval(interval);
  }, []);

  return { executions, newExecutionId };
}

export function usePositions() {
  const [positions, setPositions] = useState<Position[]>(() => generatePositions());
  const [flashingSymbols, setFlashingSymbols] = useState<Map<string, 'up' | 'down'>>(new Map());

  useEffect(() => {
    const interval = setInterval(() => {
      setPositions(prev => {
        const marketData = generateMarketData();
        return prev.map(pos => {
          const md = marketData.find(m => m.symbol === pos.symbol);
          if (md && Math.random() > 0.6) {
            const updated = updatePosition(pos, md);
            if (updated.lastPrice !== pos.lastPrice) {
              const direction = updated.lastPrice > pos.lastPrice ? 'up' : 'down';
              setFlashingSymbols(map => new Map(map).set(pos.symbol, direction));
              setTimeout(() => {
                setFlashingSymbols(map => {
                  const newMap = new Map(map);
                  newMap.delete(pos.symbol);
                  return newMap;
                });
              }, 400);
            }
            return updated;
          }
          return pos;
        });
      });
    }, 500);

    return () => clearInterval(interval);
  }, []);

  return { positions, flashingSymbols };
}

export function useMarketData() {
  const [marketData, setMarketData] = useState<MarketData[]>(() => generateMarketData());
  const [flashingSymbols, setFlashingSymbols] = useState<Map<string, 'up' | 'down'>>(new Map());

  useEffect(() => {
    const interval = setInterval(() => {
      setMarketData(prev => {
        return prev.map(md => {
          if (Math.random() > 0.4) {
            const updated = updateMarketData(md);
            const direction = updated.last > md.last ? 'up' : 'down';
            setFlashingSymbols(map => new Map(map).set(md.symbol, direction));
            setTimeout(() => {
              setFlashingSymbols(map => {
                const newMap = new Map(map);
                newMap.delete(md.symbol);
                return newMap;
              });
            }, 300);
            return updated;
          }
          return md;
        });
      });
    }, 250);

    return () => clearInterval(interval);
  }, []);

  return { marketData, flashingSymbols };
}

export function useBrokerScores() {
  const [scores, setScores] = useState<BrokerScore[]>(() => generateBrokerScores());

  useEffect(() => {
    const interval = setInterval(() => {
      setScores(generateBrokerScores());
    }, 5000);

    return () => clearInterval(interval);
  }, []);

  return scores;
}

export function useAlgoPerformance() {
  const [performance, setPerformance] = useState<AlgoPerformance[]>(() => generateAlgoPerformance());

  useEffect(() => {
    const interval = setInterval(() => {
      setPerformance(generateAlgoPerformance());
    }, 8000);

    return () => clearInterval(interval);
  }, []);

  return performance;
}

// Pipeline status simulation
export interface PipelineStage {
  name: string;
  status: 'idle' | 'running' | 'completed' | 'error';
  progress: number;
  records: number;
  duration: string;
}

export interface Pipeline {
  id: string;
  name: string;
  stages: PipelineStage[];
  lastRun: string;
  nextRun: string;
}

export function usePipelines() {
  const [pipelines, setPipelines] = useState<Pipeline[]>([
    {
      id: 'exec-ingest',
      name: 'execution.ingest',
      stages: [
        { name: 'Bronze', status: 'completed', progress: 100, records: 45230, duration: '2.3s' },
        { name: 'Silver', status: 'running', progress: 67, records: 38450, duration: '5.1s' },
        { name: 'Gold', status: 'idle', progress: 0, records: 0, duration: '-' },
      ],
      lastRun: '14:32:15',
      nextRun: '14:35:00',
    },
    {
      id: 'tca-daily',
      name: 'tca.daily_aggregate',
      stages: [
        { name: 'Bronze', status: 'completed', progress: 100, records: 12500, duration: '1.8s' },
        { name: 'Silver', status: 'completed', progress: 100, records: 12500, duration: '3.2s' },
        { name: 'Gold', status: 'running', progress: 45, records: 5625, duration: '4.5s' },
      ],
      lastRun: '14:30:00',
      nextRun: '14:45:00',
    },
    {
      id: 'broker-score',
      name: 'broker.scorecard',
      stages: [
        { name: 'Bronze', status: 'completed', progress: 100, records: 8900, duration: '1.2s' },
        { name: 'Silver', status: 'completed', progress: 100, records: 8900, duration: '2.1s' },
        { name: 'Gold', status: 'completed', progress: 100, records: 7, duration: '0.8s' },
      ],
      lastRun: '14:28:00',
      nextRun: '15:00:00',
    },
  ]);

  useEffect(() => {
    const interval = setInterval(() => {
      setPipelines(prev => prev.map(pipeline => ({
        ...pipeline,
        stages: pipeline.stages.map(stage => {
          if (stage.status === 'running') {
            const newProgress = Math.min(100, stage.progress + Math.random() * 10);
            return {
              ...stage,
              progress: newProgress,
              records: Math.floor(stage.records * newProgress / stage.progress) || stage.records,
              status: newProgress >= 100 ? 'completed' : 'running',
            };
          }
          if (stage.status === 'idle' && Math.random() > 0.95) {
            return { ...stage, status: 'running', progress: 5 };
          }
          return stage;
        }),
      })));
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  return pipelines;
}
