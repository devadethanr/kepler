import { motion } from 'motion/react';
import { useBrokerDashboard, useSafety } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

export function BrokersScreen() {
  const brokerQuery = useBrokerDashboard();
  const safetyQuery = useSafety();
  const broker = brokerQuery.data;
  const auth = broker?.auth_session ?? {};
  const safetyAuth = safetyQuery.data?.auth_session as { fresh?: boolean; reason?: string; age_hours?: number } | undefined;
  const connected = Boolean(auth.runtime_session_present) && safetyAuth?.fresh === true;
  const brokerOrders = broker?.broker_orders ?? [];
  const fills = broker?.broker_fills ?? [];

  return (
    <div className="flex-1 overflow-y-auto p-4 md:p-6 bg-surface">
      <div className="mb-6 border-b border-outline-variant/15 pb-4">
        <h1 className="text-2xl font-headline font-bold text-on-surface tracking-wider uppercase">Broker Integrations</h1>
        <p className="text-[12px] font-mono text-on-surface-variant mt-1">Kite auth, order truth, and fill ingestion from Postgres.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className={cn(
            "bg-surface-container-low border rounded-md p-5 flex flex-col gap-4",
            connected ? "border-secondary/40" : "border-error/50 bg-error/5",
          )}
        >
          <div className="flex justify-between items-start">
            <div className="flex flex-col">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase">KITE</span>
              <span className="text-[14px] font-headline font-bold text-white mt-1">Zerodha Kite Connect</span>
            </div>
            <span className={cn("material-symbols-outlined text-[20px]", connected ? "text-secondary" : "text-error")}>
              {connected ? 'swap_calls' : 'warning'}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-4 mt-2 border-t border-outline-variant/10 pt-4">
            <div className="flex flex-col">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase mb-1">User</span>
              <span className="text-[14px] font-mono font-bold text-primary">{String(auth.user_id || '-')}</span>
            </div>
	            <div className="flex flex-col">
	              <span className="text-[10px] font-mono text-on-surface-variant uppercase mb-1">Access Token</span>
	              <span className="text-[14px] font-mono font-bold text-white">{auth.has_access_token ? 'PRESENT' : 'MISSING'}</span>
	            </div>
	            <div className="flex flex-col">
	              <span className="text-[10px] font-mono text-on-surface-variant uppercase mb-1">Runtime Session</span>
	              <span className="text-[14px] font-mono font-bold text-white">{auth.runtime_session_present ? 'PRESENT' : 'MISSING'}</span>
	            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase mb-1">Auth Fresh</span>
              <span className={cn("text-[11px] font-mono font-bold uppercase", safetyAuth?.fresh === false ? "text-error" : "text-secondary")}>
                {safetyAuth?.fresh === false ? 'STALE' : 'OK'}
              </span>
            </div>
            <div className="flex flex-col">
              <span className="text-[10px] font-mono text-on-surface-variant uppercase mb-1">Age</span>
              <span className="text-[14px] font-mono font-bold text-white">{safetyAuth?.age_hours?.toFixed(1) ?? '-'}h</span>
            </div>
          </div>
          <div className="mt-2 text-[10px] font-mono bg-surface p-2 rounded border border-outline-variant/10 text-on-surface-variant flex items-center justify-between">
            <span>{String(safetyAuth?.reason || 'broker session usable')}</span>
            {connected && <span className="w-1.5 h-1.5 rounded-full bg-secondary animate-pulse"></span>}
          </div>
        </motion.div>

        <div className="lg:col-span-2 bg-surface-container-low border border-outline-variant/15 rounded-md overflow-hidden">
          <div className="p-4 border-b border-outline-variant/15 bg-surface-container flex justify-between">
            <h2 className="text-[12px] font-headline font-bold uppercase">Broker Orders</h2>
            <span className="text-[10px] font-mono text-on-surface-variant">{brokerOrders.length} orders / {fills.length} fills</span>
          </div>
          <div className="p-3 overflow-auto max-h-[520px] font-mono text-[11px]">
            {brokerOrders.map((order, index) => (
              <div key={String(order.broker_order_id || index)} className="grid grid-cols-5 gap-2 p-2 rounded hover:bg-surface-highest/40 border-b border-outline-variant/10">
                <span className="text-primary font-bold">{String(order.ticker || '-')}</span>
                <span>{String(order.broker_order_id || '-')}</span>
                <span>{String(order.order_intent_id || '-')}</span>
                <span className="text-on-surface-variant">{String(order.broker_tag || '-')}</span>
                <span className="text-right text-secondary">{String(order.status || '-').toUpperCase()}</span>
              </div>
            ))}
            {!brokerOrders.length && (
              <div className="p-8 text-center text-on-surface-variant">No broker orders recorded.</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
