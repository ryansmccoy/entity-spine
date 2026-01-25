/**
 * React hooks for EntitySpine API
 */

import { useState, useEffect, useCallback } from 'react';
import { 
  api, 
  EntityResponse, 
  ResolutionResponse, 
  NetworkResponse,
  SearchResponse,
  checkAPIConnection,
} from './api';

// Hook to check API connection status
export function useAPIStatus() {
  const [connected, setConnected] = useState<boolean | null>(null);
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    checkAPIConnection()
      .then(setConnected)
      .finally(() => setChecking(false));
  }, []);

  const recheck = useCallback(async () => {
    setChecking(true);
    const status = await checkAPIConnection();
    setConnected(status);
    setChecking(false);
  }, []);

  return { connected, checking, recheck };
}

// Hook for entity resolution
export function useResolve(query: string | null) {
  const [data, setData] = useState<ResolutionResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.resolve(query)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [query]);

  return { data, loading, error };
}

// Hook for entity search
export function useSearch(query: string | null, options?: { limit?: number }) {
  const [data, setData] = useState<SearchResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!query || query.length < 2) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.search(query, options)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [query, options?.limit]);

  return { data, loading, error };
}

// Hook for entity by ID
export function useEntity(entityId: string | null) {
  const [data, setData] = useState<EntityResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!entityId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.getEntityById(entityId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [entityId]);

  return { data, loading, error };
}

// Hook for entity network/graph
export function useEntityNetwork(entityId: string | null, maxDepth: number = 2) {
  const [data, setData] = useState<NetworkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!entityId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.getNetwork(entityId, maxDepth)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [entityId, maxDepth]);

  return { data, loading, error };
}

// Hook for subsidiaries
export function useSubsidiaries(entityId: string | null) {
  const [data, setData] = useState<{ subsidiaries: Array<{ id: string; name: string; type: string }>; count: number } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!entityId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.getSubsidiaries(entityId)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [entityId]);

  return { data, loading, error };
}

// Hook for officers
export function useOfficers(entityId: string | null, currentOnly: boolean = true) {
  const [data, setData] = useState<{
    officers: Array<{
      id: string;
      name: string;
      title: string | null;
      role_type: string;
      is_current: boolean;
    }>;
    count: number;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!entityId) {
      setData(null);
      return;
    }

    setLoading(true);
    setError(null);

    api.getOfficers(entityId, currentOnly)
      .then(setData)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [entityId, currentOnly]);

  return { data, loading, error };
}

// Combined hook for full entity profile with relationships
export function useEntityProfile(identifier: string | null) {
  const resolution = useResolve(identifier);
  const entityId = resolution.data?.entity?.entity_id || null;
  const network = useEntityNetwork(entityId);
  const subsidiaries = useSubsidiaries(entityId);
  const officers = useOfficers(entityId);

  return {
    entity: resolution.data?.entity || null,
    resolution: resolution.data,
    network: network.data,
    subsidiaries: subsidiaries.data?.subsidiaries || [],
    officers: officers.data?.officers || [],
    loading: resolution.loading || network.loading || subsidiaries.loading || officers.loading,
    error: resolution.error || network.error || subsidiaries.error || officers.error,
  };
}
