import React, { useState } from 'react';
import api, { SearchResult } from '../services/api';
import { Link } from 'react-router-dom';
import './Search.css';

const Search: React.FC = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;

    try {
      setLoading(true);
      setError(null);
      const data = await api.searchEntities(query, 20);
      setResults(data);
    } catch (err) {
      setError('Search failed. Please try again.');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Entity Search</h1>
        <p className="page-subtitle">Search by name, CIK, ticker, or any identifier</p>
      </div>

      <div className="card">
        <form onSubmit={handleSearch} className="search-form">
          <input
            type="text"
            className="input search-input"
            placeholder="Search for Apple, AAPL, CIK 0000320193, etc..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            autoFocus
          />
          <button type="submit" className="button button-primary" disabled={loading}>
            {loading ? 'Searching...' : 'Search'}
          </button>
        </form>
      </div>

      {error && <div className="error">{error}</div>}

      {results.length > 0 && (
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Results ({results.length})</h2>
          </div>
          <div className="results-list">
            {results.map((result) => (
              <Link
                key={result.entity.entity_id}
                to={`/entity/${result.entity.entity_id}`}
                className="result-item"
              >
                <div className="result-main">
                  <h3 className="result-name">{result.entity.primary_name}</h3>
                  <div className="result-meta">
                    <span className="result-type">{result.entity.entity_type}</span>
                    {result.entity.jurisdiction && (
                      <span className="result-jurisdiction">{result.entity.jurisdiction}</span>
                    )}
                    <span className="result-source">{result.entity.source_system}</span>
                  </div>
                </div>
                <div className="result-score">
                  <div className="score-bar">
                    <div className="score-fill" style={{ width: `${result.score * 100}%` }}></div>
                  </div>
                  <span className="score-text">{(result.score * 100).toFixed(0)}%</span>
                </div>
              </Link>
            ))}
          </div>
        </div>
      )}

      {!loading && results.length === 0 && query && (
        <div className="card">
          <div className="empty-state">
            <div className="empty-icon">🔍</div>
            <h3>No results found</h3>
            <p>Try searching with a different term</p>
          </div>
        </div>
      )}
    </div>
  );
};

export default Search;
