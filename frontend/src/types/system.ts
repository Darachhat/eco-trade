export type ServiceStatus = 'HEALTHY' | 'WARNING' | 'CRITICAL' | 'RUNNING' | 'DISCONNECTED';

export interface ServiceHealthItem {
  id: string;
  name: string;
  category: 'Exchange' | 'Database' | 'Cache' | 'Task Queue' | 'API Gateway';
  status: ServiceStatus;
  latencyMs: number;
  uptimePct: number;
  lastHeartbeat: string;
  details: string;
}

export interface SystemTelemetry {
  cpuUsagePct: number;
  ramUsagePct: number;
  dbPoolActive: number;
  dbPoolMax: number;
  redisMemoryMb: number;
  celeryActiveTasks: number;
  celeryQueuedTasks: number;
  wsClientsCount: number;
  fastApiRps: number;
}

export interface SystemLogEntry {
  id: string;
  timestamp: string;
  level: 'INFO' | 'WARNING' | 'ERROR' | 'DEBUG';
  service: string;
  message: string;
}

export type WSConnectionState = 'CONNECTING' | 'CONNECTED' | 'SUBSCRIBED' | 'RECONNECTING' | 'DISCONNECTED' | 'ERROR';
