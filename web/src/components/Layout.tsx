import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import './Layout.css';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path ? 'active' : '';
  };

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="sidebar-header">
          <h1 className="logo">EntitySpine</h1>
          <p className="logo-subtitle">Knowledge Graph Explorer</p>
        </div>

        <nav className="nav">
          <Link to="/" className={`nav-item ${isActive('/')}`}>
            <span className="nav-icon">📊</span>
            <span className="nav-label">Dashboard</span>
          </Link>

          <Link to="/search" className={`nav-item ${isActive('/search')}`}>
            <span className="nav-icon">🔍</span>
            <span className="nav-label">Search</span>
          </Link>

          <Link to="/graph" className={`nav-item ${isActive('/graph')}`}>
            <span className="nav-icon">🕸️</span>
            <span className="nav-label">Knowledge Graph</span>
          </Link>

          <Link to="/database" className={`nav-item ${isActive('/database')}`}>
            <span className="nav-icon">💾</span>
            <span className="nav-label">Database</span>
          </Link>

          <div className="nav-divider"></div>

          <Link to="/docs" className={`nav-item ${isActive('/docs')}`}>
            <span className="nav-icon">📚</span>
            <span className="nav-label">Documentation</span>
          </Link>

          <a
            href={process.env.REACT_APP_DOCS_URL || 'http://localhost:8001'}
            target="_blank"
            rel="noopener noreferrer"
            className="nav-item"
          >
            <span className="nav-icon">📖</span>
            <span className="nav-label">API Docs</span>
            <span className="external-icon">↗</span>
          </a>
        </nav>

        <div className="sidebar-footer">
          <div className="status-indicator">
            <div className="status-dot"></div>
            <span>API Connected</span>
          </div>
        </div>
      </aside>

      <main className="main-content">
        {children}
      </main>
    </div>
  );
};

export default Layout;
