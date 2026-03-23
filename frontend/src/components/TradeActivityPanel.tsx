import { TradeResponse } from "../types/trading";
import { formatDateTime, formatPrice } from "../utils/format";

interface TradeActivityPanelProps {
  isLoading: boolean;
  error: string | null;
  trades: TradeResponse[];
  statusFilter: string;
  hasAssignments?: boolean;
  lastUpdatedAt?: number | null;
  wasRefreshedByAction?: boolean;
  onRefresh: (status?: string) => Promise<void>;
  onStatusChange: (status: string) => void;
}

const tradeStatuses = ["ALL", "PENDING", "OPEN", "CLOSED", "SKIPPED", "CANCELED"];

const TradeActivityPanel = ({
  isLoading,
  error,
  trades,
  statusFilter,
  hasAssignments = true,
  lastUpdatedAt,
  wasRefreshedByAction = false,
  onRefresh,
  onStatusChange
}: TradeActivityPanelProps) => {
  const filteredCountLabel =
    statusFilter === "ALL" ? `${trades.length} trade(s)` : `${trades.length} ${statusFilter.toLowerCase()}`;

  const emptyLabel =
    !hasAssignments
      ? "Aucun trade pour le moment, car aucun assignment actif n'est disponible."
      : statusFilter === "ALL"
        ? "Aucun trade disponible pour le moment."
        : `Aucun trade pour le filtre ${statusFilter}.`;

  return (
    <div className="trade-panel card h-100">
      <div className="card-body">
        <div className="d-flex flex-wrap align-items-center justify-content-between gap-2 mb-3">
          <div className="panel-heading">
            <span className="panel-heading__eyebrow">Execution ledger</span>
            <h3 className="h6 fw-bold mb-1">Activite trades</h3>
            <p className="text-muted small mb-0">{filteredCountLabel}</p>
            <p className="text-muted small mb-0">Derniere mise a jour: {formatDateTime(lastUpdatedAt)}</p>
            {wasRefreshedByAction && <p className="text-success small mb-0">Rafraichi apres la derniere action.</p>}
          </div>
          <div className="d-flex align-items-center gap-2">
            <select
              className="form-select form-select-sm w-auto trade-filter"
              value={statusFilter}
              onChange={(event) => onStatusChange(event.target.value)}
            >
              {tradeStatuses.map((status) => (
                <option key={status} value={status}>
                  {status}
                </option>
              ))}
            </select>
            <button
              className="btn btn-outline-secondary btn-sm trade-refresh"
              type="button"
              onClick={() => void onRefresh(statusFilter === "ALL" ? undefined : statusFilter)}
              disabled={isLoading}
            >
              {isLoading ? "..." : "Rafraichir"}
            </button>
          </div>
        </div>

        {error && <div className="alert alert-warning py-2 dashboard-alert">{error}</div>}
        {isLoading && trades.length === 0 && <div className="text-muted small mb-3">Chargement des trades...</div>}
        {isLoading && trades.length > 0 && <div className="text-muted small mb-3">Mise a jour de la liste...</div>}

        <div className="trade-list">
          {trades.length === 0 && !isLoading && <div className="text-muted small">{emptyLabel}</div>}
          {trades.map((trade) => (
            <div className="trade-row" key={trade.id}>
              <div className="d-flex align-items-start justify-content-between gap-2">
                <div>
                  <div className="fw-semibold">#{trade.id} | {trade.symbol}</div>
                  <div className="text-muted small">
                    {trade.strategy_name} | {trade.exchange.toUpperCase()} | {trade.side}
                  </div>
                </div>
                <span
                  className={`badge trade-status ${
                    trade.status === "OPEN"
                      ? "text-bg-success"
                      : trade.status === "PENDING"
                        ? "text-bg-warning"
                        : "text-bg-light"
                  }`}
                >
                  {trade.status}
                </span>
              </div>
              <div className="trade-metrics mt-2">
                <span>Entry {formatPrice(trade.entry_price)}</span>
                <span>SL {formatPrice(trade.stop_loss)}</span>
                <span>TP {formatPrice(trade.take_profit)}</span>
                <span>Qty {trade.quantity}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default TradeActivityPanel;
