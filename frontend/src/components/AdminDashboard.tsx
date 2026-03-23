import React, { useEffect, useState } from "react";
import { fetchMultiTradeStats, TradeStats, restartStrategy } from "../services/api";
import { formatPrice } from "../utils/format";

interface AdminDashboardProps {
  token: string;
}

const getStrategyTone = (strategyName?: string) => {
  if ((strategyName ?? "").includes("H1_M5")) {
    return {
      family: "Scalping",
      className: "is-scalping"
    };
  }

  return {
    family: "Intraday",
    className: "is-intraday"
  };
};

const AdminDashboard: React.FC<AdminDashboardProps> = ({ token }) => {
  const [multiStats, setMultiStats] = useState<TradeStats[] | null>(null);
  const [interval, setInterval] = useState("all");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadStats = async () => {
    setLoading(true);
    try {
      const data = await fetchMultiTradeStats(token, interval);
      setMultiStats(data);
      setError(null);
    } catch {
      setError("Impossible de charger les stats.");
    } finally {
      setLoading(false);
    }
  };

  const handleRestart = async (id: number) => {
    try {
      await restartStrategy(token, id);
      void loadStats();
    } catch {
      alert("Erreur lors du redemarrage.");
    }
  };

  useEffect(() => {
    void loadStats();
    const timer = window.setInterval(() => void loadStats(), 30000);
    return () => clearInterval(timer);
  }, [token, interval]);

  if (loading && !multiStats) return <div className="p-4">Chargement des statistiques...</div>;
  if (error) return <div className="alert alert-danger m-4 dashboard-alert">{error}</div>;
  if (!multiStats || multiStats.length === 0) return null;

  return (
    <div className="admin-container d-grid gap-4 mb-4">
      <div className="admin-shell">
        <div>
          <div className="panel-heading__eyebrow">Operations</div>
          <h5 className="mb-0 fw-bold">Multi-Strategy Monitor</h5>
        </div>
        <select className="form-select form-select-sm w-auto trade-filter" value={interval} onChange={(e) => setInterval(e.target.value)}>
          <option value="1h">Last 1 hour</option>
          <option value="6h">Last 6 hours</option>
          <option value="24h">Last 24 hours</option>
          <option value="7d">Last 7 days</option>
          <option value="all">Since start</option>
        </select>
      </div>

      <div className="row g-4">
        {multiStats.map((stats) => (
          <div key={stats.strategy_id} className="col-12">
            <div className="card admin-card border-0 overflow-hidden">
              <div className="card-header admin-card__header py-3 d-flex flex-column flex-sm-row justify-content-between align-items-sm-center gap-3">
                <div>
                  <div className={`strategy-family-chip ${getStrategyTone(stats.strategy_name).className}`}>
                    {getStrategyTone(stats.strategy_name).family}
                  </div>
                  <h6 className="mb-1 fw-bold text-dark mt-2">{stats.strategy_name}</h6>
                  <div className="small text-muted">Cycle: {stats.trade_count}/50 trades</div>
                </div>
                <div className="d-flex gap-2 align-items-center">
                  {stats.is_paused ? (
                    <span className="badge bg-warning text-dark px-3 py-2">PAUSED | 50 trades reached</span>
                  ) : (
                    <span className={`badge ${stats.bot_status === "RUNNING" ? "bg-success" : "bg-secondary"} px-3 py-2`}>
                      BOT {stats.bot_status}
                    </span>
                  )}
                  {stats.is_paused && (
                    <button className="btn btn-primary btn-sm px-3 auth-submit" onClick={() => handleRestart(stats.strategy_id!)}>
                      Restart Cycle
                    </button>
                  )}
                </div>
              </div>
              <div className="card-body p-3 p-sm-4">
                <div className="row g-3 text-center mb-4">
                  <div className="col-6 col-md-3">
                    <div className="admin-metric h-100 d-flex flex-column justify-content-center">
                      <div className="text-muted small mb-1">Balance</div>
                      <div className="h5 mb-0 fw-bold text-primary">{stats.current_balance.toFixed(2)} USDT</div>
                    </div>
                  </div>
                  <div className="col-6 col-md-3">
                    <div className="admin-metric h-100 d-flex flex-column justify-content-center">
                      <div className="text-muted small mb-1">Win Rate</div>
                      <div className="h5 mb-0 fw-bold">{stats.win_rate.toFixed(1)}%</div>
                      <div className="x-small text-muted mt-1">{stats.total_trades} trades</div>
                    </div>
                  </div>
                  <div className="col-6 col-md-3">
                    <div className="admin-metric h-100 d-flex flex-column justify-content-center">
                      <div className="text-muted small mb-1">Wins / Losses</div>
                      <div className="h5 mb-0 fw-bold">
                        <span className="text-success">{stats.wins}</span> / <span className="text-danger">{stats.losses}</span>
                      </div>
                    </div>
                  </div>
                  <div className="col-6 col-md-3">
                    <div className="admin-metric h-100 d-flex flex-column justify-content-center">
                      <div className="text-muted small mb-1">Total PnL</div>
                      <div className={`h5 mb-0 fw-bold ${stats.total_pnl >= 0 ? "text-success" : "text-danger"}`}>
                        {stats.total_pnl >= 0 ? "+" : ""}
                        {stats.total_pnl.toFixed(2)} USDT
                      </div>
                    </div>
                  </div>
                </div>

                <div className="strategy-result-grid mb-4">
                  <div className={`strategy-result-card ${getStrategyTone(stats.strategy_name).className}`}>
                    <div className="strategy-result-card__label">Wins</div>
                    <div className="strategy-result-card__value text-success">{stats.wins}</div>
                    <div className="strategy-result-card__meta">Trades gagnes pour {getStrategyTone(stats.strategy_name).family}</div>
                  </div>
                  <div className={`strategy-result-card ${getStrategyTone(stats.strategy_name).className}`}>
                    <div className="strategy-result-card__label">Fails</div>
                    <div className="strategy-result-card__value text-danger">{stats.losses}</div>
                    <div className="strategy-result-card__meta">Trades perdus pour {getStrategyTone(stats.strategy_name).family}</div>
                  </div>
                  <div className={`strategy-result-card ${getStrategyTone(stats.strategy_name).className}`}>
                    <div className="strategy-result-card__label">Skipped</div>
                    <div className="strategy-result-card__value text-warning">{stats.skipped}</div>
                    <div className="strategy-result-card__meta">Signaux ignores ou rejetes</div>
                  </div>
                </div>

                {stats.open_trades.length > 0 && (
                  <div className="mb-4">
                    <h6 className="fw-bold mb-2 small text-uppercase text-primary">Position Ouverte</h6>
                    {stats.open_trades.map((ot) => (
                      <div key={ot.id} className="admin-open-trade d-flex justify-content-between align-items-center">
                        <div className="fw-bold">{ot.pair}</div>
                        <div className={`badge ${ot.side === "BUY" ? "text-bg-info" : "text-bg-warning"}`}>{ot.side}</div>
                        <div>
                          Entry: <b>{formatPrice(ot.entry)}</b>
                        </div>
                        <div className="text-danger">SL: {formatPrice(ot.sl)}</div>
                        <div className="text-success">TP: {formatPrice(ot.tp)}</div>
                      </div>
                    ))}
                  </div>
                )}

                {stats.recent_trades.length > 0 && (
                  <div>
                    <h6 className="fw-bold mb-2 small text-uppercase text-muted">Historique Recent</h6>
                    <div className="strategy-history-grid">
                      {stats.recent_trades.map((trade) => (
                        <div key={trade.id} className={`strategy-history-card ${getStrategyTone(stats.strategy_name).className}`}>
                          <div className="d-flex justify-content-between align-items-start gap-2">
                            <div>
                              <div className="fw-semibold">{trade.pair}</div>
                              <div className="small text-muted">{trade.side} | {trade.status}</div>
                            </div>
                            <span
                              className={`badge ${
                                trade.result === "WIN"
                                  ? "text-bg-success"
                                  : trade.result === "SKIPPED"
                                    ? "text-bg-warning"
                                    : "text-bg-danger"
                              }`}
                            >
                              {trade.result}
                            </span>
                          </div>
                          <div className="strategy-history-card__metrics">
                            <span>Entry {formatPrice(trade.entry)}</span>
                            <span>Exit {formatPrice(trade.exit)}</span>
                            <span className={trade.pnl >= 0 ? "text-success" : "text-danger"}>
                              PnL {trade.pnl >= 0 ? "+" : ""}{trade.pnl.toFixed(2)}
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default AdminDashboard;
