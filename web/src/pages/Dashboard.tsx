import React, { useEffect, useState } from 'react';
import api from '../services/api';
import './Dashboard.css';

interface Stats {
  entity_count: number;
  identifier_count: number;
  relationship_count: number;
  schemes: Record<string, number>;
}

const Dashboard: React.FC = () => {
  const [stats, setStats] = useState<Stats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    loadStats();
  }, []);

  const loadStats = async () => {
    try {
      setLoading(true);
      const data = await api.getDatabaseStats();
      setStats(data);
      setError(null);
    } catch (err) {
      setError('Failed to load statistics');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="page-container">
        <div className="loading">Loading dashboard...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="page-container">
        <div className="error">{error}</div>
      </div>
    );
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Dashboard</h1>
        <p className="page-subtitle">EntitySpine Knowledge Graph Overview</p>
      </div>

      <div className="grid grid-4">
        <div className="stat-card">
          <div className="stat-icon">🏢</div>
          <div className="stat-value">{stats?.entity_count.toLocaleString()}</div>
          <div className="stat-label">Entities</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🔗</div>
          <div className="stat-value">{stats?.identifier_count.toLocaleString()}</div>
          <div className="stat-label">Identifiers</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">🕸️</div>
          <div className="stat-value">{stats?.relationship_count.toLocaleString()}</div>
          <div className="stat-label">Relationships</div>
        </div>

        <div className="stat-card">
          <div className="stat-icon">📊</div>
          <div className="stat-value">{Object.keys(stats?.schemes || {}).length}</div>
          <div className="stat-label">ID Schemes</div>
        </div>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Identifier Schemes</h2>
          </div>
          <div className="scheme-list">
            {Object.entries(stats?.schemes || {})
              .sort(([, a], [, b]) => b - a)
              .map(([scheme, count]) => (
                <div key={scheme} className="scheme-item">
                  <span className="scheme-name">{scheme}</span>
                  <span className="scheme-count">{count.toLocaleString()}</span>
                </div>
              ))}
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Quick Actions</h2>
          </div>
          <div className="action-grid">
            <a href="/search" className="action-card">
              <span className="action-icon">🔍</span>
              <span className="action-label">Search Entities</span>
              <span className="action-arrow">→</span>
            </a>

            <a href="/graph" className="action-card">
              <span className="action-icon">🕸️</span>
              <span className="action-label">Explore Graph</span>
              <span className="action-arrow">→</span>
            </a>

            <a href="/database" className="action-card">
              <span className="action-icon">💾</span>
              <span className="action-label">Manage Data</span>
              <span className="action-arrow">→</span>
            </a>

            <a href="/docs" className="action-card">
              <span className="action-icon">📚</span>
              <span className="action-label">View Docs</span>
              <span className="action-arrow">→</span>
            </a>
          </div>
        </div>
      </div>
    </div>
  );
};

export default Dashboard;
