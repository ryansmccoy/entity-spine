import React from 'react';

const Documentation: React.FC = () => {
  const docsUrl = process.env.REACT_APP_DOCS_URL || 'http://localhost:8001';

  return (
    <div className="page-container">
      <div className="page-header">
        <h1 className="page-title">Documentation</h1>
        <p className="page-subtitle">Learn how to use EntitySpine</p>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">Quick Links</h2>
        </div>
        <div className="docs-grid">
          <a href={`${docsUrl}`} target="_blank" rel="noopener noreferrer" className="docs-card">
            <div className="docs-icon">📚</div>
            <div className="docs-title">Full Documentation</div>
            <div className="docs-desc">Complete guides, tutorials, and API reference</div>
          </a>

          <a href={`${docsUrl}/guides/CORE_CONCEPTS/`} target="_blank" rel="noopener noreferrer" className="docs-card">
            <div className="docs-icon">🎯</div>
            <div className="docs-title">Core Concepts</div>
            <div className="docs-desc">Learn the fundamentals of EntitySpine</div>
          </a>

          <a href={`${docsUrl}/guides/SEC_DATA_GUIDE/`} target="_blank" rel="noopener noreferrer" className="docs-card">
            <div className="docs-icon">🏛️</div>
            <div className="docs-title">SEC Data Guide</div>
            <div className="docs-desc">Working with SEC company data</div>
          </a>

          <a href={`${docsUrl}/guides/CORPORATE_NETWORKS/`} target="_blank" rel="noopener noreferrer" className="docs-card">
            <div className="docs-icon">🕸️</div>
            <div className="docs-title">Corporate Networks</div>
            <div className="docs-desc">Build knowledge graphs and relationships</div>
          </a>

          <a href={`${docsUrl}/api/domain/`} target="_blank" rel="noopener noreferrer" className="docs-card">
            <div className="docs-icon">⚙️</div>
            <div className="docs-title">API Reference</div>
            <div className="docs-desc">Complete API documentation</div>
          </a>

          <a href={`${docsUrl}/architecture/ARCHITECTURE_AND_TIERS/`} target="_blank" rel="noopener noreferrer" className="docs-card">
            <div className="docs-icon">🏗️</div>
            <div className="docs-title">Architecture</div>
            <div className="docs-desc">Storage tiers and design decisions</div>
          </a>
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <h2 className="card-title">About EntitySpine</h2>
        </div>
        <p style={{ marginBottom: '16px', lineHeight: '1.6' }}>
          EntitySpine is a zero-dependency entity resolution library built for SEC data.
          It helps you map entities across different identifier schemes, build corporate
          hierarchies, and create knowledge graphs.
        </p>
        <ul style={{ lineHeight: '1.8', color: 'var(--text-muted)' }}>
          <li>🔍 Entity Resolution - Match entities across data sources</li>
          <li>🏢 SEC Foundation - Built on free, public SEC data</li>
          <li>🔗 Identifier Crosswalks - CIK, LEI, TICKER, CUSIP, ISIN support</li>
          <li>🕸️ Knowledge Graphs - Model corporate networks and relationships</li>
          <li>📊 Tiered Storage - JSON → SQLite → PostgreSQL → Neo4j</li>
          <li>⚡ Zero Dependencies - stdlib-only for core functionality</li>
        </ul>
      </div>
    </div>
  );
};

export default Documentation;
