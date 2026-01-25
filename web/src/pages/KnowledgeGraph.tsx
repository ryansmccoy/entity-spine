import React, { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import ForceGraph2D from 'react-force-graph-2d';
import api, { GraphData } from '../services/api';

const KnowledgeGraph: React.FC = () => {
  const { id } = useParams<{ id?: string }>();
  const [graphData, setGraphData] = useState<GraphData>({ nodes: [], links: [] });
  const [loading, setLoading] = useState(false);
  const [entityId, setEntityId] = useState(id || '');
  const graphRef = useRef<any>();

  const loadGraph = async (targetId: string) => {
    if (!targetId) return;
    
    try {
      setLoading(true);
      const data = await api.getEntityNetwork(targetId, 2);
      setGraphData(data);
    } catch (err) {
      console.error('Failed to load graph:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Knowledge Graph</h1>
        <p className="page-subtitle">Explore entity relationships and networks</p>
      </div>

      <div className="card">
        <div className="search-form">
          <input
            type="text"
            className="input"
            placeholder="Enter entity ID to visualize network..."
            value={entityId}
            onChange={(e) => setEntityId(e.target.value)}
          />
          <button
            onClick={() => loadGraph(entityId)}
            className="button button-primary"
            disabled={loading || !entityId}
          >
            {loading ? 'Loading...' : 'Visualize'}
          </button>
        </div>
      </div>

      {graphData.nodes.length > 0 && (
        <div className="card">
          <div style={{ height: '600px', background: var(--surface) }}>
            <ForceGraph2D
              ref={graphRef}
              graphData={graphData}
              nodeLabel="name"
              nodeAutoColorBy="type"
              linkLabel="type"
              linkDirectionalArrowLength={3.5}
              linkDirectionalArrowRelPos={1}
              backgroundColor="#1e293b"
              linkColor={() => '#64748b'}
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeGraph;
