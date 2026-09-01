/**
 * Typed REST API client for EcoTrade FastAPI Backend
 */

const API_BASE_URL = '/api/v1';

export class EcoTradeApiClient {
  private static async request<T>(endpoint: string, options?: RequestInit): Promise<T> {
    try {
      const response = await fetch(`${API_BASE_URL}${endpoint}`, {
        headers: {
          'Content-Type': 'application/json',
          ...options?.headers,
        },
        ...options,
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status} ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.warn(`[EcoTrade API] Request failed for ${endpoint}:`, error);
      throw error;
    }
  }

  // Health
  static getHealth() {
    return this.request<any>('/health');
  }

  // Market
  static getTicker(symbol: string) {
    return this.request<any>(`/market/ticker/${symbol.toUpperCase()}`);
  }

  static getOrderBook(symbol: string, depth: number = 25) {
    return this.request<any>(`/market/orderbook/${symbol.toUpperCase()}?depth=${depth}`);
  }

  static getFundingRate(symbol: string) {
    return this.request<any>(`/market/funding/${symbol.toUpperCase()}`);
  }

  static getOpenInterest(symbol: string, interval: string = '1h') {
    return this.request<any>(`/market/open-interest/${symbol.toUpperCase()}?interval=${interval}`);
  }

  // Signals
  static getLatestSignals(symbol?: string, limit: number = 10) {
    const symParam = symbol ? `&symbol=${symbol.toUpperCase()}` : '';
    return this.request<any>(`/signals/latest?limit=${limit}${symParam}`);
  }

  static generateSignal(symbol: string = 'BTCUSDT', timeframe: string = '15') {
    return this.request<any>('/signals/generate', {
      method: 'POST',
      body: JSON.stringify({ symbol, timeframe }),
    });
  }

  // Performance
  static getPerformanceSummary() {
    return this.request<any>('/performance/summary');
  }

  static getModelPerformance() {
    return this.request<any>('/performance/models');
  }

  // Risk & Emergency Controls
  static getRiskStatus() {
    return this.request<any>('/risk/status');
  }

  static activateKillSwitch(reason: string = 'Frontend Manual Operator Activation') {
    return this.request<any>('/risk/kill-switch/activate', {
      method: 'POST',
      body: JSON.stringify({ reason }),
    });
  }

  static deactivateKillSwitch() {
    return this.request<any>('/risk/kill-switch/deactivate', {
      method: 'POST',
    });
  }

  // Backtest
  static runBacktest(payload: {
    symbol: string;
    timeframe: string;
    days_back?: number;
    initial_capital?: number;
    risk_per_trade?: number;
  }) {
    return this.request<any>('/backtest/run', {
      method: 'POST',
      body: JSON.stringify(payload),
    });
  }

  // Monitoring
  static getDriftStatus(symbol: string = 'BTCUSDT', timeframe: string = '15') {
    return this.request<any>(`/monitoring/drift?symbol=${symbol}&timeframe=${timeframe}`);
  }
}
