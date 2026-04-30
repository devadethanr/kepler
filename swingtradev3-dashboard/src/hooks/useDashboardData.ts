import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { connectLiveEvents } from '@/lib/sse';
import type { DashboardEvent } from '@/lib/schemas';

export const queryKeys = {
  health: ['health'] as const,
  safety: ['safety'] as const,
  snapshot: ['dashboard', 'snapshot'] as const,
  events: ['dashboard', 'events'] as const,
  execution: ['dashboard', 'execution'] as const,
  quotes: ['dashboard', 'quotes'] as const,
  broker: ['dashboard', 'broker'] as const,
  telemetry: ['dashboard', 'telemetry'] as const,
  approvals: ['approvals'] as const,
  positions: ['positions'] as const,
  trades: ['trades'] as const,
  portfolio: ['portfolio', 'summary'] as const,
  scanStatus: ['scan', 'status'] as const,
};

export function useHealth() {
  return useQuery({
    queryKey: queryKeys.health,
    queryFn: ({ signal }) => api.health(signal),
    refetchInterval: 30_000,
  });
}

export function useSafety() {
  return useQuery({
    queryKey: queryKeys.safety,
    queryFn: ({ signal }) => api.safety(signal),
    refetchInterval: 15_000,
  });
}

export function useDashboardSnapshot() {
  return useQuery({
    queryKey: queryKeys.snapshot,
    queryFn: ({ signal }) => api.snapshot(signal),
    refetchInterval: 10_000,
  });
}

export function useDashboardEvents(limit = 50) {
  return useQuery({
    queryKey: [...queryKeys.events, limit],
    queryFn: ({ signal }) => api.events(limit, undefined, signal),
    refetchInterval: 10_000,
  });
}

export function useExecutionDashboard() {
  return useQuery({
    queryKey: queryKeys.execution,
    queryFn: ({ signal }) => api.execution(signal),
    refetchInterval: 10_000,
  });
}

export function useQuotes() {
  return useQuery({
    queryKey: queryKeys.quotes,
    queryFn: ({ signal }) => api.quotes(signal),
    refetchInterval: 5_000,
  });
}

export function useBrokerDashboard() {
  return useQuery({
    queryKey: queryKeys.broker,
    queryFn: ({ signal }) => api.broker(signal),
    refetchInterval: 15_000,
  });
}

export function useTelemetry() {
  return useQuery({
    queryKey: queryKeys.telemetry,
    queryFn: ({ signal }) => api.telemetry(signal),
    refetchInterval: 15_000,
  });
}

export function useApprovals() {
  return useQuery({
    queryKey: queryKeys.approvals,
    queryFn: ({ signal }) => api.approvals(signal),
    refetchInterval: 10_000,
  });
}

export function usePositions() {
  return useQuery({
    queryKey: queryKeys.positions,
    queryFn: ({ signal }) => api.positions(signal),
    refetchInterval: 10_000,
  });
}

export function useTrades() {
  return useQuery({
    queryKey: queryKeys.trades,
    queryFn: ({ signal }) => api.trades(signal),
    refetchInterval: 30_000,
  });
}

export function useScanStatus() {
  return useQuery({
    queryKey: queryKeys.scanStatus,
    queryFn: ({ signal }) => api.scanStatus(signal),
    refetchInterval: 5_000,
  });
}

export function useApprovalActions() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.approvals });
    void queryClient.invalidateQueries({ queryKey: queryKeys.snapshot });
    void queryClient.invalidateQueries({ queryKey: queryKeys.execution });
  };
  return {
    approve: useMutation({ mutationFn: api.approve, onSuccess: invalidate }),
    reject: useMutation({ mutationFn: api.reject, onSuccess: invalidate }),
  };
}

export function useControlActions() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: queryKeys.safety });
    void queryClient.invalidateQueries({ queryKey: queryKeys.snapshot });
  };
  return {
    updateMode: useMutation({ mutationFn: api.updateMode, onSuccess: invalidate }),
    flatten: useMutation({ mutationFn: api.flatten, onSuccess: invalidate }),
    clearFlatten: useMutation({ mutationFn: api.clearFlatten, onSuccess: invalidate }),
    clearBlock: useMutation({ mutationFn: api.clearBlock, onSuccess: invalidate }),
  };
}

export function useLiveEvents() {
  const queryClient = useQueryClient();
  const [events, setEvents] = useState<DashboardEvent[]>([]);
  const [cursor, setCursor] = useState<number | null>(null);
  const [status, setStatus] = useState<'connecting' | 'live' | 'error'>('connecting');

  useEffect(() => {
    const controller = new AbortController();
    void connectLiveEvents({
      afterId: cursor,
      signal: controller.signal,
      onEvent(event) {
        if (event.type === 'ready' || event.type === 'heartbeat') {
          setCursor(event.cursor);
          setStatus('live');
          return;
        }
        setStatus('live');
        setCursor(event.event.event_id);
        setEvents((current) => [event.event, ...current].slice(0, 100));
        void queryClient.invalidateQueries({ queryKey: queryKeys.snapshot });
        void queryClient.invalidateQueries({ queryKey: queryKeys.execution });
      },
      onError() {
        setStatus('error');
      },
    });
    return () => controller.abort();
  }, [queryClient]);

  return { events, cursor, status };
}
