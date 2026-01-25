import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Search from './pages/Search';
import KnowledgeGraph from './pages/KnowledgeGraph';
import EntityDetails from './pages/EntityDetails';
import DatabaseManager from './pages/DatabaseManager';
import Documentation from './pages/Documentation';
import './App.css';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/search" element={<Search />} />
          <Route path="/graph" element={<KnowledgeGraph />} />
          <Route path="/entity/:id" element={<EntityDetails />} />
          <Route path="/database" element={<DatabaseManager />} />
          <Route path="/docs" element={<Documentation />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
