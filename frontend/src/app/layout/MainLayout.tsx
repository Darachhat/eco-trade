import React, { useState } from 'react';
import { TopBar } from './TopBar';
import { Sidebar, NavTab } from './Sidebar';
import { StatusBar } from './StatusBar';
import { LiveWarningModal } from '../../components/common/LiveWarningModal';
import { useRealtimeStream } from '../../lib/websocket/useRealtimeStream';
import { cn } from '../../lib/utils';

interface MainLayoutProps {
  activeTab: NavTab;
  onTabChange: (tab: NavTab) => void;
  children: React.ReactNode;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  activeTab,
  onTabChange,
  children,
}) => {
  // Connect real-time WebSocket / tick simulator stream
  useRealtimeStream();

  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="h-screen w-screen flex flex-col bg-terminal-bg text-terminal-text overflow-hidden">
      {/* 1. Global Top Navigation Bar */}
      <TopBar onMenuToggle={() => setMobileMenuOpen(!mobileMenuOpen)} />

      {/* 2. Main Body Container (Sidebar + Content Workspace) */}
      <div className="flex-1 flex overflow-hidden relative">
        {/* Desktop Static Sidebar */}
        <Sidebar
          activeTab={activeTab}
          onTabChange={onTabChange}
          className="hidden lg:flex"
        />

        {/* Mobile Slide-out Drawer */}
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-40 lg:hidden flex">
            <div
              className="fixed inset-0 bg-black/70 backdrop-blur-xs"
              onClick={() => setMobileMenuOpen(false)}
            />
            <Sidebar
              activeTab={activeTab}
              onTabChange={onTabChange}
              onCloseMobile={() => setMobileMenuOpen(false)}
              className="relative z-50 w-64 shadow-2xl"
            />
          </div>
        )}

        {/* Dynamic Main Content Workspace */}
        <main className="flex-1 overflow-y-auto bg-terminal-bg relative">
          {children}
        </main>
      </div>

      {/* 3. Bottom Status Bar */}
      <StatusBar />

      {/* 4. Global Modals (Live Warning Guardrail, etc.) */}
      <LiveWarningModal />
    </div>
  );
};
