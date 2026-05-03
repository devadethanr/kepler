import React, { useState, useEffect } from 'react';
import {
  type LiveEventsState,
  useDashboardSnapshot,
  useHealth,
  useSafety,
} from '@/hooks/useDashboardData';

interface TopBarProps {
  onToggleSidebar?: () => void;
  live: LiveEventsState;
}

export function TopBar({ onToggleSidebar, live }: TopBarProps) {
  const [time, setTime] = useState(new Date());
  const health = useHealth();
  const safety = useSafety();
  const snapshot = useDashboardSnapshot();
  
  useEffect(() => {
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  const formatTime = (date: Date, tz: string) => {
    return date.toLocaleTimeString('en-US', { timeZone: tz, hour12: false });
  };
  const healthStatus = health.data?.status?.toUpperCase() || 'UNKNOWN';
  const mode = String(health.data?.mode || 'paper').toUpperCase();
  const auth = safety.data?.auth_session as { fresh?: boolean; age_hours?: number } | undefined;
  const authLabel = auth?.fresh === false ? 'STALE' : auth?.age_hours !== undefined ? `${auth.age_hours.toFixed(1)}H` : 'N/A';
  const openIncidents = snapshot.data?.counts.open_incidents ?? 0;

  return (
    <header className="flex justify-between items-center w-full px-4 h-12 bg-[#121317] border-b border-[#1c1e26] z-40 shrink-0 overflow-hidden">
      <div className="flex items-center gap-3 h-full w-full overflow-hidden">
        <button onClick={onToggleSidebar} className="md:hidden text-slate-400 hover:text-white transition-colors flex items-center justify-center shrink-0">
          <span className="material-symbols-outlined text-[22px]">menu</span>
        </button>
        
        <span className="text-lg font-black tracking-tighter text-primary-container shrink-0">
          <span className="hidden md:inline">KEPLER</span>
        </span>
        
        <nav className="flex items-center overflow-x-auto no-scrollbar gap-4 md:gap-6 h-full flex-1 mask-linear-fade">
          <div className="flex flex-col justify-center px-2 shrink-0 group cursor-pointer hover:bg-[#1c1e26] transition-colors border-b-2 border-transparent h-full">
            <span className="font-bold tracking-tight text-[11px] font-sans text-white">{formatTime(time, 'Asia/Kolkata')}</span>
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest leading-none">IST</span>
          </div>
          <div className="flex flex-col justify-center px-2 group cursor-pointer hover:bg-[#1c1e26] transition-colors border-b-2 border-transparent">
            <span className="font-bold tracking-tight text-[11px] font-sans text-secondary">{healthStatus}</span>
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest leading-none text-secondary/70">{mode}</span>
          </div>
          <div className="flex flex-col justify-center px-2 group cursor-pointer border-b-2 border-primary-container bg-primary-container/5 transition-colors">
            <span className="font-bold tracking-tight text-[11px] font-sans text-primary-container">{authLabel}</span>
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest leading-none text-primary-container/70">AUTH</span>
          </div>
          <div className="flex items-center gap-2 group cursor-pointer hover:bg-[#1c1e26] transition-colors border-b-2 border-transparent px-2">
             <div className="w-1.5 h-1.5 bg-secondary rounded-full animate-[pulse_2s_ease-in-out_infinite] shadow-[0_0_8px_#42e09a]"></div>
             <div className="flex flex-col justify-center">
               <span className="font-bold tracking-tight text-[11px] font-sans text-white">{live.status.toUpperCase()}</span>
               <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest leading-none">HEARTBEAT</span>
             </div>
          </div>
          <div className="flex flex-col justify-center px-2 group cursor-pointer hover:bg-[#1c1e26] transition-colors border-b-2 border-transparent">
            <span className={openIncidents > 0 ? "font-bold tracking-tight text-[11px] font-sans text-error" : "font-bold tracking-tight text-[11px] font-sans text-secondary"}>
              {openIncidents}
            </span>
            <span className="text-[9px] font-mono text-slate-500 uppercase tracking-widest leading-none">INCIDENTS</span>
          </div>
        </nav>
      </div>
      <div className="flex items-center gap-4 shrink-0 bg-[#121317] pl-2 shadow-[-10px_0_10px_#121317]">
        <span className="hidden md:block text-[11px] font-mono tabular-nums text-on-surface-variant flex gap-2">
          <span>{formatTime(time, 'UTC')}</span>
          <span className="opacity-50">UTC</span>
        </span>
        <div className="flex items-center gap-2 text-primary-container">
          <button className="hover:bg-[#1c1e26] p-1.5 rounded transition-colors flex items-center justify-center">
            <span className="material-symbols-outlined text-[18px]">notifications_active</span>
          </button>
          <button className="hover:bg-[#1c1e26] p-1.5 rounded transition-colors flex items-center justify-center">
            <span className="material-symbols-outlined text-[18px]">settings</span>
          </button>
        </div>
      </div>
    </header>
  );
}
