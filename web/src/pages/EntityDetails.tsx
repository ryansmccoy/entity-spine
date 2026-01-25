import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import api, { Entity, IdentifierClaim } from '../services/api';

const EntityDetails: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const [entity, setEntity] = useState<Entity | null>(null);
  const [identifiers, setIdentifiers] = useState<IdentifierClaim[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (id) {
      loadEntity(id);
      loadIdentifiers(id);
    }
  }, [id]);

  const loadEntity = async (entityId: string) => {
    try {
      const data = await api.getEntity(entityId);
      setEntity(data);
    } catch (err) {
      console.error('Failed to load entity:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadIdentifiers = async (entityId: string) => {
    try {
      const data = await api.getEntityIdentifiers(entityId);
      setIdentifiers(data);
    } catch (err) {
      console.error('Failed to load identifiers:', err);
    }
  };

  if (loading) {
    return <div className="page-container"><div className="loading">Loading...</div></div>;
  }

  if (!entity) {
    return <div className="page-container"><div className="error">Entity not found</div></div>;
  }

  return (
    <div className="page-container">
      <div className="page-header">
        <Link to="/search" className="back-link">← Back to Search</Link>
        <h1 className="page-title">{entity.primary_name}</h1>
        <p className="page-subtitle">{entity.entity_type} • {entity.source_system}</p>
      </div>

      <div className="grid grid-2">
        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Entity Information</h2>
          </div>
          <div className="info-grid">
            <div className="info-item">
              <span className="info-label">Entity ID</span>
              <span className="info-value">{entity.entity_id}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Type</span>
              <span className="info-value">{entity.entity_type}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Jurisdiction</span>
              <span className="info-value">{entity.jurisdiction || 'N/A'}</span>
            </div>
            <div className="info-item">
              <span className="info-label">Source</span>
              <span className="info-value">{entity.source_system}</span>
            </div>
          </div>
        </div>

        <div className="card">
          <div className="card-header">
            <h2 className="card-title">Identifiers ({identifiers.length})</h2>
          </div>
          <div className="identifiers-list">
            {identifiers.map((claim) => (
              <div key={claim.claim_id} className="identifier-item">
                <span className="identifier-scheme">{claim.scheme}</span>
                <span className="identifier-value">{claim.identifier}</span>
                <span className="identifier-confidence">{(claim.confidence * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Actions</h2>
        </div>
        <div className="action-buttons">
          <Link to={`/graph?id=${entity.entity_id}`} className="button button-primary">
            View Knowledge Graph
          </Link>
        </div>
      </div>
    </div>
  );
};

export default EntityDetails;
