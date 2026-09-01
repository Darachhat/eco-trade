import { create } from 'zustand';
import {
  ServiceHealthItem,
  SystemLogEntry,
  SystemTelemetry,
  WSConnectionState,
} from '../types/system';

export const SYSTEM_SERVICES: ServiceHealthItem[] = [
  { id: 'srv-bybit', name: 'Bybit Derivatives WS', category: 'Exchange', status: 'HEALTHY', latencyMs: 18, uptimePct: 99.98, lastHeartbeat: 'Just now', details: 'Linear perpetual WebSocket feed stream connected' },
  { id: 'srv-bybit-rest', name: 'Bybit Market REST API', category: 'Exchange', status: 'HEALTHY', latencyMs: 32, uptimePct: 99.95, lastHeartbeat: 'Just now', details: 'v5/market ticker and orderbook endpoints active' },
  { id: 'srv-fastapi', name: 'FastAPI Backend Core', category: 'API Gateway', status: 'HEALTHY', latencyMs: 2, uptimePct: 100.0, lastHeartbeat: 'Just now', details: 'EcoTrade ASGI server active' },
  { id: 'srv-redis', name: 'Redis Cache & Pub/Sub', category: 'Cache', status: 'HEALTHY', latencyMs: 1, uptimePct: 99.99, lastHeartbeat: 'Just now', details: 'Tick buffer & IPC message broker' },
  { id: 'srv-timescale', name: 'TimescaleDB OHLCV', category: 'Database', status: 'HEALTHY', latencyMs: 4, uptimePct: 99.99, lastHeartbeat: 'Just now', details: 'Tick archive & historical kline repository' },
  { id: 'srv-celery', name: 'Celery Model Workers', category: 'Task Queue', status: 'HEALTHY', latencyMs: 5, uptimePct: 99.94, lastHeartbeat: 'Just now', details: 'Background feature extraction & drift monitoring' },
  { id: 'srv-risk', name: 'Risk Circuit Breakers', category: 'API Gateway', status: 'HEALTHY', latencyMs: 1, uptimePct: 100.0, lastHeartbeat: 'Just now', details: 'Pre-trade position sizing & drawdown enforcement' },
];

export const SYSTEM_TELEMETRY: SystemTelemetry = {
  cpuUsagePct: 14.2,
  ramUsagePct: 38.5,
  dbPoolActive: 4,
  dbPoolMax: 20,
  redisMemoryMb: 86.4,
  celeryActiveTasks: 2,
  celeryQueuedTasks: 0,
  wsClientsCount: 1,
  fastApiRps: 18.4,
};

interface SystemState {
  services: ServiceHealthItem[];
  telemetry: SystemTelemetry;
  logs: SystemLogEntry[];
  wsState: WSConnectionState;
  setWsState: (state: WSConnectionState) => void;
  addLog: (log: Omit<SystemLogEntry, 'id' | 'timestamp'>) => void;
  updateTelemetry: (partial: Partial<SystemTelemetry>) => void;
}

export const useSystemStore = create<SystemState>((set) => ({
  services: [...SYSTEM_SERVICES],
  telemetry: { ...SYSTEM_TELEMETRY },
  logs: [
    { id: 'log-1', timestamp: new Date().toISOString(), level: 'INFO', service: 'BybitLiveClient', message: 'Connected to Bybit public market stream wss://stream.bybit.com/v5/public/linear' },
    { id: 'log-2', timestamp: new Date().toISOString(), level: 'INFO', service: 'QuantEngine', message: 'Loaded 10 AI predictive models into ensemble pipeline' },
    { id: 'log-3', timestamp: new Date().toISOString(), level: 'INFO', service: 'RiskEngine', message: 'Risk limits loaded: 3% daily loss, 6% weekly drawdown' },
  ],
  wsState: 'CONNECTED',

  setWsState: (wsState) => set({ wsState }),

  addLog: (log) =>
    set((state) => ({
      logs: [
        {
          id: `log-${Date.now()}-${Math.random()}`,
          timestamp: new Date().toISOString(),
          ...log,
        },
        ...state.logs.slice(0, 100),
      ],
    })),

  updateTelemetry: (partial) =>
    set((state) => ({ telemetry: { ...state.telemetry, ...partial } })),
}));
