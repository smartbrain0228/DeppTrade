import { UserOverview } from "../types/trading";
import { formatDateTime, formatPrice } from "../utils/format";

interface OverviewPanelProps {
  isLoading: boolean;
  error: string | null;
  overview: UserOverview | null;
  lastUpdatedAt?: number | null;
  wasRefreshedByAction?: boolean;
  onRefresh: () => Promise<void>;
}

const OverviewPanel = ({
  isLoading,
  error,
  overview,
  lastUpdatedAt,
  wasRefreshedByAction = false,
  onRefresh
}: OverviewPanelProps) => {
  const isEmpty = !overview && !error;
  const runtime = overview?.runtime;

  return (
    <div className="overview-panel card">
      <div className="card-body">
        <div className="d-flex align-items-center justify-content-between gap-2 mb-3">
          <div className="panel-heading">
            <span className="panel-heading__eyebrow">User pulse</span>
            <h3 className="h6 fw-bold mb-1">Overview</h3>
            <p className="text-muted small mb-0">Synthese rapide du compte utilisateur.</p>
            <p className="text-muted small mb-0">Derniere mise a jour: {formatDateTime(lastUpdatedAt)}</p>
            {wasRefreshedByAction && <p className="text-success small mb-0">Rafraichi apres la derniere action.</p>}
          </div>
          <button className="btn btn-outline-secondary btn-sm trade-refresh" type="button" onClick={() => void onRefresh()} disabled={isLoading}>
            {isLoading ? "..." : "Rafraichir"}
          </button>
        </div>

        {error && <div className="alert alert-warning py-2 dashboard-alert">{error}</div>}
        {isLoading && isEmpty && <div className="text-muted small mb-3">Chargement de l'overview...</div>}
        {isEmpty && !isLoading && <div className="text-muted small">Aucune donnee d'overview disponible.</div>}

        {overview && (
          <>
            <div className="row g-3 mb-3">
              <div className="col-6">
                <div className="overview-metric">
                  <div className="overview-label">Open trades</div>
                  <div className="overview-value">{overview.open_trades_count}</div>
                </div>
              </div>
              <div className="col-6">
                <div className="overview-metric">
                  <div className="overview-label">Closed trades</div>
                  <div className="overview-value">{overview.closed_trades_count}</div>
                </div>
              </div>
              <div className="col-6">
                <div className="overview-metric">
                  <div className="overview-label">Closed PnL</div>
                  <div className="overview-value">${formatPrice(overview.closed_pnl ?? 0)}</div>
                </div>
              </div>
              <div className="col-6">
                <div className="overview-metric">
                  <div className="overview-label">Active risk</div>
                  <div className="overview-value">{overview.active_risk_pct.toFixed(2)}%</div>
                  <div className="overview-subtext">Max {overview.max_total_active_risk_pct.toFixed(2)}%</div>
                </div>
              </div>
            </div>

            {isLoading && <div className="text-muted small mb-3">Mise a jour de l'overview...</div>}

            <div className="overview-section mb-3">
              <div className="overview-label mb-2">Runtime</div>
              <div className="overview-runtime-grid mb-3">
                <div className="overview-runtime-card">
                  <div className="overview-label">Environnement</div>
                  <div className="overview-value">{runtime?.app_env ?? "n/a"}</div>
                  <div className="overview-subtext">Market: {runtime?.market_data_mode ?? "n/a"}</div>
                </div>
                <div className="overview-runtime-card">
                  <div className="overview-label">Services</div>
                  <div className="d-flex flex-wrap gap-2 mt-2">
                    <span className={`runtime-chip ${runtime?.worker_enabled ? "is-on" : "is-off"}`}>
                      Worker {runtime?.worker_enabled ? "ON" : "OFF"}
                    </span>
                    <span className={`runtime-chip ${runtime?.demo_engine_enabled ? "is-on" : "is-off"}`}>
                      Demo {runtime?.demo_engine_enabled ? "ON" : "OFF"}
                    </span>
                    <span className={`runtime-chip ${runtime?.telegram_configured ? "is-on" : "is-off"}`}>
                      Telegram {runtime?.telegram_configured ? "OK" : "OFF"}
                    </span>
                  </div>
                </div>
              </div>
              <div className="overview-label mb-2">Paires actives</div>
              <div className="d-flex flex-wrap gap-2">
                {overview.active_pairs.length === 0 && <span className="text-muted small">Aucune paire active.</span>}
                {overview.active_pairs.map((pair) => (
                  <span className="overview-chip" key={`${pair.exchange}-${pair.symbol}`}>
                    {pair.symbol} | {pair.exchange.toUpperCase()}
                  </span>
                ))}
              </div>
            </div>

            <div className="overview-section">
              <div className="overview-label mb-2">Trades recents</div>
              <div className="overview-recent-list">
                {overview.recent_trades.length === 0 && <div className="text-muted small">Aucun trade recent.</div>}
                {overview.recent_trades.slice(0, 4).map((trade) => (
                  <div className="overview-recent-row" key={trade.trade_id}>
                    <div className="fw-semibold small">#{trade.trade_id} | {trade.symbol}</div>
                    <div className="text-muted small">{trade.tag} | {trade.side} | {trade.status} | {trade.exchange.toUpperCase()}</div>
                  </div>
                ))}
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
};

export default OverviewPanel;
