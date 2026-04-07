import {
  AssignmentOverlayResponse,
  AuthTokens,
  Candle,
  CryptoSymbol,
  CurrentUser,
  ExchangeId,
  ExecuteSignalResponse,
  PairStrategyAssignment,
  SignalAnalysisResponse,
  TradeResponse,
  UserOverview
} from "../types/trading";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (typeof window !== "undefined" ? window.location.origin : "http://localhost:8000");

export class ApiError extends Error {
  status: number;
  detail?: string;

  constructor(message: string, status: number, detail?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

const buildAuthHeaders = (token: string) => ({
  Authorization: `Bearer ${token}`
});

async function parseApiError(response: Response, fallback: string): Promise<never> {
  let message = fallback;
  let detail: string | undefined;

  try {
    const payload = (await response.json()) as { detail?: string };
    if (typeof payload.detail === "string" && payload.detail.length > 0) {
      message = payload.detail;
      detail = payload.detail;
    }
  } catch {
    // Keep the fallback when the backend did not return a JSON body.
  }

  throw new ApiError(message, response.status, detail);
}

export const isApiError = (error: unknown): error is ApiError => error instanceof ApiError;

export const isAuthError = (error: unknown): boolean => isApiError(error) && error.status === 401;

export const fetchCandles = async (
  exchange: ExchangeId,
  symbol: CryptoSymbol,
  timeframe: string,
  limit = 500,
  signal?: AbortSignal
): Promise<Candle[]> => {
  const response = await fetch(
    `${API_BASE_URL}/candles?exchange=${exchange}&symbol=${encodeURIComponent(
      symbol
    )}&timeframe=${timeframe}&limit=${limit}`,
    { signal }
  );

  if (!response.ok) {
    return parseApiError(response, "Failed to fetch candles");
  }

  return response.json();
};

export const fetchPopularCryptos = async (signal?: AbortSignal): Promise<CryptoSymbol[]> => {
  const response = await fetch(`${API_BASE_URL}/market/popular`, { signal });

  if (!response.ok) {
    return parseApiError(response, "Failed to fetch popular cryptos");
  }

  return response.json();
};

export const login = async (
  username: string,
  password: string,
  signal?: AbortSignal
): Promise<AuthTokens> => {
  const body = new URLSearchParams({ username, password });
  const response = await fetch(`${API_BASE_URL}/auth/login`, {
    method: "POST",
    signal,
    headers: {
      "Content-Type": "application/x-www-form-urlencoded"
    },
    body
  });

  if (!response.ok) {
    return parseApiError(response, "Identifiants invalides.");
  }

  return response.json();
};

export const fetchMe = async (token: string, signal?: AbortSignal): Promise<CurrentUser> => {
  const response = await fetch(`${API_BASE_URL}/auth/me`, {
    signal,
    headers: buildAuthHeaders(token)
  });

  if (!response.ok) {
    return parseApiError(response, "Session invalide.");
  }

  return response.json();
};

export const fetchMyOverview = async (token: string, signal?: AbortSignal): Promise<UserOverview> => {
  const response = await fetch(`${API_BASE_URL}/me/overview`, {
    signal,
    headers: buildAuthHeaders(token)
  });

  if (!response.ok) {
    return parseApiError(response, "Impossible de charger l'overview.");
  }

  return response.json();
};

export const fetchMyPairStrategies = async (
  token: string,
  signal?: AbortSignal
): Promise<PairStrategyAssignment[]> => {
  const response = await fetch(`${API_BASE_URL}/me/pair-strategies`, {
    signal,
    headers: buildAuthHeaders(token)
  });

  if (!response.ok) {
    return parseApiError(response, "Impossible de charger les assignments.");
  }

  return response.json();
};

export const fetchMyTrades = async (
  token: string,
  status?: string,
  signal?: AbortSignal
): Promise<TradeResponse[]> => {
  const query = status ? `?status=${encodeURIComponent(status)}` : "";
  const response = await fetch(`${API_BASE_URL}/trades${query}`, {
    signal,
    headers: buildAuthHeaders(token)
  });

  if (!response.ok) {
    return parseApiError(response, "Impossible de charger les trades.");
  }

  return response.json();
};

export const fetchAssignmentOverlay = async (
  assignmentId: number,
  token: string,
  signal?: AbortSignal
): Promise<AssignmentOverlayResponse> => {
  const response = await fetch(
    `${API_BASE_URL}/signals/assignments/${assignmentId}/overlay?offset=0&limit=20`,
    {
      signal,
      headers: buildAuthHeaders(token)
    }
  );

  if (!response.ok) {
    return parseApiError(response, "Impossible de charger l'overlay de signal.");
  }

  return response.json();
};

export const scanAssignmentSignal = async (
  assignmentId: number,
  token: string,
  signal?: AbortSignal
): Promise<SignalAnalysisResponse> => {
  const response = await fetch(`${API_BASE_URL}/signals/assignments/${assignmentId}/scan`, {
    method: "POST",
    signal,
    headers: {
      ...buildAuthHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ htf_limit: 120, ltf_limit: 240 })
  });

  if (!response.ok) {
    return parseApiError(response, "Impossible de scanner ce signal.");
  }

  return response.json();
};

export const executeAssignmentSignal = async (
  assignmentId: number,
  token: string,
  quantity: number,
  signal?: AbortSignal
): Promise<ExecuteSignalResponse> => {
  const response = await fetch(`${API_BASE_URL}/signals/assignments/${assignmentId}/execute`, {
    method: "POST",
    signal,
    headers: {
      ...buildAuthHeaders(token),
      "Content-Type": "application/json"
    },
    body: JSON.stringify({ quantity, status: "PENDING", htf_limit: 120, ltf_limit: 240 })
  });

  if (!response.ok) {
    return parseApiError(response, "Impossible d'executer ce signal.");
  }

  return response.json();
};

export interface TradeStats {
  bot_status: string;
  current_balance: number;
  initial_balance: number;
  total_trades: number;
  skipped: number;
  wins: number;
  losses: number;
  win_rate: number;
  total_pnl: number;
  strategy_id?: number;
  strategy_name?: string;
  trade_count: number;
  is_paused: boolean;
  recent_trades: Array<{
    id: number;
    pair: string;
    side: string;
    entry: number;
    exit: number;
    pnl: number;
    status: string;
    result: string;
    timestamp: string;
  }>;
  open_trades: Array<{
    id: number;
    pair: string;
    side: string;
    entry: number;
    sl: number;
    tp: number;
  }>;
}

export const fetchMultiTradeStats = async (
  token: string,
  interval = "all",
  signal?: AbortSignal
): Promise<TradeStats[]> => {
  const response = await fetch(`${API_BASE_URL}/trades/multi-stats?interval=${interval}`, {
    signal,
    headers: buildAuthHeaders(token)
  });

  if (!response.ok) {
    return parseApiError(response, "Impossible de charger les statistiques.");
  }

  return response.json();
};

export const restartStrategy = async (
  token: string,
  assignmentId: number
): Promise<void> => {
  const response = await fetch(`${API_BASE_URL}/trades/restart/${assignmentId}`, {
    method: 'POST',
    headers: buildAuthHeaders(token)
  });

  if (!response.ok) {
    return parseApiError(response, "Impossible de redemarrer la strategie.");
  }
};
