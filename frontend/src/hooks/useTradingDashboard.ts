import { useCallback, useState } from "react";
import { useTradingStore } from "../store/useTradingStore";
import { useTradingDashboardData } from "./tradingDashboard/useTradingDashboardData";
import { useTradingDashboardSession } from "./tradingDashboard/useTradingDashboardSession";

export const useTradingDashboard = () => {
  const { clearSession } = useTradingStore();
  const [tradeStatusFilter, setTradeStatusFilter] = useState<string | undefined>(undefined);
  const [authFailureMessage, setAuthFailureMessage] = useState<string | null>(null);

  const clearAuthFailure = useCallback(() => {
    setAuthFailureMessage(null);
  }, []);

  const handleAuthFailure = useCallback((message = "Session expiree. Reconnecte-toi.") => {
    clearSession();
    setAuthFailureMessage(message);
  }, [clearSession]);

  const dashboardData = useTradingDashboardData({
    onAuthFailure: handleAuthFailure,
    tradeStatusFilter
  });

  const dashboardSession = useTradingDashboardSession({
    tradeStatusFilter,
    refreshUserData: dashboardData.refreshUserData,
    onAuthFailure: handleAuthFailure,
    onAuthSuccess: clearAuthFailure
  });

  const handleLogout = useCallback(() => {
    dashboardSession.clearAuthError();
    clearAuthFailure();
    clearSession();
  }, [clearAuthFailure, clearSession, dashboardSession]);

  const authError = dashboardSession.authError ?? authFailureMessage;

  return {
    ...dashboardData,
    authError,
    isAuthenticating: dashboardSession.isAuthenticating,
    isBootstrappingSession: dashboardSession.isBootstrappingSession,
    clearSession: handleLogout,
    handleLogin: dashboardSession.handleLogin,
    refreshOverview: dashboardData.refreshOverview,
    refreshTrades: dashboardData.refreshTrades,
    setTradeStatusFilter,
    tradeStatusFilter
  };
};
