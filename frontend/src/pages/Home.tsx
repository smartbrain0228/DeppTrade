import { useMemo } from "react";
import DashboardHeader from "../components/DashboardHeader";
import AdminDashboard from "../components/AdminDashboard";
import DashboardSidebar from "../components/DashboardSidebar";
import LoginForm from "../components/LoginForm";
import TradeActivityPanel from "../components/TradeActivityPanel";
import TradingWorkspacePanel from "../components/TradingWorkspacePanel";
import { useTradingDashboard } from "../hooks/useTradingDashboard";

const Home = () => {
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
    isLoading,
    error,
    overlayError,
    authError,
    overviewError,
    signalError,
    signalSuccessMessage,
    actionLog,
    tradeError,
    isAuthenticating,
    isBootstrappingSession,
    isOverviewLoading,
    isOverlayLoading,
    isSignalBusy,
    isTradeLoading,
    lastOverviewUpdatedAt,
    lastTradesUpdatedAt,
    lastOverlayUpdatedAt,
    lastScanAt,
    lastExecuteAt,
    lastActionRefreshTargets,
    lastActionRefreshAt,
    tradeStatusFilter,
    clearSession,
    handleLogin,
    handleScan,
    handleExecute,
    refreshOverview,
    refreshTrades,
    setTradeStatusFilter
  } = useTradingDashboard();

  const headerLabel = useMemo(() => {
    if (selectedAssignmentId == null) {
      return "Connecte-toi puis choisis un assignment pour piloter le chart.";
    }
    return `Assignment ${selectedAssignmentId} | ${selectedCrypto} sur ${exchange.toUpperCase()}.`;
  }, [exchange, selectedAssignmentId, selectedCrypto]);

  const lastCandle = candles[candles.length - 1];
  const firstCandle = candles[0];
  const price = lastCandle?.close ?? 0;
  const change = firstCandle ? ((price - firstCandle.open) / firstCandle.open) * 100 : 0;
  const selectedAssignment = assignments.find((assignment) => assignment.id === selectedAssignmentId) ?? null;

  if (accessToken && currentUser === null && isBootstrappingSession) {
    return (
      <div className="auth-shell">
        <div className="auth-stage" />
        <div className="auth-card text-center">
          <h1 className="h4 fw-bold mb-2">Reconnexion en cours</h1>
          <p className="text-muted mb-0">Validation de la session et chargement de tes donnees.</p>
        </div>
      </div>
    );
  }

  if (!accessToken || currentUser === null) {
    return <LoginForm isLoading={isAuthenticating} error={authError} onSubmit={handleLogin} />;
  }

  return (
    <div className="app-shell">
      <div className="app-backdrop" />
      <div className="container app-container">
        <DashboardHeader
          username={currentUser.username}
          headerLabel={headerLabel}
          authError={authError}
          onLogout={clearSession}
        />

        <div className="row g-4">
          <div className="col-lg-8 d-grid gap-4">
            {accessToken && <AdminDashboard token={accessToken} />}
            <TradingWorkspacePanel
              selectedCrypto={selectedCrypto}
              selectedAssignmentId={selectedAssignmentId}
              selectedAssignment={selectedAssignment}
              assignmentsCount={assignments.length}
              price={price}
              change={change}
              isLoading={isLoading}
              error={error}
              overlayError={overlayError}
              isOverlayLoading={isOverlayLoading}
              isSignalBusy={isSignalBusy}
              signalError={signalError}
              signalSuccessMessage={signalSuccessMessage}
              actionLog={actionLog}
              lastActionRefreshTargets={lastActionRefreshTargets}
              lastActionRefreshAt={lastActionRefreshAt}
              lastScan={lastScan}
              lastTrade={lastTrade}
              lastOverlayUpdatedAt={lastOverlayUpdatedAt}
              lastScanAt={lastScanAt}
              lastExecuteAt={lastExecuteAt}
              overlay={overlay}
              onScan={handleScan}
              onExecute={handleExecute}
            />
            <TradeActivityPanel
              isLoading={isTradeLoading}
              error={tradeError}
              trades={trades}
              statusFilter={tradeStatusFilter ?? "ALL"}
              hasAssignments={assignments.length > 0}
              lastUpdatedAt={lastTradesUpdatedAt}
              wasRefreshedByAction={lastActionRefreshTargets.includes("trades")}
              onRefresh={refreshTrades}
              onStatusChange={(status) => {
                const nextStatus = status === "ALL" ? undefined : status;
                setTradeStatusFilter(nextStatus);
                void refreshTrades(nextStatus);
              }}
            />
          </div>
          <DashboardSidebar
            overview={overview}
            isOverviewLoading={isOverviewLoading}
            overviewError={overviewError}
            lastOverviewUpdatedAt={lastOverviewUpdatedAt}
            overviewWasRefreshedByAction={lastActionRefreshTargets.includes("overview")}
            onRefreshOverview={refreshOverview}
          />
        </div>
      </div>
    </div>
  );
};

export default Home;
