import { create } from "zustand";
import {
  AssignmentOverlayResponse,
  AuthTokens,
  Candle,
  CryptoSymbol,
  CurrentUser,
  ExchangeId,
  PairStrategyAssignment,
  SignalAnalysisResponse,
  TradeResponse,
  UserOverview
} from "../types/trading";
import { generateCandles } from "../utils/format";

const ACCESS_TOKEN_KEY = "btc.accessToken";
const REFRESH_TOKEN_KEY = "btc.refreshToken";

const readStoredAccessToken = () => {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(ACCESS_TOKEN_KEY) ?? "";
};

const readStoredRefreshToken = () => {
  if (typeof window === "undefined") {
    return "";
  }
  return window.localStorage.getItem(REFRESH_TOKEN_KEY) ?? "";
};

const persistTokens = (tokens: AuthTokens | null) => {
  if (typeof window === "undefined") {
    return;
  }
  if (tokens === null) {
    window.localStorage.removeItem(ACCESS_TOKEN_KEY);
    window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    return;
  }
  window.localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
  window.localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
};

interface TradingState {
  exchange: ExchangeId;
  selectedCrypto: CryptoSymbol;
  candles: Candle[];
  overlay: AssignmentOverlayResponse | null;
  accessToken: string;
  refreshToken: string;
  currentUser: CurrentUser | null;
  overview: UserOverview | null;
  assignments: PairStrategyAssignment[];
  selectedAssignmentId: number | null;
  lastScan: SignalAnalysisResponse | null;
  lastTrade: TradeResponse | null;
  trades: TradeResponse[];
  setExchange: (exchange: ExchangeId) => void;
  setSelectedCrypto: (crypto: CryptoSymbol) => void;
  setCandles: (candles: Candle[]) => void;
  setOverlay: (overlay: AssignmentOverlayResponse | null) => void;
  setSession: (tokens: AuthTokens, user: CurrentUser) => void;
  clearSession: () => void;
  setOverview: (overview: UserOverview | null) => void;
  setAssignments: (assignments: PairStrategyAssignment[]) => void;
  setSelectedAssignmentId: (assignmentId: number | null) => void;
  setLastScan: (analysis: SignalAnalysisResponse | null) => void;
  setLastTrade: (trade: TradeResponse | null) => void;
  setTrades: (trades: TradeResponse[]) => void;
}

export const useTradingStore = create<TradingState>((set, get) => ({
  exchange: "binance",
  selectedCrypto: "BTC",
  candles: generateCandles(500),
  overlay: null,
  accessToken: readStoredAccessToken(),
  refreshToken: readStoredRefreshToken(),
  currentUser: null,
  overview: null,
  assignments: [],
  selectedAssignmentId: null,
  lastScan: null,
  lastTrade: null,
  trades: [],
  setExchange: (exchange) => set({ exchange }),
  setSelectedCrypto: (selectedCrypto) => set({ selectedCrypto }),
  setCandles: (candles) => set({ candles }),
  setOverlay: (overlay) => set({ overlay }),
  setSession: (tokens, user) => {
    persistTokens(tokens);
    set({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token,
      currentUser: user
    });
  },
  clearSession: () => {
    persistTokens(null);
    set({
      accessToken: "",
      refreshToken: "",
      currentUser: null,
      overview: null,
      assignments: [],
      selectedAssignmentId: null,
      overlay: null,
      lastScan: null,
      lastTrade: null,
      trades: []
    });
  },
  setOverview: (overview) => set({ overview }),
  setAssignments: (assignments) => {
    const activeAssignments = assignments.filter((item) => item.is_active);
    const nextAssignments = activeAssignments.length > 0 ? activeAssignments : assignments;
    const currentSelectedId = get().selectedAssignmentId;
    const fallbackAssignment = nextAssignments[0] ?? null;
    const selectedAssignment = nextAssignments.find((item) => item.id === currentSelectedId) ?? fallbackAssignment;

    set({
      assignments: nextAssignments,
      selectedAssignmentId: selectedAssignment?.id ?? null,
      exchange: selectedAssignment?.exchange ?? get().exchange,
      selectedCrypto: selectedAssignment?.symbol ?? get().selectedCrypto
    });
  },
  setSelectedAssignmentId: (selectedAssignmentId) => {
    const selectedAssignment = get().assignments.find((item) => item.id === selectedAssignmentId) ?? null;
    set({
      selectedAssignmentId,
      exchange: selectedAssignment?.exchange ?? get().exchange,
      selectedCrypto: selectedAssignment?.symbol ?? get().selectedCrypto,
      overlay: null,
      lastScan: null,
      lastTrade: null
    });
  },
  setLastScan: (lastScan) => set({ lastScan }),
  setLastTrade: (lastTrade) => set({ lastTrade }),
  setTrades: (trades) => set({ trades })
}));
