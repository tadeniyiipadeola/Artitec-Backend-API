/**
 * Custom React hook for fetching available communities
 * Step 2: Fetch communities when the form loads
 */
import { useState, useEffect } from 'react';

export interface Community {
  community_id: string;
  name: string;
  city: string;
  state: string;
  property_count: number;
  active_status: string;
}

interface UseCommunities {
  communities: Community[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
}

export function useCommunities(accessToken: string | null): UseCommunities {
  const [communities, setCommunities] = useState<Community[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchCommunities = async () => {
    if (!accessToken) {
      setError('No access token provided');
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch('/v1/admin/communities/available', {
        headers: {
          'Authorization': `Bearer ${accessToken}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        if (response.status === 403) {
          throw new Error('Access denied. Admin privileges required.');
        }
        throw new Error(`Failed to fetch communities: ${response.statusText}`);
      }

      const data: Community[] = await response.json();
      setCommunities(data);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Unknown error occurred';
      setError(errorMessage);
      console.error('Error fetching communities:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCommunities();
  }, [accessToken]);

  return {
    communities,
    loading,
    error,
    refetch: fetchCommunities,
  };
}
