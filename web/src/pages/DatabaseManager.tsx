import React, { useState } from 'react';
import api from '../services/api';

const DatabaseManager: React.FC = () => {
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const loadSECData = async () => {
    try {
      setLoading(true);
      setMessage('Loading SEC data... This may take a few minutes.');
      await api.loadSECData();
      setMessage('SEC data loaded successfully!');
    } catch (err) {
      setMessage('Failed to load SEC data. See console for details.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Database Management</h1>
        <p className="page-subtitle">Manage your EntitySpine database</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Data Loading</h2>
        </div>
        <div className="action-section">
          <h3>Load SEC Company Data</h3>
          <p className="text-muted">
            Load 14,000+ public companies from SEC company_tickers.json
          </p>
          <button
            onClick={loadSECData}
            className="button button-primary"
            disabled={loading}
          >
            {loading ? 'Loading...' : 'Load SEC Data'}
          </button>
          {message && (
            <div className={loading ? 'info-message' : 'success-message'}>
              {message}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Database Information</h2>
        </div>
        <p className="text-muted">
          EntitySpine uses SQLite for development and can scale to PostgreSQL for production.
          See the documentation for more information on storage tiers.
        </p>
      </div>
    </div>
  );
};

export default DatabaseManager;
