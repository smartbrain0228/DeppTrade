export type CryptoSymbol = string;

export type ExchangeId = "binance" | "mexc";

export interface Candle {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface CurrentUser {
  id: number;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface PairStrategyAssignment {
  id: number;
  symbol: string;
  exchange: ExchangeId;
  strategy_name: string;
  htf: string;
  ltf: string;
  risk_pct: number;
  max_trades_per_day: number;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface OverviewPair {
  symbol: string;
  exchange: string;
}

export interface OverviewRecentTrade {
  trade_id: number;
  tag: string;
  side: string;
  status: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  quantity: number;
  pnl: number | null;
  symbol: string;
  exchange: string;
  opened_at: string;
  closed_at: string | null;
}

export interface UserOverview {
  user_id: number;
  open_trades_count: number;
  closed_trades_count: number;
  closed_pnl: number;
  active_risk_pct: number;
  max_total_active_risk_pct: number;
  active_pairs: OverviewPair[];
  completed_pairs: OverviewPair[];
  recent_trades: OverviewRecentTrade[];
  runtime: {
    app_env: string;
    market_data_mode: string;
    worker_enabled: boolean;
    demo_engine_enabled: boolean;
    telegram_configured: boolean;
  };
}

export interface SignalTradePlan {
  side?: string;
  entry_price?: number;
  stop_loss?: number;
  take_profit?: number;
  reward_risk_ratio?: number;
}

export interface SignalAnalysisResponse {
  strategy?: string;
  timeframes?: {
    htf: string;
    ltf: string;
  };
  assignment?: {
    id: number;
    user_id: number;
    symbol_id: number;
    symbol: string;
    exchange: string;
    strategy_id: number;
    strategy_name: string;
    risk_pct: number;
    max_trades_per_day: number;
  };
  htf_bias?: {
    value: string;
    details?: Record<string, unknown>;
  };
  signal: {
    status: string;
    reason: string;
    side?: string | null;
    trade_plan?: SignalTradePlan | null;
  };
}

export interface TradeResponse {
  id: number;
  symbol: string;
  exchange: string;
  strategy_name: string;
  side: string;
  status: string;
  entry_price: number;
  stop_loss: number;
  take_profit: number;
  quantity: number;
  pnl?: number | null;
  opened_at: string;
  closed_at: string | null;
}

export interface ExecuteSignalResponse {
  analysis: SignalAnalysisResponse;
  trade: TradeResponse;
}

export interface OverlayMarker {
  kind: string;
  label: string;
  time: number | null;
  price: number | null;
  payload: Record<string, unknown>;
}

export interface OverlayZone {
  kind: string;
  lower_price: number | null;
  upper_price: number | null;
  midpoint: number | null;
}

export interface OverlayLevels {
  entry_price: number | null;
  stop_loss: number | null;
  take_profit: number | null;
}

export interface OverlayTimeline {
  bias_time: number | null;
  sweep_time: number | null;
  mss_time: number | null;
  fvg_time: number | null;
  entry_ready_time: number | null;
}

export interface OverlayItem {
  id: number;
  assignment_id: number;
  trigger: string;
  signal_status: string;
  signal_reason: string;
  side: string | null;
  htf_bias: string;
  symbol: string | null;
  exchange: string | null;
  strategy_name: string | null;
  timeframes?: {
    htf: string;
    ltf: string;
  };
  timeline: OverlayTimeline;
  markers: OverlayMarker[];
  zones: OverlayZone[];
  levels: OverlayLevels;
  trade_plan?: Record<string, unknown> | null;
  created_at: string;
}

export interface AssignmentOverlayResponse {
  assignment_id: number;
  total: number;
  count: number;
  offset: number;
  limit: number;
  latest: OverlayItem | null;
  timeline: OverlayItem[];
}
