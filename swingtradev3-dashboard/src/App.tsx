/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

import React, { useState } from 'react';
import { Sidebar } from './components/layout/Sidebar';
import { TopBar } from './components/layout/TopBar';
import { DashboardScreen } from './screens/DashboardScreen';
import { ExecutionScreen } from './screens/ExecutionScreen';
import { OrdersScreen } from './screens/OrdersScreen';
import { TickersScreen } from './screens/TickersScreen';
import { BrokersScreen } from './screens/BrokersScreen';
import { IncidentsScreen } from './screens/IncidentsScreen';
import { RiskScreen } from './screens/RiskScreen';
import { KnowledgeScreen } from './screens/KnowledgeScreen';
import { ControlPaneScreen } from './screens/ControlPaneScreen';
import { TelemetryScreen } from './screens/TelemetryScreen';
import { NewsScreen } from './screens/NewsScreen';
import { useLiveEvents } from './hooks/useDashboardData';

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
        {currentTab === 'dashboard' && <DashboardScreen />}
        {currentTab === 'telemetry' && <TelemetryScreen live={live} />}
        {currentTab === 'news' && <NewsScreen />}
        {currentTab === 'knowledge' && <KnowledgeScreen />}
        {currentTab === 'control_pane' && <ControlPaneScreen />}
        {currentTab === 'execution' && <ExecutionScreen />}
        {currentTab === 'orders' && <OrdersScreen />}
        {currentTab === 'tickers' && <TickersScreen />}
        {currentTab === 'brokers' && <BrokersScreen />}
        {currentTab === 'incidents' && <IncidentsScreen />}
        {currentTab === 'risk' && <RiskScreen />}
      </div>
    </div>
  );
}
