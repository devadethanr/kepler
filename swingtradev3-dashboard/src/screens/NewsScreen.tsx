import React from 'react';
import { cn } from '@/lib/utils';
import { useNewsDashboard } from '@/hooks/useDashboardData';
import { formatIstTime } from '@/lib/time';

export function NewsScreen() {
  const newsQuery = useNewsDashboard(150);
  const payload = newsQuery.data;
  const items = payload?.items ?? [];
  const providers = Object.values(payload?.provider_health ?? {}).sort((a, b) =>
    a.provider.localeCompare(b.provider),
  );

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-surface">
      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">
        <section className="xl:col-span-4 bg-surface-container-low rounded-md border border-outline-variant/15 overflow-hidden">
          <div className="p-3 border-b border-outline-variant/15 bg-surface-lowest flex items-center justify-between">
            <h2 className="text-[12px] font-headline font-bold text-on-surface tracking-wide uppercase">
              Provider Health
            </h2>
            <span className="text-[10px] font-mono text-on-surface-variant">
              {providers.length} sources
            </span>
          </div>
          <div className="divide-y divide-outline-variant/10">
            {(providers.length ? providers : []).map((provider) => {
              const degraded =
                provider.status === 'degraded' || Boolean(provider.last_error);
              return (
                <div key={provider.provider} className="p-3 font-mono text-[11px]">
                  <div className="flex items-center justify-between gap-3">
                    <div className="flex items-center gap-2 min-w-0">
                      <span
                        className={cn(
                          'w-2 h-2 rounded-full shrink-0',
                          degraded ? 'bg-error' : 'bg-secondary',
                        )}
                      />
                      <span className="text-white truncate">{provider.provider}</span>
                    </div>
                    <span className={degraded ? 'text-error' : 'text-secondary'}>
                      {degraded ? 'DEGRADED' : 'OK'}
                    </span>
                  </div>
                  <div className="mt-2 grid grid-cols-3 gap-2 text-on-surface-variant">
                    <span>seen {provider.items_seen}</span>
                    <span>emit {provider.items_emitted}</span>
                    <span>{provider.latency_ms ?? 0}ms</span>
                  </div>
                  {provider.last_error && (
                    <div className="mt-2 text-error truncate">{provider.last_error}</div>
                  )}
                </div>
              );
            })}
            {!providers.length && (
              <div className="p-4 text-[12px] font-mono text-on-surface-variant">
                {newsQuery.isLoading ? 'Loading news providers' : 'No provider health recorded'}
              </div>
            )}
          </div>
        </section>

        <section className="xl:col-span-8 bg-surface-container-low rounded-md border border-outline-variant/15 overflow-hidden">
          <div className="p-3 border-b border-outline-variant/15 bg-surface-lowest flex items-center justify-between">
            <h2 className="text-[12px] font-headline font-bold text-on-surface tracking-wide uppercase">
              News Audit Trail
            </h2>
            <span className="text-[10px] font-mono text-on-surface-variant">
              {payload?.item_count ?? 0} normalized items
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left font-mono text-[11px]">
              <thead className="bg-surface-high text-on-surface-variant uppercase">
                <tr>
                  <th className="px-3 py-2 font-medium">Time</th>
                  <th className="px-3 py-2 font-medium">Source</th>
                  <th className="px-3 py-2 font-medium">Ticker</th>
                  <th className="px-3 py-2 font-medium">Category</th>
                  <th className="px-3 py-2 font-medium">Headline</th>
                  <th className="px-3 py-2 font-medium">Confidence</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-outline-variant/10">
                {(items.length ? items : []).map((item, index) => (
                  <tr key={`${item.provider}-${item.url ?? index}`} className="hover:bg-surface-high">
                    <td className="px-3 py-2 text-on-surface-variant whitespace-nowrap">
                      {formatIstTime(item.published_at_ist ?? item.fetched_at_ist)}
                    </td>
                    <td className="px-3 py-2">
                      <div className="text-white">{item.provider}</div>
                      <div className="text-on-surface-variant">{item.source_type}</div>
                    </td>
                    <td className="px-3 py-2 text-primary whitespace-nowrap">
                      {item.tickers.join(', ') || '--'}
                    </td>
                    <td className="px-3 py-2 text-tertiary whitespace-nowrap">{item.category}</td>
                    <td className="px-3 py-2 min-w-[280px]">
                      <div className="text-white line-clamp-2">{item.title}</div>
                      {item.url && (
                        <a
                          href={item.url}
                          target="_blank"
                          rel="noreferrer"
                          className="text-on-surface-variant hover:text-primary truncate block"
                        >
                          {item.url}
                        </a>
                      )}
                    </td>
                    <td className="px-3 py-2 text-secondary">
                      {(item.confidence * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
                {!items.length && (
                  <tr>
                    <td colSpan={6} className="px-3 py-6 text-on-surface-variant text-center">
                      {newsQuery.isLoading ? 'Loading news audit' : 'No normalized news recorded'}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
