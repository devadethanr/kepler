import { motion } from 'motion/react';
import { usePositions, useQuotes } from '@/hooks/useDashboardData';
import { cn } from '@/lib/utils';

export function TickersScreen() {
  const quotesQuery = useQuotes();
  const positionsQuery = usePositions();
  const quotes = quotesQuery.data?.quotes ?? [];
  const positions = positionsQuery.data ?? [];

  return (
    <div className="flex flex-col h-full bg-surface p-4 md:p-6 overflow-hidden">
      <div className="flex justify-between items-center mb-6 shrink-0">
        <div>
          <h1 className="text-xl font-headline font-bold text-on-surface uppercase tracking-wider">Tickers Universe</h1>
          <p className="text-[12px] font-mono text-on-surface-variant mt-1">Quote read model derived from active broker-confirmed positions.</p>
        </div>
        <span className="text-[11px] font-mono text-on-surface-variant">{quotesQuery.isFetching ? 'Refreshing' : `${quotes.length} quotes`}</span>
      </div>

      <div className="flex-1 flex flex-col lg:flex-row gap-6 overflow-hidden">
        <div className="w-full lg:w-[60%] flex flex-col bg-surface-container-low border border-outline-variant/15 rounded-md overflow-hidden">
          <div className="grid grid-cols-5 text-[10px] font-headline text-on-surface-variant border-b border-outline-variant/15 bg-surface-container p-3 uppercase font-bold tracking-wider shrink-0">
            <div>Symbol</div>
            <div className="text-right">Price</div>
            <div className="text-right">State</div>
            <div className="text-right">Source</div>
            <div className="text-right">Fresh</div>
          </div>
          <div className="flex-1 overflow-auto no-scrollbar bg-surface relative p-2">
            <motion.div initial="hidden" animate="show" variants={{ hidden: { opacity: 0 }, show: { opacity: 1, transition: { staggerChildren: 0.05 } } }} className="flex flex-col gap-[2px]">
              {quotes.map((quote) => {
                const ticker = String(quote.ticker || '-');
                const stale = Boolean(quote.stale);
                const price = Number(quote.price || 0);
                return (
                  <motion.div key={ticker} variants={{ hidden: { opacity: 0, y: 10 }, show: { opacity: 1, y: 0 } }} className="grid grid-cols-5 text-[11px] font-mono items-center p-2 rounded hover:bg-surface-highest/50 border border-transparent hover:border-outline-variant/20 transition-colors">
                    <div className="font-bold text-primary">{ticker}</div>
                    <div className="text-right text-white">{price ? price.toFixed(2) : '-'}</div>
                    <div className="text-right text-on-surface-variant">{String(quote.position_state || '-')}</div>
                    <div className="text-right text-on-surface-variant">{String(quote.source || '-')}</div>
                    <div className={cn("text-right font-bold", stale ? 'text-error' : 'text-secondary')}>{stale ? 'STALE' : 'OK'}</div>
                  </motion.div>
                );
              })}
              {!quotes.length && (
                <div className="p-8 text-center text-[12px] font-mono text-on-surface-variant">{quotesQuery.isLoading ? 'Loading active position quotes...' : quotesQuery.isError ? 'Active position quotes unavailable.' : 'No active position quotes are available.'}</div>
              )}
            </motion.div>
          </div>
        </div>

        <div className="w-full lg:w-[40%] flex flex-col gap-6 overflow-hidden">
          <div className="flex-1 bg-surface-container-low border border-outline-variant/15 rounded-md flex flex-col overflow-hidden">
            <div className="border-b border-outline-variant/15 bg-surface-container p-3 shrink-0 flex justify-between items-center">
              <span className="text-[12px] font-headline text-on-surface font-bold uppercase tracking-wider">Open Position Map</span>
              <span className="text-[10px] bg-secondary/10 text-secondary border border-secondary/20 px-1.5 py-0.5 rounded font-mono">{positions.length} LIVE</span>
            </div>
            <div className="flex-1 flex flex-col p-4 gap-2 text-[11px] font-mono bg-surface overflow-auto">
              {positions.map((position) => {
                const current = position.current_price ?? position.entry_price;
                const move = ((current - position.entry_price) / position.entry_price) * 100;
                return (
                  <div key={position.ticker} className="bg-surface-lowest border border-outline-variant/15 rounded p-3">
                    <div className="flex justify-between">
                      <span className="text-primary font-bold">{position.ticker}</span>
                      <span className={move >= 0 ? 'text-secondary' : 'text-error'}>{move.toFixed(2)}%</span>
                    </div>
                    <div className="grid grid-cols-3 gap-2 mt-2 text-on-surface-variant">
                      <span>Qty {position.quantity}</span>
                      <span>Stop {position.stop_price.toFixed(2)}</span>
                      <span>Target {position.target_price.toFixed(2)}</span>
                    </div>
                  </div>
                );
              })}
              {!positions.length && <span className="text-on-surface-variant">{positionsQuery.isLoading ? 'Loading open positions...' : positionsQuery.isError ? 'Open positions unavailable.' : 'No open positions.'}</span>}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
