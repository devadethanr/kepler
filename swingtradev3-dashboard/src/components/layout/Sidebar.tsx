import React, { useState } from 'react';
import { cn } from '@/lib/utils';
import { AnimatePresence, motion } from 'motion/react';
import { useControlActions, useHealth } from '@/hooks/useDashboardData';

interface SidebarProps {
  currentTab: string;
  setTab: (tab: string) => void;
  isOpen?: boolean;
  onClose?: () => void;
}

export function Sidebar({ currentTab, setTab, isOpen = false, onClose }: SidebarProps) {
  const [showHealth, setShowHealth] = useState(false);
  const [showKillSwitch, setShowKillSwitch] = useState(false);
  const [killConfirm, setKillConfirm] = useState('');
  const health = useHealth();
  const actions = useControlActions();
  const serviceRows = Object.entries(health.data?.services ?? {});

  const mainNav = [
    { id: 'dashboard', label: 'Dashboard', icon: 'dashboard' },
    { id: 'telemetry', label: 'Telemetry', icon: 'account_tree' },
    { id: 'news', label: 'News', icon: 'rss_feed' },
    { id: 'knowledge', label: 'Knowledge Graph', icon: 'hub' },
    { id: 'control_pane', label: 'Control Pane', icon: 'tune' },
    { id: 'tickers', label: 'Tickers', icon: 'analytics' },
    { id: 'brokers', label: 'Brokers', icon: 'account_balance' },
    { id: 'incidents', label: 'Incidents', icon: 'emergency' },
    { id: 'orders', label: 'Orders', icon: 'receipt_long' },
    { id: 'execution', label: 'Execution', icon: 'bolt' },
    { id: 'risk', label: 'Risk', icon: 'security' },
  ];

  return (
    <>
      {isOpen && (
        <div 
          className="fixed inset-0 bg-black/60 z-40 md:hidden backdrop-blur-sm"
          onClick={onClose}
        />
      )}
      
      <nav className={cn(
        "fixed md:static inset-y-0 left-0 flex flex-col bg-[#0a0b0f] w-64 h-screen border-r border-[#1c1e26] z-50 shrink-0 transition-transform duration-300 md:translate-x-0",
        isOpen ? "translate-x-0 shadow-2xl" : "-translate-x-full"
      )}>
        <div className="px-6 py-6 border-b border-[#1c1e26]/50 flex justify-between items-center">
          <div>
            <h1 className="text-xl font-black text-white tracking-tighter">KEPLER OPS</h1>
            <p className="text-[11px] font-mono text-slate-400 mt-1">Terminal v2.4</p>
          </div>
          <button onClick={onClose} className="md:hidden text-slate-400 hover:text-white">
            <span className="material-symbols-outlined">close</span>
          </button>
        </div>
      
      <div className="flex-1 flex flex-col gap-1 px-3 py-4 overflow-y-auto">
        {mainNav.map((item) => {
          const isActive = currentTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => { setTab(item.id); if(onClose) onClose(); }}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded transition-all duration-300 text-left",
                isActive 
                  ? "bg-[#1c1e26] text-primary-container border-r-2 border-primary-container"
                  : "text-slate-400 hover:text-white hover:bg-[#1c1e26]"
              )}
            >
              <span 
                className="material-symbols-outlined text-[18px]" 
                style={{ fontVariationSettings: isActive ? "'FILL' 1" : "'FILL' 0" }}
              >
                {item.icon}
              </span>
              <span className="text-[12px] font-medium font-sans">{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="px-3 py-4 border-t border-[#1c1e26]">
        <button onClick={() => setShowHealth(true)} className="flex items-center gap-3 px-3 py-2 w-full rounded text-slate-400 hover:text-white hover:bg-[#1c1e26] transition-colors text-left mb-1">
          <span className="material-symbols-outlined text-[18px]">sensors</span>
          <span className="text-[12px] font-medium font-sans flex-1">System Health</span>
          <span className="w-1.5 h-1.5 rounded-full bg-secondary"></span>
        </button>
        <button className="flex items-center gap-3 px-3 py-2 w-full rounded text-slate-400 hover:text-white hover:bg-[#1c1e26] transition-colors text-left mb-4">
          <span className="material-symbols-outlined text-[18px]">help_outline</span>
          <span className="text-[12px] font-medium font-sans">Support</span>
        </button>
        
        <button onClick={() => setShowKillSwitch(true)} className="w-full bg-[#121317] text-error font-bold text-[12px] py-2.5 rounded uppercase tracking-widest hover:bg-error hover:text-error-container border border-error/50 transition-all flex items-center justify-center gap-2 outline outline-1 outline-transparent hover:outline-error/50">
          <span className="material-symbols-outlined text-[16px]">warning</span>
          KILL SWITCH
        </button>
      </div>

      <AnimatePresence>
        {showHealth && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050505]/80 backdrop-blur-sm">
            <motion.div 
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              className="bg-surface-container border border-outline-variant/30 w-[400px] rounded-lg shadow-2xl overflow-hidden"
            >
              <div className="bg-surface-highest px-4 py-3 border-b border-outline-variant/20 flex justify-between items-center">
                <span className="font-headline font-bold text-white uppercase tracking-wider text-[14px] flex items-center gap-2">
                  <span className="material-symbols-outlined text-secondary">sensors</span>
                  System Health Map
                </span>
                <button onClick={() => setShowHealth(false)} className="text-on-surface-variant hover:text-white"><span className="material-symbols-outlined text-[18px]">close</span></button>
              </div>
              <div className="p-5 flex flex-col gap-4 font-mono text-[12px]">
                {(serviceRows.length ? serviceRows : [['api', health.data?.status ?? 'unknown']]).map(([name, status]) => {
                  const healthy = String(status).toLowerCase().includes('healthy') || String(status).toLowerCase().includes('running') || String(status).toLowerCase() === 'ok';
                  return (
                    <div key={name} className="flex justify-between items-center bg-surface p-3 rounded border border-outline-variant/10">
                      <div className="flex gap-3 items-center">
                        <span className={cn("w-2 h-2 rounded-full", healthy ? "bg-secondary animate-pulse" : "bg-error")}></span>
                        <div className="flex flex-col">
                          <span className="text-white font-bold">{name}</span>
                          <span className="text-[10px] text-on-surface-variant">{String(status)}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          </div>
        )}

        {showKillSwitch && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center bg-[#050505]/90 backdrop-blur-md">
            <motion.div 
              initial={{ scale: 0.95, opacity: 0, y: 20 }}
              animate={{ scale: 1, opacity: 1, y: 0 }}
              exit={{ scale: 0.95, opacity: 0, y: 20 }}
              className="bg-[#1a0505] border border-error w-[480px] rounded-lg shadow-[0_0_50px_rgba(255,0,0,0.2)] overflow-hidden"
            >
              <div className="bg-error px-5 py-4 border-b border-error/50 flex justify-between items-center">
                <span className="font-headline font-bold text-error-container uppercase tracking-widest text-[16px] flex items-center gap-2">
                  <span className="material-symbols-outlined text-[24px]">warning</span>
                  RESTRICTED KILL SWITCH
                </span>
                <button onClick={() => {setShowKillSwitch(false); setKillConfirm('');}} className="text-error-container hover:text-white"><span className="material-symbols-outlined text-[20px]">close</span></button>
              </div>
              <div className="p-6 flex flex-col gap-5">
                <p className="text-[13px] font-sans text-error leading-relaxed">
                  Triggering the Kill Switch will immediately execute the following actions via the execution worker:
                </p>
                <ul className="text-[12px] font-mono text-white space-y-2 list-disc pl-5 opacity-90">
	                  <li>Disables trading and new entries through operator control flags.</li>
	                  <li>Enables exit-only mode for the execution worker.</li>
	                  <li>Persists the intervention through the FastAPI ops route.</li>
	                  <li><span className="text-error font-bold">DOES NOT</span> close existing positions (to close and exit, use FLATTEN ALL).</li>
                </ul>
                
                <div className="mt-4 pt-4 border-t border-error/20">
                   <span className="text-[11px] font-mono text-error uppercase font-bold tracking-widest mb-2 block">2-LAYER CONFIRMATION REQUIRED</span>
                   <p className="text-[11px] font-mono text-on-surface-variant mb-3">Type <b className="text-white bg-surface px-1">HALT</b> to authorize this action.</p>
                   <input 
                     type="text" 
                     value={killConfirm}
                     onChange={(e) => setKillConfirm(e.target.value)}
                     className="w-full bg-surface border border-error/50 p-3 rounded font-mono text-white text-center tracking-widest placeholder-error/30 focus:outline-none focus:ring-2 focus:ring-error"
                     placeholder="TYPE 'HALT' HERE"
                   />
                </div>
                <button 
	                  disabled={killConfirm !== 'HALT' || actions.updateMode.isPending}
	                  onClick={() => {
	                    actions.updateMode.mutate(
	                      {
	                        reason: 'dashboard kill switch',
	                        trading_enabled: false,
	                        new_entries_enabled: false,
	                        exit_only_mode: true,
	                      },
	                      {
	                        onSuccess: () => {
	                          setShowKillSwitch(false);
	                          setKillConfirm('');
	                        },
	                      },
	                    );
	                  }}
                  className="w-full bg-error disabled:bg-surface disabled:text-on-surface-variant disabled:border-outline-variant/30 disabled:cursor-not-allowed border border-error text-error-container font-black py-4 rounded tracking-widest uppercase transition-all duration-300 shadow-[0_0_20px_rgba(255,0,0,0.3)] disabled:shadow-none"
                >
                  EXECUTE KILL SWITCH
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </nav>
    </>
  );
}
