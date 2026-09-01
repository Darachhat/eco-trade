import React, { useState } from 'react';
import { MainLayout } from './app/layout/MainLayout';
import { NavTab } from './app/layout/Sidebar';
import { OverviewDashboard } from './views/OverviewDashboard';
import { MarketTerminal } from './views/MarketTerminal';
import { SignalCenter } from './views/SignalCenter';
import { PositionsView } from './views/PositionsView';
import { MT5ScalperView } from './views/MT5ScalperView';
import { AiIntelligenceView } from './views/AiIntelligenceView';
import { RiskCenterView } from './views/RiskCenterView';
import { BacktestTerminalView } from './views/BacktestTerminalView';
import { ResearchView } from './views/ResearchView';
import { ModelLabView } from './views/ModelLabView';
import { DriftMonitorView } from './views/DriftMonitorView';
import { TradeJournalView } from './views/TradeJournalView';
import { SystemMonitorView } from './views/SystemMonitorView';

export function App() {
  const [activeTab, setActiveTab] = useState<NavTab>('overview');

  const renderActiveView = () => {
    switch (activeTab) {
      case 'overview':
        return <OverviewDashboard />;
      case 'markets':
        return <MarketTerminal />;
      case 'signals':
        return <SignalCenter />;
      case 'positions':
        return <PositionsView />;
      case 'scalper':
        return <MT5ScalperView />;
      case 'ai':
        return <AiIntelligenceView />;
      case 'risk':
        return <RiskCenterView />;
      case 'backtest':
        return <BacktestTerminalView />;
      case 'research':
        return <ResearchView />;
      case 'model-lab':
        return <ModelLabView />;
      case 'drift':
        return <DriftMonitorView />;
      case 'journal':
        return <TradeJournalView />;
      case 'system':
        return <SystemMonitorView />;
      default:
        return <OverviewDashboard />;
    }
  };

  return (
    <MainLayout activeTab={activeTab} onTabChange={setActiveTab}>
      {renderActiveView()}
    </MainLayout>
  );
}

export default App;
