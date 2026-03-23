import { PairStrategyAssignment } from "../types/trading";
import {
  DashboardActionLogEntry,
  DashboardRefreshTarget
} from "../hooks/tradingDashboard/useTradingDashboardData";
import { AssignmentOverlayResponse, SignalAnalysisResponse, TradeResponse } from "../types/trading";
import { formatDateTime, formatPercent, formatPrice } from "../utils/format";
import Chart from "./Chart";
import ExchangeSelector from "./ExchangeSelector";
import OverlaySummary from "./OverlaySummary";
import SignalActionPanel from "./SignalActionPanel";

interface TradingWorkspacePanelProps {
  selectedCrypto: string;
  selectedAssignmentId: number | null;
  selectedAssignment: PairStrategyAssignment | null;
  assignmentsCount: number;
  price: number;
  change: number;
  isLoading: boolean;
  error: string | null;
  overlayError: string | null;
  isOverlayLoading: boolean;
  isSignalBusy: boolean;
  signalError: string | null;
  signalSuccessMessage?: string | null;
  actionLog?: DashboardActionLogEntry[];
  lastActionRefreshTargets?: DashboardRefreshTarget[];
  lastActionRefreshAt?: number | null;
  lastScan: SignalAnalysisResponse | null;
  lastTrade: TradeResponse | null;
  lastOverlayUpdatedAt?: number | null;
  lastScanAt?: number | null;
  lastExecuteAt?: number | null;
  overlay: AssignmentOverlayResponse | null;
  onScan: () => Promise<void>;
  onExecute: (quantity: number) => Promise<void>;
}

const TradingWorkspacePanel = ({
  selectedCrypto,
  selectedAssignmentId,
  selectedAssignment,
  assignmentsCount,
  price,
  change,
  isLoading,
  error,
  overlayError,
  isOverlayLoading,
  isSignalBusy,
  signalError,
  signalSuccessMessage,
  actionLog,
  lastActionRefreshTargets = [],
  lastActionRefreshAt,
  lastScan,
  lastTrade,
  lastOverlayUpdatedAt,
  lastScanAt,
  lastExecuteAt,
  overlay,
  onScan,
  onExecute
}: TradingWorkspacePanelProps) => {
  const hasActiveAssignment = selectedAssignmentId != null;

  return (
    <div className="workspace-shell">
      <div className="workspace-header mb-4">
        <div>
          <div className="workspace-header__eyebrow">Marche actif</div>
          <h2 className="workspace-header__title mb-1">{selectedCrypto}</h2>
          <span className="workspace-header__meta">
            {selectedAssignmentId ? `Assignment #${selectedAssignmentId}` : "Aucun assignment"}
          </span>
          {selectedAssignment && (
            <div className="workspace-assignment-meta">
              <span className="workspace-assignment-chip">{selectedAssignment.strategy_name}</span>
              <span className="workspace-assignment-chip">
                {selectedAssignment.htf}/{selectedAssignment.ltf}
              </span>
            </div>
          )}
        </div>
        <div className="workspace-price text-end">
          <div className="workspace-price__value">${formatPrice(price)}</div>
          <small className={change >= 0 ? "workspace-price__delta is-up" : "workspace-price__delta is-down"}>
            {formatPercent(change)}
          </small>
        </div>
      </div>

      <div className="workspace-toolbar mb-3">
        <ExchangeSelector />
        <span className="workspace-toolbar__stat">Assignments charges: {assignmentsCount}</span>
      </div>

      {!hasActiveAssignment && (
        <div className="alert alert-info py-2 mb-3 dashboard-alert">
          Aucun assignment selectionne. Choisis un assignment dans la sidebar pour charger les overlays, scanner un
          signal et preparer une execution.
        </div>
      )}
      {isLoading && <div className="workspace-status mb-2">Chargement des donnees...</div>}
      {error && <div className="alert alert-warning py-2 mb-2 dashboard-alert">{error}</div>}
      {overlayError && <div className="alert alert-secondary py-2 mb-2 dashboard-alert">{overlayError}</div>}
      {isOverlayLoading && !overlayError && <div className="workspace-status mb-2">Rafraichissement de l'overlay...</div>}

      {lastActionRefreshTargets.length > 0 && (
        <div className="sync-banner mb-3">
          <div className="small fw-semibold mb-1">Blocs resynchronises apres la derniere action</div>
          <div className="d-flex flex-wrap gap-2 mb-1">
            {lastActionRefreshTargets.map((target) => (
              <span key={target} className="sync-banner__chip">
                {target}
              </span>
            ))}
          </div>
          <div className="text-muted small">Mis a jour: {formatDateTime(lastActionRefreshAt)}</div>
        </div>
      )}

      <Chart />
      <SignalActionPanel
        isBusy={isSignalBusy}
        error={signalError}
        successMessage={signalSuccessMessage}
        hasActiveAssignment={hasActiveAssignment}
        actionLog={actionLog}
        lastScan={lastScan}
        lastTrade={lastTrade}
        lastScanAt={lastScanAt}
        lastExecuteAt={lastExecuteAt}
        onScan={onScan}
        onExecute={onExecute}
      />
      <div className="workspace-status mt-3">Overlay synchronise: {formatDateTime(lastOverlayUpdatedAt)}</div>
      <OverlaySummary overlay={overlay} isLoading={isOverlayLoading} error={overlayError} />
    </div>
  );
};

export default TradingWorkspacePanel;
