/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { lazy, Suspense, useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { useLiveEvents } from './hooks/useDashboardData';

const DashboardScreen = lazy(() =>
  import('./screens/DashboardScreen').then((module) => ({ default: module.DashboardScreen })),
);
const ExecutionScreen = lazy(() =>
  import('./screens/ExecutionScreen').then((module) => ({ default: module.ExecutionScreen })),
);
const OrdersScreen = lazy(() =>
  import('./screens/OrdersScreen').then((module) => ({ default: module.OrdersScreen })),
);
const TickersScreen = lazy(() =>
  import('./screens/TickersScreen').then((module) => ({ default: module.TickersScreen })),
);
const BrokersScreen = lazy(() =>
  import('./screens/BrokersScreen').then((module) => ({ default: module.BrokersScreen })),
);
const IncidentsScreen = lazy(() =>
  import('./screens/IncidentsScreen').then((module) => ({ default: module.IncidentsScreen })),
);
const RiskScreen = lazy(() =>
  import('./screens/RiskScreen').then((module) => ({ default: module.RiskScreen })),
);
const KnowledgeScreen = lazy(() =>
  import('./screens/KnowledgeScreen').then((module) => ({ default: module.KnowledgeScreen })),
);
const ControlPaneScreen = lazy(() =>
  import('./screens/ControlPaneScreen').then((module) => ({ default: module.ControlPaneScreen })),
);
const TelemetryScreen = lazy(() =>
  import('./screens/TelemetryScreen').then((module) => ({ default: module.TelemetryScreen })),
);
const NewsScreen = lazy(() =>
  import('./screens/NewsScreen').then((module) => ({ default: module.NewsScreen })),
);

const ResearchDeskScreen = lazy(() =>
  import('./screens/ResearchDeskScreen').then(module => ({ default: module.ResearchDeskScreen })),
);

class ResearchErrorBoundary extends React.Component<React.PropsWithChildren, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <main className="flex-1 p-5" role="alert">
      <h1>Research Desk could not load</h1>
      <p>Reload the page to retry. Saved rooms remain available when the service reconnects.</p>
      <button onClick={() => window.location.reload()}>Reload page</button>
    </main>;
    return this.props.children;
  }
}

export default function App() {
  const [currentTab, setCurrentTab] = useState('dashboard');
  const [isSidebarOpen, setSidebarOpen] = useState(false);
  const live = useLiveEvents();

  return (
    <div className="flex h-screen w-full bg-surface text-on-surface overflow-hidden">
      <Sidebar 
        currentTab={currentTab} 
        setTab={setCurrentTab} 
        isOpen={isSidebarOpen}
        onClose={() => setSidebarOpen(false)}
      />
      <div className="flex flex-col flex-1 h-full overflow-hidden">
        <TopBar onToggleSidebar={() => setSidebarOpen(!isSidebarOpen)} live={live} />
        <Suspense fallback={<div className="flex-1 bg-surface p-5" role="status">Loading view…</div>}>
          {currentTab === 'dashboard' && <DashboardScreen />}
          {currentTab === 'telemetry' && <TelemetryScreen live={live} />}
          {currentTab === 'research' && <ResearchErrorBoundary><ResearchDeskScreen /></ResearchErrorBoundary>}
          {currentTab === 'news' && <NewsScreen />}
          {currentTab === 'knowledge' && <KnowledgeScreen />}
          {currentTab === 'control_pane' && <ControlPaneScreen />}
          {currentTab === 'execution' && <ExecutionScreen />}
          {currentTab === 'orders' && <OrdersScreen />}
          {currentTab === 'tickers' && <TickersScreen />}
          {currentTab === 'brokers' && <BrokersScreen />}
          {currentTab === 'incidents' && <IncidentsScreen />}
          {currentTab === 'risk' && <RiskScreen />}
        </Suspense>
      </div>
    </div>
  );
}
