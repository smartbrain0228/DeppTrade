import { useCallback, useEffect, useState } from "react";
import {
  executeAssignmentSignal,
  fetchAssignmentOverlay,
  fetchCandles,
  fetchMyOverview,
  fetchMyPairStrategies,
  fetchMyTrades,
  isAuthError,
  scanAssignmentSignal
} from "../../services/api";
import { websocketService } from "../../services/websocket";
import { useTradingStore } from "../../store/useTradingStore";
import { OverlayItem, SignalAnalysisResponse } from "../../types/trading";
import { generateCandles } from "../../utils/format";
import { POLLING_INTERVAL_MS, RefreshOptions, getErrorMessage } from "./shared";

interface TradingDashboardDataOptions {
  onAuthFailure: (message?: string) => void;
  tradeStatusFilter?: string;
}

type ActionLogTone = "success" | "warning" | "danger" | "info";

export interface DashboardActionLogEntry {
  id: string;
  type: "SCAN" | "EXECUTE";
  tone: ActionLogTone;
  title: string;
  message: string;
  createdAt: number;
}

export type DashboardRefreshTarget = "assignments" | "overview" | "trades" | "overlay";

const buildAnalysisFromOverlay = (overlayItem: OverlayItem): SignalAnalysisResponse => ({
  strategy: overlayItem.strategy_name ?? undefined,
  timeframes: overlayItem.timeframes,
  assignment: {
    id: overlayItem.assignment_id,
    user_id: 0,
    symbol_id: 0,
    symbol: overlayItem.symbol ?? "",
    exchange: overlayItem.exchange ?? "",
    strategy_id: 0,
    strategy_name: overlayItem.strategy_name ?? "",
    risk_pct: 0,
    max_trades_per_day: 0
  },
  htf_bias: {
    value: overlayItem.htf_bias
  },
  signal: {
    status: overlayItem.signal_status,
    reason: overlayItem.signal_reason,
    side: overlayItem.side,
    trade_plan:
      overlayItem.trade_plan && typeof overlayItem.trade_plan === "object"
        ? (overlayItem.trade_plan as SignalAnalysisResponse["signal"]["trade_plan"])
        : null
  }
});

const getScanFeedbackMessage = (analysis: SignalAnalysisResponse) => {
  if (analysis.signal.status === "READY") {
    return "Scan termine: setup pret a l'execution.";
  }

  return `Scan termine: setup ${analysis.signal.status}, execution en attente.`;
};

export const useTradingDashboardData = ({
  onAuthFailure,
  tradeStatusFilter
}: TradingDashboardDataOptions) => {
  const {
    accessToken,
    assignments,
    currentUser,
    overview,
    exchange,
    selectedCrypto,
    candles,
    overlay,
    selectedAssignmentId,
    lastScan,
    lastTrade,
    trades,
    setAssignments,
    setCandles,
    setOverlay,
    setOverview,
    setLastScan,
    setLastTrade,
    setTrades
  } = useTradingStore();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [overlayError, setOverlayError] = useState<string | null>(null);
  const [overviewError, setOverviewError] = useState<string | null>(null);
  const [signalError, setSignalError] = useState<string | null>(null);
  const [signalSuccessMessage, setSignalSuccessMessage] = useState<string | null>(null);
  const [tradeError, setTradeError] = useState<string | null>(null);
  const [isOverviewLoading, setIsOverviewLoading] = useState(false);
  const [isOverlayLoading, setIsOverlayLoading] = useState(false);
  const [isSignalBusy, setIsSignalBusy] = useState(false);
  const [isTradeLoading, setIsTradeLoading] = useState(false);
  const [lastOverviewUpdatedAt, setLastOverviewUpdatedAt] = useState<number | null>(null);
  const [lastTradesUpdatedAt, setLastTradesUpdatedAt] = useState<number | null>(null);
  const [lastOverlayUpdatedAt, setLastOverlayUpdatedAt] = useState<number | null>(null);
  const [lastScanAt, setLastScanAt] = useState<number | null>(null);
  const [lastExecuteAt, setLastExecuteAt] = useState<number | null>(null);
  const [actionLog, setActionLog] = useState<DashboardActionLogEntry[]>([]);
  const [lastActionRefreshTargets, setLastActionRefreshTargets] = useState<DashboardRefreshTarget[]>([]);
  const [lastActionRefreshAt, setLastActionRefreshAt] = useState<number | null>(null);

  const pushActionLog = useCallback((entry: Omit<DashboardActionLogEntry, "id" | "createdAt">) => {
    setActionLog((current) => [
      {
        ...entry,
        id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
        createdAt: Date.now()
      },
      ...current
    ].slice(0, 6));
  }, []);

  const refreshUserData = useCallback(async ({
    includeAssignments = false,
    includeOverview = false,
    includeTrades = false,
    includeOverlay = false,
    tradeStatus,
    silent = false,
    signal,
    token
  }: RefreshOptions = {}) => {
    const sessionToken = token ?? accessToken;
    if (!sessionToken) {
      return;
    }

    if (includeOverview && !silent) {
      setIsOverviewLoading(true);
    }
    if (includeTrades && !silent) {
      setIsTradeLoading(true);
    }
    if (includeOverlay && !silent) {
      setIsOverlayLoading(true);
    }

    try {
      const tasks: Promise<void>[] = [];

      if (includeAssignments) {
        tasks.push(
          (async () => {
            try {
              const userAssignments = await fetchMyPairStrategies(sessionToken, signal);
              setAssignments(userAssignments);
            } catch (loadError) {
              if (signal?.aborted) {
                return;
              }
              if (isAuthError(loadError)) {
                throw loadError;
              }
            }
          })()
        );
      }

      if (includeOverview) {
        tasks.push(
          (async () => {
            try {
              const userOverview = await fetchMyOverview(sessionToken, signal);
              setOverview(userOverview);
              setOverviewError(null);
              setLastOverviewUpdatedAt(Date.now());
            } catch (loadError) {
              if (signal?.aborted) {
                return;
              }
              if (isAuthError(loadError)) {
                throw loadError;
              }
              setOverviewError(getErrorMessage(loadError, "Impossible de charger l'overview."));
            }
          })()
        );
      }

      if (includeTrades) {
        tasks.push(
          (async () => {
            try {
              const userTrades = await fetchMyTrades(sessionToken, tradeStatus, signal);
              setTrades(userTrades);
              setTradeError(null);
              setLastTradesUpdatedAt(Date.now());
            } catch (loadError) {
              if (signal?.aborted) {
                return;
              }
              if (isAuthError(loadError)) {
                throw loadError;
              }
              setTradeError(getErrorMessage(loadError, "Impossible de charger les trades."));
            }
          })()
        );
      }

      if (includeOverlay) {
        tasks.push(
          (async () => {
            if (selectedAssignmentId == null) {
              setOverlay(null);
              setOverlayError(null);
              return;
            }
            try {
              const data = await fetchAssignmentOverlay(selectedAssignmentId, sessionToken, signal);
              setOverlay(data);
              setOverlayError(null);
              setLastOverlayUpdatedAt(Date.now());
            } catch (loadError) {
              if (signal?.aborted) {
                return;
              }
              if (isAuthError(loadError)) {
                throw loadError;
              }
              setOverlay(null);
              setOverlayError(
                getErrorMessage(loadError, "Impossible de charger les overlays de signal pour cet assignment.")
              );
            }
          })()
        );
      }

      await Promise.all(tasks);
    } catch (loadError) {
      if (!signal?.aborted && isAuthError(loadError)) {
        onAuthFailure("Session expiree ou invalide. Reconnecte-toi.");
      }
    } finally {
      if (includeOverview && !silent) {
        setIsOverviewLoading(false);
      }
      if (includeTrades && !silent) {
        setIsTradeLoading(false);
      }
      if (includeOverlay && !silent) {
        setIsOverlayLoading(false);
      }
    }
  }, [
    accessToken,
    onAuthFailure,
    selectedAssignmentId,
    setAssignments,
    setOverview,
    setOverlay,
    setTrades
  ]);

  const refreshOverview = async () => {
    await refreshUserData({ includeOverview: true });
  };

  const refreshTrades = async (status?: string) => {
    const nextStatus = status === undefined ? tradeStatusFilter : status;
    await refreshUserData({ includeTrades: true, tradeStatus: nextStatus });
  };

  useEffect(() => {
    setSignalError(null);
    setSignalSuccessMessage(null);
    setActionLog([]);
    setLastActionRefreshTargets([]);
    setLastActionRefreshAt(null);
  }, [selectedAssignmentId]);

  useEffect(() => {
    if (!signalSuccessMessage) {
      return;
    }

    const timeoutId = window.setTimeout(() => {
      setSignalSuccessMessage(null);
    }, 5000);

    return () => window.clearTimeout(timeoutId);
  }, [signalSuccessMessage]);

  useEffect(() => {
    if (selectedAssignmentId == null || !accessToken || currentUser === null) {
      setOverlay(null);
      setOverlayError(null);
      setLastScan(null);
      setLastTrade(null);
      setLastScanAt(null);
      setLastExecuteAt(null);
      return;
    }

    const controller = new AbortController();
    void refreshUserData({ includeOverlay: true, signal: controller.signal });

    return () => controller.abort();
  }, [accessToken, currentUser, refreshUserData, selectedAssignmentId, setLastScan, setLastTrade, setOverlay]);

  useEffect(() => {
    const latestOverlay = overlay?.latest;
    if (!latestOverlay) {
      return;
    }

    setLastScan(buildAnalysisFromOverlay(latestOverlay));

    const createdAt = Date.parse(latestOverlay.created_at);
    if (!Number.isNaN(createdAt)) {
      setLastScanAt(createdAt);
      if (latestOverlay.trigger === "EXECUTE") {
        setLastExecuteAt(createdAt);
      }
    }
  }, [overlay, setLastScan]);

  useEffect(() => {
    let isMounted = true;
    const controller = new AbortController();

    const loadCandles = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await fetchCandles(exchange, selectedCrypto, "H1", 500, controller.signal);
        if (isMounted) {
          setCandles(data);
        }
      } catch {
        if (controller.signal.aborted) {
          return;
        }
        if (isMounted) {
          setError("Impossible de charger les donnees. Affichage des donnees locales.");
          // On ne génère des bougies que si on n'en a pas déjà
          if (candles.length === 0) {
            setCandles(generateCandles(500));
          }
        }
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadCandles();

    return () => {
      isMounted = false;
      controller.abort();
    };
  }, [exchange, selectedCrypto, setCandles]); // Retiré selectedAssignmentId

  useEffect(() => {
    let isMounted = true;

    websocketService
      .subscribeCandles(exchange, selectedCrypto, (data) => {
        if (isMounted) {
          setCandles(data);
        }
      })
      .catch(() => {
        if (isMounted) {
          setError("Flux temps reel indisponible. Donnees REST uniquement.");
        }
      });

    return () => {
      isMounted = false;
      websocketService.disconnect();
    };
  }, [exchange, selectedCrypto, setCandles]); // Retiré selectedAssignmentId

  useEffect(() => {
    if (!accessToken || currentUser === null) {
      return;
    }

    const intervalId = window.setInterval(() => {
      if (document.visibilityState !== "visible") {
        return;
      }

      void refreshUserData({
        includeOverview: true,
        includeTrades: true,
        includeOverlay: selectedAssignmentId != null,
        tradeStatus: tradeStatusFilter,
        silent: true
      });
    }, POLLING_INTERVAL_MS);

    return () => window.clearInterval(intervalId);
  }, [accessToken, currentUser, refreshUserData, selectedAssignmentId, tradeStatusFilter]);

  const handleScan = async () => {
    if (!accessToken || selectedAssignmentId == null) {
      return;
    }
    setIsSignalBusy(true);
    setSignalError(null);
    setSignalSuccessMessage(null);
    try {
      const analysis = await scanAssignmentSignal(selectedAssignmentId, accessToken);
      setLastScan(analysis);
      setLastScanAt(Date.now());
      setSignalSuccessMessage(getScanFeedbackMessage(analysis));
      pushActionLog({
        type: "SCAN",
        tone: analysis.signal.status === "READY" ? "success" : "warning",
        title: analysis.signal.status === "READY" ? "Scan exploitable" : `Scan ${analysis.signal.status}`,
        message: analysis.signal.reason
      });
      await refreshUserData({ includeOverlay: true });
      setLastActionRefreshTargets(["overlay"]);
      setLastActionRefreshAt(Date.now());
    } catch (scanError) {
      if (isAuthError(scanError)) {
        onAuthFailure();
      } else {
        const message = getErrorMessage(scanError, "Scan impossible.");
        setSignalError(message);
        setSignalSuccessMessage(null);
        pushActionLog({
          type: "SCAN",
          tone: "danger",
          title: "Scan refuse",
          message
        });
      }
    } finally {
      setIsSignalBusy(false);
    }
  };

  const handleExecute = async (quantity: number) => {
    if (!accessToken || selectedAssignmentId == null) {
      return;
    }
    setIsSignalBusy(true);
    setSignalError(null);
    setSignalSuccessMessage(null);
    try {
      const result = await executeAssignmentSignal(selectedAssignmentId, accessToken, quantity);
      setLastScan(result.analysis);
      setLastTrade(result.trade);
      setLastScanAt(Date.now());
      setLastExecuteAt(Date.now());
      setSignalSuccessMessage(`Trade #${result.trade.id} cree avec statut ${result.trade.status}.`);
      pushActionLog({
        type: "EXECUTE",
        tone: "success",
        title: `Trade #${result.trade.id} cree`,
        message: `Execution acceptee avec statut ${result.trade.status}.`
      });
      await refreshUserData({
        includeAssignments: true,
        includeOverview: true,
        includeTrades: true,
        includeOverlay: true,
        tradeStatus: tradeStatusFilter
      });
      setLastActionRefreshTargets(["assignments", "overview", "trades", "overlay"]);
      setLastActionRefreshAt(Date.now());
    } catch (executeError) {
      if (isAuthError(executeError)) {
        onAuthFailure();
      } else {
        const message = getErrorMessage(executeError, "Execution impossible.");
        setSignalError(message);
        setSignalSuccessMessage(null);
        pushActionLog({
          type: "EXECUTE",
          tone: "danger",
          title: "Execution refusee",
          message
        });
      }
    } finally {
      setIsSignalBusy(false);
    }
  };

  return {
    accessToken,
    assignments,
    currentUser,
    overview,
    exchange,
    selectedCrypto,
    candles,
    overlay,
    selectedAssignmentId,
    lastScan,
    lastTrade,
    trades,
    isLoading,
    error,
    overlayError,
    overviewError,
    signalError,
    signalSuccessMessage,
    tradeError,
    isOverviewLoading,
    isOverlayLoading,
    isSignalBusy,
    isTradeLoading,
    lastOverviewUpdatedAt,
    lastTradesUpdatedAt,
    lastOverlayUpdatedAt,
    lastScanAt,
    lastExecuteAt,
    actionLog,
    lastActionRefreshTargets,
    lastActionRefreshAt,
    refreshUserData,
    refreshOverview,
    refreshTrades,
    handleScan,
    handleExecute
  };
};
